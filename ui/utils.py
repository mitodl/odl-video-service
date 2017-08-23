"""Utils for ui app"""
import logging
import os
from collections import namedtuple
from datetime import datetime, timedelta
from functools import lru_cache
from urllib.parse import quote

import re
from pytz import UTC
import boto3
from django.conf import settings

from django.utils.dateparse import parse_datetime, parse_duration
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from botocore.signers import CloudFrontSigner
from mit_moira import Moira

log = logging.getLogger(__name__)

MoiraUser = namedtuple('MoiraUser', 'username type')


@lru_cache(1)  # memoize this function
def get_moira_client():
    """
    Gets a moira client.
    """
    errors = []
    for required_secret_file in [settings.MIT_WS_CERTIFICATE_FILE, settings.MIT_WS_PRIVATE_KEY_FILE]:
        if not os.path.isfile(required_secret_file):
            errors.append(
                "Missing required secret: {}".format(required_secret_file)
            )
    if errors:
        raise RuntimeError('\n'.join(errors))
    return Moira(settings.MIT_WS_CERTIFICATE_FILE, settings.MIT_WS_PRIVATE_KEY_FILE)


def get_moira_user(user):
    """
    Return the most likely username & type (USER, STRING) for a user in moira lists based on email.
    If the email ends with 'mit.edu', assume kerberos id = email prefix
    Otherwise use the entire email address as the username.

    Args:
        user (django.contrib.auth.User): the Django user to return a Moira user for.

    Returns:
        A namedtuple containing username and type

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
        A list of moira lists the user has access to.
    """
    moira_user = get_moira_user(user)
    try:
        moira = get_moira_client()
        return moira.user_lists(moira_user.username, moira_user.type)
    except Exception as exc:  # pylint: disable=broad-except
        log.exception('Something went wrong with the moira client: %s', str(exc))
        return []


# http://boto3.readthedocs.io/en/stable/reference/services/cloudfront.html#generate-a-signed-url-for-amazon-cloudfront

def rsa_signer(message):
    """
    Create an RSA signature for use in a signed URL

    Args:
        message(bytes): The message to be signed

    Returns:
        RSA signer
    """
    if not settings.CLOUDFRONT_PRIVATE_KEY:
        raise RuntimeError("Missing required cloudfront key secret")
    private_key = serialization.load_pem_private_key(
        settings.CLOUDFRONT_PRIVATE_KEY,
        password=None,
        backend=default_backend()
    )
    signer = private_key.signer(padding.PKCS1v15(), hashes.SHA1())
    signer.update(message)
    return signer.finalize()


def get_cloudfront_signed_url(s3_key, expires):
    """
    Given an object key in S3, returns a signed URL to access that S3 object
    from CloudFront.
    """
    if not expires > datetime.now(tz=UTC):
        raise ValueError("Not useful to generate a signed URL that has already expired")

    if not settings.CLOUDFRONT_KEY_ID:
        raise RuntimeError("Missing required env var: CLOUDFRONT_KEY_ID")
    if not settings.VIDEO_CLOUDFRONT_DIST:
        raise RuntimeError("Missing required env var: VIDEO_CLOUDFRONT_DIST")
    url = "https://{dist}.cloudfront.net/{s3_key}".format(
        dist=settings.VIDEO_CLOUDFRONT_DIST,
        s3_key=quote(s3_key)
    )
    cloudfront_signer = CloudFrontSigner(settings.CLOUDFRONT_KEY_ID, rsa_signer)
    signed_url = cloudfront_signer.generate_presigned_url(url, date_less_than=expires)
    return signed_url


def get_expiration(query_params, default_duration=timedelta(hours=2)):
    """
    Try to get an expiration time from query params
    """
    expires = query_params.get("expires")
    if expires:
        parsed = parse_datetime(expires)
        if parsed:
            return parsed
    duration = query_params.get("duration")
    if duration:
        parsed = parse_duration(duration)
        if parsed:
            return datetime.utcnow() + parsed

    return datetime.utcnow() + default_duration


def get_et_job(job_id):
    """
    Get the status of an ElasticTranscode job

    Args:
        job_id(str): ID of ElasticTranscode Job

    Returns:
        JSON representation of job status/details
    """
    et = get_transcoder_client()
    job = et.read_job(Id=job_id)
    return job['Job']


def get_et_preset(preset_id):
    """
    Get the JSON configuration of an ElasticTranscode preset
    Args:
        preset_id(str):

    Returns:
        Preset configuration
    """
    et = get_transcoder_client()
    return et.read_preset(Id=preset_id)['Preset']


def get_bucket(bucket_name):
    """Get an S3 bucket by name"""
    s3 = boto3.resource("s3")
    return s3.Bucket(bucket_name)


def get_transcoder_client():
    """Get an ElasticTranscoder client object"""
    return boto3.client('elastictranscoder', settings.AWS_REGION)


def write_to_file(filename, contents):
    """
    Write content to a file in binary mode, creating directories if necessary

    Args:
        filename (str): The full-path filename to write to.
        contents (str): What to write to the file.

    """
    if not os.path.exists(os.path.dirname(filename)):
        os.makedirs(os.path.dirname(filename))
    with open(filename, 'wb') as infile:
        infile.write(contents)


def write_x509_files():
    """Write the x509 certificate and key to files"""
    write_to_file(settings.MIT_WS_CERTIFICATE_FILE, settings.MIT_WS_CERTIFICATE)
    write_to_file(settings.MIT_WS_PRIVATE_KEY_FILE, settings.MIT_WS_PRIVATE_KEY)
