"""Utils for ui app"""

import datetime
import itertools
from urllib.parse import urljoin

import boto3
import pytz
import requests
import structlog

from ui.keycloak_utils import get_keycloak_client

log = structlog.get_logger(__name__)


def query_user_groups(email: str) -> list[str]:
    """
    Get a list of all groups a user is a member of.

    Args:
        email (str): The email to query groups for.

    Returns:
        Set[str]: A set of names of groups which contain the user as a member.
    """
    client = get_keycloak_client()
    return list(set(client.get_user_groups(email)))


def _groups_from_social_auth(user) -> set[str] | None:
    """Return the user's group names cached in their Keycloak social-auth record.

    The Keycloak ``GroupMembershipProtocolMapper`` (``full_path=True``) stores
    values like ``/some-moira-list`` or ``/parent/child`` in the ``user_groups``
    token claim.  We normalise these to bare leaf names (e.g. ``some-moira-list``,
    ``child``) so they match ``KeycloakGroup.name`` values in the OVS database.

    **Freshness note**: these groups reflect the user's Keycloak membership at
    their *last login*.  Keycloak group changes take effect on the user's next
    authentication.  If immediate revocation is required, remove this cache and
    rely solely on ``query_user_groups`` (live Keycloak admin API).

    Returns ``None`` when the cached value is absent or unusable, signalling
    that the caller should fall back to a live API query.
    """
    from social_django.models import UserSocialAuth

    try:
        social = UserSocialAuth.objects.get(user=user, provider="keycloak")
    except UserSocialAuth.DoesNotExist:
        return None

    raw = social.extra_data.get("user_groups") if social.extra_data else None
    if not isinstance(raw, list):
        return None

    groups: set[str] = set()
    for entry in raw:
        if not isinstance(entry, str):
            continue
        # Take the last non-empty segment of the path so that both
        # "/leaf" and "/parent/child" resolve to a bare group name.
        leaf = entry.rstrip("/").rsplit("/", 1)[-1]
        if leaf:
            groups.add(leaf)
    return groups if groups else None


def user_groups(user) -> set[str]:
    """
    Return the set of Keycloak group names the user belongs to.

    Reads group membership from the cached ``user_groups`` claim stored in the
    user's Keycloak social-auth ``extra_data`` record (populated at login).
    Falls back to a live Keycloak admin API query when the cache is absent or
    unusable (e.g. for users not authenticated via Keycloak OIDC).

    Args:
        user (django.contrib.auth.User): the Django user.

    Returns:
        Set[str]: A set containing the bare group names the user belongs to.
    """
    if user.is_anonymous:
        return set()

    # Per-request memoisation: avoid repeated DB (or API) lookups within the
    # same request when multiple permission checks run for the same user.
    if hasattr(user, "_keycloak_groups_cache"):
        return user._keycloak_groups_cache

    cached = _groups_from_social_auth(user)
    if cached is not None:
        user._keycloak_groups_cache = cached
        return cached

    groups = set(query_user_groups(user.email))
    user._keycloak_groups_cache = groups
    return groups


def group_members(group_name: str) -> list[dict]:
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
    email = user.email or user.username
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
    stripped_url_parts = (part.strip("/") for part in url_parts)
    url_path = "/".join(stripped_url_parts)
    if add_trailing_slash or (url_parts and url_parts[-1].endswith("/")):
        url_path = f"{url_path}/"
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
