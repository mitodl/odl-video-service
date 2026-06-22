"""
Tasks for cloudsync app
"""

import json
import mimetypes
import re
import threading
from datetime import timedelta

import boto3
import requests
from boto3.s3.transfer import TransferConfig
from botocore.exceptions import (
    BotoCoreError,
    ClientError,
    ConnectionError as BotoConnectionError,
    ConnectionClosedError,
    HTTPClientError,
)
from celery import Task, group, shared_task, states
from celery.utils.time import get_exponential_backoff_interval
from django.conf import settings
from django.db import connection
from googleapiclient.errors import HttpError
from redis.exceptions import LockError
from urllib3.exceptions import (
    ProtocolError as Urllib3ProtocolError,
    TimeoutError as Urllib3TimeoutError,
)

from cloudsync import dropbox_api
from cloudsync.api import process_watch_file, refresh_status, transcode_video
from cloudsync.exceptions import TranscodeTargetDoesNotExist
from cloudsync.youtube import API_QUOTA_ERROR_MSG, YouTubeApi
import structlog
from ui.constants import StreamSource, VideoStatus, YouTubeStatus
from ui.encodings import EncodingNames
from ui.models import Collection, EncodeJob, Video, VideoSubtitle, YouTubeVideo
from ui.utils import get_bucket, now_in_utc

log = structlog.get_logger(__name__)


class _UploadLockLost(Exception):
    """Raised from the progress callback when stream_to_s3 loses its upload lock
    mid-stream, so the upload aborts before two workers can write the same key."""


# botocore transport errors worth retrying — connection drops and read/connect
# timeouts — as opposed to permanent ones like NoCredentialsError.
TRANSIENT_BOTOCORE_ERRORS = (
    BotoConnectionError,
    ConnectionClosedError,
    HTTPClientError,
)
# S3 error codes that are transient even when their HTTP status is not 5xx
# (e.g. RequestTimeout is a 400).
TRANSIENT_S3_ERROR_CODES = frozenset(
    {
        "RequestTimeout",
        "RequestTimeTooSkewed",
        "ThrottlingException",
        "Throttling",
    }
)
# Socket/transport errors raised while boto3 streams from response.raw (the
# urllib3 socket); these are NOT requests.RequestException subclasses.
TRANSIENT_STREAM_ERRORS = (
    ConnectionError,  # builtin: ConnectionReset/BrokenPipe/etc.
    TimeoutError,  # builtin
    Urllib3ProtocolError,
    Urllib3TimeoutError,
)


def _is_transient_http_status(status):
    """5xx, plus request-timeout (408) and too-many-requests (429), are transient."""
    return status is not None and (status >= 500 or status in (408, 429))


def _should_retry_upload(exc):
    """
    True for transient upload errors worth retrying. Permanent failures fail fast:
    malformed Dropbox metadata (KeyError/ValueError), auth errors, HTTP 4xx (e.g. a
    revoked or missing shared link), and permanent S3 errors (AccessDenied,
    NoSuchBucket, ...).
    """
    if isinstance(exc, ClientError):
        meta = exc.response.get("ResponseMetadata", {})
        if _is_transient_http_status(meta.get("HTTPStatusCode")):
            return True
        return exc.response.get("Error", {}).get("Code") in TRANSIENT_S3_ERROR_CODES
    if isinstance(exc, BotoCoreError):
        return isinstance(exc, TRANSIENT_BOTOCORE_ERRORS)
    if isinstance(exc, requests.HTTPError):
        return _is_transient_http_status(getattr(exc.response, "status_code", None))
    if isinstance(exc, requests.exceptions.RequestException):
        # requests-level connection/timeout/chunked-encoding errors are transient.
        # Checked after HTTPError, since HTTPError is also a RequestException.
        return True
    return isinstance(exc, TRANSIENT_STREAM_ERRORS)


def _retry_after_seconds(exc, retries: int) -> int:
    """Return the Retry-After wait (seconds) from a 429 throttle response, else use exponential backoff."""
    seconds = None
    response = getattr(exc, "response", None)
    if response and getattr(response, "status_code", None) == 429:
        headers = getattr(response, "headers", None) or {}
        value = headers.get("Retry-After", None)
        if value:
            try:
                seconds = int(value)
            except (TypeError, ValueError):
                log.warning("Invalid Retry-After header value; ignoring")
    if seconds is None:
        # No valid Retry-After header; use exponential backoff with jitter.
        seconds = get_exponential_backoff_interval(
            factor=settings.CLOUDSYNC_STREAM_S3_RETRY_BACKOFF,
            retries=retries,
            maximum=settings.CLOUDSYNC_STREAM_S3_RETRY_MAX_BACKOFF,
            full_jitter=True,
        )
    return seconds


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
                log.error("Could not find task_id in chain")
                return
        return self.request.id


@shared_task(bind=True)
def update_video_statuses(self):
    """
    Check on statuses of all transcoding videos and update their status if appropriate
    """
    transcoding_videos = Video.objects.filter(
        status__in=(VideoStatus.TRANSCODING, VideoStatus.RETRANSCODING)
    )
    for video in transcoding_videos:
        log.info("Checking video status", video_id=video.id)
        error = (
            VideoStatus.RETRANSCODE_FAILED
            if video.status == VideoStatus.RETRANSCODING
            else VideoStatus.TRANSCODE_FAILED_INTERNAL
        )

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


