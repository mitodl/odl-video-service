"""APIs for coudsync app"""

import contextlib
import io
import json
import math
import random
import re
import time
from pathlib import Path
from collections import namedtuple
from datetime import datetime
from urllib.parse import quote
from uuid import uuid4

import boto3
import pytz
import requests
from boto3.s3.transfer import TransferConfig
from PIL import ExifTags, Image, ImageOps
from botocore.exceptions import ClientError
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from mitol.transcoding.api import media_convert_job

import structlog
from ui.api import get_duration_from_encode_job
from ui.constants import VideoStatus
from ui.encodings import EncodingNames
from ui.models import (
    TRANSCODE_PREFIX,
    Collection,
    EncodeJob,
    Video,
    VideoFile,
    VideoSubtitle,
    VideoThumbnail,
    delete_s3_objects,
)
from ui.utils import get_bucket

log = structlog.get_logger(__name__)

THUMBNAIL_PATTERN = "thumbnails/{}_thumbnail_{{count}}"
RETRANSCODE_FOLDER = "retranscode/"
ParsedVideoAttributes = namedtuple(
    "ParsedVideoAttributes",
    ["prefix", "session", "record_date", "record_date_str", "name"],
)


def _s3_uri_to_key(s3_uri: str) -> str:
    """Convert 's3://bucket/key/path' to 'key/path'."""
    parts = s3_uri.split("/", 3)
    return parts[3] if len(parts) >= 4 else ""


def _collect_output_keys(output_groups: list) -> list:
    """
    Extract S3 object keys from MediaConvert outputGroupDetails.

    For HLS groups a directory wildcard (``<dir>/*``) is appended so that
    individual ``.ts`` segment files — which are not listed in the job output —
    are also invalidated.

    ``RETRANSCODE_FOLDER`` is always stripped so that keys reflect the paths
    actually served by CloudFront after ``move_s3_objects`` has relocated them.
    """
    keys = []
    seen_wildcards = set()
    for group in output_groups:
        group_type = group.get("type", "")
        for path in group.get("playlistFilePaths", []):
            if key := _s3_uri_to_key(path):
                keys.append(key.replace(RETRANSCODE_FOLDER, "", 1))
        for output in group.get("outputDetails", []):
            for path in output.get("outputFilePaths", []):
                if key := _s3_uri_to_key(path):
                    key = key.replace(RETRANSCODE_FOLDER, "", 1)
                    keys.append(key)
                    if "HLS_GROUP" in group_type:
                        directory = key.rsplit("/", 1)[0]
                        wildcard = f"{directory}/*"
                        if wildcard not in seen_wildcards:
                            keys.append(wildcard)
                            seen_wildcards.add(wildcard)
    return keys


def _invalidate_cloudfront_paths(keys: list) -> None:
    """Create a single CloudFront invalidation batch for a list of S3 object keys."""
    dist_id = getattr(settings, "VIDEO_CDN_DISTRIBUTION_ID", "")
    if not dist_id or not keys:
        return
    paths = [f"/{k}" for k in keys]
    try:
        cf_client = boto3.client("cloudfront")
        cf_client.create_invalidation(
            DistributionId=dist_id,
            InvalidationBatch={
                "Paths": {"Quantity": len(paths), "Items": paths},
                "CallerReference": str(uuid4()),
            },
        )
    except Exception:
        log.exception(
            "CloudFront invalidation failed",
            distribution_id=dist_id,
            path_count=len(paths),
        )


def process_transcode_results(results: dict) -> None:
    """
    Create VideoFile and VideoThumbnail objects for a Video based on AWS MediaConvert job output.

    Args:
        results (dict): The MediaConvert job results from the callback.
    """
    # Fetch job details
    video_job = EncodeJob.objects.get(id=results.get("jobId"))
    video = Video.objects.get(id=video_job.object_id)

    # Capture before update_status() changes it
    is_retranscode = video.status == VideoStatus.RETRANSCODING

    # Update job state
    video_job.state = EncodeJob.State.COMPLETED
    video_job.message = results
    video_job.save()

    if is_retranscode:
        # Move old transcoded files
        video_key = video.video_s3_prefix()

        move_s3_objects(
            settings.VIDEO_S3_TRANSCODE_BUCKET,
            f"{RETRANSCODE_FOLDER}{TRANSCODE_PREFIX}/{video_key}",
            f"{TRANSCODE_PREFIX}/{video_key}",
        )
    # Extract output groups
    output_groups = results.get("outputGroupDetails", [])

    for group in output_groups:
        group_type = group.get("type")

        if "HLS_GROUP" in group_type:
            process_hls_outputs(group.get("playlistFilePaths", []), video)
        elif "FILE_GROUP" in group_type:
            process_mp4_outputs(group.get("outputDetails", []), video)

    video.duration = get_duration_from_encode_job(results)
    video.update_status(VideoStatus.COMPLETE)

    if is_retranscode:
        _invalidate_cloudfront_paths(_collect_output_keys(output_groups))

    # Ensure content_type and object_id are set for the EncodeJob
    content_type = ContentType.objects.get_for_model(video)
    video_job.content_type = content_type
    video_job.object_id = video.id
    video_job.save()


