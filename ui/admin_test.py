"""Tests for UI admin customizations"""

from unittest.mock import MagicMock, patch

import pytest
from django.contrib.admin.sites import AdminSite
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory

from ui.admin import CollectionAdmin, VideoAdmin
from ui.constants import VideoStatus
from ui.factories import CollectionFactory, VideoFactory
from ui.models import Collection, Video

pytestmark = pytest.mark.django_db


@pytest.fixture()
def collection_admin():
    """Return a CollectionAdmin instance bound to the default admin site."""
    return CollectionAdmin(model=Collection, admin_site=AdminSite())


@pytest.fixture()
def mock_request():
    """Return a minimal GET request for use in admin calls."""
    return RequestFactory().get("/admin/")


def _save_with_changed_data(admin_instance, request, obj, changed_fields):
    """Helper: call save_model with a mock form whose changed_data is changed_fields."""
    mock_form = MagicMock()
    mock_form.changed_data = changed_fields
    with patch("django.contrib.admin.ModelAdmin.save_model"):
        admin_instance.save_model(request, obj, mock_form, change=True)


@pytest.mark.parametrize(
    ["is_public", "include_in_learn", "expected_video_is_public"],
    [
        # Turning on is_public for a normal collection → videos become public
        (True, False, True),
        # Turning on is_public for a learn collection → videos stay private
        (True, True, False),
    ],
)
def test_collection_admin_save_model_is_public_propagation(
    collection_admin,
    mock_request,
    is_public,
    include_in_learn,
    expected_video_is_public,
):
    """
    When is_public is toggled on a collection via the admin:
    - Normal collections propagate the change to all their videos.
    - Collections with include_in_learn=True do NOT auto-make videos public;
      editors must explicitly publish each video.
    """
    collection = CollectionFactory(
        is_public=is_public, include_in_learn=include_in_learn
    )
    video = VideoFactory(collection=collection, is_public=False)

    _save_with_changed_data(collection_admin, mock_request, collection, ["is_public"])

    video.refresh_from_db()
    assert video.is_public is expected_video_is_public


def test_collection_admin_save_model_turning_off_public_still_propagates_for_learn(
    collection_admin, mock_request
):
    """
    Even for include_in_learn=True collections, turning is_public OFF should still
    propagate to videos so they are no longer accidentally accessible.
    """
    collection = CollectionFactory(is_public=False, include_in_learn=True)
    video = VideoFactory(collection=collection, is_public=True)

    _save_with_changed_data(collection_admin, mock_request, collection, ["is_public"])

    video.refresh_from_db()
    assert video.is_public is False


def test_collection_admin_save_model_no_change_to_is_public_skips_update(
    collection_admin, mock_request
):
    """If is_public is not in changed_data, video permissions are not touched."""
    collection = CollectionFactory(is_public=True, include_in_learn=False)
    video = VideoFactory(collection=collection, is_public=False)

    _save_with_changed_data(collection_admin, mock_request, collection, ["title"])

    video.refresh_from_db()
    assert video.is_public is False


@pytest.fixture()
def video_admin():
    """Return a VideoAdmin instance bound to the default admin site."""
    return VideoAdmin(model=Video, admin_site=AdminSite())


@pytest.fixture()
def admin_request():
    """
    A request with messages storage attached, since `message_user` writes to
    `request._messages` (normally populated by MessageMiddleware).
    """
    request = RequestFactory().get("/admin/")
    request.session = {}
    request._messages = FallbackStorage(request)
    return request


def test_retry_upload_eligible_video(video_admin, admin_request):
    """
    retry_upload should reset an UPLOAD_FAILED video with a non-empty source_url
    back to CREATED and kick off the stream_to_s3 + transcode_from_s3 chain.
    """
    video = VideoFactory(
        status=VideoStatus.UPLOAD_FAILED, source_url="http://example.com/foo.mp4"
    )

    with (
        patch("ui.admin.chain") as mocked_chain,
        patch("cloudsync.tasks.stream_to_s3") as mocked_stream,
        patch("cloudsync.tasks.transcode_from_s3") as mocked_transcode,
    ):
        video_admin.retry_upload(admin_request, Video.objects.filter(pk=video.pk))

    video.refresh_from_db()
    assert video.status == VideoStatus.CREATED
    mocked_stream.s.assert_called_once_with(video.id)
    mocked_transcode.si.assert_called_once_with(video.id)
    mocked_chain.assert_called_once_with(
        mocked_stream.s(video.id), mocked_transcode.si(video.id)
    )
    mocked_chain.return_value.delay.assert_called_once()


def test_retry_upload_skips_non_failed_status(video_admin, admin_request):
    """
    Videos not in UPLOAD_FAILED status must be skipped: no chain dispatched
    and status left untouched.
    """
    video = VideoFactory(
        status=VideoStatus.COMPLETE, source_url="http://example.com/foo.mp4"
    )

    with patch("ui.admin.chain") as mocked_chain:
        video_admin.retry_upload(admin_request, Video.objects.filter(pk=video.pk))

    video.refresh_from_db()
    assert video.status == VideoStatus.COMPLETE
    mocked_chain.assert_not_called()


def test_retry_upload_skips_video_without_source_url(video_admin, admin_request):
    """
    Even an UPLOAD_FAILED video without a source_url cannot be retried and
    must be skipped. The factory enforces a non-empty source_url via
    ValidateOnSaveMixin.full_clean(), so we clear it via .update() which
    bypasses save() validation.
    """
    video = VideoFactory(status=VideoStatus.UPLOAD_FAILED)
    Video.objects.filter(pk=video.pk).update(source_url="")

    with patch("ui.admin.chain") as mocked_chain:
        video_admin.retry_upload(admin_request, Video.objects.filter(pk=video.pk))

    video.refresh_from_db()
    assert video.status == VideoStatus.UPLOAD_FAILED
    mocked_chain.assert_not_called()


def test_retry_upload_mixed_queryset_reports_each_category(video_admin, admin_request):
    """
    With a mixed queryset, only eligible videos should be re-queued. The
    skipped categories should each trigger a message_user call so the admin
    sees what was skipped and why.
    """
    eligible = VideoFactory(
        status=VideoStatus.UPLOAD_FAILED, source_url="http://example.com/a.mp4"
    )
    wrong_status = VideoFactory(
        status=VideoStatus.COMPLETE, source_url="http://example.com/b.mp4"
    )
    no_source = VideoFactory(status=VideoStatus.UPLOAD_FAILED)
    Video.objects.filter(pk=no_source.pk).update(source_url="")
    video_admin.message_user = MagicMock()

    with (
        patch("ui.admin.chain") as mocked_chain,
        patch("cloudsync.tasks.stream_to_s3"),
        patch("cloudsync.tasks.transcode_from_s3"),
    ):
        video_admin.retry_upload(
            admin_request,
            Video.objects.filter(pk__in=[eligible.pk, wrong_status.pk, no_source.pk]),
        )

    eligible.refresh_from_db()
    wrong_status.refresh_from_db()
    no_source.refresh_from_db()

    assert eligible.status == VideoStatus.CREATED
    assert wrong_status.status == VideoStatus.COMPLETE
    assert no_source.status == VideoStatus.UPLOAD_FAILED

    assert mocked_chain.call_count == 1
    # one message for retried + one for skipped_status + one for skipped_no_source
    assert video_admin.message_user.call_count == 3
