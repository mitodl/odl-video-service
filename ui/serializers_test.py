"""
Tests for serialisers module
"""
import uuid

import pytest
from rest_framework.serializers import DateTimeField

from ui import factories, serializers

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
        'owner': collection.owner.id,
        'videos': serializers.VideoSerializer(videos, many=True).data,
        'view_lists': [],
        'admin_lists': [],
        'is_admin': None
    }
    expected['videos'].sort(key=lambda x: x['key'])
    serialized_data = serializers.CollectionSerializer(collection).data
    serialized_data['videos'].sort(key=lambda x: x['key'])
    assert serialized_data == expected


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
        'owner': collection.owner.id,
        'view_lists': [],
        'admin_lists': []
    }
    assert serializers.CollectionListSerializer(collection).data == expected


def test_video_serializer():
    """
    Test for VideoSerializer
    """
    video = factories.VideoFactory()
    video_files = [factories.VideoFileFactory(video=video)]
    video_thumbnails = [factories.VideoThumbnailFactory(video=video)]

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
        'status': video.status,
    }
    assert serializers.VideoSerializer(video).data == expected


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
