"""
Tests for views
"""
import json
from types import SimpleNamespace
from uuid import uuid4

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.reverse import reverse

from techtv2ovs.factories import TechTVVideoFactory
from ui import factories
from ui.factories import (
    UserFactory,
    CollectionFactory,
    VideoFileFactory,
    VideoFactory,
    MoiraListFactory,
    VideoSubtitleFactory,
    YouTubeVideoFactory)
from ui.models import VideoSubtitle
from ui.serializers import (
    DropboxUploadSerializer,
    VideoSerializer)
from ui.utils import get_moira_user
from ui.views import CollectionReactView

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


def test_index(logged_in_client):
    """Test index anonymous"""
    client, _ = logged_in_client
    response = client.get(reverse('index'), follow=True)
    assert response.status_code == status.HTTP_200_OK
    assert isinstance(response.context_data['view'], CollectionReactView)


def test_video_detail(logged_in_client, settings):
    """Test video detail page"""
    client, user = logged_in_client
    settings.GA_DIMENSION_CAMERA = 'camera1'
    settings.GA_TRACKING_ID = 'UA-xyz-1'
    videofileHLS = VideoFileFactory(hls=True, video__collection__owner=user)
    videofileHLS.video.status = 'Complete'
    url = reverse('video-detail', kwargs={'video_key': videofileHLS.video.hexkey})
    response = client.get(url)
    js_settings_json = json.loads(response.context_data['js_settings_json'])
    assert js_settings_json == {
        'editable': True,
        "gaTrackingID": settings.GA_TRACKING_ID,
        "ga_dimension_camera": settings.GA_DIMENSION_CAMERA,
        "public_path": '/static/bundles/',
        "videoKey": videofileHLS.video.hexkey,
        "cloudfront_base_url": settings.VIDEO_CLOUDFRONT_BASE_URL,
        "user": user.username,
        "email": user.email,
        "support_email_address": settings.EMAIL_SUPPORT,
        "dropbox_key": "foo_dropbox_key",
        "FEATURES": {
            "ENABLE_VIDEO_PERMISSIONS": False
        }
    }


