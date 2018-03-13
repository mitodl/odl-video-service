"""
Tests for ui/api.py
"""
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.http import Http404
import pytest

from ui import (
    api,
    models,
)
from ui.factories import (
    CollectionFactory,
)


pytestmark = pytest.mark.django_db


def test_process_dropbox_data_happy_path(mocker):
    """
    Tests that the process_dropbox_data in case everything is fine
    """
    mocked_chain = mocker.patch('ui.api.chain')
    mocked_stream_to_s3 = mocker.patch('cloudsync.tasks.stream_to_s3')
    mocked_transcode_from_s3 = mocker.patch('cloudsync.tasks.transcode_from_s3')
    collection = CollectionFactory()

    input_data = {
        'collection': collection.hexkey,
        'files': [{'name': name, 'link': 'http://example.com/{}'.format(name)} for name in ('foo', 'bar',)],
    }

    results = api.process_dropbox_data(input_data)
    assert len(results) == 2
    assert mocked_chain.call_count == 2
    for key, data in results.items():
        qset = models.Video.objects.filter(key=key)
        assert qset.exists()
        assert qset.count() == 1
        video = qset.first()
        assert video.collection == collection
        assert video.title == data['title']
        assert video.get_s3_key() == data['s3key']
        # checking that the functions in the chain have been called
        mocked_stream_to_s3.s.assert_any_call(video.id)
        mocked_transcode_from_s3.si.assert_any_call(video.id)
        mocked_chain.assert_any_call(
            mocked_stream_to_s3.s(video.id),
            mocked_transcode_from_s3.si(video.id)
        )


def test_process_dropbox_data_empty_link_list(mocker):
    """
    Tests that the process_dropbox_data in case the collection does not exist
    """
    mocked_chain = mocker.patch('ui.api.chain')
    mocked_stream_to_s3 = mocker.patch('cloudsync.tasks.stream_to_s3')
    mocked_transcode_from_s3 = mocker.patch('cloudsync.tasks.transcode_from_s3')
    collection = CollectionFactory()

    assert api.process_dropbox_data(
        {
            'collection': collection.hexkey,
            'files': [],
        }
    ) == {}
    assert mocked_chain.call_count == 0
    assert mocked_stream_to_s3.s.call_count == 0
    assert mocked_transcode_from_s3.si.call_count == 0


def test_process_dropbox_data_wrong_collection():
    """
    Tests that process_dropbox_data errors in case the collection does not exist
    """
    with pytest.raises(ValidationError):
        api.process_dropbox_data(
            {
                'collection': 'fooooooooo',
                'files': [],
            }
        )

    with pytest.raises(Http404):
        api.process_dropbox_data(
            {
                'collection': uuid4().hex,
                'files': [],
            }
        )
