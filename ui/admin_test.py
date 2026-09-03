"""Tests for UI admin customizations"""

from unittest.mock import MagicMock, patch

import pytest
from django.contrib import messages
from django.contrib.admin.sites import AdminSite
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory

from ui.admin import (
    CollectionAdmin,
    CollectionAdminForm,
    VideoAdmin,
    VideoAdminForm,
)
from ui.constants import VideoStatus
from ui.encodings import EncodingNames
from ui.factories import CollectionFactory, VideoFactory, VideoFileFactory
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


def test_retry_upload_eligible_video(video_admin, admin_request, mocker):
    """
    retry_upload should reset an eligible UPLOAD_FAILED video back to CREATED and
    dispatch the stream_to_s3 + transcode_from_s3 chain via the helper.
    """
    mocked_chain = mocker.patch("ui.api.chain")
    video = VideoFactory(status=VideoStatus.UPLOAD_FAILED)
    VideoFileFactory(video=video, encoding=EncodingNames.ORIGINAL)

    video_admin.retry_upload(admin_request, Video.objects.filter(pk=video.pk))

    video.refresh_from_db()
    assert video.status == VideoStatus.CREATED
    mocked_chain.return_value.delay.assert_called_once()


def test_retry_upload_skips_non_failed_status(video_admin, admin_request, mocker):
    """Videos not in UPLOAD_FAILED status are skipped, status left untouched."""
    mocked_chain = mocker.patch("ui.api.chain")
    video = VideoFactory(status=VideoStatus.COMPLETE)

    video_admin.retry_upload(admin_request, Video.objects.filter(pk=video.pk))

    video.refresh_from_db()
    assert video.status == VideoStatus.COMPLETE
    mocked_chain.assert_not_called()


def test_retry_upload_skips_video_without_source_url(
    video_admin, admin_request, mocker
):
    """
    An UPLOAD_FAILED video without a source_url cannot be retried. The factory
    enforces a non-empty source_url via full_clean(), so we clear it via .update()
    which bypasses save() validation.
    """
    mocked_chain = mocker.patch("ui.api.chain")
    video = VideoFactory(status=VideoStatus.UPLOAD_FAILED)
    VideoFileFactory(video=video, encoding=EncodingNames.ORIGINAL)
    Video.objects.filter(pk=video.pk).update(source_url="")

    video_admin.retry_upload(admin_request, Video.objects.filter(pk=video.pk))

    video.refresh_from_db()
    assert video.status == VideoStatus.UPLOAD_FAILED
    mocked_chain.assert_not_called()


def test_retry_upload_skips_missing_original_videofile(
    video_admin, admin_request, mocker
):
    """
    An UPLOAD_FAILED video without an original VideoFile would fail in transcode,
    so it is skipped (status untouched) and reported with a warning.
    """
    mocked_chain = mocker.patch("ui.api.chain")
    video = VideoFactory(status=VideoStatus.UPLOAD_FAILED)
    video_admin.message_user = MagicMock()

    video_admin.retry_upload(admin_request, Video.objects.filter(pk=video.pk))

    video.refresh_from_db()
    assert video.status == VideoStatus.UPLOAD_FAILED
    mocked_chain.assert_not_called()
    video_admin.message_user.assert_called_once()
    assert video_admin.message_user.call_args.kwargs["level"] == messages.WARNING


def test_retry_upload_reports_dispatch_failure(video_admin, admin_request, mocker):
    """If dispatch raises, status is reverted to UPLOAD_FAILED and reported as error."""
    mocked_chain = mocker.patch("ui.api.chain")
    mocked_chain.return_value.delay.side_effect = Exception("broker down")
    video = VideoFactory(status=VideoStatus.UPLOAD_FAILED)
    VideoFileFactory(video=video, encoding=EncodingNames.ORIGINAL)
    video_admin.message_user = MagicMock()

    video_admin.retry_upload(admin_request, Video.objects.filter(pk=video.pk))

    video.refresh_from_db()
    assert video.status == VideoStatus.UPLOAD_FAILED
    video_admin.message_user.assert_called_once()
    assert video_admin.message_user.call_args.kwargs["level"] == messages.ERROR


def test_retry_upload_mixed_queryset_reports_each_category(
    video_admin, admin_request, mocker
):
    """
    With a mixed queryset, only the eligible video is re-queued, and each skipped
    category triggers its own message_user call.
    """
    mocked_chain = mocker.patch("ui.api.chain")
    eligible = VideoFactory(status=VideoStatus.UPLOAD_FAILED)
    VideoFileFactory(video=eligible, encoding=EncodingNames.ORIGINAL)
    wrong_status = VideoFactory(status=VideoStatus.COMPLETE)
    no_source = VideoFactory(status=VideoStatus.UPLOAD_FAILED)
    VideoFileFactory(video=no_source, encoding=EncodingNames.ORIGINAL)
    Video.objects.filter(pk=no_source.pk).update(source_url="")
    video_admin.message_user = MagicMock()

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

    assert mocked_chain.return_value.delay.call_count == 1
    # one message each for retried + skipped_status + skipped_no_source
    assert video_admin.message_user.call_count == 3


