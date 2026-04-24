"""
Tests for api
"""

import io
import os
from datetime import datetime
from types import SimpleNamespace
import uuid

import boto3
import pytest
from botocore.exceptions import ClientError
from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from django.test import override_settings
from moto import mock_aws
from PIL import Image

from cloudsync import api
from cloudsync.api import (
    RETRANSCODE_FOLDER,
    convert_image_to_jpeg,
    create_thumbnail_in_s3,
    move_s3_objects,
    replace_thumbnail_in_s3,
    upload_subtitle_to_s3,
)
from cloudsync.conftest import MockBoto, MockClientMC
from ui.constants import VideoStatus
from ui.factories import (
    EncodeJobFactory,
    UserFactory,
    VideoFactory,
    VideoFileFactory,
    VideoSubtitleFactory,
    VideoThumbnailFactory,
)
from ui.models import TRANSCODE_PREFIX, Video

pytestmark = pytest.mark.django_db


@pytest.fixture()
def video():
    """Fixture to create a video"""
    return VideoFactory()


@pytest.fixture()
def videofile():
    """Fixture to create a videofile"""
    return VideoFileFactory()


@pytest.fixture
def file_object():
    """
    Fixture for tests requiring a file object
    """
    filename = "subtitles.vtt"
    file_data = SimpleUploadedFile(filename, bytes(1024))
    return SimpleNamespace(name=filename, data=file_data)


def test_get_error_type_from_et_erro():
    """
    Tests get_error_type_from_et_error
    """
    # weird strings
    for str_error in (
        "",
        None,
        "foo",
        "1234foo",
    ):
        assert (
            api.get_error_type_from_et_error(str_error)
            == VideoStatus.TRANSCODE_FAILED_INTERNAL
        )

    # actual error like string that should be an internal error
    assert (
        api.get_error_type_from_et_error("1234 this is an internal error")
        == VideoStatus.TRANSCODE_FAILED_INTERNAL
    )

    # actual error like string that should be a video error
    assert (
        api.get_error_type_from_et_error("4123 this is a video error")
        == VideoStatus.TRANSCODE_FAILED_VIDEO
    )


@pytest.mark.parametrize(
    "prior_status, error_status",
    [
        [VideoStatus.TRANSCODING, VideoStatus.TRANSCODE_FAILED_VIDEO],
        [VideoStatus.RETRANSCODING, VideoStatus.RETRANSCODE_FAILED],
    ],
)
def test_refresh_status_video_job_status_error(mocker, prior_status, error_status):
    """
    Verify that Video.job_status property returns the status of its encoding job
    """
    video = VideoFactory(status=prior_status)
    encodejob = EncodeJobFactory(video=video)
    MockClientMC.job = {
        "Job": {
            "Id": "1498220566931-qtmtcu",
            "Status": "Error",
        }
    }
    mocker.patch("cloudsync.api.boto3", MockBoto)
    mocker.patch("ui.models.tasks")
    api.refresh_status(video, encodejob)
    assert video.status == error_status


@pytest.mark.parametrize("status", [VideoStatus.TRANSCODING, VideoStatus.RETRANSCODING])
def test_refresh_status_video_job_status_complete(mocker, status):
    """
    Verify that Video.job_status property returns the status of its encoding job
    """
    video = VideoFactory(status=status)
    VideoFileFactory(video=video)
    encodejob = EncodeJobFactory(video=video)
    MockClientMC.job = {"Job": {"Id": "1498220566931-qtmtcu", "Status": "Complete"}}
    mocker.patch("cloudsync.api.boto3", MockBoto)
    mocker.patch(
        "cloudsync.api.process_transcode_results",
        side_effect=lambda results: video.update_status(VideoStatus.COMPLETE),
    )
    mocker.patch("ui.models.tasks")
    api.refresh_status(video, encodejob)
    assert video.status == VideoStatus.COMPLETE


