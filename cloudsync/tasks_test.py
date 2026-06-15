"""
Tests for tasks
"""

import contextlib
import io
import json
import os
import random
import string
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import PropertyMock, call

import boto3
import celery
import pytest
import requests
from celery.exceptions import Retry
from botocore.exceptions import ClientError
from django.conf import settings
from django.test import override_settings
from googleapiclient.errors import HttpError, ResumableUploadError
from moto import mock_aws
from requests import HTTPError

from cloudsync import dropbox_api
from cloudsync.conftest import MockBoto, MockHttpErrorResponse
from cloudsync.exceptions import TranscodeTargetDoesNotExist
from cloudsync.tasks import (
    VideoTask,
    fail_stuck_uploading_videos,
    monitor_watch_bucket,
    parse_content_metadata,
    remove_youtube_caption,
    remove_youtube_video,
    retranscode_video,
    schedule_retranscodes,
    sort_transcoded_m3u8_files,
    stream_to_s3,
    transcode_from_s3,
    update_youtube_statuses,
    upload_youtube_caption,
    upload_youtube_videos,
)
from cloudsync.youtube import API_QUOTA_ERROR_MSG
from ui.constants import StreamSource, VideoStatus, YouTubeStatus
from ui.factories import (
    CollectionFactory,
    UserFactory,
    VideoFactory,
    VideoFileFactory,
    VideoSubtitleFactory,
    YouTubeVideoFactory,
)
from ui.models import TRANSCODE_PREFIX, Collection, Video, YouTubeVideo
from ui.utils import now_in_utc

pytestmark = pytest.mark.django_db


def _make_uploading_video(updated_hours_ago, created_hours_ago=None):
    """Create an UPLOADING video with backdated timestamps via .update()."""
    if created_hours_ago is None:
        created_hours_ago = updated_hours_ago
    video = VideoFactory(status=VideoStatus.UPLOADING)
    Video.objects.filter(pk=video.pk).update(
        updated_at=now_in_utc() - timedelta(hours=updated_hours_ago),
        created_at=now_in_utc() - timedelta(hours=created_hours_ago),
    )
    video.refresh_from_db()
    return video


def test_fail_stuck_uploading_recent_video_notifies(mocker):
    """Stuck + recently created → UPLOAD_FAILED with an email."""
    mocked_email = mocker.patch(
        "mail.tasks.async_send_notification_email", autospec=True
    )
    video = _make_uploading_video(updated_hours_ago=3.5, created_hours_ago=3.5)

    fail_stuck_uploading_videos.delay()

    video.refresh_from_db()
    assert video.status == VideoStatus.UPLOAD_FAILED
    mocked_email.delay.assert_called_once_with(video.id)


def test_fail_stuck_uploading_within_threshold_untouched(mocker):
    """Recently-updated UPLOADING video (under threshold) is left alone."""
    mocker.patch("mail.tasks.async_send_notification_email", autospec=True)
    video = _make_uploading_video(updated_hours_ago=0.1)

    fail_stuck_uploading_videos.delay()

    video.refresh_from_db()
    assert video.status == VideoStatus.UPLOADING


def test_fail_stuck_uploading_ignores_other_statuses(mocker):
    """Non-UPLOADING videos are never touched, however old."""
    mocker.patch("mail.tasks.async_send_notification_email", autospec=True)
    video = VideoFactory(status=VideoStatus.TRANSCODING)
    Video.objects.filter(pk=video.pk).update(
        updated_at=now_in_utc() - timedelta(hours=5)
    )

    fail_stuck_uploading_videos.delay()

    video.refresh_from_db()
    assert video.status == VideoStatus.TRANSCODING


def test_fail_stuck_uploading_continues_after_error(mocker):
    """A failure on one video must not abort the sweep of the rest."""
    mocker.patch("mail.tasks.async_send_notification_email", autospec=True)
    _make_uploading_video(updated_hours_ago=3.5)
    _make_uploading_video(updated_hours_ago=3.5)
    mocked_update = mocker.patch(
        "ui.models.Video.update_status", side_effect=[Exception("boom"), None]
    )

    fail_stuck_uploading_videos.delay()

    # Both stuck videos were processed even though the first raised.
    assert mocked_update.call_count == 2


@pytest.fixture()
def video():
    """Fixture to create a video"""
    return VideoFactory()


@pytest.fixture()
def public_video():
    """Fixture to create a public video"""
    return VideoFactory(is_public=True, status=VideoStatus.COMPLETE)


@pytest.fixture()
def videofile():
    """Fixture to create a videofile"""
    return VideoFileFactory()


@pytest.fixture()
def user():
    """Fixture to create a user"""
    return UserFactory()


