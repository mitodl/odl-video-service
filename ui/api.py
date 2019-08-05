"""
API methods
"""
import logging
from uuid import uuid4

import requests
from celery import chain
from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404

from cloudsync import tasks
from ui import models
from ui.utils import multi_urljoin, edx_settings_configured

log = logging.getLogger(__name__)


def process_dropbox_data(dropbox_upload_data):
    """
    Takes care of processing a list of videos to be uploaded from dropbox

    Args:
        dropbox_links_list (dict): a dictionary containing the collection key and a list of dropbox links

    Returns:
        list: A list of dictionaries containing informations about the videos
    """
    collection_key = dropbox_upload_data['collection']
    dropbox_links_list = dropbox_upload_data['files']
    collection = get_object_or_404(models.Collection, key=collection_key)
    response_data = {}
    for dropbox_link in dropbox_links_list:
        with transaction.atomic():
            video = models.Video.objects.create(
                source_url=dropbox_link["link"],
                title=dropbox_link["name"][:models.Video._meta.get_field("title").max_length],
                collection=collection,
            )
            models.VideoFile.objects.create(
                s3_object_key=video.get_s3_key(),
                video_id=video.id,
                bucket_name=settings.VIDEO_S3_BUCKET
            )
        # Kick off chained async celery tasks to transfer file to S3, then start a transcode job
        task_result = chain(
            tasks.stream_to_s3.s(video.id),
            tasks.transcode_from_s3.si(video.id)
        )()

        response_data[video.hexkey] = {
            "s3key": video.get_s3_key(),
            "title": video.title,
            "task": task_result.id,
        }
    return response_data


def post_hls_to_edx(video_file):
    """
    Posts an HLS video to edX via API using attributes from a video file

    Args:
        video_file (ui.models.VideoFile): An HLS-encoded video file

    Returns:
        requests.models.Response: The API response
    """
    assert edx_settings_configured(), "edX settings need to be configured"
    assert video_file.can_add_to_edx(), "This video file is not of the correct type"
    hls_api_url = multi_urljoin(
        settings.EDX_BASE_URL,
        settings.EDX_HLS_API_URL,
        add_trailing_slash=True
    )
    resp = requests.post(
        hls_api_url,
        json={
            "client_video_id": video_file.video.title,
            "edx_video_id": str(uuid4()),
            "encoded_videos": [
                {
                    "url": video_file.cloudfront_url,
                    "file_size": 0,
                    "bitrate": 0,
                    "profile": "hls"
                }
            ],
            "courses": [{video_file.video.collection.edx_course_id: None}],
            "status": "file_complete",
            "duration": 0.0,
        },
        headers={
            "Authorization": "Bearer {}".format(settings.EDX_ACCESS_TOKEN),
        }
    )
    if not resp.ok:
        log.error(
            "Request to add HLS video to edX failed - VideoFile: %d, API response: [%d] %s",
            video_file.pk,
            resp.status_code,
            resp.content.decode("utf-8"),
        )
    return resp
