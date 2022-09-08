# pylint: disable-msg=too-many-lines
"""
Tests for views
"""
import json
from types import SimpleNamespace
from uuid import uuid4

import pytest
from django.contrib.auth.models import AnonymousUser
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import HttpResponseRedirect
from django.test import RequestFactory
from rest_framework import status
from rest_framework.reverse import reverse

from techtv2ovs.factories import TechTVVideoFactory
from ui import factories
from ui.constants import YouTubeStatus
from ui.encodings import EncodingNames
from ui.factories import (
    CollectionFactory,
    MoiraListFactory,
    UserFactory,
    VideoFactory,
    VideoFileFactory,
    VideoSubtitleFactory,
    YouTubeVideoFactory,
)
from ui.models import VideoSubtitle
from ui.pagination import CollectionSetPagination, VideoSetPagination
from ui.serializers import DropboxUploadSerializer, VideoSerializer
from ui.views import (
    CollectionReactView,
    HelpPageView,
    TechTVDetail,
    TechTVEmbed,
    TermsOfServicePageView,
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
    collection.view_lists.set([moira_list])
    return SimpleNamespace(video=video, moira_list=moira_list, collection=collection)


@pytest.fixture
def user_admin_list_data():
    """
    Fixture for testing VideoDetail view permissions with a collection admin_list
    """
    video = VideoFactory()
    collection = video.collection
    moira_list = factories.MoiraListFactory()
    collection.admin_lists.set([moira_list])
    return SimpleNamespace(video=video, moira_list=moira_list, collection=collection)


@pytest.fixture
def post_data(logged_in_apiclient):
    """Fixture for testing collection creation using valid post data"""
    _, user = logged_in_apiclient

    input_data = {
        "owner": user.id,
        "title": "foo title",
        "view_lists": [],
        "admin_lists": [],
    }
    return input_data


def test_index(logged_in_client):
    """Test index anonymous"""
    client, _ = logged_in_client
    response = client.get(reverse("index"), follow=True)
    assert response.status_code == status.HTTP_200_OK
    assert isinstance(response.context_data["view"], CollectionReactView)


def test_video_detail(logged_in_client, settings):
    """Test video detail page"""
    client, user = logged_in_client
    settings.GA_DIMENSION_CAMERA = "camera1"
    settings.GA_TRACKING_ID = "UA-xyz-1"
    settings.ENVIRONMENT = "test"
    settings.VERSION = "1.2.3"
    settings.ENABLE_VIDEO_PERMISSIONS = False
    settings.USE_WEBPACK_DEV_SERVER = False

    videofileHLS = VideoFileFactory(hls=True, video__collection__owner=user)
    videofileHLS.video.status = "Complete"
    url = reverse("video-detail", kwargs={"video_key": videofileHLS.video.hexkey})
    response = client.get(url)
    js_settings_json = json.loads(response.context_data["js_settings_json"])
    assert js_settings_json == {
        "is_app_admin": False,
        "gaTrackingID": settings.GA_TRACKING_ID,
        "environment": settings.ENVIRONMENT,
        "release_version": settings.VERSION,
        "sentry_dsn": "",
        "ga_dimension_camera": settings.GA_DIMENSION_CAMERA,
        "public_path": "/static/bundles/",
        "videoKey": videofileHLS.video.hexkey,
        "cloudfront_base_url": settings.VIDEO_CLOUDFRONT_BASE_URL,
        "user": user.username,
        "email": user.email,
        "support_email_address": settings.EMAIL_SUPPORT,
        "dropbox_key": "foo_dropbox_key",
        "FEATURES": {
            "ENABLE_VIDEO_PERMISSIONS": False,
            "VIDEOJS_ANNOTATIONS": False,
        },
        "is_video_admin": True,
    }


def test_video_embed(
    logged_in_client, settings
):  # pylint: disable=redefined-outer-name
    """Test video embed page"""
    client, user = logged_in_client
    settings.GA_DIMENSION_CAMERA = "camera1"
    settings.GA_TRACKING_ID = "UA-xyz-1"
    settings.ENVIRONMENT = "test"
    settings.VERSION = "1.2.3"
    settings.ENABLE_VIDEO_PERMISSIONS = False
    settings.USE_WEBPACK_DEV_SERVER = False

    videofileHLS = VideoFileFactory(
        hls=True,
        video__collection__owner=user,
        video__multiangle=True,
        video__status="Complete",
    )
    video = videofileHLS.video
    url = reverse("video-embed", kwargs={"video_key": video.hexkey})
    response = client.get(url)
    js_settings_json = json.loads(response.context_data["js_settings_json"])
    assert js_settings_json == {
        "video": VideoSerializer(video).data,
        "gaTrackingID": settings.GA_TRACKING_ID,
        "release_version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "sentry_dsn": "",
        "ga_dimension_camera": settings.GA_DIMENSION_CAMERA,
        "public_path": "/static/bundles/",
        "cloudfront_base_url": settings.VIDEO_CLOUDFRONT_BASE_URL,
        "user": user.username,
        "email": user.email,
        "is_app_admin": False,
        "support_email_address": settings.EMAIL_SUPPORT,
        "FEATURES": {
            "ENABLE_VIDEO_PERMISSIONS": False,
            "VIDEOJS_ANNOTATIONS": False,
        },
    }


def test_upload_dropbox_videos_authentication(
    mock_user_moira_lists, logged_in_apiclient
):
    """
    Tests that only authenticated users with collection admin permissions can call UploadVideosFromDropbox
    """
    client, user = logged_in_apiclient
    client.logout()
    url = reverse("upload-videos")
    collection = CollectionFactory(owner=user)
    moira_list = factories.MoiraListFactory()
    collection.admin_lists.set([moira_list])
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
                "icon": "https://foo.bar/static/images/icons64/page_white_film.png",
            }
        ],
    }
    # call with anonymous user
    assert (
        client.post(url, input_data, format="json").status_code
        == status.HTTP_403_FORBIDDEN
    )
    # call with another user
    client.force_login(other_user)
    assert (
        client.post(url, input_data, format="json").status_code
        == status.HTTP_403_FORBIDDEN
    )


