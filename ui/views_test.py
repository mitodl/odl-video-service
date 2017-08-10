"""
Tests for views
"""
import json
from uuid import uuid4

import pytest
from django.conf import settings
from django.test.utils import override_settings
from rest_framework import status
from rest_framework.reverse import reverse

from ui.factories import (
    UserFactory,
    CollectionFactory,
    VideoFileFactory,
    VideoFactory,
)
from ui.serializers import DropboxUploadSerializer

pytestmark = pytest.mark.django_db

# pylint: disable=redefined-outer-name


@pytest.fixture()
def logged_in_client(client):
    """
    Fixture for a Django client that is logged in for the test user
    """
    user = UserFactory()
    client.force_login(user)
    return client, user


@pytest.fixture()
def logged_in_apiclient(apiclient):
    """
    Fixture for a Django client that is logged in for the test user
    """
    user = UserFactory()
    apiclient.force_login(user)
    return apiclient, user


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


def test_video_detail_hls(logged_in_client, mocker):
    """Test video detail page when HLS videofile is available"""
    client, user = logged_in_client
    videofileHLS = VideoFileFactory(hls=True, video__collection__owner=user)
    mocker.patch('ui.utils.get_cloudfront_signed_url', return_value=videofileHLS.cloudfront_url)
    videofileHLS.video.status = 'Complete'
    url = reverse('video-detail', kwargs={'video_key': videofileHLS.video.hexkey})
    response = client.get(url)
    assert 'videofile' in response.context_data
    js_settings_json = json.loads(response.context_data['js_settings_json'])
    assert js_settings_json == {
        'videofile': response.context_data['videofile'].cloudfront_url,
        "gaTrackingID": settings.GA_TRACKING_ID,
        "public_path": '/static/bundles/'
    }


def test_video_detail_unencoded(logged_in_client, mocker):
    """Test video detail page when HLS videofile is not available"""
    client, user = logged_in_client
    videofile_unencoded = VideoFileFactory(unencoded=True, video__collection__owner=user)
    mocker.patch('ui.utils.get_cloudfront_signed_url', return_value=videofile_unencoded.cloudfront_url)
    url = reverse('video-detail', kwargs={'video_key': videofile_unencoded.video.hexkey})
    videofile_unencoded.video.status = 'Complete'
    response = client.get(url)
    assert 'videofile' in response.context_data
    assert response.context_data['videofile'] is None
    js_settings_json = json.loads(response.context_data['js_settings_json'])
    assert 'videofile' in js_settings_json
    assert js_settings_json['videofile'] is None


def test_video_uswitch(logged_in_client, mocker, settings):  # pylint: disable=redefined-outer-name
    """Test video detail page when Video.multiangle is True"""
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
    url = reverse('video-uswitch', kwargs={'video_key': video.hexkey})
    response = client.get(url)
    assert response.context_data['uswitchPlayerURL'] == 'https://testing_odl.mit.edu'
    js_settings_json = json.loads(response.context_data['js_settings_json'])
    assert js_settings_json == {
        'videofile': {
            'src': response.context_data['videofile'].cloudfront_url,
            'title': video.title,
            'description': video.description,
        },
        'uswitchPlayerURL': 'https://testing_odl.mit.edu',
        'gaTrackingID': settings.GA_TRACKING_ID,
        'public_path': '/static/bundles/'
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


def test_upload_dropbox_videos_authentication(logged_in_apiclient):
    """
    Tests that only authenticated users can call UploadVideosFromDropbox
    """
    client, user = logged_in_apiclient
    client.logout()
    url = reverse('upload-videos')
    collection = CollectionFactory(owner=user)
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


def test_collection_viewset_list(logged_in_apiclient):
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


def test_collection_viewset_create(logged_in_apiclient):
    """
    Tests to create a collection for an user
    """
    client, user = logged_in_apiclient
    url = reverse('models-api:collection-list')

    input_data = {
        'owner': user.id,
        'title': 'foo title'
    }
    result = client.post(url, input_data, format='json')
    assert result.status_code == status.HTTP_201_CREATED
    assert 'videos' not in result.data

    # the creation should work also without a JSON request
    result = client.post(url, input_data)
    assert result.status_code == status.HTTP_201_CREATED
    assert 'videos' not in result.data

    # user cannot create the collection if is not owner
    other_user = UserFactory()
    input_data = {
        'owner': other_user.id,
        'title': 'foo title'
    }
    assert client.post(url, input_data, format='json').status_code == status.HTTP_403_FORBIDDEN

    # or if does not specify the owner id
    input_data = {
        'title': 'foo title'
    }
    result = client.post(url, input_data, format='json')
    assert client.post(url, input_data, format='json').status_code == status.HTTP_403_FORBIDDEN


def test_collection_viewset_create_as_superuser(logged_in_apiclient):
    """
    Tests to create a collection for a superuser
    """
    client, user = logged_in_apiclient
    user.is_superuser = True
    user.save()
    url = reverse('models-api:collection-list')

    input_data = {
        'owner': user.id,
        'title': 'foo title'
    }
    result = client.post(url, input_data, format='json')
    assert result.status_code == status.HTTP_201_CREATED
    assert 'videos' not in result.data

    # user can create the collection if is not owner
    other_user = UserFactory()
    input_data = {
        'owner': other_user.id,
        'title': 'foo title'
    }
    assert client.post(url, input_data, format='json').status_code == status.HTTP_201_CREATED

    # if does not specify the owner id it gets a different error
    input_data = {
        'title': 'foo title'
    }
    result = client.post(url, input_data, format='json')
    assert client.post(url, input_data, format='json').status_code == status.HTTP_400_BAD_REQUEST


def test_collection_viewset_detail(logged_in_apiclient):
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

    result = client.put(url, {'title': 'foo title', 'owner': user.id}, format='json')
    assert result.status_code == status.HTTP_200_OK
    assert result.data['title'] == 'foo title'

    # user cannot delete the collection if is not owner
    other_user = UserFactory()
    collection.owner = other_user
    collection.save()
    result = client.delete(url)
    assert result.status_code == status.HTTP_404_NOT_FOUND

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

    result = client.put(url, {'title': 'foo title', 'owner': user.id}, format='json')
    assert result.status_code == status.HTTP_200_OK
    assert result.data['title'] == 'foo title'

    # user can delete the collection
    result = client.delete(url)
    assert result.status_code == status.HTTP_204_NO_CONTENT
