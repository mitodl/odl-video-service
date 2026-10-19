"""
API methods
"""

import hashlib
import io

import boto3
import requests
import structlog
from botocore.exceptions import BotoCoreError, ClientError
from celery import chain
from django.conf import settings
from django.core.cache import caches
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from PIL import Image, ImageOps

from cloudsync import tasks
from odl_video.constants import (
    EDX_VIDEO_IMAGE_ASPECT_RATIO,
    EDX_VIDEO_IMAGE_ASPECT_RATIO_ERROR_MARGIN,
    EDX_VIDEO_IMAGE_MAX_BYTES,
    EDX_VIDEO_IMAGE_MAX_HEIGHT,
    EDX_VIDEO_IMAGE_MAX_WIDTH,
    EDX_VIDEO_IMAGE_MIN_BYTES,
    EDX_VIDEO_IMAGE_MIN_HEIGHT,
    EDX_VIDEO_IMAGE_MIN_WIDTH,
)
from ui import models
from ui.constants import VideoStatus
from ui.encodings import EncodingNames
from ui.utils import get_error_response_summary_dict

log = structlog.get_logger(__name__)

# How long OVS remembers the last image sent to an edX endpoint, so that later pushes (e.g. every
# save of a COMPLETE video) don't re-send an unchanged thumbnail. A new image is always sent.
EDX_VIDEO_IMAGE_DEDUPE_SECONDS = 30 * 24 * 60 * 60
# Upper bound on how long one worker holds the right to send a given image
EDX_VIDEO_IMAGE_SEND_LOCK_SECONDS = 2 * 60


def dispatch_upload_chain(video_id):
    """Kick off the chained stream_to_s3 → transcode_from_s3 tasks for a video."""
    return chain(
        tasks.stream_to_s3.s(video_id), tasks.transcode_from_s3.si(video_id)
    ).delay()


def process_dropbox_data(dropbox_upload_data):
    """
    Takes care of processing a list of videos to be uploaded from dropbox

    Args:
        dropbox_links_list (dict): a dictionary containing the collection key and a list of dropbox links

    Returns:
        list: A list of dictionaries containing informations about the videos
    """
    collection_key = dropbox_upload_data["collection"]
    dropbox_links_list = dropbox_upload_data["files"]
    collection = get_object_or_404(models.Collection, key=collection_key)
    response_data = {}
    for dropbox_link in dropbox_links_list:
        with transaction.atomic():
            video = models.Video.objects.create(
                source_url=dropbox_link["link"],
                title=dropbox_link["name"][
                    : models.Video._meta.get_field("title").max_length
                ],
                collection=collection,
            )
            models.VideoFile.objects.create(
                s3_object_key=video.get_s3_key(),
                video_id=video.id,
                bucket_name=settings.VIDEO_S3_BUCKET,
            )
        # Kick off chained async celery tasks to transfer file to S3, then start a transcode job
        dispatch_upload_chain(video.id)

        response_data[video.hexkey] = {
            "s3key": video.get_s3_key(),
            "title": video.title,
        }
    return response_data


def retry_failed_upload(video):
    """
    Re-dispatch the upload chain for one UPLOAD_FAILED video; returns an outcome string.

    Guards run before the status flip and dispatch failures revert it, so the video
    is never left marooned.
    """
    if video.status != VideoStatus.UPLOAD_FAILED:
        return "skipped_status"
    if not video.source_url:
        return "skipped_no_source"
    if not video.videofile_set.filter(encoding=EncodingNames.ORIGINAL).exists():
        return "skipped_no_original"

    # Atomic compare-and-swap so two concurrent retries can't both dispatch a chain
    # for the same video; only the caller that flips the row proceeds.
    changed = models.Video.objects.filter(
        pk=video.pk, status=VideoStatus.UPLOAD_FAILED
    ).update(status=VideoStatus.CREATED)
    if changed != 1:
        return "skipped_conflict"

    try:
        dispatch_upload_chain(video.id)
    except Exception:
        models.Video.objects.filter(pk=video.pk).update(
            status=VideoStatus.UPLOAD_FAILED
        )
        log.exception("Failed to dispatch retry upload chain", video_id=video.id)
        return "dispatch_failed"
    return "retried"


