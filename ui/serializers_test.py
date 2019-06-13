"""
Tests for serialisers module
"""
import uuid

import pytest
from rest_framework.serializers import DateTimeField, ValidationError

from ui import factories, serializers
from ui.encodings import EncodingNames

pytestmark = pytest.mark.django_db

# pylint: disable=redefined-outer-name


def test_collection_serializer():
    """
    Test for CollectionSerializer
    """
    collection = factories.CollectionFactory()
    videos = [factories.VideoFactory(collection=collection) for _ in range(3)]
    expected = {
        'key': collection.hexkey,
        'created_at': DateTimeField().to_representation(collection.created_at),
        'title': collection.title,
        'description': collection.description,
        'videos': serializers.SimpleVideoSerializer(videos, many=True).data,
        'video_count': len(videos),
        'view_lists': [],
        'admin_lists': [],
        'is_admin': None
    }
    expected['videos'].sort(key=lambda x: x['key'])
    serialized_data = serializers.CollectionSerializer(collection).data
    serialized_data['videos'].sort(key=lambda x: x['key'])
    assert serialized_data == expected


def test_collection_serializer_validation_fake_admin_lists(mocker):
    """
    Test for CollectionSerializer's admin moira lists validation for fake lists
    """
    mock_client = mocker.patch('ui.serializers.get_moira_client')
    mock_client().list_exists.return_value = False
    collection = factories.CollectionFactory(admin_lists=[factories.MoiraListFactory()])
    serialized_data = serializers.CollectionSerializer(collection).data
    with pytest.raises(ValidationError) as exc:
        serializers.CollectionSerializer(data=serialized_data).is_valid(raise_exception=True)
    assert exc.match('Moira list does not exist: {}'.format(collection.admin_lists.first().name))


def test_collection_serializer_validation_fake_view_lists(mocker):
    """
    Test for CollectionSerializer's viewable moira lists validation for fake lists
    """
    mock_client = mocker.patch('ui.serializers.get_moira_client')
    mock_client().list_exists.return_value = False
    collection = factories.CollectionFactory(view_lists=[factories.MoiraListFactory()])
    serialized_data = serializers.CollectionSerializer(collection).data
    with pytest.raises(ValidationError) as exc:
        serializers.CollectionSerializer(data=serialized_data).is_valid(raise_exception=True)
    assert exc.match('Moira list does not exist: {}'.format(collection.view_lists.first().name))


def test_collection_serializer_validate_title(mocker):
    """
    Test that we can't save a blank title
    """
    mocker.patch('ui.serializers.get_moira_client')
    collection = factories.CollectionFactory(title="")
    serialized_data = serializers.CollectionSerializer(collection).data
    with pytest.raises(ValidationError) as exc:
        serializers.CollectionSerializer(data=serialized_data).is_valid(raise_exception=True)
    assert exc.value.detail == {'title': ['This field may not be blank.']}


@pytest.mark.parametrize("has_permission", [True, False])
def test_collection_serializer_admin_flag(mocker, has_permission):
    """
    Test that the is_admin flag returns an expected value based on a user's admin permission
    """
    mocked_admin_permission = mocker.patch('ui.permissions.has_admin_permission', return_value=has_permission)
    mocked_request = mocker.MagicMock()
    collection = factories.CollectionFactory()
    serialized_data = serializers.CollectionSerializer(
        collection,
        context=dict(request=mocked_request)
    ).data
    mocked_admin_permission.assert_called_with(collection, mocked_request)
    assert serialized_data['is_admin'] is has_permission


def test_collection_list_serializer():
    """
    Test for CollectionListSerializer
    """
    collection = factories.CollectionFactory()
    _ = [factories.VideoFactory(collection=collection) for _ in range(3)]
    expected = {
        'key': collection.hexkey,
        'created_at': DateTimeField().to_representation(collection.created_at),
        'title': collection.title,
        'description': collection.description,
        'view_lists': [],
        'admin_lists': [],
        'video_count': collection.videos.count(),
    }
    assert serializers.CollectionListSerializer(collection).data == expected