@shared_task
def fail_stuck_uploading_videos():
    """
    Fail videos stuck in UPLOADING past the threshold so they can be retried.
    """
    now = now_in_utc()
    threshold = now - timedelta(hours=settings.STUCK_UPLOADING_THRESHOLD_HOURS)
    stuck_videos = list(
        Video.objects.filter(status=VideoStatus.UPLOADING, updated_at__lt=threshold)
    )
    for video in stuck_videos:
        log.info(
            "Failing video stuck in UPLOADING",
            video_id=video.id,
            uploading_since=video.updated_at.isoformat(),
        )
        try:
            video.update_status(VideoStatus.UPLOAD_FAILED)
        except Exception:
            # Don't let one bad video abort the sweep of the rest.
            log.exception("Failed to update stuck video status", video_id=video.id)


def _video_upload_lock(app, video_id):
    """
    Non-blocking redis lock serializing concurrent uploads of one video.

    thread_local=False: acquired on the task thread but reacquired/released from
    s3transfer callback threads.
    """
    return app.backend.client.lock(
        f"stream_to_s3:lock:{video_id}",
        timeout=settings.CLOUDSYNC_STREAM_S3_LOCK_TTL,
        thread_local=False,
    )


@shared_task(
    bind=True,
    base=VideoTask,
    acks_late=True,
    reject_on_worker_lost=True,
    max_retries=settings.CLOUDSYNC_STREAM_S3_MAX_RETRIES,
)
def stream_to_s3(self, video_id):
    """
    Stream the contents of the given URL to Amazon S3
    """

    if not video_id:
        return False
    try:
        video = Video.objects.get(id=video_id)
    except (Video.DoesNotExist, Video.MultipleObjectsReturned):
        log.error("Exception retrieving video", video_id=video_id)
        raise

    lock = _video_upload_lock(self.app, video_id)
    if not lock.acquire(blocking=False):
        log.debug(
            "stream_to_s3 skipped; another worker holds the upload lock",
            video_id=video_id,
        )
        # Don't advance the chain: the worker that owns the upload transcodes via
        # its own chain. Returning normally would otherwise run transcode_from_s3
        # on an incomplete object and poison the video out of UPLOADING.
        self.request.chain = self.request.callbacks = None
        return False

    video.update_status(VideoStatus.UPLOADING)

    task_id = self.get_task_id()
    response = None

    try:
        response = dropbox_api.stream_shared_link(video.source_url)
        # KeyError/ValueError here mean the Dropbox metadata header is
        # missing or malformed, which is still an upload failure.
        _, content_type, content_length = parse_content_metadata(response)

        s3 = boto3.resource("s3")
        bucket = s3.Bucket(settings.VIDEO_S3_BUCKET)
        total_bytes_uploaded = 0
        last_progress_refresh = None
        # boto3's s3transfer invokes this callback concurrently from a thread
        # pool, so guard the shared progress state.
        progress_lock = threading.Lock()

        def callback(bytes_uploaded):
            """
            Callback function after upload
            """
            nonlocal total_bytes_uploaded, last_progress_refresh
            now = now_in_utc()
            with progress_lock:
                total_bytes_uploaded += bytes_uploaded
                should_refresh = (
                    last_progress_refresh is None
                    or (now - last_progress_refresh).total_seconds()
                    >= settings.CLOUDSYNC_UPLOAD_PROGRESS_REFRESH_SECONDS
                )
                if should_refresh:
                    last_progress_refresh = now
            self.update_state(
                task_id=task_id,
                state="PROGRESS",
                meta={"uploaded": total_bytes_uploaded, "total": content_length},
            )
            if should_refresh:
                # Heartbeat the lease so a short TTL survives a long upload. If we
                # can't reacquire, another worker now owns the lock and may be
                # streaming the same key — abort this upload rather than letting two
                # workers write concurrently. Redelivery/retry re-enters normal lock
                # acquisition so exactly one worker proceeds.
                try:
                    lock.reacquire()
                except LockError as exc:
                    raise _UploadLockLost from exc
                # Keep updated_at fresh so the fail_stuck_uploading_videos janitor
                # treats an actively streaming upload as alive rather than stuck.
                # Throttled (above) to avoid a DB write on every chunk callback.
                try:
                    Video.objects.filter(id=video.id).update(updated_at=now)
                finally:
                    # When invoked from an s3transfer worker thread, Django opens
                    # a thread-local connection nothing else will close; close it
                    # here to avoid leaking connections. Leave the main task's
                    # connection alone.
                    if threading.current_thread() is not threading.main_thread():
                        connection.close()

        config = TransferConfig(**settings.AWS_S3_UPLOAD_TRANSFER_CONFIG)
        bucket.upload_fileobj(
            Fileobj=response.raw,
            Key=video.get_s3_key(),
            ExtraArgs={"ContentType": content_type},
            Callback=callback,
            Config=config,
        )
    except _UploadLockLost:
        # Another worker owns the lock now and is driving this upload (and its
        # transcode chain). Give up quietly: don't fail the video, don't retry,
        # and don't advance the chain, mirroring the can't-acquire path above.
        log.warning(
            "stream_to_s3 lost upload lock mid-stream; another worker owns it",
            video_id=video_id,
        )
        self.request.chain = self.request.callbacks = None
        return False
    except Exception as exc:
        retryable = _should_retry_upload(exc)
        if retryable and self.request.retries < self.max_retries:
            countdown = _retry_after_seconds(exc, self.request.retries)
            log.warning(
                "Retrying stream_to_s3 after transient error",
                video_id=video_id,
                attempt=self.request.retries + 1,
                countdown=countdown,
                error=str(exc),
            )
            raise self.retry(exc=exc, countdown=countdown)
        if retryable:
            log.error("stream_to_s3 retries exhausted", video_id=video_id)
        video.update_status(VideoStatus.UPLOAD_FAILED)
        self.update_state(task_id=task_id, state=states.FAILURE)
        raise
    finally:
        # Always release the streamed Dropbox connection, including on the
        # successful-upload path where nothing else closes it.
        if response is not None:
            response.close()
        # Release the upload lock.
        try:
            lock.release()
        except LockError:
            log.warning(
                "stream_to_s3 upload lock already released or expired",
                video_id=video_id,
            )


