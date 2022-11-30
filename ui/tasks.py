"""
ui celery tasks
"""
from odl_video import logging
from odl_video.celery import app
from ui import api as ovs_api
from ui.encodings import EncodingNames
from ui.models import VideoFile
from django.db.models import Q

log = logging.getLogger(__name__)


@app.task
def post_video_to_edx(video_id):
    """Loads a VideoFile and calls our API method to add it to edX"""
    video_files = list(
        VideoFile.objects.filter(~Q(encoding=EncodingNames.ORIGINAL),video=video_id).select_related("video__collection")
    )
    if not video_files:
        log.error("Video doesn't exist", video_id=video_id)
        return
    response_dict = ovs_api.post_video_to_edx(video_files)
    return [
        (endpoint.full_api_url, getattr(resp, "status_code", None))
        for endpoint, resp in response_dict.items()
    ]
