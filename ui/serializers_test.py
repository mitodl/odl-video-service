"""
Tests for serialisers module
"""
import uuid

import pytest

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
        'title': collection.title,
        'description': collection.description,
        'owner': collection.owner.id,
        'videos': serializers.VideoSerializer(videos, many=True).data,
        'moira_lists': [],  # this needs to be updated when we figure out moira lists
    }
    expected['videos'].sort(key=lambda x: x['key'])
    serialized_data = serializers.CollectionSerializer(collection).data
    serialized_data['videos'].sort(key=lambda x: x['key'])
    assert serialized_data == expected


def test_collection_list_serializer():
    """
    Test for CollectionListSerializer
    """
    collection = factories.CollectionFactory()
    _ = [factories.VideoFactory(collection=collection) for _ in range(3)]
    expected = {
        'key': collection.hexkey,
        'title': collection.title,
        'description': collection.description,
        'owner': collection.owner.id,
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
        'title': video.title,
        'description': video.description,
        'videofile_set': serializers.VideoFileSerializer(video_files, many=True).data,
        'videothumbnail_set': serializers.VideoThumbnailSerializer(video_thumbnails, many=True).data,
    }
    result = serializers.VideoSerializer(video).data
    for key, val in expected.items():
        assert result[key] == val


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
    expecte_data = {
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
    assert serializer.data == expecte_data