def process_hls_outputs(file_paths: list, video: Video) -> None:
    """
    Process HLS outputs and create VideoFile objects.
    Args:
        outputs (list): List of HLS output details.
        video (Video): The video object to associate with the outputs.
    """

    # Process HLS playlists
    for file_path in file_paths:
        if file_path.endswith("__index.m3u8"):
            file_path = Path(file_path)
            bucket_name = file_path.parts[1]
            s3_path = str(Path(*file_path.parts[2:])).replace(RETRANSCODE_FOLDER, "")

            cleanup_and_upsert_video_file(
                video, EncodingNames.HLS, s3_path, bucket_name
            )


def process_mp4_outputs(outputs: list, video: Video) -> None:
    """
    Process MP4 outputs and create VideoFile objects.
    Args:
        outputs (list): List of MP4 output details.
        video (Video): The video object to associate with the outputs.
    """

    # Process MP4 outputs
    for playlist in outputs:
        for file_path in playlist.get("outputFilePaths", []):
            file_path = Path(file_path)
            bucket_name = file_path.parts[1]
            s3_path = str(Path(*file_path.parts[2:])).replace(RETRANSCODE_FOLDER, "")
            if file_path.name.endswith(".mp4"):
                cleanup_and_upsert_video_file(
                    video, EncodingNames.DESKTOP_MP4, s3_path, bucket_name
                )
            elif file_path.name.endswith(".jpg"):
                VideoThumbnail.objects.update_or_create(
                    s3_object_key=s3_path,
                    defaults={
                        "video": video,
                        "bucket_name": bucket_name,
                        "preset_id": "",
                        "max_width": playlist.get("videoDetails", {}).get(
                            "widthInPx", 0
                        ),
                        "max_height": playlist.get("videoDetails", {}).get(
                            "heightInPx", 0
                        ),
                    },
                )


def get_error_type_from_et_error(et_error):
    """
    Parses an Elastic transcoder error string and matches the error to an error in VideoStatus

    Args:
        et_error (str): a string representing the description of the Elastic Transcoder Error

    Returns:
        ui.constants.VideoStatus: a string representing the video status
    """
    if not et_error:
        log.error("Elastic transcoder did not return an error string")
        return VideoStatus.TRANSCODE_FAILED_INTERNAL
    error_code = et_error.split(" ")[0]
    try:
        error_code = int(error_code)
    except ValueError:
        log.error("Elastic transcoder did not return an expected error string")
        return VideoStatus.TRANSCODE_FAILED_INTERNAL
    if 4000 <= error_code < 5000:
        return VideoStatus.TRANSCODE_FAILED_VIDEO
    return VideoStatus.TRANSCODE_FAILED_INTERNAL


def refresh_status(video: Video, encode_job: EncodeJob = None) -> None:
    """
    Check the encode job status & if not complete, update the status via a query to AWS.
    Args:
        video(ui.models.Video): Video object to refresh status of.
        encode_job(ui.models.EncodeJob): EncodeJob associated with Video
    """
    if video.status in (VideoStatus.TRANSCODING, VideoStatus.RETRANSCODING):
        if not encode_job:
            encode_job = video.encode_jobs.latest("created_at")
        mc_job = get_media_convert_job(encode_job.id)
        if mc_job["Job"]["Status"].lower() == VideoStatus.COMPLETE.lower():
            with open("./config/results.json", encoding="utf-8") as f:
                results = prepare_results(video, encode_job, f.read())
            process_transcode_results(results)
        elif mc_job["Job"]["Status"].lower() == VideoStatus.ERROR.lower():
            if video.status == VideoStatus.RETRANSCODING:
                video.update_status(VideoStatus.RETRANSCODE_FAILED)
            else:
                video.update_status(VideoStatus.TRANSCODE_FAILED_VIDEO)
            log.error("Transcoding failed", video_id=video.id)


def get_media_convert_job(job_id: str) -> dict:
    """
    Get the MediaConvert job details.
    Args:
        job_id (str): The MediaConvert job ID.
    Returns:
        dict: The MediaConvert job details.
    """
    client = boto3.client(
        "mediaconvert",
        region_name=settings.AWS_REGION,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        endpoint_url=settings.VIDEO_S3_TRANSCODE_ENDPOINT,
    )
    results = client.get_job(Id=job_id)
    return results


