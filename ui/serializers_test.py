"""
Tests for serialisers module
"""

import uuid

import pytest
from rest_framework.serializers import DateTimeField, ValidationError

from ui import factories, serializers
from ui.encodings import EncodingNames
from ui.factories import MoiraListFactory, UserFactory, VideoFactory

pytestmark = pytest.mark.django_db


def test_collection_serializer():
    """
    Test for CollectionSerializer
    """
    user = UserFactory.create()
    collection = factories.CollectionFactory(owner=user)
    videos = [factories.VideoFactory(collection=collection) for _ in range(3)]
    expected = {
        "key": collection.hexkey,
        "created_at": DateTimeField().to_representation(collection.created_at),
        "title": collection.title,
        "description": collection.description,
        "videos": serializers.SimpleVideoSerializer(videos, many=True).data,
        "video_count": len(videos),
        "view_lists": [],
        "admin_lists": [],
        "is_logged_in_only": False,
        "is_admin": False,
        "edx_course_id": collection.edx_course_id,
        "owner": user.id,
        "owner_info": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
        },
    }
    expected["videos"].sort(key=lambda x: x["key"])
    serialized_data = serializers.CollectionSerializer(collection).data
    serialized_data["videos"].sort(key=lambda x: x["key"])
    assert serialized_data == expected


def test_collection_serializer_validation_fake_admin_lists():
    """
    Test for CollectionSerializer's admin keycloak group validation for fake lists
    """
    collection = factories.CollectionFactory(admin_lists=[factories.MoiraListFactory()])
    serialized_data = serializers.CollectionSerializer(collection).data
    with pytest.raises(ValidationError) as exc:
        serializers.CollectionSerializer(data=serialized_data).is_valid(
            raise_exception=True
        )
    assert exc.match(
        "Group does not exist: {}".format(collection.admin_lists.first().name)
    )


def test_collection_serializer_validation_fake_view_lists():
    """
    Test for CollectionSerializer's viewable keycloak group validation for fake lists
    """
    collection = factories.CollectionFactory(view_lists=[factories.MoiraListFactory()])
    serialized_data = serializers.CollectionSerializer(collection).data
    with pytest.raises(ValidationError) as exc:
        serializers.CollectionSerializer(data=serialized_data).is_valid(
            raise_exception=True
        )
    assert exc.match(
        "Group does not exist: {}".format(collection.view_lists.first().name)
    )


def test_collection_serializer_validate_title():
    """
    Test that we can't save a blank title
    """
    collection = factories.CollectionFactory(title="")
    serialized_data = serializers.CollectionSerializer(collection).data
    with pytest.raises(ValidationError) as exc:
        serializers.CollectionSerializer(data=serialized_data).is_valid(
            raise_exception=True
        )
    assert exc.value.detail == {"title": ["This field may not be blank."]}


@pytest.mark.parametrize("has_permission", [True, False])
def test_collection_serializer_admin_flag(mocker, has_permission):
    """
    Test that the is_admin flag returns an expected value based on a user's admin permission
    """
    mocked_admin_permission = mocker.patch(
        "ui.permissions.has_admin_permission", return_value=has_permission
    )
    mocked_request = mocker.MagicMock()
    collection = factories.CollectionFactory()
    serialized_data = serializers.CollectionSerializer(
        collection,
        context=dict(request=mocked_request),
    ).data
    mocked_admin_permission.assert_called_with(collection, mocked_request)
    assert serialized_data["is_admin"] is has_permission


@pytest.mark.parametrize("is_admin", [True, False])
@pytest.mark.parametrize("is_superuser", [True, False])
def test_collection_serializer_private_video(mocker, is_admin, is_superuser):
    """
    Test that a private video is not included in the serializer unless the user is super/admin
    """
    has_permission = is_superuser or is_admin
    mocker.patch("ui.permissions.has_admin_permission", return_value=has_permission)
    mocked_request = mocker.MagicMock()
    mocked_request.user = UserFactory.create(is_superuser=is_superuser)

    mocker.patch("ui.serializers.has_common_lists", return_value=is_admin)

    collection = factories.CollectionFactory(admin_lists=[MoiraListFactory.create()])
    VideoFactory.create(collection=collection)
    VideoFactory.create(is_private=True, collection=collection)

    serialized_data = serializers.CollectionSerializer(
        collection,
        context=dict(request=mocked_request),
    ).data

    assert len(serialized_data["videos"]) == (2 if has_permission else 1)


def test_collection_list_serializer():
    """
    Test for CollectionListSerializer
    """
    user = UserFactory.create()
    collection = factories.CollectionFactory(owner=user)
    _ = [factories.VideoFactory(collection=collection) for _ in range(3)]
    expected = {
        "key": collection.hexkey,
        "created_at": DateTimeField().to_representation(collection.created_at),
        "title": collection.title,
        "description": collection.description,
        "view_lists": [],
        "admin_lists": [],
        "video_count": collection.videos.count(),
        "edx_course_id": collection.edx_course_id,
        "owner": user.id,
        "owner_info": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
        },
    }
    assert serializers.CollectionListSerializer(collection).data == expected


def get_expected_result(video):
    """
    Expected result for VideoSerializer
    """
    return {
        "key": video.hexkey,
        "collection_key": video.collection.hexkey,
        "collection_title": video.collection.title,
        "created_at": DateTimeField().to_representation(video.created_at),
        "multiangle": video.multiangle,
        "title": video.title,
        "description": video.description,
        "videofile_set": serializers.VideoFileSerializer(
            video.videofile_set.all(), many=True
        ).data,
        "videothumbnail_set": serializers.VideoThumbnailSerializer(
            video.videothumbnail_set.all(), many=True
        ).data,
        "videosubtitle_set": [],
        "status": video.status,
        "collection_view_lists": [],
        "view_lists": [],
        "sources": video.sources,
        "is_private": False,
        "is_public": video.is_public,
        "is_logged_in_only": video.is_logged_in_only,
        "youtube_id": None,
        "cloudfront_url": "",
    }


