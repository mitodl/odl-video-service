import os
import os.path
import re
from urllib.parse import unquote
from celery import shared_task
from celery.utils.log import get_task_logger
import boto3
import requests


logger = get_task_logger(__name__)
CONTENT_DISPOSITION_RE = re.compile(
    r"filename\*=UTF-8''(?P<filename>[^ ]+)"
)


@shared_task(bind=True)
def stream_to_s3(self, url):
    """
    Stream the contents of the given URL to Amazon S3
    """
    response = requests.get(url, stream=True)
    response.raise_for_status()
    file_name, content_type, content_length = parse_content_metadata(response)

    s3 = boto3.resource('s3')
    bucket_name = os.environ.get("VIDEO_S3_BUCKET", "odl-video-service")
    bucket = s3.Bucket(bucket_name)
    # no easy way to tell if a bucket already exists or not, so we'll just
    # call create(), which shouldn't error if the bucket already exists.
    bucket.create()

    # Need to bind this here, because otherwise it gets lost in the callback somehow
    task_id = self.request.id

    def callback(bytes_uploaded):
        data = {
            "uploaded": bytes_uploaded,
            "total": content_length,
        }
        self.update_state(task_id=task_id, state="PROGRESS", meta=data)

    bucket.upload_fileobj(
        Fileobj=response.raw,
        Key=file_name,
        ExtraArgs={"ContentType": content_type},
        Callback=callback,
    )


def parse_content_metadata(response):
    """
    Given a Response object from Requests, return the following
    information about it:

    * The file name
    * The content type, as a string
    * The content length, as an integer number of bytes
    """
    file_name = None
    content_disposition = response.headers["Content-Disposition"]
    if content_disposition:
        result = CONTENT_DISPOSITION_RE.search(content_disposition)
        if result:
            file_name = unquote(result.group('filename'))
    if not file_name:
        file_name = unquote(os.path.basename(response.url))

    content_type = response.headers["Content-Type"]

    content_length = response.headers["Content-Length"]
    if content_length:
        content_length = int(content_length)

    return file_name, content_type, content_length