def test_upload_dropbox_videos_bad_data(logged_in_apiclient):
    """
    Tests for UploadVideosFromDropbox with bad data
    """
    client, user = logged_in_apiclient
    collection = CollectionFactory(owner=user)
    url = reverse("upload-videos")
    input_data = {
        "collection": collection.hexkey,
        "files": [
            {
                "isDir": False,
                "link": "http://foo.bar/hoo.mp4",
                "thumbnailLink": "http://foo.bar.link/hoo.mp4",
            }
        ],
    }
    assert (
        client.post(url, input_data, format="json").status_code
        == status.HTTP_400_BAD_REQUEST
    )


def test_upload_dropbox_videos(logged_in_apiclient, mocker):
    """
    Tests for UploadVideosFromDropbox happy path
    """
    client, user = logged_in_apiclient
    collection = CollectionFactory(owner=user)
    url = reverse("upload-videos")
    mocked_api = mocker.patch(
        "ui.api.process_dropbox_data", return_value={"foo": "bar"}
    )
    input_data = {
        "collection": collection.hexkey,
        "files": [
            {
                "isDir": False,
                "link": "http://foo.bar/hoo.mp4",
                "thumbnailLink": "http://foo.bar.link/hoo.mp4",
                "bytes": 80633422,
                "name": "foo file",
                "icon": "https://foo.bar/static/images/icons64/page_white_film.png",
            }
        ],
    }
    response = client.post(url, input_data, format="json")
    assert response.status_code == status.HTTP_202_ACCEPTED
    assert response.data == {"foo": "bar"}
    serializer = DropboxUploadSerializer(data=input_data)
    serializer.is_valid()
    mocked_api.assert_called_once_with(serializer.validated_data)


def test_collection_viewset_permissions(logged_in_apiclient):
    """
    Tests the list of collections for an anonymous_user
    """
    client, _ = logged_in_apiclient
    client.logout()
    collection = CollectionFactory()
    urls = (
        reverse("models-api:collection-list"),
        reverse("models-api:collection-detail", kwargs={"key": collection.hexkey}),
    )
    for url in urls:
        assert client.get(url).status_code == status.HTTP_200_OK
        assert client.post(url, {"owner": 1}).status_code == status.HTTP_403_FORBIDDEN


def test_collection_viewset_list(mock_user_moira_lists, logged_in_apiclient):
    """
    Tests the list of collections for a user
    """
    client, user = logged_in_apiclient
    url = reverse("models-api:collection-list")

    moira_list = MoiraListFactory()
    expected_collection_keys = [
        CollectionFactory(owner=user).hexkey,
        CollectionFactory(view_lists=[moira_list]).hexkey,
    ]
    prohibited_collection_keys = [
        CollectionFactory().hexkey,
        CollectionFactory(view_lists=[MoiraListFactory()]).hexkey,
    ]
    mock_user_moira_lists.return_value = {moira_list.name}

    result = client.get(url)
    assert result.status_code == status.HTTP_200_OK
    assert len(result.data["results"]) == len(expected_collection_keys)
    assert result.data["count"] == len(expected_collection_keys)
    assert result.data["num_pages"] == 1
    assert result.data["start_index"] == 1
    assert result.data["end_index"] == len(expected_collection_keys)
    for coll_data in result.data["results"]:
        assert coll_data["key"] in expected_collection_keys
        assert coll_data["key"] not in prohibited_collection_keys
        assert "videos" not in coll_data


def test_collection_viewset_list_superuser(logged_in_apiclient, settings):
    """
    Tests the list of collections for a superuser
    """
    client, user = logged_in_apiclient
    user.is_superuser = True
    user.save()
    url = reverse("models-api:collection-list")
    collections = [CollectionFactory(owner=user).hexkey for _ in range(5)]
    other_user = UserFactory()
    collections += [CollectionFactory(owner=other_user).hexkey]

    result = client.get(url)
    assert result.status_code == status.HTTP_200_OK
    assert len(result.data["results"]) == 6
    for coll_data in result.data["results"]:
        assert coll_data["key"] in collections


def test_collection_viewset_create_as_normal_user(post_data, logged_in_apiclient):
    """
    Tests that a normal user is not allowed to create a collection
    """
    client, _ = logged_in_apiclient
    url = reverse("models-api:collection-list")
    result = client.post(url, post_data, format="json")
    assert result.status_code == status.HTTP_403_FORBIDDEN


def test_collection_viewset_create_as_staff(mocker, post_data, logged_in_apiclient):
    """
    Tests that a staff user can create a collection with self as owner but nobody else
    """
    mocker.patch("ui.serializers.get_moira_client")
    client, user = logged_in_apiclient
    user.is_staff = True
    user.save()
    url = reverse("models-api:collection-list")
    result = client.post(url, post_data, format="json")
    assert result.status_code == status.HTTP_201_CREATED
    assert "videos" not in result.data

    # the creation should work also without a JSON request
    result = client.post(url, post_data)
    assert result.status_code == status.HTTP_201_CREATED
    assert "videos" not in result.data


def test_collection_viewset_create_as_superuser(mocker, post_data, logged_in_apiclient):
    """
    Tests that a superuser can create a collection for anyone as owner (but owner can't be None).
    """
    mocker.patch("ui.serializers.get_moira_client")
    client, user = logged_in_apiclient
    user.is_superuser = True
    user.save()
    url = reverse("models-api:collection-list")
    result = client.post(url, post_data, format="json")
    assert result.status_code == status.HTTP_201_CREATED
    assert "videos" not in result.data


