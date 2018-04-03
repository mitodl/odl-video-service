"""
Tests for permission module
"""
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from django.contrib.auth.models import AnonymousUser
from rest_framework.exceptions import ValidationError

from ui import factories, permissions
from ui.factories import CollectionFactory, MoiraListFactory
from ui.models import Collection
from ui.utils import get_moira_user

pytestmark = pytest.mark.django_db


# pylint: disable=redefined-outer-name,too-many-arguments,unused-argument


@pytest.fixture(scope='module')
def collection_owner_permission():
    """
    Returns an instance of IsCollectionOwner
    """
    return permissions.IsCollectionOwner()


@pytest.fixture(scope='module')
def collection_permission():
    """
    Returns an instance of HasCollectionPermissions
    """
    return permissions.HasCollectionPermissions()


@pytest.fixture(scope='module')
def video_permission():
    """
    Returns an instance of HasVideoPermissions
    """
    return permissions.HasVideoPermissions()


@pytest.fixture(scope='module')
def subtitle_permission():
    """
    Returns an instance of HasVideoPermissions
    """
    return permissions.HasVideoSubtitlePermissions()


@pytest.fixture
def collection():
    """
    Returns an instance of Collection
    """
    return factories.CollectionFactory()


@pytest.fixture
def moira_list():
    """
    Returns an instance of MoiraList
    """
    return factories.MoiraListFactory()


@pytest.fixture
def video():
    """
    Returns an instance of Video
    """
    return factories.VideoFactory()


@pytest.fixture
def subtitle():
    """
    Returns an instance of Video
    """
    return factories.VideoSubtitleFactory()


@pytest.fixture
def request_data():
    """
    Fixture for tests requiring a user, request, and view
    """
    user = factories.UserFactory()
    request = Mock(
        method='GET',
        user=user
    )
    view = Mock(kwargs={'user': user.username})
    return SimpleNamespace(user=user, request=request, view=view)


@pytest.fixture
def request_data_su():
    """
    Fixture for tests requiring a superuser, request, and view
    """
    user = factories.UserFactory(is_superuser=True)
    request = Mock(
        method='GET',
        user=user
    )
    view = Mock(kwargs={'user': user.username})
    return SimpleNamespace(user=user, request=request, view=view)


@pytest.fixture
def request_data_anon():
    """
    Fixture for tests requiring an anonymous user, request, and view
    """
    request = Mock(
        method='GET',
        user=AnonymousUser()
    )
    view = Mock(kwargs={'user': 'username'})
    return SimpleNamespace(request=request, view=view)


@pytest.fixture
def alt_moira_data():
    """
    Fixture for tests requiring a moira list, collection, and user
    """
    alt_moira_list = MoiraListFactory()
    alt_collection = CollectionFactory()
    alt_user = factories.UserFactory()
    return SimpleNamespace(moira_list=alt_moira_list, collection=alt_collection, user=alt_user)


@pytest.fixture(scope='module')
def can_upload_to_collection_permission():
    """
    Returns an instance of CanUploadToCollection
    """
    return permissions.CanUploadToCollection()


def test_is_collection_owner_anonymous_users(collection_owner_permission,
                                             collection,
                                             request_data_anon):
    """
    Test for IsCollectionOwner.has_object_permission to verify that anonymous users do not have permission
    """
    assert collection_owner_permission.has_object_permission(request_data_anon.request,
                                                             request_data_anon.view,
                                                             collection) is False


def test_is_collection_owner_user_different_from_collecton_owner(collection_owner_permission,
                                                                 collection,
                                                                 request_data):
    """
    Test for IsCollectionOwner.has_object_permission to verify
    that user who does not own the collection does not have permission
    """
    assert request_data.user != collection.owner
    assert collection_owner_permission.has_object_permission(request_data.request,
                                                             request_data.view,
                                                             collection) is False


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


def test_is_collection_owner_user_superuser(collection_owner_permission, collection, request_data_su):
    """
    Test for IsCollectionOwner.has_object_permission to verify that superusers have permission
    """
    assert collection_owner_permission.has_object_permission(request_data_su.request,
                                                             request_data_su.view,
                                                             collection) is True


