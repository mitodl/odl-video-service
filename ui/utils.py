"""Utils for ui app"""
from datetime import datetime, timedelta
from functools import lru_cache
from urllib.parse import quote

from pytz import UTC
import boto3
from django.conf import settings

from django.utils.dateparse import parse_datetime, parse_duration
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from botocore.signers import CloudFrontSigner
# from mit_moira import Moira


@lru_cache(1)  # memoize this function
def get_moira_client():
    """
    Gets a moira client.
    IMPORTANT: This function will always raise an error until we fix the Moira client library to
    accept certificate and key from strings.
    For the time being this function will simply raise every time it is called.
    """
    raise NotImplementedError(
        'get_moira_client needs to be fixed after moira client library '
        'is upgraded to support secrets from strings and not only from files'
    )
    # leaving the old code around as an example of what needs to be done

    # cert_file_path = os.path.join(settings.SECRETS_DIR, "mit-ws-cert")
    # cert_file_exists = os.path.isfile(cert_file_path)
    # key_file_path = os.path.join(settings.SECRETS_DIR, "mit-ws-key")
    # key_file_exists = os.path.isfile(key_file_path)
    # if not cert_file_exists and not key_file_exists:
    #     msg = "Missing required secrets: {cert} {key}".format(
    #         cert=cert_file_path, key=key_file_path,
    #     )
    #     raise RuntimeError(msg)
    # if not cert_file_exists:
    #     msg = "Missing required secret: {cert}".format(
    #         cert=cert_file_path,
    #     )
    #     raise RuntimeError(msg)
    # if not key_file_exists:
    #     msg = "Missing required secret: {key}".format(
    #         key=key_file_path,
    #     )
    #     raise RuntimeError(msg)
    # return Moira(cert_file_path, key_file_path)


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