def test_collection_viewset_detail(mocker, logged_in_apiclient):
    """
    Tests to retrieve a collection details for a user
    """
    mocker.patch("ui.serializers.get_moira_client")
    mocker.patch("ui.utils.get_moira_client")
    client, user = logged_in_apiclient
    collection = CollectionFactory(owner=user)
    videos = [VideoFactory(collection=collection).hexkey for _ in range(5)]
    url = reverse("models-api:collection-detail", kwargs={"key": collection.hexkey})
    result = client.get(url)
    assert result.status_code == status.HTTP_200_OK
    assert "videos" in result.data
    assert len(result.data["videos"]) == 5
    for video_data in result.data["videos"]:
        assert video_data["key"] in videos

    result = client.put(
        url, {"title": "foo title", "view_lists": [], "admin_lists": []}, format="json"
    )
    assert result.status_code == status.HTTP_200_OK
    assert result.data["title"] == "foo title"

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


@pytest.mark.parametrize("logged_in", [True, False])
@pytest.mark.parametrize("collection_key", ["fake", "fa478a0f71204913bed17bcf4065a2ee"])
def test_collection_viewset_detail_404(logged_in_apiclient, collection_key, logged_in):
    """
    Tests that a non-existent collection key returns a 404 response even if not logged in.
    """
    client, _ = logged_in_apiclient
    if not logged_in:
        client.logout()
    response = client.get("/collections/{}".format(collection_key))
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_collection_detail_anonymous(mocker, logged_in_apiclient, settings):
    """Test that anonymous users can see the collection detail page"""
    mocker.patch("ui.serializers.get_moira_client")
    mocker.patch("ui.utils.get_moira_client")
    client, _ = logged_in_apiclient
    client.logout()
    collection = CollectionFactory()
    url = reverse("collection-react-view", kwargs={"collection_key": collection.hexkey})
    result = client.get(url, follow=True)
    assert result.status_code == status.HTTP_200_OK


def test_collection_viewset_detail_as_superuser(mocker, logged_in_apiclient):
    """
    Tests to retrieve a collection details for a superuser
    """
    mocker.patch("ui.serializers.get_moira_client")
    client, user = logged_in_apiclient
    user.is_superuser = True
    user.save()

    collection = CollectionFactory(owner=UserFactory())
    url = reverse("models-api:collection-detail", kwargs={"key": collection.hexkey})
    result = client.get(url)
    assert result.status_code == status.HTTP_200_OK
    assert "videos" in result.data

    result = client.put(
        url,
        {"title": "foo title", "owner": user.id, "view_lists": [], "admin_lists": []},
        format="json",
    )
    assert result.status_code == status.HTTP_200_OK
    assert result.data["title"] == "foo title"

    # user can delete the collection
    result = client.delete(url)
    assert result.status_code == status.HTTP_204_NO_CONTENT


def test_login_next(mock_user_moira_lists, logged_in_apiclient, user_admin_list_data):
    """
    Tests that the login page redirects to the URL in the `next` parameter if present
    """
    client = logged_in_apiclient[0]
    mock_user_moira_lists.return_value = {user_admin_list_data.moira_list.name}
    video_url = reverse(
        "video-detail", kwargs={"video_key": user_admin_list_data.video.hexkey}
    )
    response = client.get(f"/login/?next={video_url}/%3Fstart%3D20", follow=True)
    final_url, status_code = response.redirect_chain[-1]
    assert final_url == f"{video_url}/?start=20"
    assert status_code == 302


def test_login_nonext(mock_user_moira_lists, logged_in_apiclient):
    """
    Tests that the login page redirects to the collections page if authenticated
    """
    client = logged_in_apiclient[0]
    response = client.get("/login", follow=True)
    final_url, status_code = response.redirect_chain[-1]
    assert final_url == "/collections/"
    assert status_code == 302


def test_video_detail_view_permission(
    mock_user_moira_lists, logged_in_apiclient, user_view_list_data
):
    """
    Tests that a user can view a video if user is a member of collection's view_lists
    """
    client = logged_in_apiclient[0]
    mock_user_moira_lists.return_value = {user_view_list_data.moira_list.name}
    url = reverse(
        "video-detail", kwargs={"video_key": user_view_list_data.video.hexkey}
    )
    result = client.get(url)
    assert result.status_code == status.HTTP_200_OK
    assert (
        json.loads(result.context_data["js_settings_json"])["is_video_admin"] is False
    )


def test_video_detail_admin_permission(
    logged_in_apiclient, mock_user_moira_lists, user_admin_list_data
):
    """
    Tests that a user can view a video if user is a member of collection's admin_lists
    """
    client = logged_in_apiclient[0]
    mock_user_moira_lists.return_value = {user_admin_list_data.moira_list.name}
    url = reverse(
        "video-detail", kwargs={"video_key": user_admin_list_data.video.hexkey}
    )
    result = client.get(url)
    assert result.status_code == status.HTTP_200_OK
    assert json.loads(result.context_data["js_settings_json"])["is_video_admin"] is True


def test_video_detail_no_permission(
    mock_user_moira_lists, logged_in_apiclient, user_admin_list_data
):
    """
    Tests that a user cannot view a video if user is not a member of collection's lists
    """
    client, _ = logged_in_apiclient
    mock_user_moira_lists.return_value = {"some_other_list"}
    url = reverse(
        "video-detail", kwargs={"video_key": user_admin_list_data.video.hexkey}
    )
    result = client.get(url)
    assert result.status_code == status.HTTP_403_FORBIDDEN


def test_video_detail_anonymous(settings, logged_in_apiclient, user_admin_list_data):
    """
    Tests that an anonymous user is redirected to the login page, with a next parameter
    """
    client, _ = logged_in_apiclient
    client.logout()
    url = reverse(
        "video-detail", kwargs={"video_key": user_admin_list_data.video.hexkey}
    )
    response = client.get(f"{url}?start=35", follow=True)
    last_url, status_code = response.redirect_chain[-1]
    assert settings.LOGIN_URL in last_url
    assert status_code == 302
    assert f"?next={url}%3Fstart%3D35" in last_url


