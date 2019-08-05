"""
ui celery tasks
"""
import logging

from odl_video.celery import app
from ui.models import VideoFile
from ui import api as ovs_api

log = logging.getLogger()


@app.task
def post_hls_to_edx(video_file_id):
    """Loads a VideoFile and calls our API method to add it to edX"""
    video_file = VideoFile.objects.filter(id=video_file_id).select_related("video__collection").first()
    if not video_file:
        log.error("VideoFile with id %s doesn't exist", video_file_id)
        return
    resp = ovs_api.post_hls_to_edx(video_file)
    return resp.status_code
