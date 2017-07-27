"""
Tasks for cloudsync app
"""
import os
import re
from urllib.parse import unquote

import requests
import boto3
from boto3.s3.transfer import TransferConfig
from botocore.exceptions import ClientError
from celery import shared_task, states, Task
from celery.utils.log import get_task_logger
from dj_elastictranscoder.models import EncodeJob
from django.conf import settings

from cloudsync.utils import VideoTranscoder
from ui.api import refresh_status
from ui.models import VideoFile, Video
from ui.constants import VideoStatus

log = get_task_logger(__name__)
CONTENT_DISPOSITION_RE = re.compile(
    r"filename\*=UTF-8''(?P<filename>[^ ]+)"
)

THUMBNAIL_PATTERN = "thumbnails/{}_thumbnail_{{count}}"


class VideoTask(Task):
    """
    Custom Celery Task class for video uploads and transcodes
    """

    def get_task_id(self):
        """
        Get the task id (depending on whether the task is chained or not)

        Args:
            request(Task.request): The task request

        Returns:
            The request id
        """
        if self.request.chain:
            try:
                return self.request.chain[0]['options']['task_id']
            except (IndexError, KeyError,) as exc:
                # Log the error and continue, using self.request.id instead
                # The worst that will happen is that progress bar won't work.
                log.error("Could not find task_id in chain: %s", str(exc))
                return
        return self.request.id


@shared_task(bind=True, base=VideoTask)
def stream_to_s3(self, video_id):
    """
    Stream the contents of the given URL to Amazon S3
    """

    if not video_id:
        return False
    try:
        video = Video.objects.get(id=video_id)
    except (Video.DoesNotExist, Video.MultipleObjectsReturned):
        log.error("Exception retrieving video with id %d", video_id)
        raise
    video.update_status(VideoStatus.UPLOADING)

    task_id = self.get_task_id()
    try:
        response = requests.get(video.source_url, stream=True, timeout=60)
        response.raise_for_status()
    except Exception:
        video.update_status(VideoStatus.UPLOAD_FAILED)
        self.update_state(task_id=task_id, state=states.FAILURE)
        raise

    _, content_type, content_length = parse_content_metadata(response)

    s3 = boto3.resource('s3')
    bucket_name = settings.VIDEO_S3_BUCKET
    bucket = s3.Bucket(bucket_name)
    total_bytes_uploaded = 0

    def callback(bytes_uploaded):
        """
        Callback function after upload
        """
        nonlocal total_bytes_uploaded
        total_bytes_uploaded += bytes_uploaded
        data = {
            "uploaded": total_bytes_uploaded,
            "total": content_length,
        }
        self.update_state(task_id=task_id, state="PROGRESS", meta=data)

    config = TransferConfig(**settings.AWS_S3_UPLOAD_TRANSFER_CONFIG)
    try:
        bucket.upload_fileobj(
            Fileobj=response.raw,
            Key=video.get_s3_key(),
            ExtraArgs={"ContentType": content_type},
            Callback=callback,
            Config=config
        )
    except Exception:
        video.update_status(VideoStatus.UPLOAD_FAILED)
        self.update_state(task_id=task_id, state=states.FAILURE)
        raise


@shared_task(bind=True, base=VideoTask)
def transcode_from_s3(self, video_id):  # pylint: disable=unused-argument
    """
    Given an S3 object key, transcode that object using a video pipeline, overwrite the original when done.

    Args:
        video_id(int): The video primary key
    """
    video = Video.objects.get(id=video_id)
    task_id = self.get_task_id()
    self.update_state(task_id=task_id, state=VideoStatus.TRANSCODING)

    video_file = VideoFile.objects.get(video__id=video_id, encoding='original')

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
    transcoder = VideoTranscoder(
        settings.ET_PIPELINE_ID,
        settings.AWS_REGION,
        settings.AWS_ACCESS_KEY_ID,
        settings.AWS_SECRET_ACCESS_KEY
    )
    try:
        transcoder.encode(video_input, outputs, Playlists=playlists)
    except ClientError as exc:
        log.error('Transcode job creation failed for video %s', video_id)
        video.update_status(VideoStatus.TRANSCODE_FAILED)
        self.update_state(task_id=task_id, state=states.FAILURE)
        if hasattr(exc, 'response'):
            transcoder.message = exc.response
        raise
    finally:
        transcoder.create_job_for_object(video)
        if video.status != VideoStatus.TRANSCODE_FAILED:
            video.update_status(VideoStatus.TRANSCODING)


@shared_task(bind=True)
def update_video_statuses(self):  # pylint: disable=unused-argument
    """
    Check on statuses of all transcoding videos and update their status if appropriate
    """
    transcoding_videos = Video.objects.filter(status=VideoStatus.TRANSCODING)
    for video in transcoding_videos:
        try:
            refresh_status(video)
        except EncodeJob.DoesNotExist:
            # Log the exception but don't raise it so other videos can be checked.
            log.exception("No EncodeJob object exists for video id %d", video.id)
            video.update_status(VideoStatus.TRANSCODE_FAILED)
        except ClientError as exc:
            # Log the exception but don't raise it so other videos can be checked.
            log.exception("AWS error when refreshing job status for video %d: %s", video.id, exc.response)
            video.update_status(VideoStatus.TRANSCODE_FAILED)


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