def test_public_video_detail_anonymous(
    settings, logged_in_apiclient, user_admin_list_data
):
    """
    Tests that an anonymous user can access a public video
    """
    client, _ = logged_in_apiclient
    client.logout()
    user_admin_list_data.video.is_public = True
    user_admin_list_data.video.save()
    url = reverse(
        "video-detail", kwargs={"video_key": user_admin_list_data.video.hexkey}
    )
    response = client.get(url, follow=True)
    assert response.status_code == 200


@pytest.mark.parametrize("is_public", [True, False])
def test_video_download(logged_in_client, is_public, mocker):
    """Tests that a video can be downloaded if public, returns 404 otherwise"""
    mock_redirect = mocker.patch(
        "ui.views.redirect", return_value=HttpResponseRedirect(redirect_to="/")
    )
    client, _ = logged_in_client
    client.logout()
    video = VideoFactory(is_public=is_public)
    VideoFileFactory(video=video, encoding=EncodingNames.ORIGINAL)
    url = reverse("video-download", kwargs={"video_key": video.hexkey})
    result = client.get(url)
    if is_public:
        mock_redirect.assert_called_with(video.download.cloudfront_url)
    else:
        assert result.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.parametrize("is_public", [True, False])
def test_video_download_nofiles(logged_in_client, is_public, mocker):
    """Tests that a 404 is returned if no videofiles are available"""
    mocker.patch(
        "ui.views.redirect", return_value=HttpResponseRedirect(redirect_to="/")
    )
    client, _ = logged_in_client
    client.logout()
    video = VideoFactory(is_public=is_public)
    assert video.download is None
    url = reverse("video-download", kwargs={"video_key": video.hexkey})
    result = client.get(url)
    assert result.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.parametrize("is_public", [True, False])
def test_techtv_video_download(logged_in_client, is_public, mocker):
    """Tests that a TechTV video can be downloaded if public, returns 404 otherwise"""
    mock_redirect = mocker.patch(
        "ui.views.redirect", return_value=HttpResponseRedirect(redirect_to="/")
    )
    client, _ = logged_in_client
    client.logout()
    ttv_video = TechTVVideoFactory(video=VideoFactory(is_public=is_public))
    VideoFileFactory(video=ttv_video.video, encoding=EncodingNames.ORIGINAL)
    url = reverse("techtv-download", kwargs={"video_key": ttv_video.ttv_id})
    result = client.get(url)
    if is_public:
        mock_redirect.assert_called_with(ttv_video.video.download.cloudfront_url)
    else:
        assert result.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.parametrize("is_public", [True, False])
def test_techtv_video_download_nofiles(logged_in_client, is_public, mocker):
    """Tests that a 404 is returned if no videofiles are available for a TechTV video"""
    mocker.patch("ui.views.redirect")
    client, _ = logged_in_client
    client.logout()
    ttv_video = TechTVVideoFactory(video=VideoFactory(is_public=is_public))
    assert ttv_video.video.download is None
    url = reverse("techtv-download", kwargs={"video_key": ttv_video.ttv_id})
    result = client.get(url)
    assert result.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.parametrize(
    "url",
    [
        "/videos/{}",
        "/videos/{}-foo",
        "/collections/foo/videos/{}",
        "/collections/foo-bar:935/videos/{}-bar/",
    ],
)
def test_techtv_detail_standard_url(
    mock_user_moira_lists, user_view_list_data, logged_in_apiclient, url
):
    """
    Tests that a URL based on a TechTV id returns the correct Video detail page
    """
    client = logged_in_apiclient[0]
    mock_user_moira_lists.return_value = {user_view_list_data.moira_list.name}
    ttv_video = TechTVVideoFactory(video=user_view_list_data.video)
    result = client.get(url.format(ttv_video.ttv_id))
    assert result.status_code == status.HTTP_200_OK
    assert (
        json.loads(result.context_data["js_settings_json"])["videoKey"]
        == user_view_list_data.video.hexkey
    )
    assert isinstance(result.context_data["view"], TechTVDetail)


def test_techtv_detail_private_url(
    mock_user_moira_lists, user_view_list_data, logged_in_apiclient
):
    """
    Tests that a URL based on a TechTV private token returns the correct Video detail page
    """
    client = logged_in_apiclient[0]
    ttv_video = TechTVVideoFactory(
        video=user_view_list_data.video, private=True, private_token=uuid4().hex
    )
    mock_user_moira_lists.return_value = {user_view_list_data.moira_list.name}
    url = reverse("techtv-private", kwargs={"video_key": ttv_video.private_token})
    result = client.get(url)
    assert result.status_code == status.HTTP_200_OK
    assert (
        json.loads(result.context_data["js_settings_json"])["videoKey"]
        == user_view_list_data.video.hexkey
    )


@pytest.mark.parametrize("url", ["/embeds/{}", "/embeds/{}-foo"])
def test_techtv_detail_embed_url(
    mock_user_moira_lists, user_view_list_data, logged_in_apiclient, url
):
    """
    Tests that an embed URL based on a TechTV id returns the correct Video embed page
    """
    client = logged_in_apiclient[0]
    ttv_video = TechTVVideoFactory(video=user_view_list_data.video)
    mock_user_moira_lists.return_value = {user_view_list_data.moira_list.name}
    result = client.get(url.format(ttv_video.ttv_id))
    assert result.status_code == status.HTTP_200_OK
    assert (
        json.loads(result.context_data["js_settings_json"])["video"]["key"]
        == user_view_list_data.video.hexkey
    )
    assert isinstance(result.context_data["view"], TechTVEmbed)