def prepare_results(video: Video, job: EncodeJob, results: str) -> dict:
    """
    Prepares the results from the MediaConvert job.
    Args:
        results (str): The MediaConvert job results.
    Returns:
        dict: The prepared results.
    """
    # Load the results from the JSON file

    results = results.replace("<JOB_ID>", job.id)

    for key in [
        "AWS_ACCOUNT_ID",
        "AWS_REGION",
        "VIDEO_TRANSCODE_QUEUE",
        "VIDEO_S3_TRANSCODE_BUCKET",
        "VIDEO_S3_TRANSCODE_PREFIX",
        "VIDEO_S3_THUMBNAIL_BUCKET",
        "VIDEO_S3_THUMBNAIL_PREFIX",
    ]:
        results = results.replace(
            f"<{key}>",
            (
                RETRANSCODE_FOLDER + getattr(settings, key, "")
                if (
                    key == "VIDEO_S3_TRANSCODE_PREFIX"
                    and video.status == VideoStatus.RETRANSCODING
                )
                else getattr(settings, key, "")
            ),
        )
    video_key = video.video_s3_prefix()
    results = results.replace("<VIDEO_KEY>", video_key).replace("<VIDEO_NAME>", "video")

    # Decode the JSON string
    try:
        results = json.loads(results)

        if video.status == VideoStatus.RETRANSCODING:
            results["outputGroupDetails"] = results.get("outputGroupDetails", [])[:-1]

    except json.JSONDecodeError:
        log.error("Failed to decode MediaConvert job results")
        return {}
    return results


def _get_template_path(video: Video) -> str | None:
    """
    Return the portrait MediaConvert template path for a shorts video,
    otherwise return None (default landscape template).
    """
    if video.collection.for_shorts:
        return settings.TRANSCODE_JOB_TEMPLATE_PORTRAIT
    return None


def transcode_video(
    video: Video, video_file: VideoFile, generate_mp4_videofile: bool = False
) -> None:
    """
    Start a transcode job for a video.

    Args:
        video (ui.models.Video): The video to transcode.
        video_file (ui.models.VideoFile): The S3 file to use for transcoding.
        generate_mp4_videofile (bool): Whether to generate an MP4 video file.
    """
    exclude_thumbnail = False
    if video.status == VideoStatus.RETRANSCODE_SCHEDULED:
        # Retranscode to a temporary folder and delete any stray S3 objects from there
        prefix = RETRANSCODE_FOLDER + TRANSCODE_PREFIX
        video_key = video.video_s3_prefix()
        # pylint:disable=no-value-for-parameter
        delete_s3_objects(
            settings.VIDEO_S3_TRANSCODE_BUCKET,
            f"{prefix}/{video_key}",
            as_filter=True,
        )
        exclude_thumbnail = True
    else:
        prefix = TRANSCODE_PREFIX

    job_id = str(uuid4())
    job_message_data = {"Status": "Submitted"}
    try:
        # Start the MediaConvert job
        job = media_convert_job(
            video_file.s3_object_key,
            destination_prefix=prefix,
            group_settings={
                "exclude_mp4": not generate_mp4_videofile,
                "exclude_thumbnail": exclude_thumbnail,
            },
            template_path=_get_template_path(video),
        )
        job_id = job.get("Job", {}).get("Id", job_id)
    except ClientError as exc:
        log.error("Transcode job creation failed", video_id=video.id)
        if video.status == VideoStatus.RETRANSCODE_SCHEDULED:
            video.update_status(VideoStatus.RETRANSCODE_FAILED)
        else:
            video.update_status(VideoStatus.TRANSCODE_FAILED_INTERNAL)
        if hasattr(exc, "response"):
            job_message_data = exc.response
        raise
    finally:
        # Get the content type for the Video model
        content_type = ContentType.objects.get_for_model(video)
        # Create or update the EncodeJob instance
        EncodeJob.objects.get_or_create(
            id=job_id,
            defaults={
                "content_type": content_type,
                "object_id": video.pk,
                "message": job_message_data,
            },
        )

        # Update video status
        if video.status == VideoStatus.RETRANSCODE_SCHEDULED:
            video.update_status(VideoStatus.RETRANSCODING)
        elif video.status not in (
            VideoStatus.TRANSCODE_FAILED_INTERNAL,
            VideoStatus.TRANSCODE_FAILED_VIDEO,
            VideoStatus.RETRANSCODE_FAILED,
        ):
            video.update_status(VideoStatus.TRANSCODING)


def create_lecture_collection_slug(video_attributes):
    """
    Create a name for a collection based on some attributes of an uploaded video filename

    Args:
        video_attributes (ParsedVideoAttributes): Named tuple of lecture video info
    """
    return (
        video_attributes.prefix
        if not video_attributes.session
        else "{}-{}".format(video_attributes.prefix, video_attributes.session)
    )