@pytest.mark.parametrize("status", [VideoStatus.TRANSCODING, VideoStatus.RETRANSCODING])
def test_refresh_status_video_job_othererror(mocker, status):
    """
    Verify that refresh_status does not raise ClientError
    """
    video = VideoFactory(status=status)
    VideoFileFactory(video=video)
    EncodeJobFactory(video=video)
    video.status = VideoStatus.TRANSCODING
    mocker.patch("cloudsync.api.boto3", MockBoto)
    error = Exception("unexpected exception")
    mocker.patch(
        "cloudsync.api.get_media_convert_job", return_value=MockClientMC(error=error)
    )
    with pytest.raises(Exception):
        api.refresh_status(video)


@pytest.mark.parametrize(
    "course_prefix, session, date_str, expected_record_date",
    [
        ("MIT-6.046-2017-Spring", "L01", "2017apr06", datetime(2017, 4, 6)),
        ("abcdefg", "L01", "2017apr06", datetime(2017, 4, 6)),
        ("MIT-6.046-2017-Spring", None, "2017apr06", datetime(2017, 4, 6)),
        ("MIT-6.046-2017-Spring", "2-190", "2017apr06", datetime(2017, 4, 6)),
        ("/&*3:<>俺正和", None, "2017apr06", datetime(2017, 4, 6)),
        ("abcdefg", None, "2017badmonthvalue06", None),
    ],
)
def test_parse_lecture_video_filename(
    course_prefix, session, date_str, expected_record_date
):
    """
    Test that a tuple of video attributes title is correctly parsed for a video file.
    """
    filename = "{}-lec-mit-0000-{}-0404{}.mp4".format(
        course_prefix, date_str, "" if not session else "-{}".format(session)
    )
    expected_parsed_attrs = api.ParsedVideoAttributes(
        prefix=course_prefix,
        session=session,
        record_date=expected_record_date,
        record_date_str=date_str,
        name=filename,
    )
    assert api.parse_lecture_video_filename(filename) == expected_parsed_attrs


@pytest.mark.parametrize(
    "filename",
    [
        "MIT-6.046-1510-L01.mp4",  # Missing -lec-mit-0000
        "Completely random name.mp4",  # No similarity to expected format
        "MIT-6.046-lec-mit-0000-2017apr06-L01",  # no extension
    ],
)
def test_parse_lecture_video_filename_failure(filename):
    """
    Test failure cases for parsing a lecture video filename
    """
    settings.UNSORTED_COLLECTION = "Unsorted"
    attributes = api.parse_lecture_video_filename(filename)
    assert attributes.prefix == settings.UNSORTED_COLLECTION
    assert attributes.record_date is None


@mock_aws
@override_settings(LECTURE_CAPTURE_USER="admin")
def test_watch_nouser():
    """
    Test that an exception is correctly handled when the LECTURE_CAPTURE_USER doesn't exist
    """
    s3 = boto3.resource("s3")
    s3c = boto3.client("s3")
    filename = "MIT-6.046-2017-Spring-lec-mit-0000-2017apr06-0404-L01.mp4"
    s3c.create_bucket(Bucket=settings.VIDEO_S3_WATCH_BUCKET)
    bucket = s3.Bucket(settings.VIDEO_S3_WATCH_BUCKET)
    bucket.upload_fileobj(io.BytesIO(os.urandom(6250000)), filename)
    with pytest.raises(User.DoesNotExist):
        api.process_watch_file(filename)
    assert not Video.objects.filter(title=filename).exists()


@mock_aws
@override_settings(LECTURE_CAPTURE_USER="admin")
def test_watch_s3_error():
    """Test that an AWS S3 ClientError is correctly handled"""
    UserFactory(username="admin")
    s3 = boto3.resource("s3")
    s3c = boto3.client("s3")
    filename = "MIT-6.046-2017-Spring-lec-mit-0000-2017apr06-0404-L01.mp4"
    s3c.create_bucket(Bucket=settings.VIDEO_S3_WATCH_BUCKET)
    bucket = s3.Bucket(settings.VIDEO_S3_WATCH_BUCKET)
    bucket.upload_fileobj(io.BytesIO(os.urandom(6250000)), filename)
    with transaction.atomic():
        with pytest.raises(ClientError):
            api.process_watch_file(filename)
    assert not Video.objects.filter(title=filename).exists()