@pytest.fixture()
def mocked_celery(mocker):
    """Mock object that patches certain celery functions"""
    exception_class = TabError
    replace_mock = mocker.patch(
        "celery.app.task.Task.replace", autospec=True, side_effect=exception_class
    )
    group_mock = mocker.patch("cloudsync.tasks.group", autospec=True)

    yield SimpleNamespace(
        replace=replace_mock,
        group=group_mock,
        replace_exception_class=exception_class,
    )


@pytest.fixture()
def mock_transcode(mocker):
    """Mock everything required for a  transcode"""
    mocker.patch("celery.app.task.Task.update_state")
    mocker.patch("cloudsync.api.process_transcode_results")
    mocker.patch("cloudsync.api.boto3", MockBoto)
    mocker.patch("cloudsync.api.delete_s3_objects")
    mocker.patch("ui.models.tasks")


@pytest.fixture()
def mock_failed_encode_job(mocker):
    """Mock everything required for a failed encode job"""
    job_result = {
        "Job": {"Id": "1498220566931-qtmtcu", "Status": "Error"},
        "Error": {"Code": 200, "Message": "FAIL"},
    }
    mocker.patch(
        "cloudsync.api.media_convert_job",
        side_effect=ClientError(error_response=job_result, operation_name="job"),
    )


@pytest.fixture()
def mock_successful_encode_job(mocker):
    """Mock everything required for a successful transcode"""
    mocker.patch(
        "cloudsync.api.media_convert_job",
        return_value={"Id": "1498220566931-qtmtcu", "Status": "Complete"},
    )


def test_empty_video_id():
    """
    Tests that an empty video id does not give a result
    """
    result = stream_to_s3("")
    assert not result


@pytest.mark.parametrize(
    "api_result, extra_headers, expected",
    [
        (
            {"name": "lecture.mp4", "size": 4096},
            {},
            ("lecture.mp4", "video/mp4", 4096),
        ),
        (
            {"name": "clip.mov"},
            {"Content-Length": "2048"},
            ("clip.mov", "video/quicktime", 2048),
        ),
    ],
    ids=["header_name_and_size", "size_fallback_to_content_length"],
)
def test_parse_content_metadata_dropbox(api_result, extra_headers, expected):
    """Dropbox responses carry metadata in the Dropbox-API-Result header."""
    response = SimpleNamespace(
        headers={
            "Dropbox-API-Result": json.dumps(api_result),
            "Content-Type": "application/octet-stream",
            **extra_headers,
        },
    )
    assert parse_content_metadata(response) == expected


def _lock_yielding(acquired):
    """Build a drop-in upload_lock context manager that always yields ``acquired``."""

    @contextlib.contextmanager
    def _cm(*_args, **_kwargs):
        yield acquired

    return _cm


def _dropbox_metadata(name, size, extra_headers=None):
    """A fake stream_shared_link response carrying the Dropbox metadata header."""
    headers = {
        "Dropbox-API-Result": json.dumps({"name": name, "size": size}),
        "Content-Type": "application/octet-stream",
    }
    if extra_headers:
        headers.update(extra_headers)
    return SimpleNamespace(headers=headers, close=lambda: None)


def _range_fetcher_for(body):
    """Build a fake fetch_shared_link_range returning 206 slices of ``body``."""

    def _fetch(_url, start, end, timeout=None):
        return SimpleNamespace(
            status_code=206,
            content=body[start : end + 1],
            headers={"Content-Range": f"bytes {start}-{end}/{len(body)}"},
        )

    return _fetch


@mock_aws
def test_happy_path(mocker, video):
    """A shared link is transferred to S3 via the authenticated resumable transfer."""
    body = os.urandom(6250000)
    mocker.patch(
        "cloudsync.tasks.dropbox_api.stream_shared_link",
        return_value=_dropbox_metadata("video.mp4", len(body)),
    )
    mocker.patch(
        "cloudsync.tasks.dropbox_api.fetch_shared_link_range",
        side_effect=_range_fetcher_for(body),
    )
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket=settings.VIDEO_S3_BUCKET)
    mocker.patch("cloudsync.tasks.upload_lock", _lock_yielding(True))
    mocker.patch("celery.app.task.Task.update_state")

    stream_to_s3(video.id)

    obj = s3.get_object(Bucket=settings.VIDEO_S3_BUCKET, Key=video.get_s3_key())
    assert obj["Body"].read() == body
    assert obj["ContentType"] == "video/mp4"
    assert Video.objects.get(id=video.id).status == VideoStatus.UPLOADING


