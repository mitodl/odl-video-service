"""
Tests for ui/api.py
"""

from types import SimpleNamespace

from uuid import uuid4

import factory
import pytest
from django.core.exceptions import ValidationError
from django.db.models import signals
from django.http import Http404

from odl_video.test_utils import any_instance_of
from ui import api, models
from ui.encodings import EncodingNames
from ui.factories import (
    CollectionEdxEndpointFactory,
    CollectionFactory,
    VideoFileFactory,
)

pytestmark = pytest.mark.django_db


@pytest.fixture()
@factory.django.mute_signals(signals.post_save)
def edx_api_scenario():
    """Fixture that provides a VideoFile with the correct properties to post to edX"""
    course_id = "course-v1:abc"
    video_file_hls = VideoFileFactory.create(
        encoding=EncodingNames.HLS,
        video__title="My Video",
        video__collection__edx_course_id=course_id,
    )
    video_file_mp4 = VideoFileFactory.create(
        encoding=EncodingNames.DESKTOP_MP4,
        video__title="My Video",
        video__collection__edx_course_id=course_id,
    )
    collection_edx_endpoint = CollectionEdxEndpointFactory(
        collection=video_file_hls.video.collection
    )
    return SimpleNamespace(
        video_file_mp4=video_file_mp4,
        video_file_hls=video_file_hls,
        course_id=course_id,
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

    assert not (
        api.process_dropbox_data(
            {
                "collection": collection.hexkey,
                "files": [],
            }
        )
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


def test_post_video_to_edx(mocker, reqmocker, edx_api_scenario):
    """
    post_video_to_edx should make POST requests to all edX API endpoints that are configured
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
            edx_api_scenario.collection_endpoint,
        ]
    ]

    refresh_token_mock = mocker.patch("ui.models.EdxEndpoint.refresh_access_token")
    api.post_video_to_edx(
        [edx_api_scenario.video_file_hls, edx_api_scenario.video_file_mp4]
    )
    assert refresh_token_mock.call_count == 1
    for mocked_post in mocked_posts:
        assert mocked_post.call_count == 1
        request_body = mocked_post.last_request.json()
        assert request_body == {
            "client_video_id": edx_api_scenario.video_file_hls.video.title,
            "edx_video_id": any_instance_of(str),
            "encoded_videos": [
                {
                    "url": edx_api_scenario.video_file_hls.cloudfront_url,
                    "file_size": 0,
                    "bitrate": 0,
                    "profile": "hls",
                },
                {
                    "url": edx_api_scenario.video_file_mp4.cloudfront_url,
                    "file_size": 0,
                    "bitrate": 0,
                    "profile": "desktop_mp4",
                },
            ],
            "courses": [{edx_api_scenario.course_id: None}],
            "status": "file_complete",
            "duration": 0.0,
        }
        assert len(request_body["edx_video_id"]) == 36


def test_post_same_video_to_edx(mocker, reqmocker, edx_api_scenario):
    """
    post_video_to_edx should make update request if the video is already posted to edX
    """
    mocked_posts = [
        reqmocker.register_uri(
            "POST",
            edx_endpoint.full_api_url,
            headers={
                "Authorization": "JWT {}".format(edx_endpoint.access_token),
            },
            status_code=400,
        )
        for edx_endpoint in [
            edx_api_scenario.collection_endpoint,
        ]
    ]
    mocked_requests = [
        reqmocker.register_uri(
            "PATCH",
            edx_endpoint.full_api_url + str(edx_api_scenario.video_file_hls.video.key),
            headers={
                "Authorization": "JWT {}".format(edx_endpoint.access_token),
            },
            status_code=200,
        )
        for edx_endpoint in [
            edx_api_scenario.collection_endpoint,
        ]
    ]
    refresh_token_mock = mocker.patch("ui.models.EdxEndpoint.refresh_access_token")
    api.post_video_to_edx(
        [edx_api_scenario.video_file_hls, edx_api_scenario.video_file_mp4]
    )
    assert refresh_token_mock.call_count == 2
    for mock_post in mocked_posts:
        assert mock_post.call_count == 1
    for mock_request in mocked_requests:
        assert mock_request.call_count == 1
        request_body = mock_request.last_request.json()
        assert request_body == {
            "client_video_id": edx_api_scenario.video_file_hls.video.title,
            "edx_video_id": str(edx_api_scenario.video_file_hls.video.key),
            "encoded_videos": [
                {
                    "url": edx_api_scenario.video_file_hls.cloudfront_url,
                    "file_size": 0,
                    "bitrate": 0,
                    "profile": "hls",
                },
                {
                    "url": edx_api_scenario.video_file_mp4.cloudfront_url,
                    "file_size": 0,
                    "bitrate": 0,
                    "profile": "desktop_mp4",
                },
            ],
            "status": "updated",
            "duration": 0.0,
        }
        assert len(request_body["edx_video_id"]) == 36


@factory.django.mute_signals(signals.post_save)
def test_post_video_to_edx_no_endpoints(mocker):
    """post_video_to_edx should log an error if no endpoints are configured for some video's collection"""
    patched_log_error = mocker.patch("ui.api.log.error")
    video_file = VideoFileFactory.create(
        encoding=EncodingNames.HLS,
        video__collection__edx_course_id="some-course-id",
    )
    responses = api.post_video_to_edx([video_file])
    patched_log_error.assert_called_once()
    assert not responses


def test_post_video_to_edx_wrong_type(mocker):
    """
    post_video_to_edx should raise an exception if the given video file is not
    configured correctly for posting to edX
    """
    video_file = VideoFileFactory.create(encoding=EncodingNames.ORIGINAL)
    with pytest.raises(Exception):
        api.post_video_to_edx(video_file)


def test_post_video_to_edx_bad_resp(mocker, reqmocker, edx_api_scenario):
    """post_video_to_edx should log an error if an edX API POST request does not return a 2** status code"""
    patched_log_error = mocker.patch("ui.api.log.error")
    collection_endpoint = edx_api_scenario.collection_endpoint
    mocked_post = reqmocker.register_uri(
        "POST",
        collection_endpoint.full_api_url,
        headers={
            "Authorization": "JWT {}".format(collection_endpoint.access_token),
        },
        status_code=403,
    )
    refresh_token_mock = mocker.patch("ui.models.EdxEndpoint.refresh_access_token")
    responses = api.post_video_to_edx([edx_api_scenario.video_file_hls])
    assert refresh_token_mock.call_count == 1
    assert mocked_post.call_count == 1
    patched_log_error.assert_called_once()
    assert "Can not add video to edX" in patched_log_error.call_args[0][0]
    assert len(responses) == 1


@pytest.mark.parametrize("attach_encoded_videos", [True, False])
def test_update_video_on_edx(
    mocker, reqmocker, edx_api_scenario, attach_encoded_videos
):
    """
    update_video_on_edx should make PATCH requests to all edX API endpoints that are configured
    for a video's collection
    """
    mocked_requests = [
        reqmocker.register_uri(
            "PATCH",
            edx_endpoint.full_api_url + str(edx_api_scenario.video_file_hls.video.key),
            headers={
                "Authorization": "JWT {}".format(edx_endpoint.access_token),
            },
            status_code=200,
        )
        for edx_endpoint in [
            edx_api_scenario.collection_endpoint,
        ]
    ]
    encoded_videos = None
    if attach_encoded_videos:
        encoded_videos = [
            {
                "url": edx_api_scenario.video_file_hls.cloudfront_url,
                "file_size": 0,
                "bitrate": 0,
                "profile": "hls",
            },
            {
                "url": edx_api_scenario.video_file_mp4.cloudfront_url,
                "file_size": 0,
                "bitrate": 0,
                "profile": "desktop_mp4",
            },
        ]

    refresh_token_mock = mocker.patch("ui.models.EdxEndpoint.refresh_access_token")
    api.update_video_on_edx(edx_api_scenario.video_file_hls.video.key, encoded_videos)
    assert refresh_token_mock.call_count == 1
    for mocked_request in mocked_requests:
        assert mocked_request.call_count == 1
        request_body = mocked_request.last_request.json()
        mock_body = {
            "edx_video_id": str(edx_api_scenario.video_file_hls.video.key),
            "client_video_id": edx_api_scenario.video_file_hls.video.title,
            "status": "updated",
            "duration": 0.0,
        }
        if encoded_videos:
            mock_body["encoded_videos"] = encoded_videos

        assert request_body == mock_body


def test_update_video_on_edx_bad_response(mocker, reqmocker, edx_api_scenario):
    """
    update_video_on_edx should return response if an edX API PATCH request does not return a 200 status code
    """
    patched_log_exception = mocker.patch("ui.api.log.exception")
    video_partial_update_url = edx_api_scenario.collection_endpoint.full_api_url + str(
        edx_api_scenario.video_file_hls.video.key
    )
    mocked_requests = reqmocker.register_uri(
        "PATCH",
        video_partial_update_url,
        headers={
            "Authorization": "JWT {}".format(edx_api_scenario.collection_endpoint),
        },
        status_code=403,
    )
    refresh_token_mock = mocker.patch("ui.models.EdxEndpoint.refresh_access_token")
    response = api.update_video_on_edx(edx_api_scenario.video_file_hls.video.key)
    assert refresh_token_mock.call_count == 1
    assert mocked_requests.call_count == 1
    patched_log_exception.assert_called_once()
    assert "Can not update video to edX" == patched_log_exception.call_args[0][0]
    assert list(response.keys())[0] == video_partial_update_url
    assert getattr(list(response.values())[0], "ok") is False


def test_get_duration_from_encode_job():
    """
    get_duration_from_encode_job should return duration from video's encode_jobs message body
    """
    encode_job = {
        "id": "1711563064503-e5qdnh",
        "outputGroupDetails": [
            {
                "outputDetails": [
                    {
                        "durationInMs": 10000.0,
                    }
                ]
            }
        ],
    }
    duration = api.get_duration_from_encode_job(encode_job)
    assert duration == 10.0

    encode_job = {}
    duration = api.get_duration_from_encode_job(encode_job)
    assert duration == 0.0