@mock_aws
@override_settings(LECTURE_CAPTURE_USER="admin")
def test_watch_filename_error(mocker):
    """Test that a video with a bad filename is moved to the 'Unsorted' collection"""
    settings.UNSORTED_COLLECTION = "Unsorted"
    # Mock media_convert_job to return a dict with Job ID
    mock_job = {"Job": {"Id": str(uuid.uuid4())}}
    mocker.patch("cloudsync.api.media_convert_job", return_value=mock_job)
    UserFactory(username="admin")
    s3 = boto3.resource("s3")
    s3c = boto3.client("s3")
    filename = "Bad filename.mp4"
    s3c.create_bucket(Bucket=settings.VIDEO_S3_WATCH_BUCKET)
    s3c.create_bucket(Bucket=settings.VIDEO_S3_BUCKET)
    bucket = s3.Bucket(settings.VIDEO_S3_WATCH_BUCKET)
    bucket.upload_fileobj(io.BytesIO(os.urandom(6250000)), filename)
    api.process_watch_file(filename)
    video = Video.objects.get(title=filename)
    assert video.collection.title == settings.UNSORTED_COLLECTION


@mock_aws
@override_settings(LECTURE_CAPTURE_USER="admin")
def test_process_watch(mocker):
    """Test that a file with valid filename is processed"""
    # Mock media_convert_job to return a dict with Job ID
    mock_job = {"Job": {"Id": str(uuid.uuid4())}}
    mock_encoder = mocker.patch(
        "cloudsync.api.media_convert_job", return_value=mock_job
    )
    mocker.patch(
        "cloudsync.api.create_lecture_collection_slug", return_value="COLLECTION TITLE"
    )
    mocker.patch("cloudsync.api.create_lecture_video_title", return_value="VIDEO TITLE")
    UserFactory(username="admin")
    s3 = boto3.resource("s3")
    s3c = boto3.client("s3")
    filename = "MIT-6.046-2017-Spring-lec-mit-0000-2017apr06-0404-L01.mp4"
    s3c.create_bucket(Bucket=settings.VIDEO_S3_WATCH_BUCKET)
    s3c.create_bucket(Bucket=settings.VIDEO_S3_BUCKET)
    bucket = s3.Bucket(settings.VIDEO_S3_WATCH_BUCKET)
    bucket.upload_fileobj(io.BytesIO(os.urandom(6250000)), filename)
    api.process_watch_file(filename)
    new_video = Video.objects.filter(source_url__endswith=filename).first()
    assert new_video is not None
    assert new_video.title == "VIDEO TITLE"
    assert new_video.collection.slug == "COLLECTION TITLE"
    assert new_video.collection.title == "COLLECTION TITLE"
    videofile = new_video.videofile_set.first()
    mock_encoder.assert_called_once_with(
        videofile.s3_object_key,
        destination_prefix=TRANSCODE_PREFIX,
        group_settings={
            "exclude_mp4": True,
            "exclude_thumbnail": False,
        },
    )


def test_lecture_collection_slug():
    """Tests for create_lecture_collection_slug"""
    video_attrs = api.ParsedVideoAttributes(
        prefix="Prefix",
        session="Session",
        record_date=None,
        record_date_str="",
        name="MIT-0.000-2020-Fall-lec-mit-0000-2020sep28-0000-L09.mp4",
    )
    assert api.create_lecture_collection_slug(video_attrs) == "Prefix-Session"
    video_attrs_no_session = api.ParsedVideoAttributes(
        prefix="Prefix",
        session=None,
        record_date=None,
        record_date_str="",
        name="MIT-0.000-2020-Fall-lec-mit-0000-2020sep28-0000-L09.mp4",
    )
    assert api.create_lecture_collection_slug(video_attrs_no_session) == "Prefix"