def test_stream_to_s3_retries_when_locked(mocker, video):
    """When another worker holds the upload lock, the task backs off via retry."""
    mocker.patch(
        "cloudsync.tasks.dropbox_api.stream_shared_link",
        return_value=_dropbox_metadata("video.mp4", 1000),
    )
    mocker.patch("cloudsync.tasks.upload_lock", _lock_yielding(False))
    mocker.patch("celery.app.task.Task.update_state")
    retry = mocker.patch.object(stream_to_s3, "retry", side_effect=Retry)

    with pytest.raises(Retry):
        stream_to_s3(video.id)
    retry.assert_called_once()


@mock_aws
def test_stream_to_s3_marks_failed_on_transfer_error(mocker, video):
    """A transfer error marks the video UPLOAD_FAILED and re-raises."""
    mocker.patch("ui.models.tasks.async_send_notification_email")
    mocker.patch(
        "cloudsync.tasks.dropbox_api.stream_shared_link",
        return_value=_dropbox_metadata("video.mp4", 1000),
    )
    mocker.patch("cloudsync.tasks.upload_lock", _lock_yielding(True))
    mocker.patch("celery.app.task.Task.update_state")
    transfer = mocker.patch("cloudsync.tasks.DropboxToS3Transfer")
    transfer.return_value.run.side_effect = RuntimeError("boom")

    with pytest.raises(RuntimeError):
        stream_to_s3(video.id)
    assert Video.objects.get(id=video.id).status == VideoStatus.UPLOAD_FAILED


def test_upload_failure(mocker, video):
    """Video is marked failed when the authenticated download errors."""
    mocker.patch("ui.models.tasks.async_send_notification_email")
    mock_update = mocker.patch("cloudsync.tasks.stream_to_s3.update_state")
    mocker.patch(
        "cloudsync.tasks.dropbox_api.stream_shared_link",
        side_effect=HTTPError("access denied"),
    )
    mocker.patch("cloudsync.tasks.boto3")
    with pytest.raises(HTTPError):
        stream_to_s3(video.id)
    assert Video.objects.get(id=video.id).status == VideoStatus.UPLOAD_FAILED
    mock_update.assert_called_once()
    assert mock_update.call_args == call(state="FAILURE", task_id=None)


def test_upload_auth_failure(mocker, video):
    """Video is marked failed when Dropbox authentication errors."""
    mocker.patch("ui.models.tasks.async_send_notification_email")
    mock_update = mocker.patch("cloudsync.tasks.stream_to_s3.update_state")
    mocker.patch(
        "cloudsync.tasks.dropbox_api.stream_shared_link",
        side_effect=dropbox_api.DropboxAuthError("token refresh failed"),
    )
    mocker.patch("cloudsync.tasks.boto3")
    with pytest.raises(dropbox_api.DropboxAuthError):
        stream_to_s3(video.id)
    assert Video.objects.get(id=video.id).status == VideoStatus.UPLOAD_FAILED
    mock_update.assert_called_once()
    assert mock_update.call_args == call(state="FAILURE", task_id=None)


@pytest.mark.parametrize(
    "exc",
    [
        requests.Timeout("read timed out"),
        requests.ConnectionError("connection reset"),
    ],
)
def test_upload_network_failure(mocker, video, exc):
    """Video is marked failed when the download raises a network-level error."""
    mocker.patch("ui.models.tasks.async_send_notification_email")
    mock_update = mocker.patch("cloudsync.tasks.stream_to_s3.update_state")
    mocker.patch(
        "cloudsync.tasks.dropbox_api.stream_shared_link",
        side_effect=exc,
    )
    mocker.patch("cloudsync.tasks.boto3")
    with pytest.raises(type(exc)):
        stream_to_s3(video.id)
    assert Video.objects.get(id=video.id).status == VideoStatus.UPLOAD_FAILED
    mock_update.assert_called_once()
    assert mock_update.call_args == call(state="FAILURE", task_id=None)


def test_upload_metadata_failure(mocker, video):
    """Video is marked failed when the Dropbox metadata header is missing."""
    mocker.patch("ui.models.tasks.async_send_notification_email")
    mock_update = mocker.patch("cloudsync.tasks.stream_to_s3.update_state")
    mocker.patch(
        "cloudsync.tasks.dropbox_api.stream_shared_link",
        return_value=SimpleNamespace(headers={}, close=lambda: None),
    )
    mocker.patch("cloudsync.tasks.boto3")
    with pytest.raises(KeyError):
        stream_to_s3(video.id)
    assert Video.objects.get(id=video.id).status == VideoStatus.UPLOAD_FAILED
    mock_update.assert_called_once()
    assert mock_update.call_args == call(state="FAILURE", task_id=None)


def test_transcode_failures(mocker, videofile, mock_transcode, mock_failed_encode_job):
    """
    Test transcode task, verify there is an EncodeJob associated with the video to encode
    """
    video = videofile.video

    # Transcode the video
    with pytest.raises(ClientError):
        transcode_from_s3(video.id)
    assert video.encode_jobs.count() == 1
    assert (
        Video.objects.get(id=video.id).status == VideoStatus.TRANSCODE_FAILED_INTERNAL
    )


