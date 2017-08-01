"""APIs for coudsync app"""
import logging

from django.conf import settings

from ui.constants import VideoStatus
from ui.encodings import EncodingNames
from ui.models import (
    VideoFile,
    VideoThumbnail,
)
from ui.utils import get_et_preset, get_bucket, get_et_job


log = logging.getLogger(__name__)


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