def test_is_collection_admin_anonymous_users(collection_permission, collection, request_data_anon):
    """
    Test for HasCollectionPermissions.has_object_permission to verify that
    anonymous users do not have permission.
    """
    assert collection_permission.has_object_permission(request_data_anon.request,
                                                       request_data_anon.view,
                                                       collection) is False


def test_is_collection_admin_user_different_from_collecton_owner(mock_moira_client,
                                                                 collection_permission,
                                                                 collection,
                                                                 request_data):
    """
    Test for HasCollectionPermissions.has_object_permission to verify
    that user who does not own the collection does not have permission
    """
    assert collection_permission.has_object_permission(request_data.request,
                                                       request_data.view,
                                                       collection) is False


def test_is_collection_user_not_matching_admin_lists(mock_moira_client,
                                                     moira_list,
                                                     collection_permission,
                                                     collection,
                                                     request_data):
    """
    Test for HasCollectionPermissions.has_object_permission to verify
    that user who does not match a collection moira admin list does not have permission
    """
    collection.admin_lists.set([moira_list])
    mock_moira_client.return_value.list_members.return_value = [get_moira_user(collection.owner).username]
    assert collection_permission.has_object_permission(request_data.request,
                                                       request_data.view,
                                                       collection) is False
    mock_moira_client.return_value.list_members.assert_called_once_with(moira_list.name, type='')


def test_is_collection_user_matching_admin_lists(mock_moira_client,
                                                 moira_list,
                                                 collection_permission,
                                                 collection,
                                                 request_data):
    """
    Test for HasCollectionPermissions.has_object_permission to verify
    that user who is in one of the collection's admin lists has permission
    """
    collection.admin_lists.set([moira_list])
    mock_moira_client.return_value.list_members.return_value = [get_moira_user(request_data.user).username]
    assert collection_permission.has_object_permission(request_data.request,
                                                       request_data.view,
                                                       collection) is True


def test_is_collection_user_not_matching_view_lists(mock_moira_client,
                                                    moira_list,
                                                    collection_permission,
                                                    collection,
                                                    request_data):
    """
    Test for HasCollectionPermissions.has_object_permission to verify
    that user who does not match a collection moira view list does not have permission
    """
    collection.view_lists.set([moira_list])
    mock_moira_client.return_value.list_members.return_value = ['someone_else']
    assert collection_permission.has_object_permission(request_data.request,
                                                       request_data.view,
                                                       collection) is False


def test_is_collection_user_matching_view_lists(mock_moira_client,
                                                moira_list,
                                                collection_permission,
                                                collection,
                                                request_data):
    """
    Test for HasCollectionPermissions.has_object_permission to verify
    that user who is in one of the collection's view lists has permission
    """
    collection.view_lists.set([moira_list])
    mock_moira_client.return_value.list_members.return_value = [get_moira_user(request_data.user).username]
    assert collection_permission.has_object_permission(request_data.request,
                                                       request_data.view,
                                                       collection) is True


def test_can_upload_to_collection_safe(can_upload_to_collection_permission,
                                       collection,
                                       request_data_anon):
    """
    Test for CanUploadToCollection with Safe Methods
    """
    request_data_anon.request.data = {'collection': collection.hexkey}
    assert can_upload_to_collection_permission.has_permission(request_data_anon.request,
                                                              request_data_anon.view) is False


def test_can_upload_to_collection_superuser(can_upload_to_collection_permission, collection, request_data_su):
    """
    Test for CanUploadToCollection with superuser
    """
    request_data_su.request.data = {'collection': collection.hexkey}
    request_data_su.request.method = 'POST'
    assert can_upload_to_collection_permission.has_permission(request_data_su.request,
                                                              request_data_su.view) is True


def test_can_upload_to_collection_no_key(mock_moira_client, can_upload_to_collection_permission, request_data):
    """
    Test for CanUploadToCollection without a collection key in the request DATA
    """
    request_data.request.method = 'POST'
    request_data.request.data = {}
    mock_moira_client.return_value.list_members.return_value = [get_moira_user(request_data.user).username]
    assert can_upload_to_collection_permission.has_permission(request_data.request, request_data.view) is False


