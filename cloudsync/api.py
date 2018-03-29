"""APIs for coudsync app"""
import logging
import re
from collections import namedtuple
from datetime import datetime

import pytz
import boto3
from boto3.s3.transfer import TransferConfig
from botocore.exceptions import ClientError
from django.conf import settings
from django.contrib.auth.models import User
from django.db import transaction

from cloudsync.exceptions import VideoFilenameError
from cloudsync.utils import VideoTranscoder
from ui.constants import VideoStatus
from ui.encodings import EncodingNames
from ui.models import (
    VideoFile,
    VideoThumbnail,
    Collection,
    Video,
    VideoSubtitle)
from ui.utils import get_et_preset, get_bucket, get_et_job

log = logging.getLogger(__name__)

THUMBNAIL_PATTERN = "thumbnails/{}_thumbnail_{{count}}"
ParsedVideoAttributes = namedtuple(
    'ParsedVideoAttributes',
    ['prefix', 'session', 'record_date', 'record_date_str']
)


def process_transcode_results(video, job):
    """
    Create VideoFile and VideoThumbnail objects for a Video based on AWS ET job output

    Args:
        video(Video): Video object to which files and thumbnails belong
        job(JSON): JSON representation of AWS ET job output
    """

    for playlist in job['Playlists']:
        VideoFile.objects.get_or_create(
            s3_object_key='{}.m3u8'.format(playlist['Name']),  # This assumes HLS encoding
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
            VideoThumbnail.objects.get_or_create(
                s3_object_key=thumb.key,
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
    if video.status == VideoStatus.TRANSCODING:
        if not encode_job:
            encode_job = video.encode_jobs.latest("created_at")
        et_job = get_et_job(encode_job.id)
        if et_job['Status'] == VideoStatus.COMPLETE:
            process_transcode_results(video, et_job)
            video.update_status(VideoStatus.COMPLETE)
        elif et_job['Status'] == VideoStatus.ERROR:
            video.update_status(get_error_type_from_et_error(et_job.get('Output', {}).get('StatusDetail')))
            log.error('Transcoding failed for video %d', video.id)
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

    user_meta = {'pipeline': 'odl-video-service-{}'.format(settings.ENVIRONMENT).lower()}

    try:
        transcoder.encode(video_input, outputs, Playlists=playlists, UserMetadata=user_meta)
    except ClientError as exc:
        log.error('Transcode job creation failed for video %s', video.id)
        video.update_status(VideoStatus.TRANSCODE_FAILED_INTERNAL)
        if hasattr(exc, 'response'):
            transcoder.message = exc.response
        raise
    finally:
        transcoder.create_job_for_object(video)
        if video.status not in (VideoStatus.TRANSCODE_FAILED_INTERNAL, VideoStatus.TRANSCODE_FAILED_VIDEO, ):
            video.update_status(VideoStatus.TRANSCODING)


def create_lecture_collection_title(video_attributes):
    """
    Create a title for a collection based on some attributes of an uploaded video filename

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
    return 'Lecture - {}'.format(video_title_date)


def process_watch_file(s3_filename):
    """
    Move the file from the watch bucket to the upload bucket, create model objects, and transcode.
    The given file is assumed to be a lecture capture video.

    Args:
        s3_filename (str): S3 object key (i.e.: a filename)
    """
    watch_bucket = get_bucket(settings.VIDEO_S3_WATCH_BUCKET)
    video_attributes = parse_lecture_video_filename(s3_filename)

    collection, _ = Collection.objects.get_or_create(
        title=create_lecture_collection_title(video_attributes),
        owner=User.objects.get(username=settings.LECTURE_CAPTURE_USER)
    )
    with transaction.atomic():
        video = Video.objects.create(
            source_url='https://{}/{}/{}'.format(settings.AWS_S3_DOMAIN, settings.VIDEO_S3_WATCH_BUCKET, s3_filename),
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
            log.error('Failed to delete video id %s after failed S3 file copy', video.hexkey)
            raise
        raise

    # Delete the original file from the watch bucket
    try:
        s3_client.delete_object(Bucket=settings.VIDEO_S3_WATCH_BUCKET, Key=s3_filename)
    except ClientError:
        log.error('Failed to delete %s from watch bucket', s3_filename)

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
        raise VideoFilenameError('No matches found for filename %s with regex %s', filename, rx)
    prefix, recording_date_str, _, _, session = matches.groups()
    try:
        record_date = datetime.strptime(recording_date_str, "%Y%b%d")
    except ValueError:
        record_date = None
    return ParsedVideoAttributes(
        prefix=prefix,
        session=session,
        record_date=record_date,
        record_date_str=recording_date_str
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
        log.error("Attempted to upload subtitle to Video that does not exist (key: %d)", video_key)
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
        log.error('An error occurred uploading caption file to video %s', video_key)
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
            log.exception('Could not delete old subtitle from S3: %s', vt.s3_object_key)
    vt.s3_object_key = s3
    vt.filename = filename
    vt.s3_object_key = s3_key
    vt.save()
    return vt
