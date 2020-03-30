"""
ui celery tasks
"""
from odl_video import logging

from odl_video.celery import app
from ui.models import VideoFile
from ui import api as ovs_api

log = logging.getLogger(__name__)


@app.task
def post_hls_to_edx(video_file_id):
    """Loads a VideoFile and calls our API method to add it to edX"""
    video_file = VideoFile.objects.filter(id=video_file_id).select_related("video__collection").first()
    if not video_file:
        log.error("VideoFile doesn't exist", videofile_id=video_file_id)
        return
    response_dict = ovs_api.post_hls_to_edx(video_file)
    return [
        (endpoint.full_api_url, getattr(resp, "status_code", None))
        for endpoint, resp in response_dict.items()
    ]