def replace_video_from_dropbox(video_key, dropbox_file):
    """
    Replace an existing video with a new file from Dropbox.
    Updates the source URL, resets the video status to Created,
    and kicks off the stream_to_s3 + retranscode_from_s3 chain.

    If the new file's extension differs from the original (e.g. .mp4 → .m4v),
    the existing original VideoFile is repointed to the new S3 key so that
    stream_to_s3 writes there and retranscode_video reads the correct object.
    The old S3 object is scheduled for deletion to avoid leaving stale files.

    Args:
        video_key (UUID): The key of the existing Video to replace
        dropbox_file (dict): A single validated DropboxFile dict with 'link', 'name', etc.

    Returns:
        dict: Basic info about the video being re-processed
    """
    video = get_object_or_404(models.Video, key=video_key)
    with transaction.atomic():
        video.source_url = dropbox_file["link"]
        video.save(update_fields=["source_url"])
        video.update_status(VideoStatus.CREATED)

        new_s3_key = video.get_s3_key()
        original_vf = video.original_video
        if original_vf and original_vf.s3_object_key != new_s3_key:
            old_s3_key = original_vf.s3_object_key
            old_bucket = original_vf.bucket_name
            original_vf.s3_object_key = new_s3_key
            original_vf.save(update_fields=["s3_object_key"])
            # Delete the stale source object asynchronously so it doesn't linger.
            models.delete_s3_objects.delay(old_bucket, old_s3_key)

    # Considering Retranscode here as that will handle replacing the existing video
    chain(tasks.stream_to_s3.s(video.id), tasks.retranscode_video.si(video.id)).delay()
    return {"key": video.hexkey, "title": video.title}


def post_video_to_edx(video_files):
    """
    Posts a video to all configured edX endpoints via API using attributes from a video file

    Args:
        video_files [ui.models.VideoFile]: An array of video files

    Returns:
        Dict[EdxEndpoint, requests.models.Response]: Each configured edX endpoint mapped to the response from the
            request to post the video file to that endpoint.
    """
    encoded_videos = []
    for video_file in video_files:
        assert video_file.can_add_to_edx, "This video file cannot be added to edX"
        encoded_videos.append(
            {
                "url": video_file.cloudfront_url,
                "file_size": 0,
                "bitrate": 0,
                "profile": video_file.encoding.lower(),
            }
        )
    edx_endpoints = models.EdxEndpoint.objects.filter(
        Q(collections__id__in=[video_files[0].video.collection_id])
    )
    if not edx_endpoints.exists():
        log.error(
            "Trying to post video to edX endpoints, but no endpoints exist",
            videofile_id=video_files[0].pk,
            videofile=video_files[0],
        )

    responses = {}
    accepted_endpoints = []
    for edx_endpoint in edx_endpoints:
        try:
            edx_endpoint.refresh_access_token()
            duration = video_files[0].video.duration
            video_key = str(video_files[0].video.key)
            resp = requests.post(
                edx_endpoint.full_api_url,
                json={
                    "client_video_id": video_files[0].video.title,
                    "edx_video_id": video_key,
                    "encoded_videos": encoded_videos,
                    "courses": [{video_files[0].video.collection.edx_course_id: None}],
                    "status": "file_complete",
                    "duration": duration,
                },
                headers={
                    "Authorization": f"JWT {edx_endpoint.access_token}",
                },
            )
            if resp.status_code == 400:
                log.info(
                    "Video already exists on edX, updating instead",
                )
                update_resp = update_video_on_edx(video_key, encoded_videos)
                resp = update_resp.get(f"{edx_endpoint.full_api_url}{video_key}")
            else:
                resp.raise_for_status()
            if resp is not None and resp.ok:
                accepted_endpoints.append(edx_endpoint)
        except requests.exceptions.RequestException as exc:
            if exc is not None and exc.response is not None:
                response_summary_dict = get_error_response_summary_dict(exc.response)
            elif isinstance(exc, requests.exceptions.ConnectionError):
                response_summary_dict = {
                    "exception": "ConnectionError (No server response)"
                }
            else:
                response_summary_dict = {"exception": str(exc)}
            log.error(
                "Can not add video to edX",
                videofile_id=video_files[0].pk,
                response=str(response_summary_dict),
            )
            resp = exc.response
        responses[edx_endpoint] = resp
    if accepted_endpoints:
        try:
            post_video_thumbnail_to_edx(
                video_files[0].video, edx_endpoints=accepted_endpoints
            )
        except Exception:
            # The video is already on edX; a thumbnail problem must not fail the video push
            log.exception(
                "Can not add video thumbnail to edX",
                video_key=video_files[0].video.hexkey,
            )
    return responses


def get_edx_video_image_error(image_bytes):
    """
    Check an image against the limits Studio enforces on video images

    Args:
        image_bytes (bytes): The image file content

    Returns:
        str or None: A description of why edX would reject the image, or None if it is acceptable
    """
    if not EDX_VIDEO_IMAGE_MIN_BYTES <= len(image_bytes) <= EDX_VIDEO_IMAGE_MAX_BYTES:
        return f"file size {len(image_bytes)} bytes is outside edX's limits"
    try:
        with Image.open(io.BytesIO(image_bytes)) as image:
            width, height = image.size
    except Exception:  # noqa: BLE001
        return "image could not be decoded"
    return get_thumbnail_dimension_error(width, height)