def test_lecture_video_title():
    """Tests for create_lecture_video_slug"""
    video_attrs = api.ParsedVideoAttributes(
        record_date=datetime(2017, 1, 1),
        record_date_str="2017jan01",
        prefix="Prefix",
        session="Session",
        name="MIT-0.000-2020-Fall-lec-mit-0000-2020sep28-0000-L09.mp4",
    )
    assert api.create_lecture_video_title(video_attrs) == "Lecture - January 01, 2017"
    video_attrs_no_date = api.ParsedVideoAttributes(
        record_date=None,
        record_date_str="2017jan01",
        prefix="Prefix",
        session="Session",
        name="MIT-0.000-2020-Fall-lec-mit-0000-2020sep28-0000-L09.mp4",
    )
    assert api.create_lecture_video_title(video_attrs_no_date) == "Lecture - 2017jan01"


@pytest.mark.parametrize(
    "status,expected_status,exclude_thumbnail",
    [
        [VideoStatus.UPLOADING, VideoStatus.TRANSCODING, False],
        [VideoStatus.RETRANSCODE_SCHEDULED, VideoStatus.RETRANSCODING, True],
    ],
)
def test_transcode_job(mocker, status, expected_status, exclude_thumbnail):
    """
    Test that video status is updated properly after a transcode job is successfully created
    """
    video = VideoFactory.create(status=status)
    videofile = VideoFileFactory.create(video=video)

    prefix = (
        RETRANSCODE_FOLDER + TRANSCODE_PREFIX
        if status == VideoStatus.RETRANSCODE_SCHEDULED
        else TRANSCODE_PREFIX
    )

    # Mock media_convert_job to return a dict with Job ID
    mock_job = {"Job": {"Id": str(uuid.uuid4())}}
    mock_encoder = mocker.patch(
        "cloudsync.api.media_convert_job", return_value=mock_job
    )
    mock_delete_objects = mocker.patch("cloudsync.api.delete_s3_objects")
    mocker.patch("ui.models.tasks")

    api.transcode_video(video, videofile)
    mock_encoder.assert_called_once_with(
        videofile.s3_object_key,
        destination_prefix=prefix,
        group_settings={
            "exclude_mp4": True,
            "exclude_thumbnail": exclude_thumbnail,
        },
    )
    assert len(video.encode_jobs.all()) == 1
    assert mock_delete_objects.call_count == (
        1 if status == VideoStatus.RETRANSCODE_SCHEDULED else 0
    )
    assert Video.objects.get(id=video.id).status == expected_status


@pytest.mark.parametrize(
    "status,error_status,exclude_thumbnail",
    [
        [VideoStatus.TRANSCODING, VideoStatus.TRANSCODE_FAILED_INTERNAL, False],
        [VideoStatus.RETRANSCODE_SCHEDULED, VideoStatus.RETRANSCODE_FAILED, True],
    ],
)
def test_transcode_job_failure(mocker, status, error_status, exclude_thumbnail):
    """
    Test that video status is updated properly after a transcode or retranscode job creation fails
    """
    mocker.patch("cloudsync.api.delete_s3_objects")
    video = VideoFactory.create(status=status)
    videofile = VideoFileFactory.create(video=video)

    job_result = {
        "Job": {"Id": "1498220566931-qtmtcu", "Status": "Error"},
        "Error": {"Code": 200, "Message": "FAIL"},
    }
    mocker.patch("ui.models.tasks")
    mock_encoder = mocker.patch(
        "cloudsync.api.media_convert_job",
        side_effect=ClientError(error_response=job_result, operation_name="job"),
    )
    with pytest.raises(ClientError):
        api.transcode_video(video, videofile)

    prefix = TRANSCODE_PREFIX
    if status == VideoStatus.RETRANSCODE_SCHEDULED:
        prefix = RETRANSCODE_FOLDER + TRANSCODE_PREFIX

    mock_encoder.assert_called_once_with(
        videofile.s3_object_key,
        destination_prefix=prefix,
        group_settings={"exclude_mp4": True, "exclude_thumbnail": exclude_thumbnail},
    )
    assert len(video.encode_jobs.all()) == 1
    assert Video.objects.get(id=video.id).status == error_status


