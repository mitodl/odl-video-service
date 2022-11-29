"""Task tests"""
import factory
import pytest
from django.db.models import signals

from ui import tasks
from ui.constants import VideoStatus
from ui.encodings import EncodingNames
from ui.factories import VideoFactory, VideoFileFactory


@pytest.mark.django_db
@factory.django.mute_signals(signals.post_save)
def test_post_video_to_edx(mocker):
    """post_video_to_edx task should load a Video and call an internal API function to post to edX"""
    patched_api_method = mocker.patch("ui.tasks.ovs_api.post_video_to_edx")
    video = VideoFactory.create(status=VideoStatus.COMPLETE)
    video_files = VideoFileFactory.create_batch(
        3,
        encoding=factory.Iterator(
            [EncodingNames.ORIGINAL, EncodingNames.HLS, EncodingNames.BASIC]
        ),
        s3_object_key=factory.Iterator([1, 2, 3]),
        video=video,
    )
    tasks.post_video_to_edx.delay(video.id)
    patched_api_method.assert_called_once_with(list(reversed(video_files)))


@pytest.mark.django_db
def test_post_video_to_edx_missing(mocker):
    """post_video_to_edx task should log an error if a Video doesn't exist with the given id"""
    patched_api_method = mocker.patch("ui.tasks.ovs_api.post_video_to_edx")
    patched_log_error = mocker.patch("ui.tasks.log.error")
    tasks.post_video_to_edx.delay(123)
    patched_log_error.assert_called_once()
    assert "doesn't exist" in patched_log_error.call_args[0][0]
    patched_api_method.assert_not_called()