def test_can_upload_to_collection_invalid_key(can_upload_to_collection_permission, request_data):
    """
    Test for CanUploadToCollection with a collection key in the request DATA that is invalid
    """
    request_data.request.method = 'POST'
    request_data.request.data = {'collection': 'fooooo'}
    with pytest.raises(ValidationError):
        can_upload_to_collection_permission.has_permission(request_data.request, request_data.view)


def test_can_upload_to_collection_other_key(mock_moira_client,
                                            can_upload_to_collection_permission,
                                            request_data):
    """
    Test for CanUploadToCollection with a collection key in the request DATA that is
    not associated to a collection
    """
    request_data.request.method = 'POST'
    request_data.request.data = {'collection': uuid4().hex}
    mock_moira_client.return_value.list_members.return_value = [get_moira_user(request_data.user).username]
    assert can_upload_to_collection_permission.has_permission(request_data.request, request_data.view) is False


def test_can_upload_to_collection_other_owner(mock_moira_client,
                                              can_upload_to_collection_permission,
                                              collection,
                                              request_data):
    """
    Test for CanUploadToCollection with a collection having another owner
    """
    request_data.request.method = 'POST'
    request_data.request.data = {'collection': collection.hexkey}
    mock_moira_client.return_value.list_members.return_value = ['someone_else']
    assert can_upload_to_collection_permission.has_permission(request_data.request, request_data.view) is False


def test_can_upload_to_collection(can_upload_to_collection_permission, collection, request_data):
    """
    Test for CanUploadToCollection happy path
    """
    request_data.request.method = 'POST'
    request_data.request.data = {'collection': collection.hexkey}
    collection.owner = request_data.user
    collection.save()
    assert can_upload_to_collection_permission.has_permission(request_data.request, request_data.view) is True


def test_video_view_permission_anonymous_users(video_permission, video, request_data_anon):
    """
    Test for HasVideoPermissions.has_object_permission to verify that anonymous users
    do not have permission to view the video
    """
    assert video_permission.has_object_permission(request_data_anon.request, request_data_anon.view, video) is False


def test_video_view_permission_other_user(mock_moira_client, video_permission, video, request_data):
    """
    Test for HasVideoPermissions.has_object_permission to verify
    that user who does not own the video's collection does not have permission
    """
    mock_moira_client.return_value.list_members.return_value = [get_moira_user(video.collection.owner).username]
    assert video_permission.has_object_permission(request_data.request, request_data.view, video) is False


def test_video_view_permission_collection_owner(video_permission, video, request_data):
    """
    Test for HasVideoPermissions.has_object_permission to verify
    that user who owns the video's collection has permission
    """
    video.collection.owner = request_data.user
    assert video_permission.has_object_permission(request_data.request, request_data.view, video) is True


def test_video_view_permission_user_superuser(video_permission, video, request_data_su):
    """
    Test for HasVideoPermissions.has_object_permission to verify that superusers have permission
    """
    assert video_permission.has_object_permission(request_data_su.request, request_data_su.view, video) is True


def test_video_view_permission_no_matching_lists(mock_moira_client, moira_list, video_permission, video, request_data):
    """
    Test for HasVideoPermissions.has_object_permission to verify
    that user who is not in the video collection's view-only moira lists cannot see it.
    """
    video.collection.view_lists.set([moira_list])
    mock_moira_client.return_value.list_members.return_value = ['someone_else']
    assert video_permission.has_object_permission(request_data.request, request_data.view, video) is False


def test_video_view_permission_matching_lists(mock_moira_client, moira_list, video_permission, video, request_data):
    """
    Test for HasVideoPermissions.has_object_permission to verify
    that a user in one of the video collection's view-only moira lists can see it.
    """
    video.collection.view_lists.set([moira_list])
    mock_moira_client.return_value.list_members.return_value = [get_moira_user(request_data.user).username]
    assert video_permission.has_object_permission(request_data.request, request_data.view, video) is True


