"""Task tests"""
import pytest
import factory

from django.db.models import signals

from ui import tasks
from ui.factories import VideoFileFactory


@pytest.mark.django_db
@factory.django.mute_signals(signals.post_save)
def test_post_hls_to_edx(mocker):
    """post_hls_to_edx task should load a VideoFile and call an internal API function to post to edX"""
    patched_api_method = mocker.patch("ui.tasks.ovs_api.post_hls_to_edx")
    video_file = VideoFileFactory.create()
    tasks.post_hls_to_edx.delay(video_file.id)
    patched_api_method.assert_called_once_with(video_file)


@pytest.mark.django_db
def test_post_hls_to_edx_missing(mocker):
    """post_hls_to_edx task should log an error if a VideoFile doesn't exist with the given id"""
    patched_api_method = mocker.patch("ui.tasks.ovs_api.post_hls_to_edx")
    patched_log_error = mocker.patch("ui.tasks.log.error")
    tasks.post_hls_to_edx.delay(123)
    patched_log_error.assert_called_once()
    assert "doesn't exist" in patched_log_error.call_args[0][0]
    patched_api_method.assert_not_called()