def create_lecture_video_title(video_attributes):
    """
    Create a title for a video based on some attributes of an uploaded video filename

    Args:
        video_attributes (ParsedVideoAttributes): Named tuple of lecture video info
    """
    video_title_date = (
        video_attributes.record_date_str
        if not video_attributes.record_date
        else video_attributes.record_date.strftime("%B %d, %Y")
    )
    return (
        "Lecture - {}".format(video_title_date)
        if video_title_date
        else video_attributes.name
    )


def process_watch_file(s3_filename):
    """
    Move the file from the watch bucket to the upload bucket, create model objects, and transcode.
    The given file is assumed to be a lecture capture video.

    Args:
        s3_filename (str): S3 object key (i.e.: a filename)
    """
    watch_bucket = get_bucket(settings.VIDEO_S3_WATCH_BUCKET)
    video_attributes = parse_lecture_video_filename(s3_filename)

    collection_slug = create_lecture_collection_slug(video_attributes)
    collection, _ = Collection.objects.get_or_create(
        slug=collection_slug,
        owner=User.objects.get(username=settings.LECTURE_CAPTURE_USER),
        defaults={"title": collection_slug},
    )
    with transaction.atomic():
        video = Video.objects.create(
            source_url="https://{}/{}/{}".format(
                settings.AWS_S3_DOMAIN,
                settings.VIDEO_S3_WATCH_BUCKET,
                quote(s3_filename),
            ),
            collection=collection,
            title=create_lecture_video_title(video_attributes),
            multiangle=True,  # Assume all videos in watch bucket are multi-angle
        )
        video_file = VideoFile.objects.create(
            s3_object_key=video.get_s3_key(),
            video_id=video.id,
            bucket_name=settings.VIDEO_S3_BUCKET,
        )

    # Copy the file to the upload bucket using a new s3 key
    s3_client = boto3.client("s3")
    copy_source = {"Bucket": watch_bucket.name, "Key": s3_filename}
    try:
        s3_client.copy(copy_source, settings.VIDEO_S3_BUCKET, video_file.s3_object_key)
    except:
        try:
            video.delete()
        except:
            log.error(
                "Failed to delete video after failed S3 file copy",
                video_hexkey=video.hexkey,
            )
            raise
        raise

    # Delete the original file from the watch bucket
    try:
        s3_client.delete_object(Bucket=settings.VIDEO_S3_WATCH_BUCKET, Key=s3_filename)
    except ClientError:
        log.error("Failed to delete from watch bucket", s3_object_key=s3_filename)

    # Start a transcode job for the video
    transcode_video(video, video_file)


def parse_lecture_video_filename(filename):
    """
    Parses the filename for required course information

    Args:
        filename(str): The name of the video file, in format
        'MIT-<course#>-<year>-<semester>-lec-mit-0000-<recording_date>-<time>-<session>.mp4'

    Returns:
        ParsedVideoAttributes: A named tuple of information extracted from the video file name
    """
    rx = (
        r"(.+)-lec-mit-0000-"  # prefix to be used as the start of the collection name
        r"(\w+)"  # Recording date (required)
        r"-(\d+)"  # Recording time (required)
        r"(-([L\d\-]+))?"  # Session or room number (optional)
        r".*\.\w"
    )  # Rest of filename including extension (required)
    matches = re.search(rx, filename)
    if not matches or len(matches.groups()) != 5:
        log.exception(
            "No matches found for filename %s with regex %s",
            positional_args=(filename, rx),
            filename=filename,
        )
        prefix = settings.UNSORTED_COLLECTION
        session = ""
        recording_date_str = ""
        record_date = None
    else:
        prefix, recording_date_str, _, _, session = matches.groups()
        try:
            record_date = datetime.strptime(recording_date_str, "%Y%b%d")
        except ValueError:
            record_date = None
    return ParsedVideoAttributes(
        prefix=prefix,
        session=session,
        record_date=record_date,
        record_date_str=recording_date_str,
        name=filename,
    )


def convert_srt_to_vtt(srt_content):
    """
    Converts SRT subtitle content to WebVTT format.

    Args:
        srt_content (str): The SRT file content.

    Returns:
        str: The converted VTT content.
    """
    # Replace SRT timestamp commas with VTT dots (00:00:00,000 -> 00:00:00.000)
    vtt = re.sub(r"(\d{2}:\d{2}:\d{2}),(\d{3})", r"\1.\2", srt_content)
    # Remove cue sequence numbers (digit-only lines preceding a timestamp line)
    vtt = re.sub(r"^\d+\s*\n(?=\d{2}:\d{2}:\d{2})", "", vtt, flags=re.MULTILINE)
    return "WEBVTT\n\n" + vtt.strip() + "\n"


