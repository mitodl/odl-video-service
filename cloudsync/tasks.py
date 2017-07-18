"""
Tasks for cloudsync app
"""
import os
import re
from urllib.parse import unquote

import requests
import boto3
from boto3.s3.transfer import TransferConfig
from celery import shared_task
from celery.utils.log import get_task_logger
from django.conf import settings
from dj_elastictranscoder.transcoder import Transcoder

from ui.models import VideoFile

log = get_task_logger(__name__)
CONTENT_DISPOSITION_RE = re.compile(
    r"filename\*=UTF-8''(?P<filename>[^ ]+)"
)

THUMBNAIL_PATTERN = "thumbnails/{}_thumbnail_{{count}}"


@shared_task(bind=True)
def stream_to_s3(self, url, s3_key):
    """
    Stream the contents of the given URL to Amazon S3
    """
    if not url:
        return False
    response = requests.get(url, stream=True)
    response.raise_for_status()
    _, content_type, content_length = parse_content_metadata(response)

    s3 = boto3.resource('s3')
    bucket_name = settings.VIDEO_S3_BUCKET
    bucket = s3.Bucket(bucket_name)

    # Need to bind this here, because otherwise it gets lost in the callback somehow
    task_id = self.request.id

    def callback(bytes_uploaded):
        """
        Callback function after upload
        """
        data = {
            "uploaded": bytes_uploaded,
            "total": content_length,
        }
        self.update_state(task_id=task_id, state="PROGRESS", meta=data)

    config = TransferConfig(**settings.AWS_S3_UPLOAD_TRANSFER_CONFIG)

    bucket.upload_fileobj(
        Fileobj=response.raw,
        Key=s3_key,
        ExtraArgs={"ContentType": content_type},
        Callback=callback,
        Config=config
    )


@shared_task(bind=True)
def transcode_from_s3(self, video_id):  # pylint: disable=unused-argument
    """
    Given an S3 object key, transcode that object using a video pipeline, overwrite the original when done.

    Args:
        video_id(int): The video primary key
    """
    if not settings.ET_PRESET_IDS:
        raise ValueError("At least one transcode preset required in settings")

    video_file = VideoFile.objects.get(video__id=video_id, encoding='original')
    video = video_file.video

    video_input = {
        'Key': video_file.s3_object_key,
    }

    # Generate an output video file for each encoding (assumed to be HLS)
    outputs = [{
        'Key': video.transcode_key(preset),
        'PresetId': preset,
        'SegmentDuration': '10.0'
    } for preset in settings.ET_PRESET_IDS]

    playlists = [{
        'Format': 'HLSv3',
        'Name': video.transcode_key('_index'),
        'OutputKeys': [output['Key'] for output in outputs]
    }]

    # Generate thumbnails for the 1st encoding (no point in doing so for each).
    outputs[0]['ThumbnailPattern'] = THUMBNAIL_PATTERN.format(video_file.s3_basename)
    transcoder = Transcoder(
        settings.ET_PIPELINE_ID,
        settings.AWS_REGION,
        settings.AWS_ACCESS_KEY_ID,
        settings.AWS_SECRET_ACCESS_KEY
    )
    transcoder.encode(video_input, outputs, Playlists=playlists)
    transcoder.create_job_for_object(video)


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
