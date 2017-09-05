"""
Tests for views
"""
import json
from types import SimpleNamespace
from uuid import uuid4

import pytest
from django.conf import settings
from django.test.utils import override_settings
from rest_framework import status
from rest_framework.reverse import reverse

from ui import factories
from ui.factories import (
    UserFactory,
    CollectionFactory,
    VideoFileFactory,
    VideoFactory,
)
from ui.serializers import (
    DropboxUploadSerializer,
    VideoSerializer,
)

pytestmark = pytest.mark.django_db

# pylint: disable=redefined-outer-name,unused-argument


@pytest.fixture()
def logged_in_client(client):
    """
    Fixture for a Django client that is logged in for the test user
    """
    user = UserFactory()
    client.force_login(user)
    return client, user


@pytest.fixture
def logged_in_apiclient(apiclient):
    """
    Fixture for a Django client that is logged in for the test user
    """
    user = UserFactory()
    apiclient.force_login(user)
    return apiclient, user


@pytest.fixture
def user_view_list_data():
    """
    Fixture for testing VideoDetail view permissions with a collection view_list
    """
    video = VideoFactory()
    collection = video.collection
    moira_list = factories.MoiraListFactory()
    collection.view_lists = [moira_list]
    return SimpleNamespace(video=video, moira_list=moira_list, collection=collection)


@pytest.fixture
def user_admin_list_data():
    """
    Fixture for testing VideoDetail view permissions with a collection admin_list
    """
    video = VideoFactory()
    collection = video.collection
    moira_list = factories.MoiraListFactory()
    collection.admin_lists = [moira_list]
    return SimpleNamespace(video=video, moira_list=moira_list, collection=collection)


@pytest.fixture
def post_data(logged_in_apiclient):
    """Fixture for testing collection creation using valid post data"""
    _, user = logged_in_apiclient

    input_data = {
        'owner': user.id,
        'title': 'foo title',
        'view_lists': [],
        'admin_lists': []
    }
    return input_data


def test_index_anonymous(client):
    """Test index anonymous"""
    response = client.get(reverse('index'))
    assert response.status_code == status.HTTP_200_OK
    assert 'login_form' in response.context_data
    assert 'register_form' in response.context_data
    assert response.template_name == ['ui/index.html']


def test_upload_anonymous(client):
    """Test upload anonymous"""
    collection = CollectionFactory()
    url = reverse('upload', kwargs={'collection_key': collection.hexkey})
    response = client.get(url)
    assert response.status_code == status.HTTP_302_FOUND
    assert response['Location'] == '/login/?next={}'.format(url)


@override_settings(DROPBOX_KEY='dbkey')
def test_dropbox_keys_in_context(logged_in_client):
    """Test dropbox keys in context"""
    client, user = logged_in_client
    collection = CollectionFactory(owner=user)
    response = client.get(reverse('upload', kwargs={'collection_key': collection.hexkey}))
    assert response.status_code == status.HTTP_200_OK
    assert response.context_data['dropbox_key'] == 'dbkey'
    assert response.template_name == ['ui/upload.html']


def test_video_detail(logged_in_client, mocker):
    """Test video detail page"""
    client, user = logged_in_client
    videofileHLS = VideoFileFactory(hls=True, video__collection__owner=user)
    mocker.patch('ui.utils.get_cloudfront_signed_url', return_value=videofileHLS.cloudfront_url)
    videofileHLS.video.status = 'Complete'
    url = reverse('video-detail', kwargs={'video_key': videofileHLS.video.hexkey})
    response = client.get(url)
    js_settings_json = json.loads(response.context_data['js_settings_json'])
    assert js_settings_json == {
        'editable': True,
        "gaTrackingID": settings.GA_TRACKING_ID,
        "public_path": '/static/bundles/',
        "videoKey": videofileHLS.video.hexkey,
        "thumbnail_base_url": settings.VIDEO_THUMBNAIL_BASE_URL,
        "user": user.email
    }