@pytest.mark.parametrize('youtube', [True, False])
@pytest.mark.parametrize('public', [True, False])
@pytest.mark.parametrize('allow_share_openedx', [True, False])
@pytest.mark.parametrize('hsl', [True, False])
def test_video_serializer(youtube, public, allow_share_openedx, hsl):
    """
    Test for VideoSerializer
    """
    video = factories.VideoFactory()
    video.collection.allow_share_openedx = allow_share_openedx
    video_files = [factories.VideoFileFactory(video=video, hls=hsl)]
    video_thumbnails = [factories.VideoThumbnailFactory(video=video)]
    video.is_public = public
    if youtube and public:
        factories.YouTubeVideoFactory(video=video)

    expected = {
        'key': video.hexkey,
        'collection_key': video.collection.hexkey,
        'collection_title': video.collection.title,
        'created_at': DateTimeField().to_representation(video.created_at),
        'multiangle': video.multiangle,
        'title': video.title,
        'description': video.description,
        'videofile_set': serializers.VideoFileSerializer(video_files, many=True).data,
        'videothumbnail_set': serializers.VideoThumbnailSerializer(video_thumbnails, many=True).data,
        'videosubtitle_set': [],
        'status': video.status,
        'collection_view_lists': [],
        'view_lists': [],
        'sources': video.sources,
        'is_private': False,
        'is_public': public,
        'youtube_id': (video.youtube_id if youtube and public else None),
        'cloudfront_url': (video.videofile_set.filter(encoding=EncodingNames.HLS).first().cloudfront_url
                           if allow_share_openedx and hsl else ""),
    }
    assert serializers.VideoSerializer(video).data == expected


def test_video_serializer_validate_title(mocker):
    """
    Test that VideoSerializer raises if title is blank
    """
    mocker.patch('ui.serializers.get_moira_client')
    video = factories.VideoFactory()
    video.title = ""
    serialized_data = serializers.VideoSerializer(video).data
    with pytest.raises(ValidationError) as exc:
        serializers.VideoSerializer(data=serialized_data).is_valid(raise_exception=True)
    assert exc.value.detail == {'title': ['This field may not be blank.']}


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
                "icon": "https://foo.bar/static/images/icons64/page_white_film.png"
            }
        ]
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
                "icon": "https://foo.bar/static/images/icons64/page_white_film.png"
            }
        ]
    }
    serializer = serializers.DropboxUploadSerializer(data=input_data)
    assert serializer.is_valid()
    assert serializer.data == expected_data


def test_subtitle_upload_serializer():
    """ Test for the VideoSubtitleUploadSerializer """

    input_data = {"video": "9734262d30144b8cbedb94a872158581", "language": "en", "filename": "foo.vtt"}
    serializer = serializers.VideoSubtitleUploadSerializer(data=input_data)
    assert serializer.is_valid()
    output_data = {
        "video": str(uuid.UUID("9734262d30144b8cbedb94a872158581")),
        "language": "en",
        "filename": "foo.vtt"
    }
    assert serializer.data == output_data


def test_subtitle_serializer():
    """
    Test for VideoSubtitleSerializer
    """
    subtitle = factories.VideoSubtitleFactory()

    expected = {
        'id': subtitle.id,
        'language': subtitle.language,
        'language_name': subtitle.language_name,
        's3_object_key': subtitle.s3_object_key,
        'bucket_name': subtitle.bucket_name,
        'filename': subtitle.filename,
        'created_at': DateTimeField().to_representation(subtitle.created_at)
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
        'key': video.hexkey,
        'created_at': DateTimeField().to_representation(video.created_at),
        'title': video.title,
        'description': video.description,
        'videofile_set': serializers.VideoFileSerializer(video_files, many=True).data,
        'videosubtitle_set': [],
        'is_public': video.is_public,
        'is_private': video.is_private,
        'view_lists': [],
        'collection_view_lists': [],
        'videothumbnail_set': serializers.VideoThumbnailSerializer(video_thumbnails, many=True).data,
        'status': video.status,
        'collection_key': video.collection.hexkey
    }
    assert serializers.SimpleVideoSerializer(video).data == expected