def test_retranscode_failures(
    mocker, videofile, mock_transcode, mock_failed_encode_job
):
    """
    Test transcode task, verify there is an EncodeJob associated with the video to encode
    """
    video = videofile.video

    # Retranscode the video
    with pytest.raises(ClientError):
        retranscode_video(video.id)
    assert (
        Video.objects.filter(
            id=video.id,
            status=VideoStatus.RETRANSCODE_FAILED,
            schedule_retranscode=False,
        ).count()
        == 1
    )


def test_transcode_target_does_not_exist():
    """
    Test transcode task, verify exception is thrown when target does not exist.
    """
    nonexistent_video_id = 12345
    with pytest.raises(TranscodeTargetDoesNotExist):
        transcode_from_s3(nonexistent_video_id)


def test_retranscode_target_does_not_exist():
    """
    Test retranscode task, verify exception is thrown when target does not exist.
    """
    nonexistent_video_id = 12345
    with pytest.raises(TranscodeTargetDoesNotExist):
        retranscode_video(nonexistent_video_id)


def test_transcode_starting(
    mocker, videofile, mock_transcode, mock_successful_encode_job
):
    """
    Test that video status is updated properly after a transcode success
    """
    video = videofile.video
    transcode_from_s3(video.id)
    assert video.encode_jobs.count() == 1
    assert (
        Video.objects.filter(
            id=video.id, status=VideoStatus.TRANSCODING, schedule_retranscode=False
        ).count()
        == 1
    )


def test_retranscode_starting(
    mocker, videofile, mock_transcode, mock_successful_encode_job
):
    """
    Test that video status is updated properly after a retranscode success
    """
    video = videofile.video
    retranscode_video(video.id)
    assert (
        Video.objects.filter(id=video.id, status=VideoStatus.RETRANSCODING).count() == 1
    )


def test_video_task_chain(mocker):
    """
    Test that video task get_task_id method returns the correct id from the chain.
    """

    def ctx():
        """Return a mock context object"""
        return celery.app.task.Context(
            {
                "lang": "py",
                "task": "cloudsync.tasks.stream_to_s3",
                "id": "1853b857-84d8-4af4-8b19-1c307c1e07d5",
                "chain": [
                    {
                        "task": "cloudsync.tasks.transcode_from_s3",
                        "args": [351],
                        "kwargs": {},
                        "options": {"task_id": "1a859e5a-8f71-4e01-9349-5ebc6dc66631"},
                    }
                ],
            }
        )

    mocker.patch(
        "cloudsync.tasks.VideoTask.request",
        new_callable=PropertyMock,
        return_value=ctx(),
    )
    task = VideoTask()
    assert task.get_task_id() == task.request.chain[0]["options"]["task_id"]


def test_video_task_bad_chain(mocker):
    """
    Test that video task get_task_id method returns the task.id if the chain is not valid.
    """

    def ctx():
        """Return a mock context object"""
        return celery.app.task.Context(
            {
                "lang": "py",
                "task": "cloudsync.tasks.stream_to_s3",
                "id": "1853b857-84d8-4af4-8b19-1c307c1e07d5",
                "chain": [
                    {
                        "task": "cloudsync.tasks.transcode_from_s3",
                        "args": [351],
                        "kwargs": {},
                        "options": {},
                    }
                ],
            }
        )

    mocker.patch(
        "cloudsync.tasks.VideoTask.request",
        new_callable=PropertyMock,
        return_value=ctx(),
    )
    task = VideoTask()
    assert task.get_task_id() is None


def test_video_task_no_chain(mocker):
    """
    Test that video task get_task_id method returns the task.id if the chain is not present.
    """

    def ctx():
        """Return a mock context object"""
        return celery.app.task.Context(
            {
                "lang": "py",
                "task": "cloudsync.tasks.stream_to_s3",
                "id": "1853b857-84d8-4af4-8b19-1c307c1e07d5",
            }
        )

    mocker.patch(
        "cloudsync.tasks.VideoTask.request",
        new_callable=PropertyMock,
        return_value=ctx(),
    )
    task = VideoTask()
    assert task.get_task_id() == task.request.id


def test_stream_to_s3_no_video():
    """Test DoesNotExistError"""
    with pytest.raises(Video.DoesNotExist):
        stream_to_s3(999999)


