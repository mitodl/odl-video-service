"""
Tasks for cloudsync app
"""

import os
import re
from urllib.parse import unquote

import boto3
import requests
from boto3.s3.transfer import TransferConfig
from botocore.exceptions import ClientError
from celery import Task, group, shared_task, states
from dj_elastictranscoder.models import EncodeJob
from django.conf import settings
from googleapiclient.errors import HttpError

from cloudsync.api import process_watch_file, refresh_status, transcode_video
from cloudsync.exceptions import TranscodeTargetDoesNotExist
from cloudsync.youtube import API_QUOTA_ERROR_MSG, YouTubeApi
from odl_video import logging
from ui.constants import StreamSource, VideoStatus, YouTubeStatus
from ui.encodings import EncodingNames
from ui.models import Collection, Video, VideoSubtitle, YouTubeVideo
from ui.utils import get_bucket

log = logging.getLogger(__name__)


CONTENT_DISPOSITION_RE = re.compile(r"filename\*=UTF-8''(?P<filename>[^ ]+)")


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
                return self.request.chain[0]["options"]["task_id"]
            except (
                IndexError,
                KeyError,
            ):
                # Log the error and continue, using self.request.id instead
                # The worst that will happen is that progress bar won't work.
                log.error("Could not find task_id in chain")  # noqa: TRY400
                return None
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
        log.error("Exception retrieving video", video_id=video_id)  # noqa: TRY400
        raise
    video.update_status(VideoStatus.UPLOADING)

    task_id = self.get_task_id()
    try:
        response = requests.get(video.source_url, stream=True, timeout=60)
        response.raise_for_status()
    except requests.HTTPError:
        video.update_status(VideoStatus.UPLOAD_FAILED)
        self.update_state(task_id=task_id, state=states.FAILURE)
        raise

    _, content_type, content_length = parse_content_metadata(response)

    s3 = boto3.resource("s3")
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
            Config=config,
        )
    except Exception:
        video.update_status(VideoStatus.UPLOAD_FAILED)
        self.update_state(task_id=task_id, state=states.FAILURE)
        raise


@shared_task(bind=True, base=VideoTask)
def transcode_from_s3(self, video_id):
    """
    Given an S3 object key, transcode that object using a video pipeline, overwrite the original when done.

    Args:
        video_id(int): The video primary key
    """  # noqa: E501
    try:
        video = Video.objects.get(id=video_id)
    except Video.DoesNotExist as exc:
        # Note: we ignore this exception in sentry, per
        # odl_video.sentry.before_send
        raise TranscodeTargetDoesNotExist from exc
    task_id = self.get_task_id()
    self.update_state(task_id=task_id, state=VideoStatus.TRANSCODING)

    video_file = video.videofile_set.get(encoding="original")

    try:
        transcode_video(video, video_file, True)  # noqa: FBT003
    except ClientError:
        self.update_state(task_id=task_id, state=states.FAILURE)
        raise


@shared_task(bind=True, base=VideoTask)
def retranscode_video(self, video_id):
    """
    Given an S3 object key, retranscode that object using a video pipeline

    Args:
        video_id(int): The video primary key
    """
    try:
        video = Video.objects.get(id=video_id)
    except Video.DoesNotExist as exc:
        # Note: we ignore this exception in sentry, per
        # odl_video.sentry.before_send
        raise TranscodeTargetDoesNotExist from exc
    task_id = self.get_task_id()
    self.update_state(task_id=task_id, state=VideoStatus.RETRANSCODING)

    video_file = video.videofile_set.get(encoding="original")

    try:
        video.update_status(VideoStatus.RETRANSCODE_SCHEDULED)
        transcode_video(video, video_file, True)  # noqa: FBT003
    except ClientError:
        self.update_state(task_id=task_id, state=states.FAILURE)
        video.update_status(VideoStatus.RETRANSCODE_FAILED)
        raise