def test_video_view_permission_matching_lists_post(mock_moira_client,
                                                   moira_list,
                                                   video_permission,
                                                   video,
                                                   request_data):
    """
    Test for HasVideoPermissions.has_object_permission to verify
    that a user in one of the video collection's view-only moira lists cannot use unsafe methods.
    """
    video.collection.view_lists.set([moira_list])
    request_data.request.method = 'POST'
    mock_moira_client.return_value.list_members.return_value = [get_moira_user(request_data.user).username]
    assert video_permission.has_object_permission(request_data.request, request_data.view, video) is False


def test_video_view_permission_matching_admin_lists(mock_moira_client,
                                                    moira_list,
                                                    video_permission,
                                                    video,
                                                    request_data):
    """
    Test for HasVideoPermissions.has_object_permission to verify
    that a user in one of the video collection's admin-only moira lists can see it.
    """
    video.collection.admin_lists.set([moira_list])
    mock_moira_client.return_value.list_members.return_value = [get_moira_user(request_data.user).username]
    assert video_permission.has_object_permission(request_data.request, request_data.view, video) is True


def test_video_admin_permission_anonymous_users(video_permission, video, request_data_anon):
    """
    Test for HasAdminPermissionsForVideo.has_object_permission to verify that anonymous users
    do not have permission to edit the video
    """
    request_data_anon.request.method = 'POST'
    assert video_permission.has_object_permission(request_data_anon.request, request_data_anon.view, video) is False


def test_video_admin_permission_other_user(mock_moira_client, moira_list, video_permission, video, request_data):
    """
    Test for HasAdminPermissionsForVideo.has_object_permission to verify
    that user who does not own the video's collection does not have permission
    """
    video.collection.view_lists.set([moira_list])
    mock_moira_client.return_value.list_members.return_value = [get_moira_user(request_data.user).username]
    request_data.request.method = 'POST'
    assert video_permission.has_object_permission(request_data.request, request_data.view, video) is False


def test_video_admin_permission_collection_owner(video_permission, video, request_data):
    """
    Test for HasAdminPermissionsForVideo.has_object_permission to verify
    that user who owns the video's collection has permission
    """
    video.collection.owner = request_data.user
    request_data.request.method = 'POST'
    assert video_permission.has_object_permission(request_data.request, request_data.view, video) is True


def test_video_admin_permission_superuser(video_permission, video, request_data_su):
    """
    Test for HasAdminPermissionsForVideo.has_object_permission to verify that superusers have permission
    """
    request_data_su.request.method = 'POST'
    assert video_permission.has_object_permission(request_data_su.request, request_data_su.view, video) is True


def test_video_admin_permission_no_matching_lists(mock_moira_client, moira_list,
                                                  video_permission,
                                                  video,
                                                  request_data):
    """
    Test for HasAdminPermissionsForVideo.has_object_permission to verify
    that user who is not in the video collection's admin moira lists cannot edit it.
    """
    video.collection.admin_lists.set([moira_list])
    request_data.request.method = 'POST'
    mock_moira_client.return_value.list_members.return_value = ['someone_else']
    assert video_permission.has_object_permission(request_data.request, request_data.view, video) is False


def test_video_admin_permission_matching_view_lists(mock_moira_client,
                                                    moira_list,
                                                    video_permission,
                                                    video,
                                                    request_data):
    """
    Test for HasAdminPermissionsForVideo.has_object_permission to verify
    that a user in one of the video collection's view-only moira lists cannot edit it.
    """
    video.collection.view_lists.set([moira_list])
    request_data.request.method = 'POST'
    mock_moira_client.return_value.list_members.return_value = [get_moira_user(request_data.user).username]
    assert video_permission.has_object_permission(request_data.request, request_data.view, video) is False


def test_video_admin_permission_matching_admin_lists(mock_moira_client,
                                                     moira_list,
                                                     video_permission,
                                                     video,
                                                     request_data):
    """
    Test for HasAdminPermissionsForVideo.has_object_permission to verify
    that a user in one of the video collection's admin moira lists can edit it.
    """
    video.collection.admin_lists.set([moira_list])
    request_data.request.method = 'POST'
    mock_moira_client.return_value.list_members.return_value = [get_moira_user(request_data.user).username]
    assert video_permission.has_object_permission(request_data.request, request_data.view, video) is True