def test_video_embed(logged_in_client, mocker, settings):  # pylint: disable=redefined-outer-name
    """Test video embed page"""
    settings.USWITCH_URL = 'https://testing_odl.mit.edu'
    client, user = logged_in_client
    videofileHLS = VideoFileFactory(
        hls=True,
        video__collection__owner=user,
        video__multiangle=True,
        video__status='Complete'
    )
    video = videofileHLS.video
    mocker.patch('ui.utils.get_cloudfront_signed_url', return_value=videofileHLS.cloudfront_url)
    url = reverse('video-embed', kwargs={'video_key': video.hexkey})
    response = client.get(url)
    assert response.context_data['uswitchPlayerURL'] == 'https://testing_odl.mit.edu'
    js_settings_json = json.loads(response.context_data['js_settings_json'])
    assert js_settings_json == {
        "video": VideoSerializer(video).data,
        "gaTrackingID": settings.GA_TRACKING_ID,
        "public_path": "/static/bundles/",
        "thumbnail_base_url": settings.VIDEO_THUMBNAIL_BASE_URL,
        "user": user.email
    }


def test_mosaic_view(logged_in_client, settings):  # pylint: disable=redefined-outer-name
    """Test the MosaicView"""
    client, _ = logged_in_client
    video = VideoFactory(multiangle=True)
    settings.USWITCH_URL = 'https://testing_odl.mit.edu'
    url = reverse('video-mosaic', kwargs={'video_key': video.hexkey})
    response = client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert response.context_data['uswitchPlayerURL'] == 'https://testing_odl.mit.edu'


def test_upload_dropbox_videos_authentication(mock_moira_client, logged_in_apiclient):
    """
    Tests that only authenticated users with collection admin permissions can call UploadVideosFromDropbox
    """
    client, user = logged_in_apiclient
    client.logout()
    url = reverse('upload-videos')
    collection = CollectionFactory(owner=user)
    moira_list = factories.MoiraListFactory()
    collection.admin_lists = [moira_list]
    collection.save()
    other_user = UserFactory()
    input_data = {
        "collection": collection.hexkey,
        "files": [
            {
                "isDir": False,
                "link": "http://foo.bar/hoo.mp4",
                "thumbnailLink": "http://foo.bar.link/hoo.mp4",
                "bytes": 80633422,
                "name": "foo file",
                "icon": "https://foo.bar/static/images/icons64/page_white_film.png"
            }
        ]
    }
    # call with anonymous user
    assert client.post(url, input_data, format='json').status_code == status.HTTP_403_FORBIDDEN
    # call with another user
    client.force_login(other_user)
    assert client.post(url, input_data, format='json').status_code == status.HTTP_403_FORBIDDEN


def test_upload_dropbox_videos_bad_data(logged_in_apiclient):
    """
    Tests for UploadVideosFromDropbox with bad data
    """
    client, user = logged_in_apiclient
    collection = CollectionFactory(owner=user)
    url = reverse('upload-videos')
    input_data = {
        "collection": collection.hexkey,
        "files": [
            {
                "isDir": False,
                "link": "http://foo.bar/hoo.mp4",
                "thumbnailLink": "http://foo.bar.link/hoo.mp4",
            }
        ]
    }
    assert client.post(url, input_data, format='json').status_code == status.HTTP_400_BAD_REQUEST


def test_upload_dropbox_videos(logged_in_apiclient, mocker):
    """
    Tests for UploadVideosFromDropbox happy path
    """
    client, user = logged_in_apiclient
    collection = CollectionFactory(owner=user)
    url = reverse('upload-videos')
    mocked_api = mocker.patch('ui.api.process_dropbox_data', return_value={'foo': 'bar'})
    input_data = {
        "collection": collection.hexkey,
        "files": [
            {
                "isDir": False,
                "link": "http://foo.bar/hoo.mp4",
                "thumbnailLink": "http://foo.bar.link/hoo.mp4",
                "bytes": 80633422,
                "name": "foo file",
                "icon": "https://foo.bar/static/images/icons64/page_white_film.png"
            }
        ]
    }
    response = client.post(url, input_data, format='json')
    assert response.status_code == status.HTTP_202_ACCEPTED
    assert response.data == {'foo': 'bar'}
    serializer = DropboxUploadSerializer(data=input_data)
    serializer.is_valid()
    mocked_api.assert_called_once_with(serializer.validated_data)