def test_upload_subtitles(logged_in_apiclient, mocker):
    """
    Tests for UploadVideoSubtitle
    """
    mocker.patch("ui.views.cloudapi.boto3")
    expected_subtitle_key = "subtitles/test/20171227121212_en.vtt"
    mocker.patch("ui.models.Video.subtitle_key", return_value=expected_subtitle_key)
    client, user = logged_in_apiclient
    video = VideoFactory(collection=CollectionFactory(owner=user))
    yt_video = YouTubeVideoFactory(video=video, status=YouTubeStatus.PROCESSED)
    filename = "subtitles.vtt"
    youtube_task = mocker.patch("ui.views.upload_youtube_caption.delay")
    input_data = {
        "collection": video.collection.hexkey,
        "video": video.hexkey,
        "language": "en",
        "filename": filename,
        "file": SimpleUploadedFile(filename, bytes(1024)),
    }
    response = client.post(reverse("upload-subtitles"), input_data, format="multipart")
    assert response.status_code == status.HTTP_202_ACCEPTED
    expected_data = {
        "language": "en",
        "filename": filename,
        "s3_object_key": expected_subtitle_key,
        "language_name": "English",
    }
    for key in expected_data:
        assert expected_data[key] == response.data[key]
    assert (
        VideoSubtitle.objects.get(id=response.data["id"]).video.youtube_id
        == yt_video.id
    )
    youtube_task.assert_called_once_with(response.data["id"])


def test_upload_subtitles_authentication(
    mock_user_moira_lists, logged_in_apiclient, mocker
):
    """
    Tests that only authenticated users with collection admin permissions can call UploadVideoSubtitle
    """
    client, user = logged_in_apiclient
    client.logout()
    url = reverse("upload-subtitles")
    moira_list = factories.MoiraListFactory()
    video = VideoFactory(collection=CollectionFactory(admin_lists=[moira_list]))
    filename = "file.vtt"
    input_data = {
        "collection": video.collection.hexkey,
        "video": video.hexkey,
        "language": "en",
        "filename": filename,
        "file": SimpleUploadedFile(filename, bytes(1024)),
    }
    mocker.patch(
        "ui.views.cloudapi.upload_subtitle_to_s3",
        return_value=VideoSubtitle(video=video, filename=filename),
    )
    mocker.patch("ui.utils.cache")
    # call with anonymous user
    assert (
        client.post(url, input_data, format="multipart").status_code
        == status.HTTP_403_FORBIDDEN
    )
    # call with another user not on admin list
    client.force_login(user)
    assert (
        client.post(url, input_data, format="multipart").status_code
        == status.HTTP_403_FORBIDDEN
    )
    # call with user on admin list
    mock_user_moira_lists.return_value = {moira_list.name}
    assert (
        client.post(url, input_data, format="multipart").status_code
        == status.HTTP_202_ACCEPTED
    )


def test_delete_subtitles_authentication(
    mock_user_moira_lists, logged_in_apiclient, mocker
):
    """
    Tests that only authenticated users with collection admin permissions can delete VideoSubtitles
    """
    mocker.patch("ui.views.VideoSubtitle.delete_from_s3")
    mocker.patch("ui.utils.cache")
    client, user = logged_in_apiclient
    client.logout()
    moira_list = factories.MoiraListFactory()
    video = VideoFactory(collection=CollectionFactory(admin_lists=[moira_list]))
    subtitle = VideoSubtitleFactory(video=video)
    url = reverse("models-api:subtitle-detail", kwargs={"id": subtitle.id})

    # call with anonymous user
    assert client.delete(url).status_code == status.HTTP_403_FORBIDDEN
    # call with another user not on admin list
    client.force_login(user)
    assert client.delete(url).status_code == status.HTTP_403_FORBIDDEN
    # call with user on admin list
    mock_user_moira_lists.return_value = {moira_list.name}
    assert client.delete(url).status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.parametrize(
    "url",
    [
        "/fake_page/",
        "/collections/baduuid/",
        "/collections/41ee85f9dbe141f5b8fa59dcf8c3063e/",
        "/collections/01234567890123456789012345678901/",
        "/collections/012345678901234567890123456789012/",
        "/videos/baduuid/",
        "/videos/01234567890123456789012345678902/",
        "/videos/012345678901234567890123456789012/",
        "/videos/baduuid/embed/",
        "/videos/01234567890123456789012345678901/embed/",
        "/videos/012345678901234567890123456789012/embed/",
    ],
)
def test_page_not_found(url, logged_in_apiclient, settings):
    """
    We should show the React container for our 404 page
    """
    settings.VIDEO_CLOUDFRONT_BASE_URL = "cloudfront_base_url"
    settings.GA_TRACKING_ID = "tracking_id"
    settings.ENVIRONMENT = "test"
    settings.VERSION = "1.2.3"
    settings.GA_DIMENSION_CAMERA = "camera1"
    settings.EMAIL_SUPPORT = "support"
    settings.ENABLE_VIDEO_PERMISSIONS = False
    settings.USE_WEBPACK_DEV_SERVER = False

    client, user = logged_in_apiclient
    resp = client.get(url)
    assert resp.status_code == status.HTTP_404_NOT_FOUND
    assert json.loads(resp.context[0]["js_settings_json"]) == {
        "cloudfront_base_url": settings.VIDEO_CLOUDFRONT_BASE_URL,
        "gaTrackingID": settings.GA_TRACKING_ID,
        "environment": settings.ENVIRONMENT,
        "release_version": settings.VERSION,
        "sentry_dsn": "",
        "ga_dimension_camera": settings.GA_DIMENSION_CAMERA,
        "public_path": "/static/bundles/",
        "status_code": status.HTTP_404_NOT_FOUND,
        "support_email_address": settings.EMAIL_SUPPORT,
        "email": user.email,
        "user": user.username,
        "is_app_admin": False,
        "FEATURES": {
            "ENABLE_VIDEO_PERMISSIONS": False,
            "VIDEOJS_ANNOTATIONS": False,
        },
    }


def test_terms_page(mocker, logged_in_client):
    """Test terms page"""
    mocker.patch("ui.utils.get_moira_client")
    client, _ = logged_in_client
    response = client.get(reverse("terms-react-view"))
    assert response.status_code == status.HTTP_200_OK
    assert b"Terms of Service" in response.content