DIRTY_DESCRIPTION = (
    "<p>Keep <strong>this</strong></p><script>alert(1)</script>"
    '<p style="color:red">and this</p>'
)
CLEAN_DESCRIPTION = "<p>Keep <strong>this</strong></p><p>and this</p>"


def _collection_form(description):
    """Build a bound CollectionAdminForm with the given description"""
    owner = VideoFactory.create().collection.owner
    return CollectionAdminForm(
        data={"title": "A series", "description": description, "owner": owner.id}
    )


def _video_form(description):
    """Build a bound VideoAdminForm with the given description"""
    video = VideoFactory.create()
    return VideoAdminForm(
        data={
            "title": video.title,
            "description": description,
            "collection": video.collection.id,
            "source_url": video.source_url,
            "status": video.status,
        },
        instance=video,
    )


def test_admin_form_accepts_clean_rich_text():
    """Markup within the allowlist passes through untouched"""
    form = _collection_form(CLEAN_DESCRIPTION)
    form.is_valid()  # other required fields are not the subject here
    assert "description" not in form.errors
    assert form.cleaned_data["description"] == CLEAN_DESCRIPTION


def test_admin_form_rejects_disallowed_tags_and_names_them():
    """
    The admin edits raw HTML, so silently dropping a tag would leave the author
    wondering where their formatting went. Refuse and say what was wrong.
    """
    form = _collection_form(DIRTY_DESCRIPTION)
    assert not form.is_valid()
    message = " ".join(form.errors["description"])
    assert "<script>" in message
    assert "not supported" in message


def test_admin_form_rejects_headings_explicitly():
    """Headings are the likeliest paste; Learn strips them, so OVS refuses them"""
    form = _collection_form("<h2>Session notes</h2><p>body</p>")
    assert not form.is_valid()
    assert "<h2>" in " ".join(form.errors["description"])


def test_admin_form_reports_dropped_attributes():
    """An attribute-only problem is reported as an attribute problem"""
    form = _collection_form('<p class="ql-align-center">centered</p>')
    assert not form.is_valid()
    assert "attributes would be dropped" in " ".join(form.errors["description"])


def test_admin_form_tidies_malformed_markup_instead_of_refusing():
    """
    An unclosed tag loses nothing - nh3 closes it correctly - so accept the
    tidied version rather than making the admin fix it by hand.
    """
    form = _collection_form("<p>unclosed <strong>bold</p>")
    form.is_valid()
    assert "description" not in form.errors
    assert form.cleaned_data["description"] == "<p>unclosed <strong>bold</strong></p>"


def test_admin_form_accepts_a_link_despite_the_added_rel():
    """
    nh3 adds rel="noopener noreferrer" to every anchor. That is an addition, not
    a loss, so correct input with a link must not be rejected for differing.
    """
    form = _collection_form('<p><a href="https://learn.mit.edu">go</a></p>')
    form.is_valid()
    assert "description" not in form.errors
    assert 'rel="noopener noreferrer"' in form.cleaned_data["description"]


@pytest.mark.parametrize(
    "href",
    [
        "javascript:alert(1)",
        "//evil.example/x",
        "/site-relative",
        "ftp://files.mit.edu",
    ],
)
def test_admin_form_rejects_a_link_that_would_lose_its_target(href):
    """
    nh3 drops the href but keeps the <a>, so the link silently stops working.
    Protocol- and site-relative hrefs are included: url_schemes does not
    constrain them, and on MIT Learn they would resolve against the wrong host.
    """
    form = _collection_form(f'<a href="{href}">x</a>')
    assert not form.is_valid()
    message = " ".join(form.errors["description"])
    assert "lose their target" in message
    assert href in message


def test_admin_form_allows_an_empty_description():
    """Clearing the field is not an error"""
    form = _collection_form("")
    form.is_valid()
    assert "description" not in form.errors
    assert form.cleaned_data["description"] == ""


def test_video_admin_form_validates_description_too():
    """Video descriptions get the same treatment as collection descriptions"""
    form = _video_form(DIRTY_DESCRIPTION)
    assert not form.is_valid()
    assert "<script>" in " ".join(form.errors["description"])


def test_admin_form_documents_the_allowlist_in_help_text():
    """An admin editing raw HTML needs to be told which tags survive"""
    help_text = str(_collection_form("").fields["description"].help_text)
    assert "strong" in help_text
    assert "Headings" in help_text


def test_collection_admin_uses_the_validating_form():
    """The form is actually attached, not just defined"""
    assert CollectionAdmin.form is CollectionAdminForm
    assert VideoAdmin.form is VideoAdminForm
