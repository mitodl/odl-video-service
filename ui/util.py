"""Utils for ui app"""
import os.path
from datetime import datetime, timedelta
from functools import lru_cache
import configparser

from mit_moira import Moira
from django.utils.dateparse import parse_datetime, parse_duration
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from botocore.signers import CloudFrontSigner


@lru_cache(1)  # memoize this function
def get_dropbox_credentials():
    """get dropbox credentials"""
    file_path = "/run/secrets/dropbox-credentials"
    if not os.path.isfile(file_path):
        msg = "Missing required secret: {path}".format(path=file_path)
        raise RuntimeError(msg)
    config = configparser.ConfigParser()
    config.read_file(open(file_path))
    key = config.get("default", "dropbox_app_key")
    secret = config.get("default", "dropbox_app_secret")
    return key, secret


@lru_cache(1)  # memoize this function
def get_moira_client():
    """get moira client"""
    cert_file_path = "/run/secrets/mit-ws-cert"
    cert_file_exists = os.path.isfile(cert_file_path)
    key_file_path = "/run/secrets/mit-ws-key"
    key_file_exists = os.path.isfile(key_file_path)
    if not cert_file_exists and not key_file_exists:
        msg = "Missing required secrets: {cert} {key}".format(
            cert=cert_file_path, key=key_file_path,
        )
        raise RuntimeError(msg)
    if not cert_file_exists:
        msg = "Missing required secret: {cert}".format(
            cert=cert_file_path,
        )
        raise RuntimeError(msg)
    if not key_file_exists:
        msg = "Missing required secret: {key}".format(
            key=key_file_path,
        )
        raise RuntimeError(msg)
    return Moira(cert_file_path, key_file_path)


# http://boto3.readthedocs.io/en/stable/reference/services/cloudfront.html#generate-a-signed-url-for-amazon-cloudfront

def rsa_signer(message):
    """rsa signer"""
    private_key_file_path = "/run/secrets/cloudfront-key"
    if not os.path.isfile(private_key_file_path):
        msg = "Missing required secret: {path}".format(path=private_key_file_path)
        raise RuntimeError(msg)
    with open(private_key_file_path, 'rb') as key_file:
        private_key = serialization.load_pem_private_key(
            key_file.read(),
            password=None,
            backend=default_backend()
        )
    signer = private_key.signer(padding.PKCS1v15(), hashes.SHA1())
    signer.update(message)
    return signer.finalize()


def cloudfront_signed_url(key, expires):
    """
    Given an object key in S3, return a signed URL to access that S3 object
    from CloudFront.
    """
    assert expires > datetime.utcnow(), \
        "Not useful to generate a signed URL that has already expired"

    key_id = os.environ.get("CLOUDFRONT_KEY_ID")
    if not key_id:
        raise RuntimeError("Missing required env var: CLOUDFRONT_KEY_ID")
    cloudfront_dist = os.environ.get("VIDEO_CLOUDFRONT_DIST")
    if not cloudfront_dist:
        raise RuntimeError("Missing required env var: VIDEO_CLOUDFRONT_DIST")
    url = "https://{dist}.cloudfront.net/{key}".format(
        dist=cloudfront_dist, key=key,
    )
    cloudfront_signer = CloudFrontSigner(key_id, rsa_signer)
    signed_url = cloudfront_signer.generate_presigned_url(
        url, date_less_than=expires,
    )
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
