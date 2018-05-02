"""Utils for ui app"""
import logging
import os
from collections import namedtuple
from functools import lru_cache
import json
import random
import re

import boto3
from django.conf import settings
from django.core.cache import caches

from mit_moira import Moira
from googleapiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials

from ui.exceptions import MoiraException, GoogleAnalyticsException

log = logging.getLogger(__name__)

MoiraUser = namedtuple('MoiraUser', 'username type')
MOIRA_CACHE_KEY = 'moira_lists_{user_id}'
cache = caches['redis']


class UserMoiraMembership:
    """
    Simple class for storing which lists a user is and isn't a member of
    """
    member_of = set()
    not_member_of = set()

    def __init__(self, member_of=None, not_member_of=None):
        if member_of:
            self.member_of = set(member_of)
        if not_member_of:
            self.not_member_of = set(not_member_of)


@lru_cache(1)  # memoize this function
def get_moira_client():
    """
    Gets a moira client.

    Returns:
        Moira: A moira client
    """

    _check_files_exist([settings.MIT_WS_CERTIFICATE_FILE,
                        settings.MIT_WS_PRIVATE_KEY_FILE])
    try:
        return Moira(settings.MIT_WS_CERTIFICATE_FILE, settings.MIT_WS_PRIVATE_KEY_FILE)
    except Exception as exc:  # pylint: disable=broad-except
        raise MoiraException('Something went wrong with creating a moira client') from exc


def _check_files_exist(paths):
    """Checks that files exist at given paths."""
    errors = []
    for path in paths:
        if not os.path.isfile(path):
            errors.append("File missing: expected path '{}'".format(path))
    if errors:
        raise RuntimeError('\n'.join(errors))


def get_moira_user(user):
    """
    Return the most likely username & type (USER, STRING) for a user in moira lists based on email.
    If the email ends with 'mit.edu', assume kerberos id = email prefix
    Otherwise use the entire email address as the username.

    Args:
        user (django.contrib.auth.User): the Django user to return a Moira user for.

    Returns:
        MoiraUser: A namedtuple containing username and type
    """
    if re.search(r'(@|\.)mit.edu$', user.email):
        return MoiraUser(user.email.split('@')[0], 'USER')
    return MoiraUser(user.email, 'STRING')


def set_moira_cache(user, membership):
    """
    Set the user's moira lists cache

    Args:
        user (django.contrib.auth.User): the Django user to return a Moira user for.
        membership (UserMoiraMembership): object specifying which lists a member is or isn't on.
    """
    cache.set(MOIRA_CACHE_KEY.format(user_id=user.id), membership, settings.MOIRA_CACHE_TIMEOUT)


def delete_moira_cache(user):
    """
    Delete the user's moira list cache

    Args:
        user (django.contrib.auth.User): the Django user to return a Moira user for.
    """
    cache.delete(MOIRA_CACHE_KEY.format(user_id=user.id))


def query_moira_lists(user):
    """
    Get a UserMoiraMembership object with all the moira lists a user has access to, by querying the Moira service.

    Args:
        user (django.contrib.auth.User): the Django user.

    Returns:
        UserMoiraMembership: A list of moira lists the user has access to.
    """
    moira_user = get_moira_user(user)
    moira = get_moira_client()
    try:
        membership = UserMoiraMembership(member_of=moira.user_lists(moira_user.username, moira_user.type))
        set_moira_cache(user, membership)
        return membership
    except Exception as exc:  # pylint: disable=broad-except
        if 'java.lang.NullPointerException' in str(exc):
            # User is not a member of any moira lists, so ignore exception and return empty list
            membership = UserMoiraMembership()
            set_moira_cache(user, membership)
            return membership
        raise MoiraException('Something went wrong with getting moira-lists for %s' % user.username) from exc


def user_moira_lists(user):
    """
    Get a list of all the moira lists a user has access to, from the cache if it exists,
    otherwise query Moira service and create the cache.

    Args:
        user (django.contrib.auth.User): the Django user.

    Returns:
        UserMoiraMembership: An object containing all known lists the user does & doesn't have access to.
    """
    return cache.get(MOIRA_CACHE_KEY.format(user_id=user.id)) or query_moira_lists(user)


def has_common_lists(user, list_names):
    """
    Return true if the user is a member of any of the supplied moira list names, false otherwise.
    Updates the user's moira cache if necessary.

    Returns:
        bool: True if there is any name in list_names which is in the user's moira lists
    """
    if user.is_anonymous:
        return False
    user_lists = user_moira_lists(user)
    if set(user_lists.member_of.intersection(list_names)):
        return True
    unmatched_lists = set([l for l in list_names if l not in user_lists.not_member_of | user_lists.member_of])
    moira_user = get_moira_user(user)
    client = get_moira_client()
    for moiralist in unmatched_lists:
        try:
            members = set(client.list_members(moiralist, type=''))
            if moira_user.username in members:
                user_lists.member_of.add(moiralist)
                set_moira_cache(user, user_lists)
                return True
            else:
                user_lists.not_member_of.add(moiralist)
        except Exception as exc:
            raise MoiraException('Something went wrong with getting moira-list members: %s', moiralist) from exc
    set_moira_cache(user, user_lists)
    return False