@pytest.mark.parametrize("replace", [True, False])
@pytest.mark.parametrize("s3error", [True, False])
def test_upload_subtitle_to_s3(mocker, video, file_object, replace, s3error):
    """
    Test that a VideoSubtitle object is returned after a .vtt upload to S3
    """
    mocker.patch("cloudsync.api.boto3")
    mock_s3delete = mocker.patch(
        "ui.models.VideoS3.delete_from_s3",
        side_effect=(
            None
            if not s3error
            else ClientError(
                error_response={
                    "Job": {"Id": "1498220566931-qtmtcu", "Status": "Error"},
                    "Error": {"Code": 200, "Message": "FAIL"},
                },
                operation_name="DeleteObject",
            )
        ),
    )
    if replace:
        VideoSubtitleFactory.create(video=video)
    subtitle_data = {
        "video": video.hexkey,
        "language": "en",
        "filename": file_object.name,
    }
    subtitle = upload_subtitle_to_s3(subtitle_data, file_object.data)
    assert mock_s3delete.call_count == (1 if replace else 0)
    assert subtitle.filename == file_object.name
    assert subtitle.video == video
    assert subtitle.language == "en"


def test_upload_subtitle_to_s3_no_video(mocker, file_object):
    """
    Test that a VideoSubtitle object is not returned with .vtt upload to S3 missing video key
    """
    mocker.patch("cloudsync.api.boto3")
    subtitle_data = {"video": None, "language": "en", "filename": file_object.name}
    assert upload_subtitle_to_s3(subtitle_data, file_object.data) is None


def test_upload_subtitle_to_s3_bad_video(mocker, file_object):
    """
    Test that a VideoSubtitle object raises Exception after a .vtt upload to S3 with nonexistent video key
    """
    mocker.patch("cloudsync.api.boto3")
    subtitle_data = {
        "video": "12345678123456781234567812345678",
        "language": "en",
        "filename": file_object.name,
    }
    with pytest.raises(Video.DoesNotExist):
        upload_subtitle_to_s3(subtitle_data, file_object.data)


@pytest.mark.parametrize("replace", [True, False])
@pytest.mark.parametrize("s3error", [True, False])
def test_upload_subtitle_to_s3_srt(mocker, video, file_object, replace, s3error):
    """
    Test that a VideoSubtitle object is returned after a .srt upload to S3
    """
    mocker.patch("cloudsync.api.boto3")
    mock_s3delete = mocker.patch(
        "ui.models.VideoS3.delete_from_s3",
        side_effect=(
            None
            if not s3error
            else ClientError(
                error_response={
                    "Job": {"Id": "1498220566931-qtmtcu", "Status": "Error"},
                    "Error": {"Code": 200, "Message": "FAIL"},
                },
                operation_name="DeleteObject",
            )
        ),
    )
    if replace:
        VideoSubtitleFactory.create(video=video)
    subtitle_data = {
        "video": video.hexkey,
        "language": "en",
        "filename": "subtitles.srt",
    }
    subtitle = upload_subtitle_to_s3(subtitle_data, file_object.data)
    assert mock_s3delete.call_count == (1 if replace else 0)
    assert subtitle.filename == "subtitles.srt"
    assert subtitle.video == video
    assert subtitle.language == "en"
    # SRT is converted to VTT before upload, so the S3 key should have .vtt extension
    assert subtitle.s3_object_key.endswith(".vtt")


@mock_aws
def test_move_s3_objects():
    """
    Test that move_s3_objects changes the S3 object keys to expected values
    """
    s3 = boto3.resource("s3")
    s3c = boto3.client("s3")
    bucket_name = "MYBUCKET"
    filename = "MYFILE"
    from_prefix = "fromtest/"
    to_prefix = "totest/"
    s3c.create_bucket(Bucket=bucket_name)
    bucket = s3.Bucket(bucket_name)
    bucket.upload_fileobj(io.BytesIO(os.urandom(6250000)), f"{from_prefix}{filename}")

    bucket_keys = [obj.key for obj in bucket.objects.all()]
    assert f"{from_prefix}{filename}" in bucket_keys
    assert f"{to_prefix}{filename}" not in bucket_keys

    move_s3_objects(bucket_name, from_prefix, to_prefix)

    bucket_keys = [obj.key for obj in bucket.objects.all()]
    assert f"{from_prefix}{filename}" not in bucket_keys
    assert f"{to_prefix}{filename}" in bucket_keys