def upload_subtitle_to_s3(caption_data, file_data):
    """
    Uploads a subtitle file to S3
    Args:
        caption_data(dict): Subtitle upload data
        file_data(InMemoryUploadedFile): File being uploaded

    Returns:
        VideoSubtitle or None: New or updated VideoSubtitle (or None)
    """
    video_key = caption_data.get("video")
    filename = caption_data.get("filename")
    language = caption_data.get("language", "en")
    if not video_key:
        return None
    try:
        video = Video.objects.get(key=video_key)
    except Video.DoesNotExist:
        log.error(
            "Attempted to upload subtitle to Video that does not exist",
            video_key=video_key,
        )
        raise

    # Extract file extension from filename
    file_extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else "vtt"
    # Validate extension
    if file_extension not in ["vtt", "srt"]:
        file_extension = "vtt"  # Default to vtt if invalid

    # Convert SRT to VTT before uploading
    if file_extension == "srt":
        srt_content = file_data.read().decode("utf-8")
        vtt_content = convert_srt_to_vtt(srt_content)
        file_data = io.BytesIO(vtt_content.encode("utf-8"))
        file_extension = "vtt"

    content_type = "text/vtt"

    s3 = boto3.resource("s3")
    bucket_name = settings.VIDEO_S3_SUBTITLE_BUCKET
    bucket = s3.Bucket(bucket_name)
    config = TransferConfig(**settings.AWS_S3_UPLOAD_TRANSFER_CONFIG)
    s3_key = video.subtitle_key(
        datetime.now(tz=pytz.UTC), language, extension=file_extension
    )

    try:
        bucket.upload_fileobj(
            Fileobj=file_data,
            Key=s3_key,
            ExtraArgs={"ContentType": content_type},
            Config=config,
        )
    except Exception:
        log.error("An error occurred uploading caption file", video_key=video_key)
        raise

    vt, created = VideoSubtitle.objects.get_or_create(
        video=video,
        language=language,
        bucket_name=bucket_name,
        defaults={"s3_object_key": s3_key},
    )
    if not created:
        try:
            vt.delete_from_s3()
        except ClientError:
            log.exception(
                "Could not delete old subtitle from S3", s3_object_key=vt.s3_object_key
            )
    vt.s3_object_key = s3
    vt.filename = filename
    vt.s3_object_key = s3_key
    vt.save()
    return vt


def convert_image_to_jpeg(file_data, max_width=None, max_height=None):
    """
    Convert an uploaded image to JPEG format using PIL, downscaling it if
    either dimension exceeds the configured maximums.

    If the source is already a JPEG and within the size limits, the original
    bytes are returned unchanged to avoid a lossy re-encode. If the file
    cannot be decoded or is not a JPEG/PNG, a ValueError is raised.

    Args:
        file_data: A file-like object containing the source image.
        max_width (int | None): Maximum allowed width in pixels. Defaults to
            ``settings.THUMBNAIL_UPLOAD_MAX_WIDTH``.
        max_height (int | None): Maximum allowed height in pixels. Defaults to
            ``settings.THUMBNAIL_UPLOAD_MAX_HEIGHT``.

    Returns:
        tuple[io.BytesIO, int, int]: A ``(buffer, width, height)`` tuple where
        *buffer* is a BytesIO containing the JPEG-encoded image and *width* /
        *height* are the final pixel dimensions.

    Raises:
        ValueError: If the file cannot be decoded or is not a JPEG or PNG image.
    """
    if max_width is None:
        max_width = settings.THUMBNAIL_UPLOAD_MAX_WIDTH
    if max_height is None:
        max_height = settings.THUMBNAIL_UPLOAD_MAX_HEIGHT
    if max_width <= 0 or max_height <= 0:
        raise ValueError(
            f"Invalid thumbnail max dimensions: {max_width}x{max_height}. Both must be positive integers."
        )
    try:
        with Image.open(file_data) as img:
            # Cache format before exif_transpose; the copy it returns loses .format.
            img_format = img.format
            if img_format not in ("JPEG", "PNG"):
                raise ValueError(
                    f"Unsupported image format: {img_format!r}. Only JPEG and PNG are supported."
                )

            # Read the orientation tag *before* transposing — exif_transpose()
            # always returns a new object, so an identity check is unreliable.
            exif_orientation = img.getexif().get(ExifTags.Base.Orientation, 1)
            exif_changed = exif_orientation != 1

            # Normalise EXIF orientation so pixel data matches display orientation
            # before any size computation or re-encode.
            img = ImageOps.exif_transpose(img)

            # Downscale if either dimension exceeds the configured limit.
            orig_w, orig_h = img.size
            if orig_w > max_width or orig_h > max_height:
                img.thumbnail((max_width, max_height), Image.LANCZOS)
            final_w, final_h = img.size
            if (
                img_format == "JPEG"
                and not exif_changed
                and (orig_w, orig_h) == (final_w, final_h)
            ):
                # No resize and no EXIF rotation — return original bytes to avoid lossy re-encode.
                file_data.seek(0)
                buf = io.BytesIO(file_data.read())
                buf.seek(0)
                return buf, final_w, final_h

            # PNG or resized JPEG: convert to a JPEG-compatible mode if needed.
            if img.mode not in ("L", "RGB", "CMYK"):
                img = img.convert("RGB")
            output = io.BytesIO()
            img.save(output, format="JPEG")
            output.seek(0)
            return output, final_w, final_h
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f"Could not decode image: {exc}") from exc


