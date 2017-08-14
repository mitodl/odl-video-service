"""APIs for coudsync app"""
import logging
import re

import boto3
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
    Video)
from ui.utils import get_et_preset, get_bucket, get_et_job

log = logging.getLogger(__name__)

THUMBNAIL_PATTERN = "thumbnails/{}_thumbnail_{{count}}"


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
            video.update_status(VideoStatus.TRANSCODE_FAILED)
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
    try:
        transcoder.encode(video_input, outputs, Playlists=playlists)
    except ClientError as exc:
        log.error('Transcode job creation failed for video %s', video.id)
        video.update_status(VideoStatus.TRANSCODE_FAILED)
        if hasattr(exc, 'response'):
            transcoder.message = exc.response
        raise
    finally:
        transcoder.create_job_for_object(video)
        if video.status != VideoStatus.TRANSCODE_FAILED:
            video.update_status(VideoStatus.TRANSCODING)


def process_watch_file(s3key):
    """
    Move the file from the watch bucket to the upload bucket, create model objects, and transcode

    Args:
        s3key(str): S3 object key

    """
    watch_bucket = get_bucket(settings.VIDEO_S3_WATCH_BUCKET)

    title = extract_title(s3key)
    collection, _ = Collection.objects.get_or_create(title=title,
                                                     owner=User.objects.get(username=settings.LECTURE_CAPTURE_USER))

    # Create the necessary models
    with transaction.atomic():
        video = Video.objects.create(
            source_url='https://{}/{}/{}'.format(settings.AWS_S3_DOMAIN, settings.VIDEO_S3_WATCH_BUCKET, s3key),
            collection=collection,
            title=s3key,
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
        'Key': s3key
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
        s3_client.delete_object(Bucket=settings.VIDEO_S3_WATCH_BUCKET, Key=s3key)
    except ClientError:
        log.error('Failed to delete %s from watch bucket', s3key)

    # Start a transcode job for the video
    transcode_video(video, video_file)


def extract_title(filename):
    """
    Parses the filename for required course information
    Args:
        filename(str): The name of the video file, in format
        'MIT-<course#>-<year>-<semester>-lec-mit-0000-<recording_date>-<time>-<session>.mp4'

    Returns:
        A string which should match a collection title: MIT-<course>-<session>-<year>-<semester>
    """
    rx = (r'(.+)-lec-mit-0000-'  # prefix to be used as the start of the collection name
          r'(\w+)'  # Recording date (required)
          r'-(\d+)'  # Recording time (required)
          r'(-([L\d\-]+))?'  # Session or room number (optional)
          r'.*\.\w')  # Rest of filename including extension (required)
    matches = re.search(rx, filename)
    if not matches or len(matches.groups()) != 5:
        raise VideoFilenameError('No matches found for filename %s with regex %s', filename, rx)
    prefix, _, _, _, session = matches.groups()
    return '-'.join([val for val in (prefix, session) if val])