@mock_aws
def test_transcode_video_client_error_no_job_id(mocker):
    """
    Test that when ClientError is raised without a job ID in response,
    the job_id used is the one we generated with uuid4
    """

    video = VideoFactory.create(status=VideoStatus.UPLOADING)
    video_file = VideoFileFactory.create(video=video)

    # Mock uuid4 to return a known value
    mock_uuid = "test-uuid-1234"
    mocker.patch("cloudsync.api.uuid4", return_value=mock_uuid)
    mocker.patch("cloudsync.api.delete_s3_objects")
    mocker.patch("ui.models.tasks")

    # Create a ClientError without Job ID in response
    error_response = {
        "Error": {"Code": "InvalidParameter", "Message": "Invalid parameter value"}
    }
    mock_client_error = ClientError(
        error_response=error_response, operation_name="CreateJob"
    )
    # Mock media_convert_job to raise our ClientError
    mocker.patch("cloudsync.api.media_convert_job", side_effect=mock_client_error)

    # Execute the function and catch the expected exception
    with pytest.raises(ClientError):
        api.transcode_video(video, video_file)

    # Verify that an EncodeJob was created with our uuid
    assert len(video.encode_jobs.all()) == 1
    encode_job = video.encode_jobs.first()
    assert encode_job.id == mock_uuid
    assert encode_job.object_id == video.pk
    assert encode_job.message == error_response

    # Verify video status was updated
    video.refresh_from_db()
    assert video.status == VideoStatus.TRANSCODE_FAILED_INTERNAL


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_jpeg_file():
    """
    Return a minimal in-memory JPEG file-like object using PIL.
    """
    buf = io.BytesIO()
    Image.new("RGB", (640, 480), color=(255, 0, 0)).save(buf, format="JPEG")
    buf.seek(0)
    return buf


def _make_png_file():
    """
    Return a minimal in-memory PNG file-like object using PIL.
    """
    buf = io.BytesIO()
    Image.new("RGBA", (640, 480), color=(0, 128, 255, 200)).save(buf, format="PNG")
    buf.seek(0)
    return buf


def _make_bilevel_png_file():
    """
    Return a minimal 1-bit (bilevel) PNG file-like object using PIL.
    Mode '1' is not directly JPEG-compatible and triggered the OSError bug.
    """
    buf = io.BytesIO()
    Image.new("1", (2, 2)).save(buf, format="PNG")
    buf.seek(0)
    return buf


# ---------------------------------------------------------------------------
# Tests for replace_thumbnail_in_s3
# ---------------------------------------------------------------------------


@mock_aws
def test_replace_thumbnail_in_s3_updates_s3_and_model():
    """
    Happy path: the S3 object is overwritten and the thumbnail dimensions are updated.
    """
    s3c = boto3.client("s3", region_name="us-east-1")
    thumbnail = VideoThumbnailFactory(
        s3_object_key="thumbnails/abc/thumb.jpg",
        bucket_name="thumb-bucket",
        max_width=100,
        max_height=100,
    )
    s3c.create_bucket(Bucket="thumb-bucket")

    new_image = _make_jpeg_file()
    replace_thumbnail_in_s3(thumbnail, new_image)

    # Dimensions must be written back to the model
    thumbnail.refresh_from_db()
    assert thumbnail.max_width == 640
    assert thumbnail.max_height == 480

    # The object must exist in S3 under the same key
    obj = s3c.get_object(Bucket="thumb-bucket", Key="thumbnails/abc/thumb.jpg")
    assert obj["ResponseMetadata"]["HTTPStatusCode"] == 200