def test_video_viewset_analytics(mocker, logged_in_apiclient):
    """
    Tests to retrieve video analytics
    """
    mocker.patch("ui.serializers.get_moira_client")
    mocker.patch("ui.utils.get_moira_client")
    mock_get_video_analytics = mocker.patch("ui.views.get_video_analytics")
    mock_get_video_analytics.return_value = {"mock-analytics-data": "foo"}
    client, user = logged_in_apiclient
    collection = CollectionFactory(owner=user)
    video = VideoFactory(collection=collection)
    url = reverse("models-api:video-analytics", kwargs={"key": video.hexkey})
    result = client.get(url)
    assert result.status_code == status.HTTP_200_OK
    assert mock_get_video_analytics.called_once_with(video)
    assert result.data["data"] == mock_get_video_analytics.return_value


def test_video_viewset_analytics_mock_data(mocker, logged_in_apiclient):
    """
    Tests to retrieve mock video analytics data.
    """
    mocker.patch("ui.serializers.get_moira_client")
    mocker.patch("ui.utils.get_moira_client")
    mock_generate_mock_video_analytics_data = mocker.patch(
        "ui.views.generate_mock_video_analytics_data"
    )
    mock_generate_mock_video_analytics_data.return_value = {
        "mock-analytics-data": "foo"
    }
    client, user = logged_in_apiclient
    collection = CollectionFactory(owner=user)
    video = VideoFactory(collection=collection)
    url = reverse("models-api:video-analytics", kwargs={"key": video.hexkey})
    seed = "some_seed"
    n = 2
    result = client.get(url, {"mock": 1, "seed": seed, "n": n})
    assert result.status_code == status.HTTP_200_OK
    assert mock_generate_mock_video_analytics_data.called_once_with(seed=seed, n=n)
    assert result.data["data"] == mock_generate_mock_video_analytics_data.return_value


def test_video_viewset_analytics_throw(mocker, logged_in_apiclient):
    """
    Tests to retrieve video analytics w/ error.
    """
    mocker.patch("ui.serializers.get_moira_client")
    mocker.patch("ui.utils.get_moira_client")
    client, user = logged_in_apiclient
    collection = CollectionFactory(owner=user)
    video = VideoFactory(collection=collection)
    url = reverse("models-api:video-analytics", kwargs={"key": video.hexkey})
    result = client.get(url, {"throw": 1})
    assert result.status_code == 500


def test_video_viewset_list(mocker, mock_user_moira_lists, logged_in_apiclient):
    # pylint: disable-msg=too-many-locals
    """
    Tests the list of videos for a user.

    A quasi-integration test, because we're also testing models.VideoManager.all_vieweable here.
    """
    view_list = MoiraListFactory()
    admin_list = MoiraListFactory()
    mocker.patch("ui.serializers.ui_permissions")
    mock_user_moira_lists.return_value = [view_list.name, admin_list.name]
    non_matching_list = MoiraListFactory()
    client, user = logged_in_apiclient
    collections = {
        "owned": CollectionFactory(owner=user),
        "unowned": CollectionFactory(),
        "can_view": CollectionFactory(
            view_lists=[view_list], admin_lists=[non_matching_list]
        ),
        "can_admin": CollectionFactory(
            view_lists=[non_matching_list], admin_lists=[admin_list]
        ),
        "can_view_and_admin": CollectionFactory(
            view_lists=[view_list], admin_lists=[admin_list]
        ),
        "can_not_view_or_admin": CollectionFactory(
            view_lists=[non_matching_list], admin_lists=[non_matching_list]
        ),
    }
    viewable_collections = [
        collections[key]
        for key in ["owned", "can_view", "can_admin", "can_view_and_admin"]
    ]
    unowned_view_only_collections = [collections[key] for key in ["can_view"]]
    unowned_adminable_collections = [
        collections[key] for key in ["can_admin", "can_view_and_admin"]
    ]
    unviewable_collections = [
        collections[key] for key in ["unowned", "can_not_view_or_admin"]
    ]
    expected_viewable_videos = [
        *[
            VideoFactory(
                title="no view_lists, in viewable collections",
                view_lists=[],
                collection=collection,
            )
            for collection in viewable_collections
        ],
        *[
            VideoFactory(
                title="matching view_lists, in unviewable collections",
                view_lists=[view_list],
                collection=collection,
            )
            for collection in unviewable_collections
        ],
        *[
            VideoFactory(
                title=(
                    "matching view_lists, is_public=True," " in unviewable collections"
                ),
                view_lists=[view_list],
                is_public=True,
                collection=collection,
            )
            for collection in unviewable_collections
        ],
        *[
            VideoFactory(
                title=(
                    "non-matching view_lists, is_public=True,"
                    " in unviewable collections"
                ),
                view_lists=[non_matching_list],
                is_public=True,
                collection=collection,
            )
            for collection in unviewable_collections
        ],
        *[
            VideoFactory(
                title="no view_lists, is_public=True, in unviewable collections",
                view_lists=[],
                is_public=True,
                collection=collection,
            )
            for collection in unviewable_collections
        ],
        *[
            VideoFactory(
                title=(
                    "no view_lists, is_private=True, is_public=False,"
                    "in unowned adminable collections"
                ),
                view_lists=[],
                is_private=True,
                is_public=False,
                collection=collection,
            )
            for collection in unowned_adminable_collections
        ],
    ]
    expected_prohibited_videos = [
        *[
            VideoFactory(
                title=("no view_lists, is_public=False," " in unviewable collections"),
                view_lists=[],
                is_public=False,
                collection=collection,
            )
            for collection in unviewable_collections
        ],
        *[
            VideoFactory(
                title=(
                    "no view_lists, is_private=True, is_public=False,"
                    "in unowned view-only collections"
                ),
                view_lists=[],
                is_private=True,
                is_public=True,
                collection=collection,
            )
            for collection in unowned_view_only_collections
        ],
        *[
            VideoFactory(
                title=(
                    "no view_lists, is_private=True, is_public=True,"
                    " in unowned view-only collections"
                ),
                view_lists=[],
                is_private=True,
                is_public=True,
                collection=collection,
            )
            for collection in unowned_view_only_collections
        ],
        *[
            VideoFactory(
                title=(
                    "non-matching view_lists, is_private=False,"
                    " is_public=False, in unviewable collections"
                ),
                view_lists=[non_matching_list],
                is_private=False,
                is_public=False,
                collection=collection,
            )
            for collection in unviewable_collections
        ],
    ]
    url = reverse("models-api:video-list")
    result = client.get(url)
    assert result.status_code == status.HTTP_200_OK
    expected_viewable_key_titles = {
        (video.hexkey, video.title) for video in expected_viewable_videos
    }
    expected_prohibited_key_titles = {
        (video.hexkey, video.title) for video in expected_prohibited_videos
    }
    actual_key_titles = {
        (result["key"], result["title"]) for result in result.data["results"]
    }
    assert actual_key_titles == expected_viewable_key_titles
    assert actual_key_titles.isdisjoint(expected_prohibited_key_titles)
    assert result.data["num_pages"] == 1
    assert result.data["start_index"] == 1
    assert result.data["end_index"] == len(expected_viewable_videos)
    assert result.data["count"] == len(expected_viewable_key_titles)
    # pylint: enable-msg=too-many-locals


