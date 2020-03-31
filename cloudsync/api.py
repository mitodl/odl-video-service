"""APIs for coudsync app"""
import re
from collections import namedtuple
from datetime import datetime
from urllib.parse import quote

import pytz
import boto3
from boto3.s3.transfer import TransferConfig
from botocore.exceptions import ClientError
from django.conf import settings
from django.contrib.auth.models import User
from django.db import transaction

from cloudsync.utils import VideoTranscoder
from ui.constants import VideoStatus
from ui.encodings import EncodingNames
from ui.models import (
    TRANSCODE_PREFIX,
    VideoFile,
    VideoThumbnail,
    Collection,
    Video,
    VideoSubtitle,
    delete_s3_objects
)
from ui.utils import get_et_preset, get_bucket, get_et_job
from odl_video import logging

log = logging.getLogger(__name__)

THUMBNAIL_PATTERN = "thumbnails/{}_thumbnail_{{count}}"
RETRANSCODE_FOLDER = "retranscode/"
ParsedVideoAttributes = namedtuple(
    'ParsedVideoAttributes',
    ['prefix', 'session', 'record_date', 'record_date_str', 'name']
)


def process_transcode_results(video, job):
    """
    Create VideoFile and VideoThumbnail objects for a Video based on AWS ET job output

    Args:
        video(Video): Video object to which files and thumbnails belong
        job(JSON): JSON representation of AWS ET job output
    """
    if video.status == VideoStatus.RETRANSCODING:
        # Overwrite old playlists/files with new transcoding output
        move_s3_objects(
            settings.VIDEO_S3_TRANSCODE_BUCKET,
            f"{RETRANSCODE_FOLDER}{TRANSCODE_PREFIX}/{video.hexkey}",
            f"{TRANSCODE_PREFIX}/{video.hexkey}")

    for playlist in job['Playlists']:
        VideoFile.objects.update_or_create(
            # This assumes HLS encoding
            s3_object_key='{}.m3u8'.format(playlist['Name'].replace(RETRANSCODE_FOLDER, "")),
            defaults={
                'video': video,
                'bucket_name': settings.VIDEO_S3_TRANSCODE_BUCKET,
                'encoding': EncodingNames.HLS,
                'preset_id': ','.join([output['PresetId'] for output in job['Outputs']]),
            }

        )
    for output in job['Outputs']:
        if 'ThumbnailPattern' not in output:
            continue
        thumbnail_pattern = output['ThumbnailPattern'].replace("{count}", "")
        preset = get_et_preset(output['PresetId'])
        bucket = get_bucket(settings.VIDEO_S3_THUMBNAIL_BUCKET)
        for thumb in bucket.objects.filter(Prefix=thumbnail_pattern):
            VideoThumbnail.objects.update_or_create(
                s3_object_key=thumb.key.replace(RETRANSCODE_FOLDER, ""),
                defaults={
                    'video': video,
                    'bucket_name': settings.VIDEO_S3_THUMBNAIL_BUCKET,
                    'preset_id': output['PresetId'],
                    'max_height': int(preset['Thumbnails']['MaxHeight']),
                    'max_width': int(preset['Thumbnails']['MaxWidth'])
                }
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
        log.error('Elastic transcoder did not return an error string')
        return VideoStatus.TRANSCODE_FAILED_INTERNAL
    error_code = et_error.split(' ')[0]
    try:
        error_code = int(error_code)
    except ValueError:
        log.error('Elastic transcoder did not return an expected error string')
        return VideoStatus.TRANSCODE_FAILED_INTERNAL
    if 4000 <= error_code < 5000:
        return VideoStatus.TRANSCODE_FAILED_VIDEO
    return VideoStatus.TRANSCODE_FAILED_INTERNAL


def refresh_status(video, encode_job=None):
    """
    Check the encode job status & if not complete, update the status via a query to AWS.

    Args:
        video(ui.models.Video): Video object to refresh status of.
        encode_job(dj_elastictranscoder.models.EncodeJob): EncodeJob associated with Video
    """
    if video.status in (VideoStatus.TRANSCODING, VideoStatus.RETRANSCODING):
        if not encode_job:
            encode_job = video.encode_jobs.latest("created_at")
        et_job = get_et_job(encode_job.id)
        if et_job['Status'] == VideoStatus.COMPLETE:
            process_transcode_results(video, et_job)
            video.update_status(VideoStatus.COMPLETE)
        elif et_job['Status'] == VideoStatus.ERROR:
            if video.status == VideoStatus.RETRANSCODING:
                video.update_status(VideoStatus.RETRANSCODE_FAILED)
            else:
                video.update_status(get_error_type_from_et_error(et_job.get('Output', {}).get('StatusDetail')))
            log.error('Transcoding failed', video_id=video.id)
        encode_job.message = et_job
        encode_job.save()


def transcode_video(video, video_file):
    """
    Start a transcode job for a video

    Args:
        video(ui.models.Video): the video to transcode
        video_file(ui.models.Videofile): the s3 file to use for transcoding
    """

    video_input = {
        'Key': video_file.s3_object_key,
    }

    if video.status == VideoStatus.RETRANSCODE_SCHEDULED:
        # Retranscode to a temporary folder and delete any stray S3 objects from there
        prefix = RETRANSCODE_FOLDER
        # pylint:disable=no-value-for-parameter
        delete_s3_objects(
            settings.VIDEO_S3_TRANSCODE_BUCKET,
            f"{prefix}{TRANSCODE_PREFIX}/{video.hexkey}",
            as_filter=True
        )
    else:
        prefix = ""

    # Generate an output video file for each encoding (assumed to be HLS)
    outputs = [{
        'Key': f"{prefix}{video.transcode_key(preset)}",
        'PresetId': preset,
        'SegmentDuration': '10.0'
    } for preset in settings.ET_PRESET_IDS]

    playlists = [{
        'Format': 'HLSv3',
        'Name': f"{prefix}{video.transcode_key('_index')}",
        'OutputKeys': [output['Key'] for output in outputs]
    }]

    # Generate thumbnails for the 1st encoding (no point in doing so for each).
    if video.status != VideoStatus.RETRANSCODE_SCHEDULED:
        outputs[0]['ThumbnailPattern'] = f"{prefix}{THUMBNAIL_PATTERN.format(video_file.s3_basename)}"

    transcoder = VideoTranscoder(
        settings.ET_PIPELINE_ID,
        settings.AWS_REGION,
        settings.AWS_ACCESS_KEY_ID,
        settings.AWS_SECRET_ACCESS_KEY
    )

    user_meta = {'pipeline': 'odl-video-service-{}'.format(settings.ENVIRONMENT).lower()}

    try:
        transcoder.encode(video_input, outputs, Playlists=playlists, UserMetadata=user_meta)
    except ClientError as exc:
        log.error('Transcode job creation failed', video_id=video.id)
        if video.status == VideoStatus.RETRANSCODE_SCHEDULED:
            video.status = VideoStatus.RETRANSCODE_FAILED
        else:
            video.update_status(VideoStatus.TRANSCODE_FAILED_INTERNAL)
        video.save()
        if hasattr(exc, 'response'):
            transcoder.message = exc.response
        raise
    finally:
        transcoder.create_job_for_object(video)
        if video.status == VideoStatus.RETRANSCODE_SCHEDULED:
            video.update_status(VideoStatus.RETRANSCODING)
        elif video.status not in (
                VideoStatus.TRANSCODE_FAILED_INTERNAL,
                VideoStatus.TRANSCODE_FAILED_VIDEO,
                VideoStatus.RETRANSCODE_FAILED
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
        else '{}-{}'.format(video_attributes.prefix, video_attributes.session)
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
        else video_attributes.record_date.strftime('%B %d, %Y')
    )
    return 'Lecture - {}'.format(video_title_date) if video_title_date else video_attributes.name


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
        defaults={
            'title': collection_slug
        }
    )
    with transaction.atomic():
        video = Video.objects.create(
            source_url='https://{}/{}/{}'.format(
                settings.AWS_S3_DOMAIN,
                settings.VIDEO_S3_WATCH_BUCKET,
                quote(s3_filename)
            ),
            collection=collection,
            title=create_lecture_video_title(video_attributes),
            multiangle=True  # Assume all videos in watch bucket are multi-angle
        )
        video_file = VideoFile.objects.create(
            s3_object_key=video.get_s3_key(),
            video_id=video.id,
            bucket_name=settings.VIDEO_S3_BUCKET
        )

    # Copy the file to the upload bucket using a new s3 key
    s3_client = boto3.client('s3')
    copy_source = {
        'Bucket': watch_bucket.name,
        'Key': s3_filename
    }
    try:
        s3_client.copy(copy_source, settings.VIDEO_S3_BUCKET, video_file.s3_object_key)
    except:
        try:
            video.delete()
        except:
            log.error('Failed to delete video after failed S3 file copy',
                      video_hexkey=video.hexkey)
            raise
        raise

    # Delete the original file from the watch bucket
    try:
        s3_client.delete_object(Bucket=settings.VIDEO_S3_WATCH_BUCKET, Key=s3_filename)
    except ClientError:
        log.error('Failed to delete from watch bucket',
                  s3_object_key=s3_filename)

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
    rx = (r'(.+)-lec-mit-0000-'  # prefix to be used as the start of the collection name
          r'(\w+)'  # Recording date (required)
          r'-(\d+)'  # Recording time (required)
          r'(-([L\d\-]+))?'  # Session or room number (optional)
          r'.*\.\w')  # Rest of filename including extension (required)
    matches = re.search(rx, filename)
    if not matches or len(matches.groups()) != 5:
        log.error('No matches found',
                  filename=filename, regex=rx, exc_info=True)
        prefix = settings.UNSORTED_COLLECTION
        session = ''
        recording_date_str = ''
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
        name=filename
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
    video_key = caption_data.get('video')
    filename = caption_data.get('filename')
    language = caption_data.get('language', 'en')
    if not video_key:
        return None
    try:
        video = Video.objects.get(key=video_key)
    except Video.DoesNotExist:
        log.error("Attempted to upload subtitle to Video that does not exist",
                  video_key=video_key)
        raise

    s3 = boto3.resource('s3')
    bucket_name = settings.VIDEO_S3_SUBTITLE_BUCKET
    bucket = s3.Bucket(bucket_name)
    config = TransferConfig(**settings.AWS_S3_UPLOAD_TRANSFER_CONFIG)
    s3_key = video.subtitle_key(datetime.now(tz=pytz.UTC), language)

    try:
        bucket.upload_fileobj(
            Fileobj=file_data,
            Key=s3_key,
            ExtraArgs={"ContentType": 'mime/vtt'},
            Config=config
        )
    except Exception:
        log.error('An error occurred uploading caption file',
                  video_key=video_key)
        raise

    vt, created = VideoSubtitle.objects.get_or_create(
        video=video,
        language=language,
        bucket_name=bucket_name,
        defaults={
            "s3_object_key": s3_key
        })
    if not created:
        try:
            vt.delete_from_s3()
        except ClientError:
            log.error('Could not delete old subtitle from S3',
                      s3_object_key=vt.s3_object_key,
                      exc_info=True)
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
        copy_src = {
            "Bucket": bucket_name,
            "Key": obj.key
        }
        bucket.copy(copy_src, Key=obj.key.replace(from_prefix, to_prefix))
    delete_s3_objects.delay(bucket_name, from_prefix, as_filter=True)
