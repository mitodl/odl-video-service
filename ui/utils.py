"""Utils for ui app"""

import datetime
import itertools
import json
import random
import re
from typing import List, Dict, Set
from urllib.parse import urljoin

import boto3
import pytz
import requests
from django.conf import settings
from google.oauth2.service_account import (
    Credentials as ServiceAccountCredentials,
)
from googleapiclient.discovery import build

from odl_video import logging
from ui.exceptions import GoogleAnalyticsException

from ui.keycloak_utils import get_keycloak_client

log = logging.getLogger(__name__)


def query_user_groups(email: str) -> List[str]:
    """
    Get a list of all groups a user is a member of.

    Args:
        email (str): The email to query groups for.

    Returns:
        Set[str]: A set of names of groups which contain the user as a member.
    """
    client = get_keycloak_client()
    return list(set(client.get_user_groups(email)))


def user_groups(user) -> Set[str]:
    """
    Get a list of all the groups a user has access to.

    Args:
        user (django.contrib.auth.User): the Django user.

    Returns:
        Set[str]: A set containing all groups the user belongs to.
    """
    if user.is_anonymous:
        return set()

    return set(query_user_groups(user.email))


def group_members(group_name: str) -> List[Dict]:
    """
    Get a list of all users in a given group

    Args:
        group_name (str): name of the group.

    Returns:
        List[Dict]: A list of users as dictionaries
    """
    client = get_keycloak_client()
    return client.get_group_members_by_name(group_name)


def has_common_groups(user, group_names) -> bool:
    """
    Return true if the user is a member of any of the supplied group names, false otherwise.

    Returns:
        bool: True if there is any name in group_names which is in the user's groups
    """
    if user.is_anonymous:
        return False

    user_group_list = user_groups(user)
    return not user_group_list.isdisjoint(group_names)


def query_lists(user):
    """
    Get a list of all groups a user has access to by querying the Keycloak service.

    Args:
        user (django.contrib.auth.User): the Django user.

    Returns:
        List[str]: A list of names of groups which contain the user as a member.
    """
    email = user.username
    if "@" not in email:
        email = f"{email}@mit.edu"
    return query_user_groups(email)


def user_lists(user):
    """
    Get a set of all the groups a user has access to, from the cache if it exists,
    otherwise query Keycloak service and create the cache.

    Args:
        user (django.contrib.auth.User): the Django user.

    Returns:
        Set[str]: A set containing all known groups the user belongs to.
    """
    return user_groups(user)


def list_members(group_name):
    """
    Get a list of all users in a given group

    Args:
        group_name (str): name of the group.

    Returns:
        list_users(list): A list of users
    """
    return group_members(group_name)


def has_common_lists(user, list_names):
    """
    Return true if the user is a member of any of the supplied group names, false otherwise.

    Returns:
        bool: True if there is any name in list_names which is in the user's groups
    """
    return has_common_groups(user, list_names)


def get_bucket(bucket_name):
    """
    Get an S3 bucket by name

    Args:
        bucket_name (str): The name of an S3 bucket

    Returns:
        boto.s3.bucket.Bucket: An S3 bucket
    """
    s3 = boto3.resource("s3")
    return s3.Bucket(bucket_name)


def get_video_analytics(video):
    """Get video analytics data from Google Analytics."""
    ga_client = get_google_analytics_client()
    ga_response = (
        ga_client.reports()
        .batchGet(body=generate_google_analytics_query(video))
        .execute()
    )
    try:
        return parse_google_analytics_response(ga_response)
    except Exception as exc:
        raise GoogleAnalyticsException("Could not parse analytics response") from exc


def get_google_analytics_client():
    """Gets a Google Analytics client.

    Returns:
        analytics_client: An analytics client
    """
    try:
        credentials = ServiceAccountCredentials.from_service_account_info(
            json.loads(settings.GA_KEYFILE_JSON)
        )
        analytics_client = build("analyticsreporting", "v4", credentials=credentials)
        return analytics_client
    except Exception as exc:
        raise GoogleAnalyticsException(
            "Something went wrong with creating a GoogleAnalytics client"
        ) from exc


def generate_google_analytics_query(video):
    """Generates a Google Analytics query.

    Returns:
        analytics_query: a query dict suitable to use as the body of an
        analytics 'batchGet' request.
    """
    # https://developers.google.com/analytics/devguides/reporting/core/v3/reference
    START_DATE = "2005-01-01"
    END_DATE = "9999-01-01"
    dimensions = [{"name": "ga:eventAction"}]
    if video.multiangle:
        # [adorsk, 2018-03]
        # Achtung! Only use the camera angle dimension for multiangle.
        # Single-camera videos do not set a custom dimension for events
        # sent to GoogleAnalytics.
        dimensions.append({"name": "ga:" + settings.GA_DIMENSION_CAMERA})
    query = {
        "reportRequests": [
            {
                "viewId": settings.GA_VIEW_ID,
                "dateRanges": [{"startDate": START_DATE, "endDate": END_DATE}],
                "metrics": [{"expression": "ga:totalEvents"}],
                "dimensions": dimensions,
                "dimensionFilterClauses": [
                    {
                        "filters": [
                            {
                                "dimensionName": "ga:eventLabel",
                                "operator": "EXACT",
                                # 2018-03, dorsk
                                # Achtung! We do video.hexkey.capitalize()
                                # because GA has capitalized event data,
                                # due to an unexpected side-effect of the
                                # react-ga library.
                                # See: https://github.com/mitodl/odl-video-service/pull/472
                                "expressions": [video.hexkey.capitalize()],
                            },
                        ],
                    }
                ],
            },
        ],
    }
    return query