def test_video_embed(logged_in_client, settings):  # pylint: disable=redefined-outer-name
    """Test video embed page"""
    client, user = logged_in_client
    settings.GA_DIMENSION_CAMERA = 'camera1'
    settings.GA_TRACKING_ID = 'UA-xyz-1'
    videofileHLS = VideoFileFactory(
        hls=True,
        video__collection__owner=user,
        video__multiangle=True,
        video__status='Complete'
    )
    video = videofileHLS.video
    url = reverse('video-embed', kwargs={'video_key': video.hexkey})
    response = client.get(url)
    js_settings_json = json.loads(response.context_data['js_settings_json'])
    assert js_settings_json == {
        "video": VideoSerializer(video).data,
        "gaTrackingID": settings.GA_TRACKING_ID,
        "ga_dimension_camera": settings.GA_DIMENSION_CAMERA,
        "public_path": "/static/bundles/",
        "cloudfront_base_url": settings.VIDEO_CLOUDFRONT_BASE_URL,
        "user": user.username,
        "email": user.email,
        "support_email_address": settings.EMAIL_SUPPORT,
        "FEATURES": {
            "ENABLE_VIDEO_PERMISSIONS": False
        }
    }


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
    Tests the list of collections for a user
    """
    client, user = logged_in_apiclient
    url = reverse('models-api:collection-list')

    moira_list = MoiraListFactory()
    expected_collection_keys = [
        CollectionFactory(owner=user).hexkey,
        CollectionFactory(view_lists=[moira_list]).hexkey
    ]
    prohibited_collection_keys = [
        CollectionFactory().hexkey,
        CollectionFactory(view_lists=[MoiraListFactory()]).hexkey
    ]
    mock_moira_client.return_value.user_lists.return_value = [moira_list.name]

    result = client.get(url)
    assert result.status_code == status.HTTP_200_OK
    assert len(result.data) == len(expected_collection_keys)
    for coll_data in result.data:
        assert coll_data['key'] in expected_collection_keys
        assert coll_data['key'] not in prohibited_collection_keys
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


def test_collection_viewset_create_as_staff(mocker, post_data, logged_in_apiclient):
    """
    Tests that a staff user can create a collection with self as owner but nobody else
    """
    mocker.patch('ui.serializers.get_moira_client')
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


def test_collection_viewset_create_as_superuser(mocker, post_data, logged_in_apiclient):
    """
    Tests that a superuser can create a collection for anyone as owner (but owner can't be None).
    """
    mocker.patch('ui.serializers.get_moira_client')
    client, user = logged_in_apiclient
    user.is_superuser = True
    user.save()
    url = reverse('models-api:collection-list')
    result = client.post(url, post_data, format='json')
    assert result.status_code == status.HTTP_201_CREATED
    assert 'videos' not in result.data


def test_collection_viewset_detail(mocker, logged_in_apiclient):
    """
    Tests to retrieve a collection details for a user
    """
    mocker.patch('ui.serializers.get_moira_client')
    mocker.patch('ui.utils.get_moira_client')
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


def test_collection_viewset_detail_as_superuser(mocker, logged_in_apiclient):
    """
    Tests to retrieve a collection details for a superuser
    """
    mocker.patch('ui.serializers.get_moira_client')
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


def test_collections_next(mock_moira_client, logged_in_apiclient, user_admin_list_data):
    """
    Tests that the collections page redirects to the URL in the `next` parameter if present
    """
    client, user = logged_in_apiclient
    mock_moira_client.return_value.list_members.return_value = [user.username]
    video_url = reverse('video-detail', kwargs={'video_key': user_admin_list_data.video.hexkey})
    response = client.get('/collections/?next={}'.format(video_url), follow=True)
    final_url, status_code = response.redirect_chain[-1]
    assert video_url == final_url
    assert status_code == 302


def test_video_detail_view_permission(mock_moira_client, logged_in_apiclient, user_view_list_data):
    """
    Tests that a user can view a video if user is a member of collection's view_lists
    """
    client, user = logged_in_apiclient
    mock_moira_client.return_value.list_members.return_value = [get_moira_user(user).username]
    url = reverse('video-detail', kwargs={'video_key': user_view_list_data.video.hexkey})
    result = client.get(url)
    assert result.status_code == status.HTTP_200_OK
    assert json.loads(result.context_data['js_settings_json'])['editable'] is False


def test_video_detail_admin_permission(logged_in_apiclient, mock_moira_client, user_admin_list_data):
    """
    Tests that a user can view a video if user is a member of collection's admin_lists
    """
    client, user = logged_in_apiclient
    mock_moira_client.return_value.list_members.return_value = [get_moira_user(user).username]
    url = reverse('video-detail', kwargs={'video_key': user_admin_list_data.video.hexkey})
    result = client.get(url)
    assert result.status_code == status.HTTP_200_OK
    assert json.loads(result.context_data['js_settings_json'])['editable'] is True


def test_video_detail_no_permission(mock_moira_client, logged_in_apiclient, user_admin_list_data):
    """
    Tests that a user cannot view a video if user is not a member of collection's lists
    """
    client, _ = logged_in_apiclient
    mock_moira_client.return_value.list_members.return_value = ['someone_else']
    url = reverse('video-detail', kwargs={'video_key': user_admin_list_data.video.hexkey})
    result = client.get(url)
    assert result.status_code == status.HTTP_403_FORBIDDEN


def test_video_detail_anonymous(settings, logged_in_apiclient, user_admin_list_data):
    """
    Tests that an anonymous user is redirected to the login page, with a next parameter
    """
    client, _ = logged_in_apiclient
    client.logout()
    url = reverse('video-detail', kwargs={'video_key': user_admin_list_data.video.hexkey})
    response = client.get(url, follow=True)
    last_url, status_code = response.redirect_chain[-1]
    assert settings.LOGIN_URL in last_url
    assert status_code == 302
    assert '?next=/videos/{}'.format(user_admin_list_data.video.hexkey) in last_url


def test_techtv_detail_standard_url(mock_moira_client, user_view_list_data, logged_in_apiclient):
    """
    Tests that a URL based on a TechTV id returns the correct Video detail page
    """
    client, user = logged_in_apiclient
    ttv_video = TechTVVideoFactory(video=user_view_list_data.video)
    mock_moira_client.return_value.list_members.return_value = [get_moira_user(user).username]
    url = reverse('techtv-detail', kwargs={'video_key': ttv_video.ttv_id})
    result = client.get(url)
    assert result.status_code == status.HTTP_200_OK
    assert json.loads(result.context_data['js_settings_json'])['videoKey'] == user_view_list_data.video.hexkey


def test_techtv_detail_private_url(mock_moira_client, user_view_list_data, logged_in_apiclient):
    """
    Tests that a URL based on a TechTV private token returns the correct Video detail page
    """
    client, user = logged_in_apiclient
    ttv_video = TechTVVideoFactory(video=user_view_list_data.video, private=True, private_token=uuid4().hex)
    mock_moira_client.return_value.list_members.return_value = [get_moira_user(user).username]
    url = reverse('techtv-private', kwargs={'video_key': ttv_video.private_token})
    result = client.get(url)
    assert result.status_code == status.HTTP_200_OK
    assert json.loads(result.context_data['js_settings_json'])['videoKey'] == user_view_list_data.video.hexkey


def test_techtv_detail_embed_url(mock_moira_client, user_view_list_data, logged_in_apiclient):
    """
    Tests that an embed URL based on a TechTV id returns the correct Video embed page
    """
    client, user = logged_in_apiclient
    ttv_video = TechTVVideoFactory(video=user_view_list_data.video)
    mock_moira_client.return_value.list_members.return_value = [get_moira_user(user).username]
    url = reverse('techtv-embed', kwargs={'video_key': ttv_video.ttv_id})
    result = client.get(url)
    assert result.status_code == status.HTTP_200_OK
    assert json.loads(result.context_data['js_settings_json'])['video']['key'] == user_view_list_data.video.hexkey


@pytest.mark.parametrize("enable_video_permissions", [False, True])
def test_upload_subtitles(logged_in_apiclient, mocker, enable_video_permissions, settings):
    """
    Tests for UploadVideoSubtitle
    """
    mocker.patch('ui.views.cloudapi.boto3')
    expected_subtitle_key = 'subtitles/test/20171227121212_en.vtt'
    mocker.patch('ui.models.Video.subtitle_key', return_value=expected_subtitle_key)
    settings.ENABLE_VIDEO_PERMISSIONS = enable_video_permissions
    client, user = logged_in_apiclient
    video = VideoFactory(collection=CollectionFactory(owner=user))
    yt_video = YouTubeVideoFactory(video=video)
    filename = 'subtitles.vtt'
    youtube_task = mocker.patch('ui.views.upload_youtube_caption.delay')
    input_data = {
        "collection": video.collection.hexkey,
        "video": video.hexkey,
        "language": "en",
        "filename": filename,
        "file": SimpleUploadedFile(filename, bytes(1024))
    }
    response = client.post(reverse('upload-subtitles'), input_data, format='multipart')
    assert response.status_code == status.HTTP_202_ACCEPTED
    expected_data = {
        'language': 'en',
        'filename': filename,
        's3_object_key': expected_subtitle_key,
        'language_name': 'English'
    }
    for key in expected_data:
        assert expected_data[key] == response.data[key]
    if enable_video_permissions:
        assert VideoSubtitle.objects.get(id=response.data['id']).video.youtube_id == yt_video.id
        youtube_task.assert_called_once_with(response.data['id'])


def test_upload_subtitles_authentication(mock_moira_client, logged_in_apiclient, mocker):
    """
    Tests that only authenticated users with collection admin permissions can call UploadVideoSubtitle
    """
    client, user = logged_in_apiclient
    client.logout()
    url = reverse('upload-subtitles')
    moira_list = factories.MoiraListFactory()
    video = VideoFactory(collection=CollectionFactory(admin_lists=[moira_list]))
    filename = "file.vtt"
    input_data = {
        "collection": video.collection.hexkey,
        "video": video.hexkey,
        "language": "en",
        "filename": filename,
        "file": SimpleUploadedFile(filename, bytes(1024))
    }
    mocker.patch(
        'ui.views.cloudapi.upload_subtitle_to_s3',
        return_value=VideoSubtitle(video=video, filename=filename))
    # call with anonymous user
    assert client.post(url, input_data, format='multipart').status_code == status.HTTP_403_FORBIDDEN
    # call with another user not on admin list
    client.force_login(user)
    assert client.post(url, input_data, format='multipart').status_code == status.HTTP_403_FORBIDDEN
    # call with user on admin list
    mock_moira_client.return_value.list_members.return_value = [get_moira_user(user).username]
    assert client.post(url, input_data, format='multipart').status_code == status.HTTP_202_ACCEPTED


def test_delete_subtitles_authentication(mock_moira_client, logged_in_apiclient, mocker):
    """
    Tests that only authenticated users with collection admin permissions can delete VideoSubtitles
    """
    mocker.patch('ui.views.VideoSubtitle.delete_from_s3')
    client, user = logged_in_apiclient
    client.logout()
    moira_list = factories.MoiraListFactory()
    video = VideoFactory(collection=CollectionFactory(admin_lists=[moira_list]))
    subtitle = VideoSubtitleFactory(video=video)
    url = reverse('models-api:subtitle-detail', kwargs={'id': subtitle.id})

    # call with anonymous user
    assert client.delete(url).status_code == status.HTTP_403_FORBIDDEN
    # call with another user not on admin list
    client.force_login(user)
    assert client.delete(url).status_code == status.HTTP_403_FORBIDDEN
    # call with user on admin list
    mock_moira_client.return_value.list_members.return_value = [get_moira_user(user).username]
    assert client.delete(url).status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.parametrize("url", [
    "/fake_page/",
    "/collections/baduuid/",
    "/collections/41ee85f9dbe141f5b8fa59dcf8c3063e/",
    "/collections/01234567890123456789012345678901/",
    "/collections/012345678901234567890123456789012/",
    "/videos/baduuid/",
    "/videos/01234567890123456789012345678902/",
    "/videos/012345678901234567890123456789012/",
    "/videos/baduuid/embed/"
    "/videos/01234567890123456789012345678901/embed/",
    "/videos/012345678901234567890123456789012/embed/",
])
def test_page_not_found(url, logged_in_apiclient, settings):
    """
    We should show the React container for our 404 page
    """
    settings.VIDEO_CLOUDFRONT_BASE_URL = 'cloudfront_base_url'
    settings.GA_TRACKING_ID = 'tracking_id'
    settings.GA_DIMENSION_CAMERA = 'camera1'
    settings.EMAIL_SUPPORT = 'support'

    client, user = logged_in_apiclient
    resp = client.get(url)
    assert resp.status_code == status.HTTP_404_NOT_FOUND
    assert json.loads(resp.context[0]['js_settings_json']) == {
        'cloudfront_base_url': settings.VIDEO_CLOUDFRONT_BASE_URL,
        'gaTrackingID': settings.GA_TRACKING_ID,
        "ga_dimension_camera": settings.GA_DIMENSION_CAMERA,
        'public_path': '/static/bundles/',
        'status_code': status.HTTP_404_NOT_FOUND,
        'support_email_address': settings.EMAIL_SUPPORT,
        'email': user.email,
        'user': user.username,
        "FEATURES": {
            "ENABLE_VIDEO_PERMISSIONS": False
        }
    }


def test_terms_page(mocker, logged_in_client):
    """Test terms page"""
    mocker.patch('ui.utils.get_moira_client')
    client, _ = logged_in_client
    response = client.get(reverse('terms-react-view'))
    assert response.status_code == status.HTTP_200_OK
    assert b'Terms of Service' in response.content
