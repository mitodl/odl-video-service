"""
ui celery tasks
"""

import celery
from django.db.models import Q

from mail.utils import chunks
from odl_video import logging
from odl_video.celery import app
from ui import api as ovs_api
from ui.api import update_video_on_edx
from ui.encodings import EncodingNames
from ui.models import VideoFile

log = logging.getLogger(__name__)


@app.task
def post_video_to_edx(video_id):
    """Loads a VideoFile and calls our API method to add it to edX"""
    video_files = sorted(
        list(
            VideoFile.objects.filter(
                ~Q(encoding=EncodingNames.ORIGINAL), video=video_id
            ).select_related("video__collection")
        ),
        key=lambda vf: vf.id,
    )
    if not video_files:
        log.error("Video doesn't exist", video_id=video_id)
        return
    response_dict = ovs_api.post_video_to_edx(video_files)
    return [
        (endpoint.full_api_url, getattr(resp, "status_code", None))
        for endpoint, resp in response_dict.items()
    ]


@app.task
def batch_update_video_on_edx(video_keys, chunk_size=1000):
    """
    batch update videos on their associated edX endpoints

    Args:
        video_keys(list): A list of video UUID keys
        chunk_size(int): the chunk size in a batch API call
    """
    return celery.group(
        [
            batch_update_video_on_edx_chunked(chunk)
            for chunk in chunks(
                video_keys,
                chunk_size=chunk_size,
            )
        ]
    )


@app.task
def batch_update_video_on_edx_chunked(video_keys):
    """
    batch update videos on their associated edX endpoints in chunks

    Args:
        video_keys(list): A list of video UUID keys
    """
    response = {}
    for video_key in video_keys:
        response_dict = update_video_on_edx(video_key)
        for endpoint, resp in response_dict.items():
            if getattr(resp, "ok", None):
                response[endpoint] = "succeed"
            else:
                response[endpoint] = "failed"
    return response
