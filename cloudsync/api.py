"""APIs for coudsync app"""

import json
from pathlib import Path
import re
from collections import namedtuple
from datetime import datetime
from urllib.parse import quote
from uuid import uuid4

import boto3
import pytz
from boto3.s3.transfer import TransferConfig
from botocore.exceptions import ClientError
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from mitol.transcoding.api import media_convert_job

from odl_video import logging
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

log = logging.getLogger(__name__)

THUMBNAIL_PATTERN = "thumbnails/{}_thumbnail_{{count}}"
RETRANSCODE_FOLDER = "retranscode/"
ParsedVideoAttributes = namedtuple(
    "ParsedVideoAttributes",
    ["prefix", "session", "record_date", "record_date_str", "name"],
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

    # Update job state
    video_job.state = EncodeJob.State.COMPLETED
    video_job.message = results
    video_job.save()

    if video.status == VideoStatus.RETRANSCODING:
        # Move old transcoded files
        move_s3_objects(
            settings.VIDEO_S3_TRANSCODE_BUCKET,
            f"{RETRANSCODE_FOLDER}{TRANSCODE_PREFIX}/{video.hexkey}",
            f"{TRANSCODE_PREFIX}/{video.hexkey}",
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
    video.status = VideoStatus.COMPLETE
    video.save()

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
            VideoFile.objects.update_or_create(
                s3_object_key=s3_path,
                defaults={
                    "video": video,
                    "bucket_name": bucket_name,
                    "encoding": EncodingNames.HLS,
                    "preset_id": "",
                },
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
                VideoFile.objects.update_or_create(
                    s3_object_key=s3_path,
                    defaults={
                        "video": video,
                        "bucket_name": bucket_name,
                        "encoding": EncodingNames.DESKTOP_MP4,
                        "preset_id": "",
                    },
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

    results = results.replace("<VIDEO_KEY>", video.key.hex).replace(
        "<VIDEO_NAME>", "video"
    )

    # Decode the JSON string
    try:
        results = json.loads(results)

        if video.status == VideoStatus.RETRANSCODING:
            results["outputGroupDetails"] = results.get("outputGroupDetails", [])[:-1]

    except json.JSONDecodeError:
        log.error("Failed to decode MediaConvert job results")
        return {}
    return results


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
        # pylint:disable=no-value-for-parameter
        delete_s3_objects(
            settings.VIDEO_S3_TRANSCODE_BUCKET,
            f"{prefix}/{video.hexkey}",
            as_filter=True,
        )
        exclude_thumbnail = True
    else:
        prefix = TRANSCODE_PREFIX

    job_id = str(uuid4())
    err_msg = {"Job": {"Status": "Error", "Id": job_id}}
    try:
        # Start the MediaConvert job
        job = media_convert_job(
            video_file.s3_object_key,
            destination_prefix=prefix,
            group_settings={
                "exclude_mp4": not generate_mp4_videofile,
                "exclude_thumbnail": exclude_thumbnail,
            },
        )
        job_id = job.get("Job", {}).get("Id", job_id)
    except ClientError as exc:
        log.error("Transcode job creation failed", video_id=video.id)
        if video.status == VideoStatus.RETRANSCODE_SCHEDULED:
            video.update_status(VideoStatus.RETRANSCODE_FAILED)
        else:
            video.update_status(VideoStatus.TRANSCODE_FAILED_INTERNAL)
        if hasattr(exc, "response"):
            err_msg = exc.response
            job_id = err_msg["Job"].get("Id", job_id) if "Job" in err_msg else job_id
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
                "message": err_msg,
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

    s3 = boto3.resource("s3")
    bucket_name = settings.VIDEO_S3_SUBTITLE_BUCKET
    bucket = s3.Bucket(bucket_name)
    config = TransferConfig(**settings.AWS_S3_UPLOAD_TRANSFER_CONFIG)
    s3_key = video.subtitle_key(datetime.now(tz=pytz.UTC), language)

    try:
        bucket.upload_fileobj(
            Fileobj=file_data,
            Key=s3_key,
            ExtraArgs={"ContentType": "mime/vtt"},
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
