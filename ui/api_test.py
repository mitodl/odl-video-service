"""
Tests for ui/api.py
"""
# pylint: disable=unused-argument,redefined-outer-name
from uuid import uuid4
from types import SimpleNamespace
import pytest
import factory
import requests

from django.core.exceptions import ValidationError
from django.http import Http404
from django.db.models import signals

from ui import (
    api,
    models,
)
from ui.factories import (
    CollectionFactory,
    VideoFileFactory,
    CollectionEdxEndpointFactory,
    EdxEndpointFactory,
)
from ui.encodings import EncodingNames
from odl_video.test_utils import any_instance_of, MockResponse

pytestmark = pytest.mark.django_db


@pytest.fixture()
@factory.django.mute_signals(signals.post_save)
def edx_api_scenario():
    """Fixture that provides a VideoFile with the correct properties to post to edX"""
    course_id = "course-v1:abc"
    video_file = VideoFileFactory.create(
        encoding=EncodingNames.HLS,
        video__title="My Video",
        video__collection__edx_course_id=course_id,
    )
    default_endpoint = EdxEndpointFactory.create(is_global_default=True)
    collection_edx_endpoint = CollectionEdxEndpointFactory(
        collection=video_file.video.collection, edx_endpoint__is_global_default=False
    )
    return SimpleNamespace(
        video_file=video_file,
        course_id=course_id,
        default_endpoint=default_endpoint,
        collection_endpoint=collection_edx_endpoint.edx_endpoint,
    )


def test_process_dropbox_data_happy_path(mocker):
    """
    Tests that the process_dropbox_data in case everything is fine
    """
    mocked_chain = mocker.patch("ui.api.chain")
    mocked_stream_to_s3 = mocker.patch("cloudsync.tasks.stream_to_s3")
    mocked_transcode_from_s3 = mocker.patch("cloudsync.tasks.transcode_from_s3")
    collection = CollectionFactory()

    input_data = {
        "collection": collection.hexkey,
        "files": [
            {"name": name, "link": "http://example.com/{}".format(name)}
            for name in (
                "foo",
                "bar",
            )
        ],
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
        assert video.title == data["title"]
        assert video.get_s3_key() == data["s3key"]
        # checking that the functions in the chain have been called
        mocked_stream_to_s3.s.assert_any_call(video.id)
        mocked_transcode_from_s3.si.assert_any_call(video.id)
        mocked_chain.assert_any_call(
            mocked_stream_to_s3.s(video.id), mocked_transcode_from_s3.si(video.id)
        )


def test_process_dropbox_data_empty_link_list(mocker):
    """
    Tests that the process_dropbox_data in case the collection does not exist
    """
    mocked_chain = mocker.patch("ui.api.chain")
    mocked_stream_to_s3 = mocker.patch("cloudsync.tasks.stream_to_s3")
    mocked_transcode_from_s3 = mocker.patch("cloudsync.tasks.transcode_from_s3")
    collection = CollectionFactory()

    assert (
        api.process_dropbox_data(
            {
                "collection": collection.hexkey,
                "files": [],
            }
        )
        == {}
    )
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
                "collection": "fooooooooo",
                "files": [],
            }
        )

    with pytest.raises(Http404):
        api.process_dropbox_data(
            {
                "collection": uuid4().hex,
                "files": [],
            }
        )


def test_post_hls_to_edx(mocker, reqmocker, edx_api_scenario):
    """
    post_hls_to_edx should make POST requests to all edX API endpoints that are configured
    for a video file's collection
    """
    mocked_posts = [
        reqmocker.register_uri(
            "POST",
            edx_endpoint.full_api_url,
            headers={
                "Authorization": "JWT {}".format(edx_endpoint.access_token),
            },
            status_code=200,
        )
        for edx_endpoint in [
            edx_api_scenario.default_endpoint,
            edx_api_scenario.collection_endpoint,
        ]
    ]

    refresh_token_mock = mocker.patch("ui.models.EdxEndpoint.refresh_access_token")
    api.post_hls_to_edx(edx_api_scenario.video_file)
    assert refresh_token_mock.call_count == 2
    for mocked_post in mocked_posts:
        assert mocked_post.call_count == 1
        request_body = mocked_post.last_request.json()
        assert request_body == {
            "client_video_id": edx_api_scenario.video_file.video.title,
            "edx_video_id": any_instance_of(str),
            "encoded_videos": [
                {
                    "url": edx_api_scenario.video_file.cloudfront_url,
                    "file_size": 0,
                    "bitrate": 0,
                    "profile": "hls",
                }
            ],
            "courses": [{edx_api_scenario.course_id: None}],
            "status": "file_complete",
            "duration": 0.0,
        }
        assert len(request_body["edx_video_id"]) == 36


@factory.django.mute_signals(signals.post_save)
def test_post_hls_to_edx_no_endpoints(mocker):
    """post_hls_to_edx should log an error if no endpoints are configured for some video's collection"""
    patched_log_error = mocker.patch("ui.api.log.error")
    video_file = VideoFileFactory.create(
        encoding=EncodingNames.HLS,
        video__collection__edx_course_id="some-course-id",
    )
    responses = api.post_hls_to_edx(video_file)
    patched_log_error.assert_called_once()
    assert responses == {}


def test_post_hls_to_edx_wrong_type(mocker):
    """
    post_hls_to_edx should raise an exception if the given video file is not
    configured correctly for posting to edX
    """
    video_file = VideoFileFactory.create(encoding=EncodingNames.ORIGINAL)
    with pytest.raises(Exception):
        api.post_hls_to_edx(video_file)


def test_post_hls_to_edx_bad_resp(mocker, reqmocker, edx_api_scenario):
    """post_hls_to_edx should log an error if an edX API POST request does not return a 2** status code"""
    patched_log_error = mocker.patch("ui.api.log.error")
    default_endpoint = edx_api_scenario.default_endpoint
    collection_endpoint = edx_api_scenario.collection_endpoint
    mocked_posts = [
        reqmocker.register_uri(
            "POST",
            default_endpoint.full_api_url,
            exc=requests.exceptions.RequestException(
                response=MockResponse(
                    content='{"error": "text"}'.encode("utf-8"),
                    status_code=400,
                    url=default_endpoint.full_api_url,
                )
            ),
        ),
        reqmocker.register_uri(
            "POST",
            collection_endpoint.full_api_url,
            headers={
                "Authorization": "Bearer {}".format(collection_endpoint.access_token),
            },
            status_code=200,
        ),
    ]
    responses = api.post_hls_to_edx(edx_api_scenario.video_file)
    for mocked_post in mocked_posts:
        assert mocked_post.call_count == 1
    patched_log_error.assert_called_once()
    assert "Can not add HLS video to edX" in patched_log_error.call_args[0][0]
    assert len(responses) == 2