def test_video_viewset_list_anonymous(logged_in_apiclient):
    """
    Tests the list of collections for an anonymous user
    """
    client, _ = logged_in_apiclient
    client.logout()
    url = reverse("models-api:video-list")
    collection = CollectionFactory()
    public_video_keys = [
        VideoFactory(collection=collection, is_public=True).hexkey for _ in range(2)
    ]
    VideoFactory(collection=collection, is_public=False)
    result = client.get(url)
    assert result.status_code == status.HTTP_200_OK
    assert len(result.data["results"]) == len(public_video_keys)
    for coll_data in result.data["results"]:
        assert coll_data["key"] in public_video_keys


def test_video_viewset_list_superuser(logged_in_apiclient, settings):
    """
    Tests the list of collections for a superuser
    """
    client, user = logged_in_apiclient
    user.is_superuser = True
    user.save()
    url = reverse("models-api:video-list")
    owned_collection = CollectionFactory(owner=user)
    unowned_collection = CollectionFactory()
    owned_video_keys = [
        VideoFactory(collection=owned_collection).hexkey for _ in range(5)
    ]
    unowned_video_keys = [VideoFactory(collection=unowned_collection).hexkey]
    combined_video_keys = owned_video_keys + unowned_video_keys
    result = client.get(url)
    assert result.status_code == status.HTTP_200_OK
    assert len(result.data["results"]) == len(combined_video_keys)
    for coll_data in result.data["results"]:
        assert coll_data["key"] in combined_video_keys


def test_videos_pagination(mocker, logged_in_apiclient):
    """
    Verify that the correct number of videos is returned per page
    """
    mocker.patch("ui.serializers.get_moira_client")
    mocker.patch("ui.utils.get_moira_client")
    page_size = 8
    VideoSetPagination.page_size = page_size
    client, user = logged_in_apiclient
    collection = CollectionFactory(owner=user)
    videos = VideoFactory.create_batch(20, collection=collection)
    url = reverse("models-api:video-list")
    result = client.get(url)
    assert len(result.data["results"]) == min(page_size, len(videos))
    for i in range(1, 3):
        paged_url = url + "?page={}".format(i)
        result = client.get(paged_url)
        assert len(result.data["results"]) == min(
            page_size, max(0, len(videos) - page_size * (i - 1))
        )


def test_videos_pagination_constrain_collection(mocker, logged_in_apiclient):
    """
    Verify that videos are only returned for the specified collection.
    """
    mocker.patch("ui.serializers.get_moira_client")
    mocker.patch("ui.utils.get_moira_client")
    page_size = 8
    VideoSetPagination.page_size = page_size
    client, user = logged_in_apiclient
    collections = CollectionFactory.create_batch(3, owner=user)
    videos_by_collection_key = {
        collection.hexkey: VideoFactory.create_batch(20, collection=collection)
        for collection in collections
    }
    url = reverse("models-api:video-list")
    target_collection = collections[1]
    result = client.get(url, {"collection": target_collection.hexkey})
    expected_videos = videos_by_collection_key[target_collection.hexkey]
    assert len(result.data["results"]) == min(page_size, len(expected_videos))
    for i in range(1, 3):
        paged_url = url + "?page={}".format(i)
        result = client.get(paged_url)
        assert len(result.data["results"]) == min(
            page_size, max(0, len(expected_videos) - page_size * (i - 1))
        )


def test_videos_default_ordering(mocker, logged_in_apiclient):
    """Verify that by default results are returned in the created_at descending order"""
    mocker.patch("ui.serializers.get_moira_client")
    mocker.patch("ui.utils.get_moira_client")
    VideoSetPagination.page_size = 5
    client, user = logged_in_apiclient
    collection = CollectionFactory(owner=user)
    VideoFactory.create_batch(10, collection=collection)
    url = reverse("models-api:video-list")
    p1_response = client.get("{}?page=1".format(url))
    assert len(p1_response.data["results"]) == 5
    for i in range(4):
        current_video_date = p1_response.data["results"][i]["created_at"]
        next_video_date = p1_response.data["results"][i + 1]["created_at"]
        assert current_video_date >= next_video_date

    p2_response = client.get("{}?page=2".format(url))
    last_entry_data = p1_response.data["results"][-1]["created_at"]
    first_entry_data = p2_response.data["results"][0]["created_at"]
    assert last_entry_data >= first_entry_data
    for i in range(4):
        current_video_date = p2_response.data["results"][i]["created_at"]
        next_video_date = p2_response.data["results"][i + 1]["created_at"]
        assert current_video_date >= next_video_date


