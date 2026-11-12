"""Task tests"""

import time

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
            [EncodingNames.ORIGINAL, EncodingNames.HLS, EncodingNames.DESKTOP_MP4]
        ),
        s3_object_key=factory.Iterator([1, 2, 3]),
        video=video,
    )
    tasks.post_video_to_edx.delay(video.id)
    # using 1:3 in order to remove the original video from those being posted to edx.
    patched_api_method.assert_called_once_with(
        sorted(video_files[1:3], key=lambda vf: vf.id)
    )


@pytest.mark.django_db
def test_post_video_to_edx_missing(mocker):
    """post_video_to_edx task should log an error if a Video doesn't exist with the given id"""
    patched_api_method = mocker.patch("ui.tasks.ovs_api.post_video_to_edx")
    patched_log_error = mocker.patch("ui.tasks.log.error")
    tasks.post_video_to_edx.delay(123)
    patched_log_error.assert_called_once()
    assert "doesn't exist" in patched_log_error.call_args[0][0]
    patched_api_method.assert_not_called()


@pytest.mark.django_db
def test_batch_update_video_on_edx(mocker):
    """
    batch_update_video_on_edx should call batch_update_video_on_edx_chunked for each chunk of video keys
    """
    mock_batch = mocker.patch("ui.tasks.batch_update_video_on_edx_chunked")
    group_mock = mocker.patch("ui.tasks.celery.group", autospec=True)
    all_ids = list(range(1, 101))
    tasks.batch_update_video_on_edx(all_ids, chunk_size=10)

    assert group_mock.call_count == 1
    for i in list(range(10)):
        mock_batch.assert_any_call(all_ids[i * 10 : i * 10 + 10])


@pytest.mark.django_db
def test_clear_social_auth_state():
    """Stale social-auth OAuth state is deleted and recent state is kept"""
    from social_django.models import Nonce

    now = int(time.time())
    Nonce.objects.create(
        server_url="keycloak", timestamp=now - 15 * 24 * 60 * 60, salt="stale"
    )
    Nonce.objects.create(server_url="keycloak", timestamp=now, salt="fresh")

    tasks.clear_social_auth_state()

    assert list(Nonce.objects.values_list("salt", flat=True)) == ["fresh"]


def test_clear_social_auth_state_is_scheduled():
    """celery beat runs the cleanup task when Keycloak is enabled"""
    from odl_video import settings as project_settings

    entry = project_settings.CELERY_BEAT_SCHEDULE["clear-social-auth-state"]
    assert entry["task"] == tasks.clear_social_auth_state.name