def parse_google_analytics_response(ga_response):
    """Parse a Google Analytics response.

    Returns:
        data: a dict of parsed response data, in this shape:
            {
                'times': [0, ..., N], # list of all times
                'channels': ['camera0', ..., 'cameraN'], # list of all channels
                'views_at_times': {
                    0: {
                        'camera0': 23,
                        'camera1': 3,
                        ...
                        <cameraN>: <X>
                    },
                    ...
                    <timeN>: <views_per_channel_at_timeN>
                },
            }
    """
    times = set()
    channels = set()
    views_at_times = {}
    report = ga_response["reports"][0]
    # Check dimensions,
    # to account for singlecam/multicam query differences.
    dimensions = report["columnHeader"]["dimensions"]
    is_multichannel = len(dimensions) == 2
    rows = report["data"].get("rows", [])
    for row in rows:
        m = re.match(r"T(\d{4})", row["dimensions"][0])
        if not m:
            continue
        time_ = int(m.group(1))
        if is_multichannel:
            channel = row["dimensions"][1]
        else:
            channel = "views"
        if re.match(r"camera\d+|views", channel):
            viewers = int(row["metrics"][0]["values"][0])
            views_at_times.setdefault(time_, {}).update({channel: viewers})
            times.add(time_)
            channels.add(channel)
    return {
        "times": sorted(list(times)),
        "channels": sorted(list(channels)),
        "is_multichannel": is_multichannel,
        "views_at_times": views_at_times,
    }


def generate_mock_video_analytics_data(n=24, seed=42):
    """Generate a mock analytics response.

    This can be useful for doing integration tests with the frontend.
    """
    local_random = random.Random(seed)
    times = list(range(int(n)))
    channels = ["camera%s" % (i + 1) for i in range(4)]
    views_at_times = {
        t: {channel: local_random.randint(0, 100) for channel in channels}
        for t in times
    }
    return {
        "times": sorted(list(times)),
        "channels": sorted(list(channels)),
        "views_at_times": views_at_times,
    }


def multi_urljoin(url_base, *url_parts, add_trailing_slash=False):
    """
    Takes a base URL and any number of strings that make up the URL path and returns a valid slash-separated URL

    Args:
         url_base (str): The base of the URL, e.g.: "http://example.com"
         url_parts (str): Strings that make up the URL path (e.g.: "api/v1/" "/my-resource/" "1")
         add_trailing_slash (bool): If True, adds a trailing slash to the URL if the last part of the URL path did
            not already have a trailing slash.

    Returns:
        str: Valid slash-separated URL
    """
    stripped_url_parts = map(lambda part: part.strip("/"), url_parts)
    url_path = "/".join(stripped_url_parts)
    if add_trailing_slash or (url_parts and url_parts[-1].endswith("/")):
        url_path = "".join((url_path, "/"))
    return urljoin(url_base, url_path)


def partition(items, predicate=bool):
    """
    Partitions an iterable into two different iterables - the first does not match the given condition, and the second
    does match the given condition.

    Args:
        items (iterable): An iterable of items to partition
        predicate (function): A function that takes each item and returns True or False
    Returns:
        tuple of iterables: An iterable of non-matching items, paired with an iterable of matching items
    """
    a, b = itertools.tee((predicate(item), item) for item in items)
    return (item for pred, item in a if not pred), (item for pred, item in b if pred)


def partition_to_lists(items, predicate=bool):
    """
    Partitions an iterable into two different lists - the first does not match the given condition, and the second
    does match the given condition.

    Args:
        items (iterable): An iterable of items to partition
        predicate (function): A function that takes each item and returns True or False
    Returns:
        tuple of lists: A list of non-matching items, paired with a list of matching items
    """
    a, b = partition(items, predicate=predicate)
    return list(a), list(b)


def get_error_response_summary_dict(response):
    """
    Returns a summary of an error raised from a failed HTTP request using the requests library

    Args:
        response (requests.models.Response): The requests library response object

    Returns:
        dict: A summary of the error response
    """
    # If the response is an HTML document, include the URL in the summary but not the raw HTML
    if "text/html" in response.headers.get("Content-Type", ""):
        summary_dict = {"content": "(HTML body ignored)"}
    else:
        summary_dict = {"content": response.text}
    return {"code": response.status_code, "url": response.url, **summary_dict}


def now_in_utc():
    """
    Get the current time in UTC

    Returns:
        datetime.datetime: A datetime object for the current time
    """
    return datetime.datetime.now(tz=pytz.UTC)


def send_refresh_request(base_api_url, client_id, client_secret):
    """
    Send a request to edx for a new JWT access token

    Args:
        base_api_url (str): edx base url
        client_id (str): edx client id
        client_secret (str): edx client secret
    Returns:
        resp: response from edx with the new access token
    """
    access_token_url = urljoin(base_api_url, "/oauth2/access_token/")
    data = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "token_type": "JWT",
    }

    resp = requests.post(access_token_url, data=data)

    resp.raise_for_status()
    return resp.json()