@mock_aws
@override_settings(LECTURE_CAPTURE_USER="admin")
def test_monitor_watch(mocker, user):
    """Test the Watch bucket monitor task"""
    UserFactory(username="admin")
    mock_encoder = mocker.patch("cloudsync.api.media_convert_job")
    s3 = boto3.resource("s3")
    s3c = boto3.client("s3")
    filename = "MIT-6.046-2017-Spring-lec-mit-0000-2017apr06-0404-L01.mp4"
    s3c.create_bucket(Bucket=settings.VIDEO_S3_WATCH_BUCKET)
    s3c.create_bucket(Bucket=settings.VIDEO_S3_BUCKET)
    bucket = s3.Bucket(settings.VIDEO_S3_WATCH_BUCKET)
    bucket.upload_fileobj(io.BytesIO(os.urandom(6250000)), filename)
    assert s3c.get_object(Bucket=bucket.name, Key=filename) is not None
    monitor_watch_bucket.delay()
    new_video = Video.objects.get(source_url__endswith=filename)
    new_videofile = new_video.original_video
    mock_encoder.assert_called_once_with(
        new_videofile.s3_object_key,
        destination_prefix=TRANSCODE_PREFIX,
        group_settings={
            "exclude_mp4": True,
            "exclude_thumbnail": False,
        },
        template_path=None,
    )
    assert new_videofile.bucket_name == settings.VIDEO_S3_BUCKET
    with pytest.raises(ClientError):
        s3c.get_object(Bucket=bucket.name, Key=filename)


@mock_aws
@override_settings(LECTURE_CAPTURE_USER="admin")
@pytest.mark.parametrize(
    "filename,unsorted",
    [
        ["MIT-6.046-2017-Spring-lec-mit-0000-2017apr06-0404-L01.mp4", False],
        ["Bad Name.mp4", True],
        ["MIT-6.046-lec-mit-0000-2017apr06-0404.mp4", False],
    ],
)
def test_monitor_watch_badname(mocker, filename, unsorted):
    """
    Test that videos are created for files with good and bad names
    """
    settings.UNSORTED_COLLECTION = "Unsorted"
    user = UserFactory(username="admin")
    mock_encoder = mocker.patch("cloudsync.api.media_convert_job")
    s3 = boto3.resource("s3")
    s3c = boto3.client("s3")
    s3c.create_bucket(Bucket=settings.VIDEO_S3_WATCH_BUCKET)
    s3c.create_bucket(Bucket=settings.VIDEO_S3_BUCKET)
    bucket = s3.Bucket(settings.VIDEO_S3_WATCH_BUCKET)
    bucket.upload_fileobj(io.BytesIO(os.urandom(6250000)), filename)
    monitor_watch_bucket.delay()
    mock_encoder.assert_called_once()
    collection, _ = Collection.objects.get_or_create(
        slug=settings.UNSORTED_COLLECTION, owner=user
    )
    assert collection.videos.filter(title=filename).exists() == unsorted


@pytest.mark.parametrize(
    "source", [StreamSource.CLOUDFRONT, StreamSource.YOUTUBE, None]
)
@pytest.mark.parametrize("max_uploads", [2, 4])
def test_upload_youtube_videos(mocker, source, max_uploads):
    """
    Test that the upload_youtube_videos task calls YouTubeApi.upload_video
    & creates a YoutubeVideo object for each public video, up to the max daily limit
    """
    settings.YT_UPLOAD_LIMIT = max_uploads
    private_videos = VideoFactory.create_batch(
        2, is_public=False, status=VideoStatus.COMPLETE
    )
    VideoFactory.create_batch(
        3,
        collection=CollectionFactory(stream_source=source),
        is_public=True,
        status=VideoStatus.COMPLETE,
    )
    mock_uploader = mocker.patch(
        "cloudsync.tasks.YouTubeApi.upload_video",
        return_value={
            "id": "".join([random.choice(string.ascii_lowercase) for n in range(8)]),
            "status": {"uploadStatus": "uploaded"},
        },
    )
    upload_youtube_videos()
    assert mock_uploader.call_count == (
        min(3, max_uploads) if source == StreamSource.YOUTUBE else 0
    )
    for video in Video.objects.filter(is_public=True).order_by("-created_at")[
        : settings.YT_UPLOAD_LIMIT
    ]:
        if video.collection.stream_source == StreamSource.YOUTUBE:
            assert YouTubeVideo.objects.filter(video=video).first() is not None
        else:
            assert YouTubeVideo.objects.filter(video=video).first() is None
    for video in private_videos:
        assert YouTubeVideo.objects.filter(video=video).first() is None


def test_upload_youtube_videos_error(mocker):
    """
    Test that the YoutubeVideo object is deleted if an error occurs during upload, and all videos are processed
    """
    collection = CollectionFactory(stream_source=StreamSource.YOUTUBE)
    videos = VideoFactory.create_batch(
        3, collection=collection, is_public=True, status=VideoStatus.COMPLETE
    )
    mock_uploader = mocker.patch(
        "cloudsync.tasks.YouTubeApi.upload_video", side_effect=OSError
    )
    upload_youtube_videos()
    assert mock_uploader.call_count == 3
    for video in videos:
        assert YouTubeVideo.objects.filter(video=video).first() is None


