"""Utils for ui app"""
import logging
import os
from collections import namedtuple
from functools import lru_cache

import re
import boto3
from django.conf import settings

from mit_moira import Moira

from ui.exceptions import MoiraException

log = logging.getLogger(__name__)

MoiraUser = namedtuple('MoiraUser', 'username type')


@lru_cache(1)  # memoize this function
def get_moira_client():
    """
    Gets a moira client.

    Returns:
        Moira: A moira client
    """
    errors = []
    for required_secret_file in [settings.MIT_WS_CERTIFICATE_FILE, settings.MIT_WS_PRIVATE_KEY_FILE]:
        if not os.path.isfile(required_secret_file):
            errors.append(
                "Missing required secret: {}".format(required_secret_file)
            )
    if errors:
        raise RuntimeError('\n'.join(errors))
    try:
        return Moira(settings.MIT_WS_CERTIFICATE_FILE, settings.MIT_WS_PRIVATE_KEY_FILE)
    except Exception as exc:  # pylint: disable=broad-except
        raise MoiraException('Something went wrong with creating a moira client') from exc


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


def user_moira_lists(user):
    """
    Get a list of all the moira lists a user has access to.

    Args:
        user (django.contrib.auth.User): the Django user.

    Returns:
        list: A list of moira lists the user has access to.
    """
    moira_user = get_moira_user(user)
    moira = get_moira_client()
    try:
        return moira.user_lists(moira_user.username, moira_user.type)
    except Exception as exc:  # pylint: disable=broad-except
        if 'java.lang.NullPointerException' in str(exc):
            # User is not a member of any moira lists, so ignore exception and return empty list
            return []
        raise MoiraException('Something went wrong with getting moira-lists for %s' % user.username) from exc


def has_common_lists(user, list_names):
    """
    Return true if the user is a member of any of the supplied moira list names

    Returns:
        bool: True if there is any name in list_names which is in the user's moira lists
    """
    if user.is_anonymous:
        return False
    moira_user = get_moira_user(user)
    client = get_moira_client()
    for moiralist in list_names:
        try:
            members = set(client.list_members(moiralist, type=''))
            if moira_user.username in members:
                return True
        except Exception as exc:
            raise MoiraException('Something went wrong with getting moira-list members: %s', moiralist) from exc
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