@mock_aws
@override_settings(VIDEO_CLOUDFRONT_DIST="EDIST123")
def test_replace_thumbnail_in_s3_invalidates_cloudfront(mocker):
    """
    When VIDEO_CLOUDFRONT_DIST is set, a CloudFront invalidation is issued.
    """
    mock_cf = mocker.MagicMock()
    mock_boto3 = mocker.patch("cloudsync.api.boto3")
    # resource("s3").Bucket(...).upload_fileobj must not raise
    mock_boto3.resource.return_value.Bucket.return_value.upload_fileobj.return_value = (
        None
    )
    mock_boto3.client.return_value = mock_cf

    thumbnail = VideoThumbnailFactory(
        s3_object_key="thumbnails/abc/thumb.jpg",
        bucket_name="thumb-bucket",
    )

    replace_thumbnail_in_s3(thumbnail, _make_jpeg_file())

    mock_cf.create_invalidation.assert_called_once()
    call_kwargs = mock_cf.create_invalidation.call_args[1]
    assert call_kwargs["DistributionId"] == "EDIST123"
    assert (
        "/thumbnails/abc/thumb.jpg"
        in call_kwargs["InvalidationBatch"]["Paths"]["Items"]
    )


@mock_aws
def test_replace_thumbnail_in_s3_s3_error_propagates(mocker):
    """
    If the S3 upload raises, the exception is re-raised and the model is not updated.
    """
    original_width = 50
    original_height = 50
    thumbnail = VideoThumbnailFactory(
        max_width=original_width,
        max_height=original_height,
        bucket_name="thumb-bucket",
    )

    mock_boto3 = mocker.patch("cloudsync.api.boto3")
    mock_boto3.resource.return_value.Bucket.return_value.upload_fileobj.side_effect = (
        Exception("S3 upload failed")
    )

    with pytest.raises(Exception, match="S3 upload failed"):
        replace_thumbnail_in_s3(thumbnail, _make_jpeg_file())

    # Model must NOT have been updated
    thumbnail.refresh_from_db()
    assert thumbnail.max_width == original_width
    assert thumbnail.max_height == original_height


# ---------------------------------------------------------------------------
# Tests for create_thumbnail_in_s3
# ---------------------------------------------------------------------------