@pytest.mark.parametrize("msg", [API_QUOTA_ERROR_MSG, "other error"])
def test_upload_youtube_quota_exceeded(mocker, msg):
    """
    Test that the YoutubeVideo object is deleted if an error occurs during upload,
    and the loop is halted if the quota is exceeded.
    """
    collection = CollectionFactory(stream_source=StreamSource.YOUTUBE)
    videos = VideoFactory.create_batch(
        3, collection=collection, is_public=True, status=VideoStatus.COMPLETE
    )
    mock_uploader = mocker.patch(
        "cloudsync.tasks.YouTubeApi.upload_video",
        side_effect=ResumableUploadError(
            MockHttpErrorResponse(403), str.encode(msg, "utf-8")
        ),
    )
    upload_youtube_videos()
    assert mock_uploader.call_count == (1 if msg == API_QUOTA_ERROR_MSG else 3)
    for video in videos:
        assert YouTubeVideo.objects.filter(video=video).first() is None


def test_remove_youtube_video(mocker, public_video):
    """
    Test that the remove_youtube_video task calls YouTubeApi.delete_video
    """
    mock_delete = mocker.patch("cloudsync.tasks.YouTubeApi.delete_video")
    yt_video = YouTubeVideoFactory(video=public_video)
    remove_youtube_video(yt_video.id)
    mock_delete.assert_called_once_with(yt_video.id)


def test_remove_youtube_video_404(mocker, public_video):
    """
    Test that the remove_youtube_video task does not raise an exception if a 404 error occurs
    """
    mock_delete = mocker.patch(
        "cloudsync.tasks.YouTubeApi.delete_video",
        side_effect=HttpError(MockHttpErrorResponse(404), b""),
    )
    yt_video = YouTubeVideoFactory(video=public_video)
    remove_youtube_video(yt_video.id)
    mock_delete.assert_called_once_with(yt_video.id)


def test_remove_youtube_video_500(mocker, public_video):
    """
    Test that the remove_youtube_video task raises an exception if a 500 error occurs
    """
    mocker.patch(
        "cloudsync.tasks.YouTubeApi.delete_video",
        side_effect=HttpError(MockHttpErrorResponse(500), b""),
    )
    yt_video = YouTubeVideoFactory(video=public_video)
    with pytest.raises(HttpError):
        remove_youtube_video(yt_video.id)


def test_upload_youtube_caption(mocker, public_video):
    """
    Test that the upload_youtube_caption task calls YouTubeApi.upload_caption with correct arguments
    """
    mocker.patch("cloudsync.tasks.YouTubeApi.upload_video")
    mock_uploader = mocker.patch("cloudsync.tasks.YouTubeApi.upload_caption")
    subtitle = VideoSubtitleFactory(video=public_video)
    yt_video = YouTubeVideoFactory(video=public_video)
    upload_youtube_caption(subtitle.id)
    mock_uploader.assert_called_once_with(subtitle, yt_video.id)


def test_remove_youtube_caption(mocker, public_video):
    """
    Test that the upload_youtube_caption task calls YouTubeApi.upload_caption with correct arguments,
    and only for language captions that actually exist on Youtube
    """
    mock_delete = mocker.patch("cloudsync.tasks.YouTubeApi.delete_caption")
    mocker.patch(
        "cloudsync.tasks.YouTubeApi.list_captions",
        return_value={"fr": "foo", "en": "bar"},
    )
    YouTubeVideoFactory(video=public_video)
    VideoSubtitleFactory(video=public_video, language="en")
    VideoSubtitleFactory(video=public_video, language="fr")
    remove_youtube_caption(public_video.id, "fr")
    remove_youtube_caption(public_video.id, "zh")
    mock_delete.assert_called_once_with("foo")


def test_update_youtube_statuses(mocker):
    """
    Test that the correct number of YouTubeVideo objects have their statuses updated to the correct value
    and captions are uploaded for them.
    """
    mock_uploader = mocker.patch("cloudsync.tasks.YouTubeApi.upload_caption")
    mocker.patch(
        "cloudsync.tasks.YouTubeApi.video_status", return_value=YouTubeStatus.PROCESSED
    )
    processing_videos = YouTubeVideoFactory.create_batch(
        2, status=YouTubeStatus.UPLOADED
    )
    completed_videos = YouTubeVideoFactory.create_batch(
        3, status=YouTubeStatus.PROCESSED
    )
    for yt_video in processing_videos + completed_videos:
        VideoSubtitleFactory(video=yt_video.video)
    update_youtube_statuses()
    assert mock_uploader.call_count == 2
    assert YouTubeVideo.objects.filter(status=YouTubeStatus.PROCESSED).count() == 5