def test_video_admin_permission_matching_lists_post(mock_moira_client,
                                                    moira_list,
                                                    video_permission,
                                                    video,
                                                    request_data):
    """
    Test for HasAdminPermissionsForVideo.has_object_permission to verify
    that a user in one of the video collection's admin moira lists can use unsafe methods.
    """
    video.collection.admin_lists.set([moira_list])
    request_data.request.method = 'POST'
    mock_moira_client.return_value.list_members.return_value = [get_moira_user(request_data.user).username]
    assert video_permission.has_object_permission(request_data.request, request_data.view, video) is True


def test_override_video_public_collection_private(video_permission,
                                                  request_data_anon,
                                                  video):
    """
    A public video in a private collection should be viewable by anonymous users if video permissions enabled
    """
    video.is_public = True
    assert video_permission.has_object_permission(
        request_data_anon.request, request_data_anon.view, video) is True


def test_override_video_public_collection_view_lists(video_permission,
                                                     mock_moira_client,
                                                     moira_list,
                                                     request_data_anon,
                                                     video):
    """
    A public video in a collection with view lists should be viewable by anonymous users if video permissions enabled
    """
    video.is_public = True
    video.collection.view_lists.set([moira_list])
    mock_moira_client.return_value.list_members.return_value = ['someone_else']
    assert video_permission.has_object_permission(
        request_data_anon.request, request_data_anon.view, video) is True


def test_override_video_private_collection_view_lists(mock_moira_client,
                                                      request_data,
                                                      video_permission,
                                                      video,
                                                      moira_list):
    """
    A private video should not be viewable by users in the collection view lists if video permissions enabled
    """
    video.is_private = True
    video.collection.view_lists.set([moira_list])
    video.save()
    mock_moira_client.return_value.list_members.return_value = [get_moira_user(request_data.user).username]
    assert video_permission.has_object_permission(
        request_data.request, request_data.view, video) is False


def test_override_video_private_collection_admin_lists(mock_moira_client,
                                                       moira_list,
                                                       request_data,
                                                       video_permission,
                                                       video):
    """
    A private video should be viewable by users in the collection admin lists
    """
    video.is_private = True
    video.collection.admin_lists.set([moira_list])
    mock_moira_client.return_value.list_members.return_value = [get_moira_user(request_data.user).username]
    assert video_permission.has_object_permission(request_data.request, request_data.view, video) is True


def test_override_video_view_lists_collection_view_lists(mock_moira_client,
                                                         request_data,
                                                         video_permission,
                                                         video):
    """
    A video with view lists should by viewable by users in those lists but not users in collection view lists,
    if video permissions are enabled
    """
    def mock_list_members(name, **kwargs):
        """ Return the request user's username for the video view list only """
        return [get_moira_user(request_data.request.user).username] if name == video_list.name else ['other']

    video_list = MoiraListFactory()
    collection_list = MoiraListFactory()
    video.view_lists.set([video_list])
    video.collection.view_lists.set([collection_list])
    mock_moira_client.return_value.list_members.side_effect = mock_list_members
    assert video_permission.has_object_permission(
        request_data.request, request_data.view, video) is True


def test_override_video_view_lists_collection_admin_lists(mock_moira_client,
                                                          request_data,
                                                          video_permission,
                                                          video):
    """
    A video with view lists should by viewable by users in collection admin lists
    """
    video_list = MoiraListFactory()
    collection_list = MoiraListFactory()

    def mock_list_members(name, **kwargs):
        """ Return the request user's username for the collection admin list only """
        return [get_moira_user(request_data.request.user).username] if name == collection_list.name else ['other']

    mock_moira_client.return_value.list_members.side_effect = mock_list_members
    video.view_lists.set([video_list])
    video.collection.admin_lists.set([collection_list])
    assert video_permission.has_object_permission(request_data.request, request_data.view, video) is True