@shared_task(bind=True)
def schedule_retranscodes(self):
    """
    Start retranscode tasks for all scheduled videos,
    and reset scheduled collections without scheduled videos
    """
    # Reset all collections with no scheduled videos
    Collection.objects.filter(schedule_retranscode=True).exclude(
        videos__schedule_retranscode=True
    ).update(schedule_retranscode=False)

    # Run retranscodes on all videos with schedule_retranscode=True
    videos = Video.objects.filter(schedule_retranscode=True).values_list(
        "id", flat=True
    )
    if videos:  # noqa: RET503
        try:
            retranscode_tasks = group(
                [retranscode_video.si(video_id) for video_id in videos]
            )
        except:  # noqa: E722
            error = "schedule_retranscodes threw an error"
            log.exception(error)
            return error
        raise self.replace(retranscode_tasks)


@shared_task(bind=True)
def update_video_statuses(self):  # noqa: ARG001
    """
    Check on statuses of all transcoding videos and update their status if appropriate
    """
    transcoding_videos = Video.objects.filter(
        status__in=(VideoStatus.TRANSCODING, VideoStatus.RETRANSCODING)
    )
    for video in transcoding_videos:
        if video.status == VideoStatus.RETRANSCODING:
            error = VideoStatus.RETRANSCODE_FAILED
        else:
            error = VideoStatus.TRANSCODE_FAILED_INTERNAL
        try:
            refresh_status(video)
        except EncodeJob.DoesNotExist:
            # Log the exception but don't raise it so other videos can be checked.
            log.exception("No EncodeJob object exists for video", video_id=video.id)
            video.update_status(error)
        except ClientError as exc:
            # Log the exception but don't raise it so other videos can be checked.
            log.exception(
                "AWS error when refreshing job status",
                video_id=video.id,
                response=exc.response,
            )
            video.update_status(error)


@shared_task()
def upload_youtube_videos():
    """
    Upload public videos one at a time to YouTube (if not already there) until the daily maximum is reached.
    """  # noqa: E501
    yt_queue = (
        Video.objects.filter(is_public=True)
        .filter(status=VideoStatus.COMPLETE)
        .filter(youtubevideo__id__isnull=True)
        .exclude(collection__stream_source=StreamSource.CLOUDFRONT)
        .order_by("-created_at")[: settings.YT_UPLOAD_LIMIT]
    )
    for video in yt_queue.all():
        youtube_video = YouTubeVideo.objects.create(video=video)
        try:
            youtube = YouTubeApi()
            response = youtube.upload_video(video)
            youtube_video.id = response["id"]
            youtube_video.status = response["status"]["uploadStatus"]
            youtube_video.save()
        except HttpError as error:
            log.exception(
                "HttpError uploading video to Youtube",
                video_hexkey=video.hexkey,
                status=youtube_video.status,
            )
            if API_QUOTA_ERROR_MSG in error.content.decode("utf-8"):
                break
        except:  # noqa: E722
            log.exception(
                "Error uploading video to Youtube",
                video_hexkey=video.hexkey,
                status=youtube_video.status,
            )
        finally:
            # If anything went wrong with the upload, delete the YouTubeVideo object.
            # Another upload attempt will be made the next time the task is run.
            if youtube_video.id is None:
                youtube_video.delete()


@shared_task(bind=True)
def remove_youtube_video(self, video_id):  # noqa: ARG001
    """
    Delete a video from Youtube
    """
    try:
        YouTubeApi().delete_video(video_id)
    except HttpError as error:
        if error.resp.status == 404:  # noqa: PLR2004
            log.info("Not found on Youtube, already deleted?", video_id=video_id)
        else:
            raise


@shared_task(bind=True)
def upload_youtube_caption(self, caption_id):  # noqa: ARG001
    """
    Upload a video caption file to YouTube
    """
    caption = VideoSubtitle.objects.get(id=caption_id)
    yt_video = YouTubeVideo.objects.get(video=caption.video)
    youtube = YouTubeApi()
    youtube.upload_caption(caption, yt_video.id)


@shared_task(bind=True)
def remove_youtube_caption(self, video_id, language):  # noqa: ARG001
    """
    Remove Youtube captions not matching a video's subtitle language)
    """
    video = Video.objects.get(id=video_id)
    captions = YouTubeApi().list_captions(video.youtube_id)
    if language in captions.keys():  # noqa: SIM118
        YouTubeApi().delete_caption(captions[language])


