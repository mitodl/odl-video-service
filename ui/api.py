"""
API methods
"""
from uuid import uuid4

import requests
from celery import chain
from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404

from cloudsync import tasks
from odl_video import logging
from ui import models
from ui.utils import get_error_response_summary_dict

log = logging.getLogger(__name__)


def process_dropbox_data(dropbox_upload_data):
    """
    Takes care of processing a list of videos to be uploaded from dropbox

    Args:
        dropbox_links_list (dict): a dictionary containing the collection key and a list of dropbox links

    Returns:
        list: A list of dictionaries containing informations about the videos
    """
    collection_key = dropbox_upload_data["collection"]
    dropbox_links_list = dropbox_upload_data["files"]
    collection = get_object_or_404(models.Collection, key=collection_key)
    response_data = {}
    for dropbox_link in dropbox_links_list:
        with transaction.atomic():
            video = models.Video.objects.create(
                source_url=dropbox_link["link"],
                title=dropbox_link["name"][
                    : models.Video._meta.get_field("title").max_length
                ],
                collection=collection,
            )
            models.VideoFile.objects.create(
                s3_object_key=video.get_s3_key(),
                video_id=video.id,
                bucket_name=settings.VIDEO_S3_BUCKET,
            )
        # Kick off chained async celery tasks to transfer file to S3, then start a transcode job
        task_result = chain(
            tasks.stream_to_s3.s(video.id), tasks.transcode_from_s3.si(video.id)
        )()

        response_data[video.hexkey] = {
            "s3key": video.get_s3_key(),
            "title": video.title,
            "task": task_result.id,
        }
    return response_data


def post_video_to_edx(video_files):
    """
    Posts a video to all configured edX endpoints via API using attributes from a video file

    Args:
        video_files [ui.models.VideoFile]: An array of video files

    Returns:
        Dict[EdxEndpoint, requests.models.Response]: Each configured edX endpoint mapped to the response from the
            request to post the video file to that endpoint.
    """
    encoded_videos = []
    for video_file in video_files:
        assert video_file.can_add_to_edx, "This video file cannot be added to edX"
        encoded_videos.append(
            {
                "url": video_file.cloudfront_url,
                "file_size": 0,
                "bitrate": 0,
                "profile": video_file.encoding,
            }
        )
    edx_endpoints = models.EdxEndpoint.objects.filter(
        Q(collections__id__in=[video_file[0].video.collection_id])
    )
    if not edx_endpoints.exists():
        log.error(
            "Trying to post video to edX endpoints, but no endpoints exist",
            videofile_id=video_file[0].pk,
            videofile=video_file[0],
        )

    responses = {}
    for edx_endpoint in edx_endpoints:
        try:
            edx_endpoint.refresh_access_token()
            resp = requests.post(
                edx_endpoint.full_api_url,
                json={
                    "client_video_id": video_file.video.title,
                    "edx_video_id": str(uuid4()),
                    "encoded_videos": encoded_videos,
                    "courses": [{video_file.video.collection.edx_course_id: None}],
                    "status": "file_complete",
                    "duration": 0.0,
                },
                headers={
                    "Authorization": "JWT {}".format(edx_endpoint.access_token),
                },
            )
            resp.raise_for_status()
        except requests.exceptions.RequestException as exc:
            if exc is not None and exc.response is not None:
                response_summary_dict = get_error_response_summary_dict(exc.response)
            elif isinstance(exc, requests.exceptions.ConnectionError):
                response_summary_dict = {
                    "exception": "ConnectionError (No server response)"
                }
            else:
                response_summary_dict = {"exception": str(exc)}
            log.error(
                "Can not add video to edX",
                videofile_id=video_file.pk,
                response=str(response_summary_dict),
            )
            resp = exc.response
        responses[edx_endpoint] = resp
    return responses
