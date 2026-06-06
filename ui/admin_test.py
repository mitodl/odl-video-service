"""Tests for UI admin customizations"""

from unittest.mock import MagicMock, patch

import pytest
from django.contrib.admin.sites import AdminSite
from django.test import RequestFactory

from ui.admin import CollectionAdmin
from ui.factories import CollectionFactory, VideoFactory
from ui.models import Collection

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