@shared_task(bind=True)
def update_youtube_statuses(self):  # noqa: ARG001
    """
    Update the status of recently uploaded YouTube videos and upload captions if complete
    """  # noqa: E501
    youtube = YouTubeApi()
    videos_processing = YouTubeVideo.objects.filter(status=YouTubeStatus.UPLOADED)
    for yt_video in videos_processing:
        try:
            yt_video.status = youtube.video_status(yt_video.id)
            yt_video.save()
            if yt_video.status == YouTubeStatus.PROCESSED:
                for subtitle in yt_video.video.videosubtitle_set.all():
                    youtube.upload_caption(subtitle, yt_video.id)
        except IndexError:
            # Video might be a dupe or deleted, mark it as failed and continue to next one.  # noqa: E501
            yt_video.status = YouTubeStatus.FAILED
            yt_video.save()
            log.exception(
                "Status of YoutubeVideo not found.",
                youtubevideo_id=yt_video.id,
                youtubevideo_video_id=yt_video.video_id,
            )
        except HttpError as error:
            if API_QUOTA_ERROR_MSG in error.content.decode("utf-8"):
                # Don't raise the error, task will try on next run until daily quota is reset  # noqa: E501
                break
            raise


@shared_task(bind=True)
def monitor_watch_bucket(self):  # noqa: ARG001
    """
    Check the watch bucket for any files and import them if found. All files found in the
    S3 bucket indicated by 'VIDEO_S3_WATCH_BUCKET' is assumed to be a lecture capture video.
    """  # noqa: E501
    watch_bucket = get_bucket(settings.VIDEO_S3_WATCH_BUCKET)
    for key in watch_bucket.objects.all():
        try:
            process_watch_file(key.key)
        except ClientError as exc:
            # Log ClientError, raise later so other files can be processed.
            log.exception(
                "AWS error when ingesting file from watch bucket",
                s3_object_key=key.key,
                response=exc.response,
            )
        except Exception:
            # Log any other exception, raise later so other files can be processed.
            log.exception(
                "AWS error when ingesting file from watch bucket", s3_object_key=key.key
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
            file_name = unquote(result.group("filename"))
    if not file_name:
        file_name = unquote(os.path.basename(response.url))  # noqa: PTH119

    content_type = response.headers["Content-Type"]

    content_length = response.headers["Content-Length"]
    if content_length:
        content_length = int(content_length)

    return file_name, content_type, content_length


@shared_task(bind=True)
def sort_transcoded_m3u8_files(self):  # noqa: ARG001
    """
    Sort files with highest resolution first in trancoded video playlist
    """
    for video in Video.objects.filter(videofile__encoding=EncodingNames.HLS).iterator():
        for transcoded_video in video.transcoded_videos:
            s3_filename = transcoded_video.s3_object_key
            s3_client = boto3.client("s3")
            try:
                file = s3_client.get_object(
                    Bucket=settings.VIDEO_S3_TRANSCODE_BUCKET, Key=s3_filename
                )
            except ClientError:
                log.error("Object not found on s3", video_id=video.id)  # noqa: TRY400
                continue

            file_content = file["Body"].read().decode()

            delimiter = "#EXT-X-STREAM-INF:"
            lines = file_content.split(delimiter)
            header = lines.pop(0)

            if str.strip(header) != "#EXTM3U":
                log.error(
                    "Unexpected format for transcoded video file", video_id=video.id
                )
                continue

            try:
                lines.sort(
                    key=lambda line: [
                        -int(re.search(r"RESOLUTION=(\d+)", line).group(1)),
                        -int(re.search(r"BANDWIDTH=(\d+)", line).group(1)),
                    ]
                )
            except AttributeError:
                log.error(  # noqa: TRY400
                    "Unexpected format for transcoded video file", video_id=video.id
                )
                continue

            lines.insert(0, header)
            sorted_content = delimiter.join(lines)

            if sorted_content != file_content:
                s3_client.put_object(
                    Body=str.encode(sorted_content),
                    Bucket=settings.VIDEO_S3_TRANSCODE_BUCKET,
                    Key=s3_filename,
                )
