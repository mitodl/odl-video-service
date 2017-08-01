"""
Tests for permission module
"""
from unittest.mock import Mock
from uuid import uuid4

import pytest
from django.contrib.auth.models import AnonymousUser
from rest_framework.exceptions import ValidationError

from ui import factories, permissions


pytestmark = pytest.mark.django_db

# pylint: disable=redefined-outer-name


@pytest.fixture(scope='module')
def collection_owner_permission():
    """
    Returns an instance of IsCollectionOwner
    """
    return permissions.IsCollectionOwner()


@pytest.fixture
def collection():
    """
    Returns an instance of Collection
    """
    return factories.CollectionFactory()


def test_is_collection_owner_anonymous_users(collection_owner_permission, collection):
    """
    Test for IsCollectionOwner.has_object_permission to verify that anonymous users do not have permission
    """
    request = Mock(
        user=AnonymousUser()
    )
    view = Mock(kwargs={'user': 'username'})
    assert collection_owner_permission.has_object_permission(request, view, collection) is False


def test_is_collection_owner_user_different_from_collecton_owner(collection_owner_permission, collection):
    """
    Test for IsCollectionOwner.has_object_permission to verify
    that user who does not own the collection does not have permission
    """
    other_user = factories.UserFactory()
    request = Mock(
        user=other_user
    )
    view = Mock(kwargs={'user': other_user.username})
    assert collection_owner_permission.has_object_permission(request, view, collection) is False


def test_is_collection_owner_user_collecton_owner(collection_owner_permission, collection):
    """
    Test for IsCollectionOwner.has_object_permission to verify
    that user who owns the collection has permission
    """
    request = Mock(
        user=collection.owner
    )
    view = Mock(kwargs={'user': collection.owner.username})
    assert collection_owner_permission.has_object_permission(request, view, collection) is True


def test_is_collection_owner_user_superuser(collection_owner_permission, collection):
    """
    Test for IsCollectionOwner.has_object_permission to verify that superusers have permission
    """
    other_user = factories.UserFactory()
    other_user.is_superuser = True
    other_user.save()
    request = Mock(
        user=other_user
    )
    view = Mock(kwargs={'user': other_user.username})
    assert collection_owner_permission.has_object_permission(request, view, collection) is True


@pytest.fixture(scope='module')
def can_upload_to_collection_permission():
    """
    Returns an instance of CanUploadToCollection
    """
    return permissions.CanUploadToCollection()


def test_can_upload_to_collection_safe(can_upload_to_collection_permission):
    """
    Test for CanUploadToCollection with Safe Methods
    """
    request = Mock(
        user=AnonymousUser(),
        method='GET'
    )
    view = Mock(kwargs={'user': 'username'})
    assert can_upload_to_collection_permission.has_permission(request, view) is True


def test_can_upload_to_collection_superuser(can_upload_to_collection_permission):
    """
    Test for CanUploadToCollection with superuser
    """
    user = factories.UserFactory()
    user.is_superuser = True
    user.save()
    request = Mock(
        user=user,
        method='POST'
    )
    view = Mock(kwargs={'user': user.username})
    assert can_upload_to_collection_permission.has_permission(request, view) is True


def test_can_upload_to_collection_no_key(can_upload_to_collection_permission):
    """
    Test for CanUploadToCollection without a collection key in the request DATA
    """
    user = factories.UserFactory()
    request = Mock(
        user=user,
        method='POST',
        data={}
    )
    view = Mock(kwargs={'user': user.username})
    assert can_upload_to_collection_permission.has_permission(request, view) is False


def test_can_upload_to_collection_invalid_key(can_upload_to_collection_permission):
    """
    Test for CanUploadToCollection with a collection key in the request DATA that is invalid
    """
    user = factories.UserFactory()
    request = Mock(
        user=user,
        method='POST',
        data={'collection': 'fooooo'}
    )
    view = Mock(kwargs={'user': user.username})
    with pytest.raises(ValidationError):
        can_upload_to_collection_permission.has_permission(request, view)


def test_can_upload_to_collection_other_key(can_upload_to_collection_permission):
    """
    Test for CanUploadToCollection with a collection key in the request DATA that is
    not associated to a collection
    """
    user = factories.UserFactory()
    request = Mock(
        user=user,
        method='POST',
        data={'collection': uuid4().hex}
    )
    view = Mock(kwargs={'user': user.username})
    assert can_upload_to_collection_permission.has_permission(request, view) is False


def test_can_upload_to_collection_other_owner(can_upload_to_collection_permission, collection):
    """
    Test for CanUploadToCollection with a collection having another owner
    """
    user = factories.UserFactory()
    request = Mock(
        user=user,
        method='POST',
        data={'collection': collection.hexkey}
    )
    view = Mock(kwargs={'user': user.username})
    assert can_upload_to_collection_permission.has_permission(request, view) is False


def test_can_upload_to_collection(can_upload_to_collection_permission, collection):
    """
    Test for CanUploadToCollection happy path
    """
    request = Mock(
        user=collection.owner,
        method='POST',
        data={'collection': collection.hexkey}
    )
    view = Mock(kwargs={'user': collection.owner.username})
    assert can_upload_to_collection_permission.has_permission(request, view) is True
