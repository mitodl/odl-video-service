"""
API methods
"""
import logging

from dj_elastictranscoder.models import EncodeJob
from django.conf import settings

from ui.encodings import EncodingNames
from ui.utils import get_et_preset, get_bucket, get_et_job
from ui.models import VideoFile, VideoThumbnail


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


def refresh_status(video):
    """
    Check the encode job status & if not complete, update the status via a query to AWS.

    Args:
        video(ui.models.Video): Video object to refresh status of.
    """
    if video.status not in ['Complete', 'Error']:
        try:
            job = get_et_job(video.encode_jobs.latest("created_at").id)
            if job['Status'] == 'Complete':
                process_transcode_results(video, job)
            video.status = job['Status']
            video.save()
        except EncodeJob.DoesNotExist:
            log.error("No encoding job exists for video id %d", video.id)