def get_et_job(job_id):
    """
    Get the status of an ElasticTranscode job

    Args:
        job_id (str): ID of ElasticTranscode Job

    Returns:
        dict: JSON representation of job status/details
    """
    et = get_transcoder_client()
    job = et.read_job(Id=job_id)
    return job['Job']


def get_et_preset(preset_id):
    """
    Get the JSON configuration of an ElasticTranscode preset
    Args:
        preset_id (str): A preset id

    Returns:
        dict: Preset configuration
    """
    et = get_transcoder_client()
    return et.read_preset(Id=preset_id)['Preset']


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


def get_transcoder_client():
    """
    Get an ElasticTranscoder client object

    Returns:
        botocore.client.ElasticTranscoder:
            An ElasticTranscoder client object
    """
    return boto3.client('elastictranscoder', settings.AWS_REGION)


def write_to_file(filename, contents):
    """
    Write content to a file in binary mode, creating directories if necessary

    Args:
        filename (str): The full-path filename to write to.
        contents (bytes): What to write to the file.

    """
    if not os.path.exists(os.path.dirname(filename)):
        os.makedirs(os.path.dirname(filename))
    with open(filename, 'wb') as infile:
        infile.write(contents)


def write_x509_files():
    """Write the x509 certificate and key to files"""
    write_to_file(settings.MIT_WS_CERTIFICATE_FILE, settings.MIT_WS_CERTIFICATE)
    write_to_file(settings.MIT_WS_PRIVATE_KEY_FILE, settings.MIT_WS_PRIVATE_KEY)


def get_video_analytics(video):
    """Get video analytics data from Google Analytics."""
    ga_client = get_google_analytics_client()
    ga_response = ga_client.reports().batchGet(
        body=generate_google_analytics_query(video)).execute()
    try:
        return parse_google_analytics_response(ga_response)
    except Exception as exc:
        raise GoogleAnalyticsException(
            'Could not parse analytics response') from exc


def get_google_analytics_client():
    """Gets a Google Analytics client.

    Returns:
        analytics_client: An analytics client
    """
    try:
        credentials = ServiceAccountCredentials.from_json_keyfile_dict(
            json.loads(settings.GA_KEYFILE_JSON))
        analytics_client = build('analyticsreporting', 'v4',
                                 credentials=credentials)
        return analytics_client
    except Exception as exc:  # pylint: disable=broad-except
        raise GoogleAnalyticsException('Something went wrong with creating a'
                                       'GoogleAnaltics client') from exc


def generate_google_analytics_query(video):
    """Generates a Google Analytics query.

    Returns:
        analytics_query: a query dict suitable to use as the body of an
        analytics 'batchGet' request.
    """
    # https://developers.google.com/analytics/devguides/reporting/core/v3/reference
    START_DATE = '2005-01-01'
    END_DATE = '9999-01-01'
    dimensions = [{'name': 'ga:eventAction'}]
    if video.multiangle:
        # [adorsk, 2018-03]
        # Achtung! Only use the camera angle dimension for multiangle.
        # Single-camera videos do not set a custom dimension for events
        # sent to GoogleAnalytics.
        dimensions.append({'name': 'ga:' + settings.GA_DIMENSION_CAMERA})
    query = {
        'reportRequests': [
            {
                'viewId': settings.GA_VIEW_ID,
                'dateRanges': [{'startDate': START_DATE, 'endDate': END_DATE}],
                'metrics': [{'expression': 'ga:totalEvents'}],
                'dimensions': dimensions,
                'dimensionFilterClauses': [
                    {
                        'filters': [
                            {
                                'dimensionName': 'ga:eventLabel',
                                'operator': 'EXACT',
                                # 2018-03, dorsk
                                # Achtung! We do video.hexkey.capitalize()
                                # because GA has capitalized event data,
                                # due to an unexpected side-effect of the
                                # react-ga library.
                                # See: https://github.com/mitodl/odl-video-service/pull/472
                                'expressions': [video.hexkey.capitalize()]
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
    report = ga_response['reports'][0]
    # Check dimensions,
    # to account for singlecam/multicam query differences.
    dimensions = report['columnHeader']['dimensions']
    is_multichannel = len(dimensions) == 2
    rows = report['data'].get('rows', [])
    for row in rows:
        m = re.match(r'T(\d{4})', row['dimensions'][0])
        if not m:
            continue
        time_ = int(m.group(1))
        if is_multichannel:
            channel = row['dimensions'][1]
        else:
            channel = 'views'
        viewers = int(row['metrics'][0]['values'][0])
        views_at_times.setdefault(time_, {}).update({channel: viewers})
        times.add(time_)
        channels.add(channel)
    return {
        'times': sorted(list(times)),
        'channels': sorted(list(channels)),
        'is_multichannel': is_multichannel,
        'views_at_times': views_at_times,
    }


def generate_mock_video_analytics_data(n=24, seed=42):
    """Generate a mock analytics response.

    This can be useful for doing integration tests with the frontend.
    """
    local_random = random.Random(seed)
    times = [i for i in range(int(n))]
    channels = ['camera%s' % (i + 1) for i in range(4)]
    views_at_times = {
        t: {
            channel: local_random.randint(0, 100)
            for channel in channels
        }
        for t in times
    }
    return {
        'times': sorted(list(times)),
        'channels': sorted(list(channels)),
        'views_at_times': views_at_times,
    }