def test_collection_viewset_permissions(logged_in_apiclient):
    """
    Tests the list of collections for an anonymous_user
    """
    client, _ = logged_in_apiclient
    client.logout()
    urls = (
        reverse('models-api:collection-list'),
        reverse('models-api:collection-detail', kwargs={'key': uuid4().hex}),
    )
    for url in urls:
        assert client.get(url).status_code == status.HTTP_403_FORBIDDEN
        assert client.post(url, {'owner': 1}).status_code == status.HTTP_403_FORBIDDEN


def test_collection_viewset_list(mock_moira_client, logged_in_apiclient):
    """
    Tests the list of collections for an user
    """
    client, user = logged_in_apiclient
    url = reverse('models-api:collection-list')
    collections = [CollectionFactory(owner=user).hexkey for _ in range(5)]
    other_user = UserFactory()
    CollectionFactory(owner=other_user)

    result = client.get(url)
    assert result.status_code == status.HTTP_200_OK
    assert len(result.data) == 5
    for coll_data in result.data:
        assert coll_data['key'] in collections
        assert 'videos' not in coll_data


def test_collection_viewset_list_superuser(logged_in_apiclient):
    """
    Tests the list of collections for a superuser
    """
    client, user = logged_in_apiclient
    user.is_superuser = True
    user.save()
    url = reverse('models-api:collection-list')
    collections = [CollectionFactory(owner=user).hexkey for _ in range(5)]
    other_user = UserFactory()
    collections += [CollectionFactory(owner=other_user).hexkey]

    result = client.get(url)
    assert result.status_code == status.HTTP_200_OK
    assert len(result.data) == 6
    for coll_data in result.data:
        assert coll_data['key'] in collections


def test_collection_viewset_create_as_normal_user(post_data, logged_in_apiclient):
    """
    Tests that a normal user is not allowed to create a collection
    """
    client, _ = logged_in_apiclient
    url = reverse('models-api:collection-list')
    result = client.post(url, post_data, format='json')
    assert result.status_code == status.HTTP_403_FORBIDDEN


def test_collection_viewset_create_as_staff(post_data, logged_in_apiclient):
    """
    Tests that a staff user can create a collection with self as owner but nobody else
    """
    client, user = logged_in_apiclient
    user.is_staff = True
    user.save()
    url = reverse('models-api:collection-list')
    result = client.post(url, post_data, format='json')
    assert result.status_code == status.HTTP_201_CREATED
    assert 'videos' not in result.data

    # the creation should work also without a JSON request
    result = client.post(url, post_data)
    assert result.status_code == status.HTTP_201_CREATED
    assert 'videos' not in result.data

    # user cannot create the collection if is not owner
    other_user = UserFactory()
    input_data = {
        'owner': other_user.id,
        'title': 'foo title',
        'view_lists': [],
        'admin_lists': []
    }
    assert client.post(url, input_data, format='json').status_code == status.HTTP_403_FORBIDDEN

    # or if does not specify the owner id
    input_data = {
        'title': 'foo title',
        'view_lists': [],
        'admin_lists': []
    }
    assert client.post(url, input_data, format='json').status_code == status.HTTP_400_BAD_REQUEST


def test_collection_viewset_create_as_superuser(post_data, logged_in_apiclient):
    """
    Tests that a superuser can create a collection for anyone as owner (but owner can't be None).
    """
    client, user = logged_in_apiclient
    user.is_superuser = True
    user.save()
    url = reverse('models-api:collection-list')
    result = client.post(url, post_data, format='json')
    assert result.status_code == status.HTTP_201_CREATED
    assert 'videos' not in result.data

    # user can create the collection if is not owner
    other_user = UserFactory()
    input_data = {
        'owner': other_user.id,
        'view_lists': [],
        'admin_lists': [],
        'title': 'foo title'
    }
    assert client.post(url, input_data, format='json').status_code == status.HTTP_201_CREATED

    # if does not specify the owner id it gets a different error
    input_data = {
        'title': 'foo title',
        'view_lists': [],
        'admin_lists': []
    }
    assert client.post(url, input_data, format='json').status_code == status.HTTP_400_BAD_REQUEST