def test_update_youtube_statuses_api_quota_exceeded(mocker):
    """
    Test that the update_youtube_statuses task stops without raising an error if the API quota is exceeded.
    """
    mock_video_status = mocker.patch(
        "cloudsync.tasks.YouTubeApi.video_status",
        side_effect=HttpError(
            MockHttpErrorResponse(403), str.encode(API_QUOTA_ERROR_MSG, "utf-8")
        ),
    )
    YouTubeVideoFactory.create_batch(3, status=YouTubeStatus.UPLOADED)
    update_youtube_statuses()
    mock_video_status.assert_called_once()


def test_update_youtube_statuses_error(mocker):
    """
    Test that an error is raised if any error occurs other than exceeding daily API quota
    """
    mock_video_status = mocker.patch(
        "cloudsync.tasks.YouTubeApi.video_status",
        side_effect=HttpError(MockHttpErrorResponse(403), b"other error"),
    )
    YouTubeVideoFactory.create_batch(3, status=YouTubeStatus.UPLOADED)
    with pytest.raises(HttpError):
        update_youtube_statuses()
    mock_video_status.assert_called_once()


def test_update_youtube_statuses_dupe(mocker):
    """
    Test that the status of a potential dupe video is saved as 'failed'
    """
    mock_video_status = mocker.patch(
        "cloudsync.tasks.YouTubeApi.video_status",
        side_effect=[IndexError, YouTubeStatus.PROCESSED, YouTubeStatus.UPLOADED],
    )
    YouTubeVideoFactory.create_batch(3, status=YouTubeStatus.UPLOADED)
    update_youtube_statuses()
    assert mock_video_status.call_count == 3
    for status in [
        YouTubeStatus.FAILED,
        YouTubeStatus.PROCESSED,
        YouTubeStatus.UPLOADED,
    ]:
        assert len(YouTubeVideo.objects.filter(status=status).all()) == 1


def test_update_youtube_statuses_failed(mocker):
    """
    Test that the correct number of YouTubeVideo objects have their statuses updated to FAILED
    and no captions are uploaded.
    """
    mock_uploader = mocker.patch("cloudsync.tasks.YouTubeApi.upload_caption")
    mocker.patch(
        "cloudsync.tasks.YouTubeApi.video_status", return_value=YouTubeStatus.FAILED
    )
    processing_videos = YouTubeVideoFactory.create_batch(
        2, status=YouTubeStatus.UPLOADED
    )
    for yt_video in processing_videos:
        VideoSubtitleFactory(video=yt_video.video)
    update_youtube_statuses()
    assert mock_uploader.call_count == 0
    assert YouTubeVideo.objects.filter(status=YouTubeStatus.FAILED).count() == 2


def test_schedule_retranscodes(
    mocker, mock_transcode, mock_successful_encode_job, mocked_celery
):
    """
    Test that schedule_retranscodes triggers retranscode_video tasks for each scheduled video
    """
    retranscode_video_mock = mocker.patch(
        "cloudsync.tasks.retranscode_video", autospec=True
    )
    collection = CollectionFactory.create(schedule_retranscode=True)
    scheduled_videos = VideoFactory.create_batch(5, schedule_retranscode=True)
    VideoFactory.create_batch(3, schedule_retranscode=False)
    with pytest.raises(mocked_celery.replace_exception_class):
        schedule_retranscodes.delay()
    assert mocked_celery.group.call_count == 1
    assert retranscode_video_mock.si.call_count == len(scheduled_videos)
    for video in scheduled_videos:
        retranscode_video_mock.si.assert_any_call(video.id)
    assert Collection.objects.get(id=collection.id).schedule_retranscode is False


def test_no_scheduled_retranscodes(mocked_celery):
    """
    Test that schedule_retranscodes doesn't raise a replacement if no videos need a retranscode
    """
    schedule_retranscodes.delay()
    assert mocked_celery.group.call_count == 0


def test_schedule_retranscodes_error(mocker, mocked_celery):
    """
    Test that schedule_retranscodes logs an error if it occurs
    """
    mock_error_log = mocker.patch("cloudsync.tasks.log.exception")
    mocker.patch("cloudsync.tasks.retranscode_video.si", side_effect=ClientError)
    VideoFactory.create_batch(5, schedule_retranscode=True)
    schedule_retranscodes.delay()
    mock_error_log.assert_called_with("schedule_retranscodes threw an error")