def replace_thumbnail_in_s3(thumbnail, file_data):
    """
    Replaces the image content of an existing VideoThumbnail by overwriting its S3
    object in-place so that the S3 key (and therefore the CloudFront URL) never changes.
    The image is downscaled to at most ``settings.THUMBNAIL_UPLOAD_MAX_WIDTH`` ×
    ``settings.THUMBNAIL_UPLOAD_MAX_HEIGHT`` pixels before upload; the resulting
    dimensions are persisted on the record.

    Args:
        thumbnail (VideoThumbnail): The existing thumbnail record whose S3 object
            should be overwritten.
        file_data (InMemoryUploadedFile): The new image file to upload.
    """
    jpeg_data, width, height = convert_image_to_jpeg(file_data)
    s3 = boto3.resource("s3")
    bucket = s3.Bucket(thumbnail.bucket_name)
    config = TransferConfig(**settings.AWS_S3_UPLOAD_TRANSFER_CONFIG)
    try:
        bucket.upload_fileobj(
            Fileobj=jpeg_data,
            Key=thumbnail.s3_object_key,
            ExtraArgs={"ContentType": "image/jpeg"},
            Config=config,
        )
    except Exception:
        log.error(
            "An error occurred replacing thumbnail in S3",
            s3_object_key=thumbnail.s3_object_key,
        )
        raise

    thumbnail.max_width = width
    thumbnail.max_height = height
    thumbnail.save(update_fields=["max_width", "max_height"])

    # Invalidate the CloudFront cache so the new image is served immediately.
    _invalidate_cloudfront_paths([thumbnail.s3_object_key])


def create_thumbnail_in_s3(video, file_data):
    """
    Uploads a new thumbnail image to S3 and creates a VideoThumbnail record for it.
    Used when a video has no existing thumbnail. The image is downscaled to at most
    ``settings.THUMBNAIL_UPLOAD_MAX_WIDTH`` × ``settings.THUMBNAIL_UPLOAD_MAX_HEIGHT``
    pixels before upload.

    Args:
        video (Video): The video to create the thumbnail for.
        file_data (InMemoryUploadedFile): The image file to upload.

    Returns:
        VideoThumbnail: The newly created VideoThumbnail instance.
    """
    jpeg_data, width, height = convert_image_to_jpeg(file_data)
    bucket_name = settings.VIDEO_S3_THUMBNAIL_BUCKET
    s3_key = "thumbnails/{video_key}/video_thumbnail.0000000.jpg".format(
        video_key=video.hexkey,
    )
    s3 = boto3.resource("s3")
    bucket = s3.Bucket(bucket_name)
    config = TransferConfig(**settings.AWS_S3_UPLOAD_TRANSFER_CONFIG)

    try:
        bucket.upload_fileobj(
            Fileobj=jpeg_data,
            Key=s3_key,
            ExtraArgs={"ContentType": "image/jpeg"},
            Config=config,
        )
    except Exception as exc:
        log.exception(
            "An error occurred uploading new thumbnail to S3",
            video_key=video.key,
            exc_info=exc,
        )
        raise

    return VideoThumbnail.objects.create(
        video=video,
        s3_object_key=s3_key,
        bucket_name=bucket_name,
        max_width=width,
        max_height=height,
    )


def move_s3_objects(bucket_name, from_prefix, to_prefix):
    """
    Copies files from one prefix (subfolder) to another, then deletes the originals

    Args:
        bucket_name (str): The bucket name
        from_prefix(str): The subfolder to copy from
        to_prefix(str): The subfolder to copy to
    """
    bucket = get_bucket(bucket_name)
    for obj in bucket.objects.filter(Prefix=from_prefix):
        copy_src = {"Bucket": bucket_name, "Key": obj.key}
        bucket.copy(copy_src, Key=obj.key.replace(from_prefix, to_prefix))
    delete_s3_objects.delay(bucket_name, from_prefix, as_filter=True)


