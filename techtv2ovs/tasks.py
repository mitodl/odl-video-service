""" Celery tasks for techtv2ovs """
from os.path import splitext

import boto3
from celery import shared_task
from django.conf import settings

from techtv2ovs.constants import TTV_VIDEO_BUCKET, ImportStatus
from techtv2ovs.models import TechTVVideo
from ui.models import VideoFile
from odl_video import logging

log = logging.getLogger(__name__)

# pylint: disable=unused-argument,broad-except


def parse_encoding(filename):
    """
    Get the correct encoding base on the video file's name

    Args:
        filename (str): The video file name

    Returns:
        str: The encoding for the videofile.

    """
    basename = splitext(filename)[0].split('/')[-1].lower()
    return basename.upper() if basename == 'hd' else basename


@shared_task(bind=True)
def process_videofiles(self, ttv_id, files, run_copy):
    """
    Copy over S3 video files for a TechTV video, and create a VideoFile object for each.
    Update the TechTVVideo and Video statuses when done (complete, error, or missing).

    Args:
        ttv_id (int): The ID of the TechTVVideo object
        files (list): A list of S3 videofile objects
        run_copy (bool): Copy S3 files between buckets
    """
    ttv_video = TechTVVideo.objects.get(id=ttv_id)
    ttv_video.videofile_status = ImportStatus.CREATED
    for s3file in files:
        try:
            # Copy S3 objects to OVS buckets (if not already there)
            src = {'Bucket': TTV_VIDEO_BUCKET, 'Key': s3file['Key']}
            if 'original' in s3file['Key']:
                dst_bucket = settings.VIDEO_S3_BUCKET
                dst_key = 'techtv/{}'.format(s3file['Key'])
            else:
                dst_bucket = settings.VIDEO_S3_TRANSCODE_BUCKET
                dst_key = 'transcoded/techtv/{}'.format(
                    s3file['Key'].replace(ttv_video.external_id, ttv_video.video.hexkey)
                )
            if run_copy:
                s3client = boto3.client('s3')
                meta = s3client.list_objects_v2(Bucket=dst_bucket, Prefix=dst_key)
                if 'Contents' not in meta or not meta['Contents']:
                    s3client.copy(src, dst_bucket, dst_key)

            # Create VideoFile for each S3 object
            VideoFile.objects.get_or_create(
                s3_object_key=dst_key,
                encoding=parse_encoding(dst_key),
                defaults={
                    'bucket_name': dst_bucket,
                    'video': ttv_video.video
                }
            )
        except Exception as exc:
            log.exception("Error processing video file for ttv video",
                          s3_object_key=s3file['Key'],
                          ttv_video_id=ttv_video.id)
            ttv_video.status = ImportStatus.ERROR
            ttv_video.videofile_status = ImportStatus.ERROR
            ttv_video.errors += '{}\n\n'.format(str(exc))

    # Update statuses
    if ttv_video.videofile_status != ImportStatus.ERROR:
        ttv_video.videofile_status = ImportStatus.COMPLETE if files else ImportStatus.MISSING
    if ttv_video.status != ImportStatus.ERROR:
        ttv_video.status = ttv_video.videofile_status
    ttv_video.video.status = ttv_video.videofile_status if files else ImportStatus.ERROR
    ttv_video.video.save()
    ttv_video.save()