@mock_aws
def test_sort_transcoded_m3u8_files(mocker):
    """
    Test that sort_transcoded_m3u8_files changes the m3u8 file on s3 if it needs to be sorted
    """
    s3c = boto3.client("s3")

    bucket_name = "MYBUCKET"
    s3c.create_bucket(Bucket=bucket_name)
    mocker.patch("cloudsync.tasks.settings.VIDEO_S3_TRANSCODE_BUCKET", bucket_name)

    file_key = "key"
    file_body = """
#EXTM3U
#EXT-X-STREAM-INF:PROGRAM-ID=1,BANDWIDTH=2723000,RESOLUTION=1280x720,CODECS="avc1.4d001f,mp4a.40.2"
video_1504127981867-06dkm6.m3u8
#EXT-X-STREAM-INF:PROGRAM-ID=1,BANDWIDTH=4881000,RESOLUTION=1920x1080,CODECS="avc1.4d001f,mp4a.40.2"
video_1504127981921-c2jlwt.m3u8
#EXT-X-STREAM-INF:PROGRAM-ID=1,BANDWIDTH=2723000,RESOLUTION=1920x1080,CODECS="avc1.4d001f,mp4a.40.2"
video_1504127981921-c2jlwt.m3u8
"""
    s3c.put_object(Body=file_body, Bucket=bucket_name, Key=file_key)
    VideoFileFactory(s3_object_key=file_key, encoding="HLS")

    already_sorted_file_key = "already_sorted"
    already_sorted_file_body = """
#EXTM3U
#EXT-X-STREAM-INF:PROGRAM-ID=1,BANDWIDTH=4881000,RESOLUTION=1920x1080,CODECS="avc1.4d001f,mp4a.40.2"
video_1604127981921-c2jlwt.m3u8
#EXT-X-STREAM-INF:PROGRAM-ID=1,BANDWIDTH=2723000,RESOLUTION=1280x720,CODECS="avc1.4d001f,mp4a.40.2"
video_1604127981867-06dkm6.m3u8
"""
    s3c.put_object(
        Body=already_sorted_file_body, Bucket=bucket_name, Key=already_sorted_file_key
    )
    VideoFileFactory(s3_object_key=already_sorted_file_key, encoding="HLS")

    invalid_header_file_key = "invalid_header"
    invalid_header_file_body = """
invalid_header
#EXT-X-STREAM-INF:PROGRAM-ID=1,BANDWIDTH=2723000,RESOLUTION=1280x720,CODECS="avc1.4d001f,mp4a.40.2"
video_1504127981867-06dkm6.m3u8
"""
    s3c.put_object(
        Body=invalid_header_file_body, Bucket=bucket_name, Key=invalid_header_file_key
    )
    VideoFileFactory(s3_object_key=invalid_header_file_key, encoding="HLS")

    invalid_content_file_key = "invalid_content"
    invalid_content_file_body = """
#EXTM3U
#EXT-X-STREAM-INF: No
#EXT-X-STREAM-INF: RESOLUTIONS
"""
    s3c.put_object(
        Body=invalid_content_file_body, Bucket=bucket_name, Key=invalid_content_file_key
    )
    VideoFileFactory(s3_object_key=invalid_content_file_key, encoding="HLS")

    # The task should not raise an error if a VideoFile hase a s3_object_key without a corresponding
    # file on s3
    VideoFileFactory(s3_object_key="not a valid key", encoding="HLS")

    sort_transcoded_m3u8_files()

    expected_file_body = """
#EXTM3U
#EXT-X-STREAM-INF:PROGRAM-ID=1,BANDWIDTH=4881000,RESOLUTION=1920x1080,CODECS="avc1.4d001f,mp4a.40.2"
video_1504127981921-c2jlwt.m3u8
#EXT-X-STREAM-INF:PROGRAM-ID=1,BANDWIDTH=2723000,RESOLUTION=1920x1080,CODECS="avc1.4d001f,mp4a.40.2"
video_1504127981921-c2jlwt.m3u8
#EXT-X-STREAM-INF:PROGRAM-ID=1,BANDWIDTH=2723000,RESOLUTION=1280x720,CODECS="avc1.4d001f,mp4a.40.2"
video_1504127981867-06dkm6.m3u8
"""
    updated_file = s3c.get_object(Bucket=bucket_name, Key=file_key)
    assert updated_file["Body"].read().decode() == expected_file_body

    already_sorted_file = s3c.get_object(
        Bucket=bucket_name, Key=already_sorted_file_key
    )
    assert already_sorted_file["Body"].read().decode() == already_sorted_file_body

    invalid_header_file = s3c.get_object(
        Bucket=bucket_name, Key=invalid_header_file_key
    )
    assert invalid_header_file["Body"].read().decode() == invalid_header_file_body

    invalid_content_file = s3c.get_object(
        Bucket=bucket_name, Key=invalid_content_file_key
    )
    assert invalid_content_file["Body"].read().decode() == invalid_content_file_body