def cleanup_and_upsert_video_file(
    video: Video, encoding: str, s3_path: str, bucket_name: str
) -> None:
    """
    Ensures there is only one VideoFile object for a given video and encoding.
    If there are duplicates, delete them. Then, create or update the VideoFile object
    with the given s3_path.

    Args:
        video (Video): The video to check for duplicate VideoFile objects.
        encoding (str): The encoding type to check for duplicates.
        s3_path (str): The s3_object_key that should be retained.
        bucket_name (str): The S3 bucket name where the video file is stored.
    """
    video_files = VideoFile.objects.filter(video=video, encoding=encoding)
    for vf in video_files:
        if vf.s3_object_key != s3_path:
            try:
                log.debug(
                    "Deleting duplicate VideoFile",
                    video_id=video.id,
                    video_file_id=vf.id,
                    s3_object_key=vf.s3_object_key,
                )
                vf.delete()
            except Exception as exc:
                log.error(
                    "Failed to delete duplicate VideoFile",
                    video_id=video.id,
                    video_file_id=vf.id,
                    s3_object_key=vf.s3_object_key,
                    error=str(exc),
                )

    VideoFile.objects.update_or_create(
        s3_object_key=s3_path,
        defaults={
            "video": video,
            "bucket_name": bucket_name,
            "encoding": encoding,
            "preset_id": "",
        },
    )


# S3 requires every part except the last to be at least 5 MiB.
S3_MIN_PART_SIZE = 5 * 1024 * 1024


class TransferError(Exception):
    """Raised when the source returns an unexpected response and cannot be transferred."""


@contextlib.contextmanager
def upload_lock(redis_client, lock_key, ttl):
    """
    Best-effort distributed lock serializing concurrent runs of the same upload.

    Under ``acks_late`` a long upload can be redelivered to a second worker while the first is
    still running; this lock keeps them from racing the same multipart upload. Yields ``True``
    if acquired (and releases on exit), ``False`` otherwise.
    """
    acquired = bool(redis_client.set(lock_key, b"1", nx=True, ex=ttl))
    try:
        yield acquired
    finally:
        if acquired:
            try:
                redis_client.delete(lock_key)
            except Exception:  # noqa: BLE001 - releasing the lock must never mask the result
                log.warning("failed to release upload lock", lock_key=lock_key)