def test_collection_viewset_detail(mock_moira_client, logged_in_apiclient):
    """
    Tests to retrieve a collection details for an user
    """
    client, user = logged_in_apiclient
    collection = CollectionFactory(owner=user)
    videos = [VideoFactory(collection=collection).hexkey for _ in range(5)]
    url = reverse('models-api:collection-detail', kwargs={'key': collection.hexkey})
    result = client.get(url)
    assert result.status_code == status.HTTP_200_OK
    assert 'videos' in result.data
    assert len(result.data['videos']) == 5
    for video_data in result.data['videos']:
        assert video_data['key'] in videos

    result = client.put(url, {'title': 'foo title',
                              'owner': user.id,
                              'view_lists': [],
                              'admin_lists': []},
                        format='json')
    assert result.status_code == status.HTTP_200_OK
    assert result.data['title'] == 'foo title'

    # user cannot delete the collection if is not owner
    other_user = UserFactory()
    collection.owner = other_user
    collection.save()
    result = client.delete(url)
    assert result.status_code == status.HTTP_403_FORBIDDEN

    collection.owner = user
    collection.save()
    result = client.delete(url)
    assert result.status_code == status.HTTP_204_NO_CONTENT


def test_collection_viewset_detail_as_superuser(logged_in_apiclient):
    """
    Tests to retrieve a collection details for a superuser
    """
    client, user = logged_in_apiclient
    user.is_superuser = True
    user.save()

    collection = CollectionFactory(owner=UserFactory())
    url = reverse('models-api:collection-detail', kwargs={'key': collection.hexkey})
    result = client.get(url)
    assert result.status_code == status.HTTP_200_OK
    assert 'videos' in result.data

    result = client.put(url, {'title': 'foo title',
                              'owner': user.id,
                              'view_lists': [],
                              'admin_lists': []},
                        format='json')
    assert result.status_code == status.HTTP_200_OK
    assert result.data['title'] == 'foo title'

    # user can delete the collection
    result = client.delete(url)
    assert result.status_code == status.HTTP_204_NO_CONTENT


def test_video_detail_view_permission(mock_moira_client, logged_in_apiclient, user_view_list_data):
    """
    Tests that a user can view a video if user is a member of collection's view_lists
    """
    client, _ = logged_in_apiclient
    mock_moira_client.return_value.user_lists.return_value = [user_view_list_data.moira_list.name]
    url = reverse('video-detail', kwargs={'video_key': user_view_list_data.video.hexkey})
    result = client.get(url)
    assert result.status_code == status.HTTP_200_OK
    assert json.loads(result.context_data['js_settings_json'])['editable'] is False


def test_video_detail_admin_permission(logged_in_apiclient, mock_moira_client, user_admin_list_data):
    """
    Tests that a user can view a video if user is a member of collection's admin_lists
    """
    client, _ = logged_in_apiclient
    mock_moira_client.return_value.user_lists.return_value = [user_admin_list_data.moira_list.name]
    url = reverse('video-detail', kwargs={'video_key': user_admin_list_data.video.hexkey})
    result = client.get(url)
    assert result.status_code == status.HTTP_200_OK
    assert json.loads(result.context_data['js_settings_json'])['editable'] is True


def test_video_detail_no_permission(mock_moira_client, logged_in_apiclient, user_admin_list_data):
    """
    Tests that a user cannot view a video if user is not a member of collection's lists
    """
    client, _ = logged_in_apiclient
    mock_moira_client.return_value.user_lists.return_value = ['other_list']
    url = reverse('video-detail', kwargs={'video_key': user_admin_list_data.video.hexkey})
    result = client.get(url)
    assert result.status_code == status.HTTP_403_FORBIDDEN