@pytest.mark.parametrize("youtube", [True, False])
@pytest.mark.parametrize("public", [True, False])
def test_video_serializer(youtube, public):
    """
    Test for VideoSerializer
    """
    video = factories.VideoFactory()
    factories.VideoFileFactory(video=video)
    factories.VideoThumbnailFactory(video=video)
    video.is_public = public
    if youtube and public:
        factories.YouTubeVideoFactory(video=video)
    expected = get_expected_result(video)

    expected["youtube_id"] = video.youtube_id if youtube and public else None
    assert serializers.VideoSerializer(video).data == expected


@pytest.mark.parametrize("has_permission", [True, False])
@pytest.mark.parametrize("allow_share_openedx", [True, False])
@pytest.mark.parametrize("hls", [True, False])
def test_video_serializer_with_sharing_url(
    mocker, has_permission, allow_share_openedx, hls
):
    """
    Test for VideoSerializer for sharing cloudfront url
    """
    mocked_admin_permission = mocker.patch(
        "ui.permissions.has_admin_permission", return_value=has_permission
    )
    mocked_request = mocker.MagicMock()
    video = factories.VideoFactory()
    factories.VideoFileFactory(video=video, hls=hls)
    factories.VideoThumbnailFactory(video=video)
    video.collection.allow_share_openedx = allow_share_openedx
    video.is_public = True
    expected = get_expected_result(video)
    expected["cloudfront_url"] = (
        video.videofile_set.filter(encoding=EncodingNames.HLS).first().cloudfront_url
        if allow_share_openedx and hls and has_permission
        else ""
    )
    assert (
        serializers.VideoSerializer(video, context={"request": mocked_request}).data
        == expected
    )
    mocked_admin_permission.assert_called_with(video.collection, mocked_request)


def test_video_serializer_validate_title():
    """
    Test that VideoSerializer raises if title is blank
    """
    video = factories.VideoFactory()
    video.title = ""
    serialized_data = serializers.VideoSerializer(video).data
    with pytest.raises(ValidationError) as exc:
        serializers.VideoSerializer(data=serialized_data).is_valid(raise_exception=True)
    assert exc.value.detail == {"title": ["This field may not be blank."]}


def test_dropbox_upload_serializer():
    """
    Test for DropboxUploadSerializer
    """
    input_data = {
        "collection": "9734262d30144b8cbedb94a872158581",
        "files": [
            {
                "isDir": False,
                "link": "http://foo.bar/hoo.mp4",
                "thumbnailLink": "http://foo.bar.link/hoo.mp4",
                "bytes": 80633422,
                "id": "id:foooo",
                "name": "foo file",
                "icon": "https://foo.bar/static/images/icons64/page_white_film.png",
            }
        ],
    }
    expected_data = {
        "collection": str(uuid.UUID("9734262d30144b8cbedb94a872158581")),
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
    serializer = serializers.DropboxUploadSerializer(data=input_data)
    assert serializer.is_valid()
    assert serializer.data == expected_data


def test_subtitle_upload_serializer():
    """Test for the VideoSubtitleUploadSerializer"""

    input_data = {
        "video": "9734262d30144b8cbedb94a872158581",
        "language": "en",
        "filename": "foo.vtt",
    }
    serializer = serializers.VideoSubtitleUploadSerializer(data=input_data)
    assert serializer.is_valid()
    output_data = {
        "video": str(uuid.UUID("9734262d30144b8cbedb94a872158581")),
        "language": "en",
        "filename": "foo.vtt",
    }
    assert serializer.data == output_data


def test_subtitle_serializer():
    """
    Test for VideoSubtitleSerializer
    """
    subtitle = factories.VideoSubtitleFactory()

    expected = {
        "id": subtitle.id,
        "language": subtitle.language,
        "language_name": subtitle.language_name,
        "s3_object_key": subtitle.s3_object_key,
        "bucket_name": subtitle.bucket_name,
        "filename": subtitle.filename,
        "created_at": DateTimeField().to_representation(subtitle.created_at),
    }
    assert serializers.VideoSubtitleSerializer(subtitle).data == expected


def test_simplevideo_serializer():
    """
    Test for SimpleVideoSerializer
    """
    video = factories.VideoFactory()
    video_files = [factories.VideoFileFactory(video=video)]
    video_thumbnails = [factories.VideoThumbnailFactory(video=video)]
    expected = {
        "key": video.hexkey,
        "created_at": DateTimeField().to_representation(video.created_at),
        "title": video.title,
        "description": video.description,
        "videofile_set": serializers.VideoFileSerializer(video_files, many=True).data,
        "videosubtitle_set": [],
        "is_public": video.is_public,
        "is_private": video.is_private,
        "view_lists": [],
        "collection_view_lists": [],
        "videothumbnail_set": serializers.VideoThumbnailSerializer(
            video_thumbnails, many=True
        ).data,
        "status": video.status,
        "collection_key": video.collection.hexkey,
        "cloudfront_url": "",
    }
    assert serializers.SimpleVideoSerializer(video).data == expected


def test_user_serializer():
    """Test for UserSerializer"""
    user = factories.UserFactory(username="testuser", email="testuser@example.com")
    serialized_data = serializers.UserSerializer(user).data

    assert serialized_data == {
        "id": user.id,
        "username": user.username,
        "email": user.email,
    }