class S3Transfer:
    """
    Resumable, bounded-memory transfer of a remote file to S3.

    Drives an S3 multipart upload by fetching the source in byte ranges, so a mid-transfer
    stall costs a single part re-fetch (~one ``part_size``) rather than restarting the whole
    upload. The caller supplies ``content_type`` and ``total`` (typically read from the
    source's response headers); ``total`` may be ``None``, in which case it is discovered
    from a ranged request's ``Content-Range``.
    """

    def __init__(
        self,
        *,
        bucket,
        key,
        content_type,
        total,
        s3_client,
        range_fetcher,
        part_size,
        max_range_attempts=5,
        backoff_base=2,
        backoff_max=60,
        progress_callback=None,
    ):
        self.bucket = bucket
        self.key = key
        self.content_type = content_type
        self.total = total
        self.s3 = s3_client
        # range_fetcher(start, end) -> a response with .status_code, .content and
        # .headers, fetching the inclusive byte range from the source. Auth and
        # transport live in the caller (e.g. cloudsync.dropbox_api); retries live here.
        self.range_fetcher = range_fetcher
        self.part_size = max(part_size, S3_MIN_PART_SIZE)
        self.max_range_attempts = max_range_attempts
        self.backoff_base = backoff_base
        self.backoff_max = backoff_max
        self.progress_callback = progress_callback

    def run(self):
        """Transfer the source to S3, choosing the single-PUT or multipart path by size."""
        total = self.total if self.total is not None else self._discover_total()
        if total <= self.part_size:
            self._put_single(total)
        else:
            self._multipart(total)

    def _put_single(self, total):
        """Upload a small file in one PUT."""
        body = self._fetch_range(0, total - 1)
        self.s3.put_object(
            Bucket=self.bucket, Key=self.key, Body=body, ContentType=self.content_type
        )
        self._report(len(body), total)

    def _multipart(self, total):
        """Upload a large file as an S3 multipart upload, one byte range per part."""
        num_parts = math.ceil(total / self.part_size)
        upload_id, completed = self._resume_or_create(num_parts)
        try:
            parts = {n: etag for n, (etag, _size) in completed.items()}
            bytes_done = sum(size for _etag, size in completed.values())
            for part_number in range(1, num_parts + 1):
                if part_number in parts:
                    continue
                start = (part_number - 1) * self.part_size
                end = min(start + self.part_size, total) - 1
                body = self._fetch_range(start, end)
                response = self.s3.upload_part(
                    Bucket=self.bucket,
                    Key=self.key,
                    PartNumber=part_number,
                    UploadId=upload_id,
                    Body=body,
                )
                parts[part_number] = response["ETag"]
                bytes_done += len(body)
                self._report(bytes_done, total)
            self.s3.complete_multipart_upload(
                Bucket=self.bucket,
                Key=self.key,
                UploadId=upload_id,
                MultipartUpload={
                    "Parts": [
                        {"PartNumber": n, "ETag": parts[n]} for n in sorted(parts)
                    ]
                },
            )
        except Exception:
            # Drop already-uploaded parts so they don't linger and incur storage cost.
            # A hard worker kill bypasses this; the bucket lifecycle rule is the backstop.
            self._abort(upload_id)
            raise

    def _resume_or_create(self, num_parts):
        """
        Adopt an in-progress multipart upload for this key if one exists, else create one.

        Returns ``(upload_id, completed)`` where ``completed`` maps part number ->
        ``(etag, size)`` for parts already uploaded. Older duplicate uploads for the key are
        aborted; an adopted upload whose part sizes no longer match ``part_size`` is discarded
        and restarted so byte boundaries stay aligned.
        """
        existing = self._existing_uploads_for_key()
        if existing:
            chosen = existing[0]["UploadId"]
            for older in existing[1:]:
                self._abort(older["UploadId"])
            completed = self._completed_parts(chosen)
            if self._has_size_drift(completed, num_parts):
                log.info("multipart part size drift; restarting upload", key=self.key)
                self._abort(chosen)
            else:
                return chosen, completed
        return self._create_upload(), {}

    def _existing_uploads_for_key(self):
        """In-progress multipart uploads for this exact key, newest first."""
        response = self.s3.list_multipart_uploads(Bucket=self.bucket, Prefix=self.key)
        uploads = [u for u in response.get("Uploads", []) if u["Key"] == self.key]
        return sorted(uploads, key=lambda u: u["Initiated"], reverse=True)

    def _completed_parts(self, upload_id):
        """Map of part number -> (etag, size) for parts already uploaded to ``upload_id``."""
        parts = {}
        marker = 0
        while True:
            response = self.s3.list_parts(
                Bucket=self.bucket,
                Key=self.key,
                UploadId=upload_id,
                PartNumberMarker=marker,
            )
            for part in response.get("Parts", []):
                parts[part["PartNumber"]] = (part["ETag"], part["Size"])
            if not response.get("IsTruncated"):
                return parts
            marker = response["NextPartNumberMarker"]

    def _has_size_drift(self, completed, num_parts):
        """True if any non-final completed part no longer matches the configured part size."""
        for part_number, (_etag, size) in completed.items():
            if part_number > num_parts:
                return True
            if part_number < num_parts and size != self.part_size:
                return True
        return False

    def _create_upload(self):
        """Create a new multipart upload and return its id."""
        return self.s3.create_multipart_upload(
            Bucket=self.bucket, Key=self.key, ContentType=self.content_type
        )["UploadId"]

    def _abort(self, upload_id):
        """Abort a multipart upload, logging (not raising) if the abort itself fails."""
        try:
            self.s3.abort_multipart_upload(
                Bucket=self.bucket, Key=self.key, UploadId=upload_id
            )
        except ClientError:
            log.exception("failed to abort multipart upload", key=self.key)

    def _fetch_range(self, start, end):
        """
        Fetch ``bytes=start-end`` from the source with retries and exponential backoff.

        Each attempt calls ``range_fetcher`` afresh, so a fetcher that re-resolves auth (an
        expired token or a signed CDN URL) recovers for free. The last error is raised once the
        attempt budget is exhausted (e.g. a permanently revoked link).
        """
        last_error = None
        for attempt in range(1, self.max_range_attempts + 1):
            try:
                response = self.range_fetcher(start, end)
                if response.status_code not in (200, 206):
                    raise TransferError(
                        f"unexpected status {response.status_code} for bytes {start}-{end}"
                    )
                return response.content
            except (requests.exceptions.RequestException, TransferError) as exc:
                last_error = exc
                if attempt >= self.max_range_attempts:
                    break
                log.warning(
                    "retrying range fetch",
                    start=start,
                    end=end,
                    attempt=attempt,
                    error=str(exc),
                )
                self._sleep_backoff(attempt)
        raise last_error

    def _sleep_backoff(self, attempt):
        """Sleep for an exponentially growing, jittered delay before the next attempt."""
        delay = min(self.backoff_max, self.backoff_base * (2 ** (attempt - 1)))
        time.sleep(delay + random.uniform(0, delay / 2))

    def _discover_total(self):
        """Determine the total size from a ranged request's Content-Range header."""
        response = self.range_fetcher(0, 0)
        match = re.match(
            r"bytes \d+-\d+/(\d+)", response.headers.get("Content-Range", "")
        )
        if not match:
            raise TransferError("could not determine total size of source")
        return int(match.group(1))

    def _report(self, uploaded, total):
        """Invoke the progress callback, if any, with cumulative bytes and the total."""
        if self.progress_callback:
            self.progress_callback(uploaded, total)
