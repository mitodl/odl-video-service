import os
from datetime import datetime

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from botocore.signers import CloudFrontSigner

# http://boto3.readthedocs.io/en/stable/reference/services/cloudfront.html#generate-a-signed-url-for-amazon-cloudfront

def rsa_signer(message):
    private_key_contents = os.environ.get("AWS_PRIVATE_KEY_CONTENTS")
    if not private_key_contents:
        raise RuntimeError("Missing required env var: AWS_PRIVATE_KEY_CONTENTS")
    # replace literal '\n' with newline character
    private_key_contents = private_key_contents.replace('\\n', '\n')
    private_key = serialization.load_pem_private_key(
        private_key_contents.encode(),
        password=None,
        backend=default_backend()
    )
    signer = private_key.signer(padding.PKCS1v15(), hashes.SHA1())
    signer.update(message)
    return signer.finalize()


def cloudfront_signed_url(key, expires_at):
    """
    Given an object key in S3, return a signed URL to access that S3 object
    from CloudFront.
    """
    assert expires_at > datetime.utcnow(), \
        "Not useful to generate a signed URL that has already expired"

    private_key_id = os.environ.get("AWS_PRIVATE_KEY_ID")
    if not private_key_id:
        raise RuntimeError("Missing required env var: AWS_PRIVATE_KEY_ID")
    cloudfront_dist = os.environ.get("VIDEO_CLOUDFRONT_DIST")
    if not cloudfront_dist:
        raise RuntimeError("Missing required env var: VIDEO_CLOUDFRONT_DIST")
    url = "https://{dist}.cloudfront.net/{key}".format(
        dist=cloudfront_dist, key=key,
    )
    cloudfront_signer = CloudFrontSigner(private_key_id, rsa_signer)
    signed_url = cloudfront_signer.generate_presigned_url(
        url, date_less_than=expires_at,
    )
    return signed_url
