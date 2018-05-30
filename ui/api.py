"""
API methods
"""
import logging

from celery import chain
from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404

from cloudsync import tasks
from ui import models


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
                title=dropbox_link["name"][:250],
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