def pad_image_for_edx(image_bytes):
    """
    Make a copy of an image that edX accepts: pad it with black bars to 16:9, keeping the whole
    frame visible, then scale it to between 640x360 and 1280x720 and encode it as JPEG.

    Args:
        image_bytes (bytes): The image file content

    Returns:
        bytes or None: The JPEG content of the padded copy, or None if the image can't be decoded
    """
    try:
        with Image.open(io.BytesIO(image_bytes)) as source:
            image = ImageOps.exif_transpose(source).convert("RGB")
    except Exception:  # noqa: BLE001
        return None
    width, height = image.size
    if width / height > EDX_VIDEO_IMAGE_ASPECT_RATIO:
        canvas_size = (width, round(width / EDX_VIDEO_IMAGE_ASPECT_RATIO))
    else:
        canvas_size = (round(height * EDX_VIDEO_IMAGE_ASPECT_RATIO), height)
    padded = Image.new("RGB", canvas_size, (0, 0, 0))
    padded.paste(image, ((canvas_size[0] - width) // 2, (canvas_size[1] - height) // 2))
    if canvas_size[0] > EDX_VIDEO_IMAGE_MAX_WIDTH:
        padded = padded.resize(
            (EDX_VIDEO_IMAGE_MAX_WIDTH, EDX_VIDEO_IMAGE_MAX_HEIGHT), Image.LANCZOS
        )
    elif canvas_size[0] < EDX_VIDEO_IMAGE_MIN_WIDTH:
        padded = padded.resize(
            (EDX_VIDEO_IMAGE_MIN_WIDTH, EDX_VIDEO_IMAGE_MIN_HEIGHT), Image.LANCZOS
        )
    output = io.BytesIO()
    padded.save(output, format="JPEG", quality=85)
    return output.getvalue()


def get_thumbnail_dimension_error(width, height):
    """
    Check image dimensions against the size and aspect ratio edX requires for video images

    Args:
        width (int): Image width in pixels
        height (int): Image height in pixels

    Returns:
        str or None: A user-facing description of the requirement, or None if the dimensions are acceptable
    """
    too_small = width < EDX_VIDEO_IMAGE_MIN_WIDTH or height < EDX_VIDEO_IMAGE_MIN_HEIGHT
    aspect_ratio_delta = abs(width / height - EDX_VIDEO_IMAGE_ASPECT_RATIO)
    if too_small or aspect_ratio_delta > EDX_VIDEO_IMAGE_ASPECT_RATIO_ERROR_MARGIN:
        return (
            f"Thumbnails must be 16:9 and at least "
            f"{EDX_VIDEO_IMAGE_MIN_WIDTH}x{EDX_VIDEO_IMAGE_MIN_HEIGHT} pixels. "
            f"This image is {width}x{height}."
        )
    return None


def post_video_thumbnail_to_edx(video, edx_endpoints=None):
    """
    Uploads a video's thumbnail to the Studio video image API of its collection's edX endpoints.
    Endpoints without a studio_base_url are skipped, as are images that edX would reject.

    Args:
        video (ui.models.Video): The video whose thumbnail should be uploaded
        edx_endpoints (iterable of ui.models.EdxEndpoint): Endpoints to upload to. Defaults to all
            endpoints configured for the video's collection.

    Returns:
        Dict[EdxEndpoint, requests.models.Response]: Each endpoint the image was sent to, mapped to
            the response from that request.
    """
    if edx_endpoints is None:
        edx_endpoints = models.EdxEndpoint.objects.filter(
            collections__id=video.collection_id
        )
    edx_endpoints = [endpoint for endpoint in edx_endpoints if endpoint.studio_base_url]
    thumbnail = video.videothumbnail_set.first()
    course_id = video.collection.edx_course_id
    if not edx_endpoints or thumbnail is None or not course_id:
        return {}

    try:
        s3_object = boto3.client("s3").get_object(
            Bucket=thumbnail.bucket_name, Key=thumbnail.s3_object_key
        )
        image_bytes = s3_object["Body"].read()
    except (BotoCoreError, ClientError):
        log.exception(
            "Can not add video thumbnail to edX, the image could not be read from S3",
            video_key=video.hexkey,
            s3_object_key=thumbnail.s3_object_key,
        )
        return {}
    error = get_edx_video_image_error(image_bytes)
    if error:
        # e.g. a frame auto-captured from a 4:3 or portrait video; uploads are already 16:9
        padded_bytes = pad_image_for_edx(image_bytes)
        if padded_bytes is None or get_edx_video_image_error(padded_bytes):
            log.warning(
                "Not adding video thumbnail to edX, the image does not meet edX's requirements",
                video_key=video.hexkey,
                reason=error,
            )
            return {}
        log.info(
            "Sending edX a 16:9 copy of the video thumbnail padded with black bars",
            video_key=video.hexkey,
            reason=error,
        )
        image_bytes = padded_bytes

    image_hash = hashlib.sha256(image_bytes).hexdigest()
    cache = caches["redis"]
    responses = {}
    for edx_endpoint in edx_endpoints:
        # One dialog save pushes the same image twice (thumbnail upload, then the video save
        # signal), often from two workers at once. Only one worker may send a given image at a
        # time (cache.add is atomic), and an image identical to the last one sent is skipped.
        last_sent_key = f"edx-video-image:{edx_endpoint.id}:{video.key}:last-sent"
        sending_key = (
            f"edx-video-image:{edx_endpoint.id}:{video.key}:{image_hash}:sending"
        )
        if not cache.add(sending_key, 1, timeout=EDX_VIDEO_IMAGE_SEND_LOCK_SECONDS):
            log.info(
                "Video thumbnail is already being sent to this edX endpoint, skipping",
                video_key=video.hexkey,
                edx_endpoint=edx_endpoint.name,
            )
            continue
        try:
            if cache.get(last_sent_key) == image_hash:
                log.info(
                    "Video thumbnail was just sent to this edX endpoint, skipping",
                    video_key=video.hexkey,
                    edx_endpoint=edx_endpoint.name,
                )
                continue
            edx_endpoint.refresh_access_token()
            resp = requests.post(
                edx_endpoint.video_image_api_url(course_id, video.key),
                files={"file": ("video_thumbnail.jpg", image_bytes, "image/jpeg")},
                headers={"Authorization": f"JWT {edx_endpoint.access_token}"},
                timeout=60,
            )
            resp.raise_for_status()
            cache.set(last_sent_key, image_hash, timeout=EDX_VIDEO_IMAGE_DEDUPE_SECONDS)
        except requests.exceptions.RequestException as exc:
            log.error(
                "Can not add video thumbnail to edX",
                video_key=video.hexkey,
                edx_endpoint=edx_endpoint.name,
                response=str(
                    get_error_response_summary_dict(exc.response)
                    if exc.response is not None
                    else {"exception": str(exc)}
                ),
            )
            resp = exc.response
        finally:
            cache.delete(sending_key)
        responses[edx_endpoint] = resp
    return responses


def update_video_on_edx(video_key, encoded_videos=None):
    """
    Update a video to their configured edX endpoints by making PATCH request to api/val/v0/videos/{edx_video_id}

    Args:
        video_key(str): video UUID key
    Returns:
        Dict[EdxEndpoint, requests.models.Response]: Each configured edX endpoint mapped to the response from the
            request to update the video to that endpoint.
    """
    video = models.Video.objects.filter(key=video_key).first()
    edx_endpoints = models.EdxEndpoint.objects.filter(
        collections__id__in=[video.collection.id]
    ).all()
    responses = {}
    for edx_endpoint in edx_endpoints:
        video_partial_update_url = edx_endpoint.full_api_url + str(video.key)
        try:
            edx_endpoint.refresh_access_token()
            payload = {
                "edx_video_id": str(video.key),
                "client_video_id": video.title,
                "duration": video.duration,
                "status": "file_complete",
            }
            if encoded_videos:
                payload["encoded_videos"] = encoded_videos
            resp = requests.patch(
                video_partial_update_url,
                json=payload,
                headers={
                    "Authorization": f"JWT {edx_endpoint.access_token}",
                },
            )
            resp.raise_for_status()
        except requests.exceptions.RequestException as exc:
            log.exception("Can not update video to edX")
            resp = exc.response
        responses[video_partial_update_url] = resp
    return responses


def get_duration_from_encode_job(encode_job):
    """
    Get video's duration from EncodeJob

    Args:
        encode_job: EncodeJob object
    Returns:
        duration: float
    """
    duration = 0.0
    if encode_job and (output_groups := encode_job.get("outputGroupDetails", [])):
        # Get the first output group
        output_group = output_groups[0]
        if outputs := output_group.get("outputDetails", []):
            # Get the first output
            output = outputs[0]
            duration_in_ms = output.get("durationInMs", 0)
            # Convert milliseconds to seconds
            duration = duration_in_ms / 1000.0

    return duration
