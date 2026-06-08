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
from ui.constants import VideoStatus
from ui.encodings import EncodingNames
from ui.factories import (
    CollectionEdxEndpointFactory,
    CollectionFactory,
    VideoFactory,
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


def test_replace_video_from_dropbox(mocker):
    """
    replace_video_from_dropbox should update source_url, reset video status,
    and kick off the stream_to_s3 + retranscode_video chain.
    """
    mocked_chain = mocker.patch("ui.api.chain")
    mocked_stream_to_s3 = mocker.patch("cloudsync.tasks.stream_to_s3")
    mocked_retranscode = mocker.patch("cloudsync.tasks.retranscode_video")
    video = VideoFactory()
    dropbox_file = {
        "link": "http://dropbox.example.com/new_video.mp4",
        "name": "new_video.mp4",
        "bytes": 12345678,
        "isDir": False,
        "thumbnailLink": "http://dropbox.example.com/new_video.mp4",
        "icon": "https://dropbox.example.com/icon.png",
    }

    result = api.replace_video_from_dropbox(video.key, dropbox_file)

    video.refresh_from_db()
    assert video.source_url == dropbox_file["link"]
    assert result == {"key": video.hexkey, "title": video.title}
    mocked_chain.assert_called_once()
    mocked_stream_to_s3.s.assert_called_once_with(video.id)
    mocked_retranscode.si.assert_called_once_with(video.id)


def test_replace_video_from_dropbox_different_extension(mocker):
    """
    When the replacement file has a different extension from the original
    (e.g. .mp4 → .m4v), replace_video_from_dropbox must:
      - repoint the original VideoFile's s3_object_key to the new key
        (derived from the updated source_url) so stream_to_s3 writes there
        and retranscode_video reads the correct object, and
      - schedule async deletion of the now-stale old S3 object.
    """
    mocker.patch("ui.api.chain")
    mocker.patch("cloudsync.tasks.stream_to_s3")
    mocker.patch("cloudsync.tasks.retranscode_video")
    mock_delete = mocker.patch("ui.models.delete_s3_objects")

    # Create a video whose source URL (and therefore get_s3_key()) ends in .mp4.
    video = VideoFactory(source_url="http://dropbox.example.com/original_video.mp4")
    original_vf = VideoFileFactory(
        video=video,
        s3_object_key=video.get_s3_key(),
        encoding=EncodingNames.ORIGINAL,
    )
    old_s3_key = original_vf.s3_object_key
    assert old_s3_key.endswith(".mp4")

    # Replacement file uses a different extension.
    dropbox_file = {
        "link": "http://dropbox.example.com/replacement_video.m4v",
        "name": "replacement_video.m4v",
        "bytes": 9876543,
        "isDir": False,
        "thumbnailLink": "http://dropbox.example.com/replacement_video.m4v",
        "icon": "https://dropbox.example.com/icon.png",
    }

    api.replace_video_from_dropbox(video.key, dropbox_file)

    video.refresh_from_db()
    original_vf.refresh_from_db()

    # source_url must point at the new file.
    assert video.source_url == dropbox_file["link"]

    # The VideoFile must now carry the new key so the chain uses the right object.
    expected_new_key = video.get_s3_key()
    assert expected_new_key.endswith(".m4v")
    assert original_vf.s3_object_key == expected_new_key

    # The stale old object must be queued for deletion.
    mock_delete.delay.assert_called_once_with(original_vf.bucket_name, old_s3_key)


def test_replace_video_from_dropbox_same_extension_no_delete(mocker):
    """
    When the replacement file has the same extension as the original, the
    VideoFile key is unchanged and no S3 deletion is scheduled.
    """
    mocker.patch("ui.api.chain")
    mocker.patch("cloudsync.tasks.stream_to_s3")
    mocker.patch("cloudsync.tasks.retranscode_video")
    mock_delete = mocker.patch("ui.models.delete_s3_objects")

    video = VideoFactory(source_url="http://dropbox.example.com/original_video.mp4")
    original_vf = VideoFileFactory(
        video=video,
        s3_object_key=video.get_s3_key(),
        encoding=EncodingNames.ORIGINAL,
    )
    old_s3_key = original_vf.s3_object_key

    dropbox_file = {
        "link": "http://dropbox.example.com/replacement_video.mp4",
        "name": "replacement_video.mp4",
        "bytes": 9876543,
        "isDir": False,
        "thumbnailLink": "http://dropbox.example.com/replacement_video.mp4",
        "icon": "https://dropbox.example.com/icon.png",
    }

    api.replace_video_from_dropbox(video.key, dropbox_file)

    original_vf.refresh_from_db()
    assert original_vf.s3_object_key == old_s3_key
    mock_delete.delay.assert_not_called()


def test_replace_video_from_dropbox_not_found():
    """replace_video_from_dropbox raises Http404 when the video key does not exist."""
    with pytest.raises(Http404):
        api.replace_video_from_dropbox(
            uuid4(), {"link": "http://example.com/video.mp4"}
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
            "status": "file_complete",
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
            "status": "file_complete",
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


def test_retry_failed_upload_dispatches(mocker):
    """An eligible UPLOAD_FAILED video is reset to CREATED and re-queued."""
    mocked_chain = mocker.patch("ui.api.chain")
    video = VideoFactory(status=VideoStatus.UPLOAD_FAILED)
    VideoFileFactory(video=video, encoding=EncodingNames.ORIGINAL)

    outcome = api.retry_failed_upload(video)

    assert outcome == "retried"
    video.refresh_from_db()
    assert video.status == VideoStatus.CREATED
    mocked_chain.return_value.delay.assert_called_once()


def test_retry_failed_upload_skips_missing_original(mocker):
    """Without an original VideoFile the chain would fail in transcode; skip it."""
    mocked_chain = mocker.patch("ui.api.chain")
    video = VideoFactory(status=VideoStatus.UPLOAD_FAILED)

    outcome = api.retry_failed_upload(video)

    assert outcome == "skipped_no_original"
    video.refresh_from_db()
    assert video.status == VideoStatus.UPLOAD_FAILED
    mocked_chain.assert_not_called()


def test_retry_failed_upload_reverts_on_dispatch_failure(mocker):
    """If dispatch raises, the video is restored to UPLOAD_FAILED, not marooned."""
    mocked_chain = mocker.patch("ui.api.chain")
    mocked_chain.return_value.delay.side_effect = Exception("broker down")
    video = VideoFactory(status=VideoStatus.UPLOAD_FAILED)
    VideoFileFactory(video=video, encoding=EncodingNames.ORIGINAL)

    outcome = api.retry_failed_upload(video)

    assert outcome == "dispatch_failed"
    video.refresh_from_db()
    assert video.status == VideoStatus.UPLOAD_FAILED


def test_retry_failed_upload_skips_conflict(mocker):
    """
    If the persisted row is no longer UPLOAD_FAILED when the atomic transition
    runs (a concurrent retry grabbed it first), skip without dispatching.
    """
    mocked_chain = mocker.patch("ui.api.chain")
    video = VideoFactory(status=VideoStatus.CREATED)
    VideoFileFactory(video=video, encoding=EncodingNames.ORIGINAL)
    # In-memory object looks eligible, but the persisted row is not UPLOAD_FAILED.
    video.status = VideoStatus.UPLOAD_FAILED

    outcome = api.retry_failed_upload(video)

    assert outcome == "skipped_conflict"
    mocked_chain.assert_not_called()
    video.refresh_from_db()
    assert video.status == VideoStatus.CREATED


def test_retry_failed_upload_skips_non_failed(mocker):
    """A video not in UPLOAD_FAILED status is skipped."""
    mocked_chain = mocker.patch("ui.api.chain")
    video = VideoFactory(status=VideoStatus.COMPLETE)

    outcome = api.retry_failed_upload(video)

    assert outcome == "skipped_status"
    mocked_chain.assert_not_called()


def test_retry_failed_upload_skips_no_source(mocker):
    """A video without a source_url cannot be retried."""
    mocked_chain = mocker.patch("ui.api.chain")
    video = VideoFactory(status=VideoStatus.UPLOAD_FAILED)
    models.Video.objects.filter(pk=video.pk).update(source_url="")
    video.refresh_from_db()

    outcome = api.retry_failed_upload(video)

    assert outcome == "skipped_no_source"
    mocked_chain.assert_not_called()