@shared_task(bind=True, base=VideoTask)
def transcode_from_s3(self, video_id):
    """
    Given an S3 object key, transcode that object using a video pipeline, overwrite the original when done.

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
    self.update_state(task_id=task_id, state=VideoStatus.TRANSCODING)

    video_file = video.videofile_set.get(encoding="original")

    try:
        transcode_video(video, video_file, True)
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
        transcode_video(video, video_file, True)
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
    if videos:
        try:
            retranscode_tasks = group(
                [retranscode_video.si(video_id) for video_id in videos]
            )
        except:  # noqa: E722
            error = "schedule_retranscodes threw an error"
            log.exception(error)
            return error
        raise self.replace(retranscode_tasks)


@shared_task()
def upload_youtube_videos():
    """
    Upload public videos one at a time to YouTube (if not already there) until the daily maximum is reached.
    """
    yt_queue = (
        Video.objects.filter(is_public=True)
        .filter(status=VideoStatus.COMPLETE)
        .filter(youtubevideo__id__isnull=True)
        .filter(collection__stream_source=StreamSource.YOUTUBE)
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
def remove_youtube_video(self, video_id):
    """
    Delete a video from Youtube
    """
    try:
        YouTubeApi().delete_video(video_id)
    except HttpError as error:
        if error.resp.status == 404:
            log.info("Not found on Youtube, already deleted?", video_id=video_id)
        else:
            raise


@shared_task(bind=True)
def upload_youtube_caption(self, caption_id):
    """
    Upload a video caption file to YouTube
    """
    caption = VideoSubtitle.objects.get(id=caption_id)
    yt_video = YouTubeVideo.objects.get(video=caption.video)
    youtube = YouTubeApi()
    youtube.upload_caption(caption, yt_video.id)


@shared_task(bind=True)
def remove_youtube_caption(self, video_id, language):
    """
    Remove Youtube captions not matching a video's subtitle language)
    """
    video = Video.objects.get(id=video_id)
    captions = YouTubeApi().list_captions(video.youtube_id)
    if language in captions.keys():
        YouTubeApi().delete_caption(captions[language])


@shared_task(bind=True)
def update_youtube_statuses(self):
    """
    Update the status of recently uploaded YouTube videos and upload captions if complete
    """
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
            # Video might be a dupe or deleted, mark it as failed and continue to next one.
            yt_video.status = YouTubeStatus.FAILED
            yt_video.save()
            log.exception(
                "Status of YoutubeVideo not found.",
                youtubevideo_id=yt_video.id,
                youtubevideo_video_id=yt_video.video_id,
            )
        except HttpError as error:
            if API_QUOTA_ERROR_MSG in error.content.decode("utf-8"):
                # Don't raise the error, task will try on next run until daily quota is reset
                break
            raise


@shared_task(bind=True)
def monitor_watch_bucket(self):
    """
    Check the watch bucket for any files and import them if found. All files found in the
    S3 bucket indicated by 'VIDEO_S3_WATCH_BUCKET' is assumed to be a lecture capture video.
    """
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

    For authenticated Dropbox downloads the metadata arrives in the
    ``Dropbox-API-Result`` header with a generic octet-stream content type, so
    the MIME type is derived from the file name.
    """
    metadata = json.loads(response.headers["Dropbox-API-Result"])
    file_name = metadata["name"]
    content_type = mimetypes.guess_type(file_name)[0] or "application/octet-stream"
    content_length = metadata.get("size")
    if content_length is None:
        header_length = response.headers.get("Content-Length")
        content_length = int(header_length) if header_length else None
    return file_name, content_type, content_length


@shared_task(bind=True)
def sort_transcoded_m3u8_files(self):
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
                log.error("Object not found on s3", video_id=video.id)
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
                log.error(
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