@mock_aws
@override_settings(
    VIDEO_S3_THUMBNAIL_BUCKET="thumbnail-bucket",
    AWS_S3_UPLOAD_TRANSFER_CONFIG={},
)
def test_create_thumbnail_in_s3_creates_record_and_uploads():
    """
    Happy path: the S3 object is uploaded and a VideoThumbnail record is created.
    """
    s3c = boto3.client("s3", region_name="us-east-1")
    s3c.create_bucket(Bucket="thumbnail-bucket")

    video = VideoFactory()
    new_image = _make_jpeg_file()

    thumbnail = create_thumbnail_in_s3(video, new_image)

    # A VideoThumbnail record must be created
    assert thumbnail.pk is not None
    assert thumbnail.video == video
    assert thumbnail.bucket_name == "thumbnail-bucket"
    assert thumbnail.max_width == 640
    assert thumbnail.max_height == 480
    assert thumbnail.s3_object_key.startswith("thumbnails/")
    assert thumbnail.s3_object_key.endswith(".jpg")

    # The object must exist in S3
    obj = s3c.get_object(Bucket="thumbnail-bucket", Key=thumbnail.s3_object_key)
    assert obj["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert video.hexkey in thumbnail.s3_object_key


@mock_aws
def test_replace_thumbnail_in_s3_converts_png_to_jpeg():
    """
    A PNG input file should be converted to JPEG before being uploaded to S3.
    """
    s3c = boto3.client("s3", region_name="us-east-1")
    thumbnail = VideoThumbnailFactory(
        s3_object_key="thumbnails/abc/thumb.jpg",
        bucket_name="thumb-bucket",
    )
    s3c.create_bucket(Bucket="thumb-bucket")

    replace_thumbnail_in_s3(thumbnail, _make_png_file())

    obj = s3c.get_object(Bucket="thumb-bucket", Key="thumbnails/abc/thumb.jpg")
    assert obj["ResponseMetadata"]["HTTPStatusCode"] == 200
    # The stored bytes must be a valid JPEG (starts with JPEG magic bytes)
    body = obj["Body"].read()
    assert body[:2] == b"\xff\xd8"


@mock_aws
def test_replace_thumbnail_in_s3_converts_bilevel_png_to_jpeg():
    """
    A bilevel (mode '1') PNG — not directly JPEG-compatible — must be converted
    to RGB before saving, rather than raising an OSError.
    """
    s3c = boto3.client("s3", region_name="us-east-1")
    thumbnail = VideoThumbnailFactory(
        s3_object_key="thumbnails/abc/thumb.jpg",
        bucket_name="thumb-bucket",
    )
    s3c.create_bucket(Bucket="thumb-bucket")

    replace_thumbnail_in_s3(thumbnail, _make_bilevel_png_file())

    obj = s3c.get_object(Bucket="thumb-bucket", Key="thumbnails/abc/thumb.jpg")
    body = obj["Body"].read()
    assert body[:2] == b"\xff\xd8"


@mock_aws
@override_settings(
    VIDEO_S3_THUMBNAIL_BUCKET="thumbnail-bucket",
    AWS_S3_UPLOAD_TRANSFER_CONFIG={},
)
def test_create_thumbnail_in_s3_converts_png_to_jpeg():
    """
    A PNG input file should be converted to JPEG before being uploaded to S3.
    """
    s3c = boto3.client("s3", region_name="us-east-1")
    s3c.create_bucket(Bucket="thumbnail-bucket")

    video = VideoFactory()
    thumbnail = create_thumbnail_in_s3(video, _make_png_file())

    assert thumbnail.s3_object_key.endswith(".jpg")
    obj = s3c.get_object(Bucket="thumbnail-bucket", Key=thumbnail.s3_object_key)
    body = obj["Body"].read()
    assert body[:2] == b"\xff\xd8"


# ---------------------------------------------------------------------------
# Unit tests for convert_image_to_jpeg
# ---------------------------------------------------------------------------


def test_convert_image_to_jpeg_passthrough_for_jpeg():
    """
    A JPEG input that is within the size limit must be returned as-is (same
    bytes) to avoid a lossy re-encode. The returned dimensions match the image.
    """
    buf = io.BytesIO()
    Image.new("RGB", (2, 2), color=(255, 0, 0)).save(buf, format="JPEG")
    original_bytes = buf.getvalue()
    buf.seek(0)

    result, width, height = convert_image_to_jpeg(buf)
    assert result.read() == original_bytes
    assert width == 2
    assert height == 2


@override_settings(THUMBNAIL_UPLOAD_MAX_WIDTH=200, THUMBNAIL_UPLOAD_MAX_HEIGHT=150)
def test_convert_image_to_jpeg_resizes_large_image():
    """
    An image whose dimensions exceed the configured maximums must be downscaled
    proportionally. The returned dimensions reflect the resized image.
    """
    big_w = 800
    big_h = 600
    buf = io.BytesIO()
    Image.new("RGB", (big_w, big_h), color=(0, 128, 0)).save(buf, format="JPEG")
    buf.seek(0)

    result, width, height = convert_image_to_jpeg(buf)
    assert width <= 200
    assert height <= 150
    # Aspect ratio preserved within a pixel of rounding
    assert abs(width / height - big_w / big_h) < 0.01
    # Result is a valid JPEG
    result.seek(0)
    img = Image.open(result)
    assert img.format == "JPEG"


def test_convert_image_to_jpeg_raises_for_corrupt_data():
    """
    Corrupt / non-image bytes must raise ValueError rather than an unhandled exception.
    """
    with pytest.raises(ValueError, match="Could not decode image"):
        convert_image_to_jpeg(io.BytesIO(b"this is not an image"))


def test_convert_image_to_jpeg_raises_for_unsupported_format():
    """
    Non-JPEG/PNG images (e.g. GIF) must raise ValueError with a clear message.
    """
    buf = io.BytesIO()
    Image.new("RGB", (1, 1)).save(buf, format="GIF")
    buf.seek(0)
    with pytest.raises(ValueError, match="Unsupported image format"):
        convert_image_to_jpeg(buf)