def test_collections_view(mock_moira_client, moira_list, collection, alt_moira_data):
    """
    Test that CollectionManager.all_viewable returns the lists that the user has view access to.
    """
    collection.view_lists.set([moira_list])
    alt_moira_data.collection.view_lists.set([alt_moira_data.moira_list])
    mock_moira_client.return_value.user_lists.return_value = [moira_list.name]
    assert collection in Collection.objects.all_viewable(alt_moira_data.user)
    assert alt_moira_data.collection not in Collection.objects.all_viewable(alt_moira_data.user)


def test_collections_view_admin_user(mock_moira_client, moira_list, collection, alt_moira_data):
    """
    Test that CollectionManager.all_viewable returns the lists that the user has view access to.
    """
    collection.admin_lists.set([moira_list])
    alt_moira_data.collection.admin_lists.set([alt_moira_data.moira_list])
    alt_moira_data.collection.view_lists.set([moira_list])
    mock_moira_client.return_value.user_lists.return_value = [moira_list.name]
    for col in (collection, alt_moira_data.collection):
        assert col in Collection.objects.all_viewable(alt_moira_data.user)


def test_collections_admin(mock_moira_client, collection, moira_list, alt_moira_data):
    """
    Test that CollectionManager.all_admin returns the lists that the user has admin access to.
    """
    collection.admin_lists.set([moira_list])
    alt_moira_data.collection.view_lists.set([moira_list])
    mock_moira_client.return_value.user_lists.return_value = [moira_list.name]
    assert collection in Collection.objects.all_admin(alt_moira_data.user)
    assert alt_moira_data.collection not in Collection.objects.all_admin(alt_moira_data.user)


def test_subtitle_view_permission_no_matching_lists(mock_moira_client,
                                                    moira_list,
                                                    subtitle_permission,
                                                    subtitle,
                                                    request_data):
    """
    Test for HasVideoSubtitlePermissions.has_object_permission to verify
    that user who is not in the subtitle collection's view-only moira lists cannot see it.
    """
    subtitle.video.collection.view_lists.set([moira_list])
    mock_moira_client.return_value.list_members.return_value = ['someone_else']
    assert subtitle_permission.has_object_permission(request_data.request, request_data.view, subtitle) is False


def test_subtitle_view_permission_matching_lists(mock_moira_client,
                                                 moira_list,
                                                 subtitle_permission,
                                                 subtitle,
                                                 request_data):
    """
    Test for HasVideoSubtitlePermissions.has_object_permission to verify
    that a user in one of the subtitle collection's view-only moira lists can see it.
    """
    subtitle.video.collection.view_lists.set([moira_list])
    mock_moira_client.return_value.list_members.return_value = [get_moira_user(request_data.user).username]
    assert subtitle_permission.has_object_permission(request_data.request, request_data.view, subtitle) is True


def test_subtitle_admin_permission_no_matching_lists(mock_moira_client, moira_list,
                                                     subtitle_permission,
                                                     subtitle,
                                                     request_data):
    """
    Test for HasVideoSubtitlePermissions.has_object_permission to verify
    that user who is not in the subtitle collection's admin moira lists cannot edit it.
    """
    subtitle.video.collection.admin_lists.set([moira_list])
    mock_moira_client.return_value.list_members.return_value = ['someone_else']
    request_data.request.method = 'POST'
    assert subtitle_permission.has_object_permission(request_data.request, request_data.view, subtitle) is False


def test_subtitle_admin_permission_matching_lists(mock_moira_client,
                                                  moira_list,
                                                  subtitle_permission,
                                                  subtitle,
                                                  request_data):
    """
    Test for HasVideoSubtitlePermissions.has_object_permission to verify
    that a user in one of the subtitle collection's admin moira lists can use unsafe methods.
    """
    subtitle.video.collection.admin_lists.set([moira_list])
    mock_moira_client.return_value.list_members.return_value = [get_moira_user(request_data.user).username]
    request_data.request.method = 'POST'
    assert subtitle_permission.has_object_permission(request_data.request, request_data.view, subtitle) is True