@pytest.mark.parametrize("field", ["created_at", "title"])
def test_videos_ordering(mocker, logged_in_apiclient, field):
    """Verify that results are returned in the appropriate order"""
    mocker.patch("ui.serializers.get_moira_client")
    mocker.patch("ui.utils.get_moira_client")
    VideoSetPagination.page_size = 5
    client, user = logged_in_apiclient
    collection = CollectionFactory(owner=user)
    VideoFactory.create_batch(10, collection=collection)
    url = reverse("models-api:video-list")
    p1_response = client.get("{}?page=1&ordering={}".format(url, field))
    assert len(p1_response.data["results"]) == 5
    for i in range(4):
        assert (
            p1_response.data["results"][i][field].lower()
            <= p1_response.data["results"][i + 1][field].lower()
        )
    p2_response = client.get("{}?page=2&ordering={}".format(url, field))
    assert (
        p1_response.data["results"][-1][field].lower()
        <= p2_response.data["results"][0][field].lower()
    )
    for i in range(4):
        assert (
            p2_response.data["results"][i][field].lower()
            <= p2_response.data["results"][i + 1][field].lower()
        )


def test_collection_pagination(mocker, logged_in_apiclient):
    """
    Verify that the correct number of collections is returned per page
    """
    mocker.patch("ui.serializers.get_moira_client")
    mocker.patch("ui.utils.get_moira_client")
    page_size = 8
    CollectionSetPagination.page_size = page_size
    client, user = logged_in_apiclient
    collections = CollectionFactory.create_batch(20, owner=user)
    url = reverse("models-api:collection-list")
    result = client.get(url)
    assert len(result.data["results"]) == min(page_size, len(collections))
    for i in range(1, 3):
        paged_url = url + "?page={}".format(i)
        result = client.get(paged_url)
        assert len(result.data["results"]) == min(
            page_size, max(0, len(collections) - page_size * (i - 1))
        )


@pytest.mark.parametrize("field", ["created_at", "title"])
def test_collection_ordering(mocker, logged_in_apiclient, field):
    """Verify that results are returned in the appropriate order"""
    mocker.patch("ui.serializers.get_moira_client")
    mocker.patch("ui.utils.get_moira_client")
    CollectionSetPagination.page_size = 5
    client, user = logged_in_apiclient
    CollectionFactory.create_batch(10, owner=user)
    url = reverse("models-api:collection-list")
    p1_response = client.get("{}?page=1&ordering={}".format(url, field))
    assert len(p1_response.data["results"]) == 5
    for i in range(4):
        assert (
            p1_response.data["results"][i][field].lower()
            <= p1_response.data["results"][i + 1][field].lower()
        )
    p2_response = client.get("{}?page=2&ordering={}".format(url, field))
    assert (
        p1_response.data["results"][-1][field].lower()
        <= p2_response.data["results"][0][field].lower()
    )
    for i in range(4):
        assert (
            p2_response.data["results"][i][field].lower()
            <= p2_response.data["results"][i + 1][field].lower()
        )


def test_help_for_anonymous_user(mock_user_moira_lists):
    """Test help page for anonymous user"""
    request = RequestFactory()
    request.method = "GET"
    request.user = AnonymousUser()
    response = HelpPageView.as_view()(request)
    assert response.status_code == status.HTTP_200_OK


def test_terms_of_service_for_anonymous_user(mock_user_moira_lists):
    """Test help page for anonymous user"""
    request = RequestFactory()
    request.method = "GET"
    request.user = AnonymousUser()
    response = TermsOfServicePageView.as_view()(request)
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.parametrize(
    "url",
    [
        reverse("member-lists", kwargs={"username_or_email": "test_user"}),
        reverse("list-members", kwargs={"list_name": "test_name"}),
    ],
)
def test_moira_list_views_permission(logged_in_apiclient, mocker, url):
    """
    Tests that only authenticated users with admin permissions can call MoiraListsForUser and UsersForMoiraList
    """
    mocker.patch("ui.views.list_members", return_value=[])

    client, user = logged_in_apiclient
    client.logout()

    # call with anonymous user
    assert client.get(url).status_code == status.HTTP_403_FORBIDDEN
    # call with another user not on admin list
    client.force_login(user)
    assert client.get(url).status_code == status.HTTP_403_FORBIDDEN
    # call with user on admin list
    user.is_staff = True
    user.save()
    client.force_login(user)
    assert client.get(url).status_code == status.HTTP_200_OK


def test_moira_list_users(logged_in_apiclient, mock_moira_client):
    """Test that UsersForMoiraList returns list of users for a given list name"""
    client, user = logged_in_apiclient
    user.is_staff = True
    user.save()
    client.force_login(user)
    mock_moira_client.return_value.list_members.return_value = [
        "fakeuser1",
        "fakeuser2",
    ]
    url = reverse("list-members", kwargs={"list_name": "Test-list_name.1"})
    expected = {"users": ["fakeuser1", "fakeuser2"]}
    response = client.get(url)

    assert response.status_code == status.HTTP_200_OK
    assert expected == response.data


def test_users_moira_list(logged_in_apiclient, mock_moira_client):
    """Test that MoiraListsForUser returns lists for a given username or email."""
    client, user = logged_in_apiclient
    user.is_staff = True
    user.save()
    client.force_login(user)
    list_names = ["test_moira_list01", "test_moira_list02"]
    mock_moira_client.return_value.user_list_membership.return_value = [
        {"listName": list_name} for list_name in list_names
    ]

    username_or_email = [
        user.username,
        user.email,
        UserFactory(email="user-name.1@mit.edu").email,
    ]

    for arg in username_or_email:
        url = reverse("member-lists", kwargs={"username_or_email": arg})
        expected = {"user_lists": list_names}

        response = client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert expected == response.data
