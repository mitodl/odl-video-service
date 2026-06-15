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
import requests
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
    S3Transfer,
    _collect_output_keys,
    _invalidate_cloudfront_paths,
    _s3_uri_to_key,
    convert_image_to_jpeg,
    create_thumbnail_in_s3,
    move_s3_objects,
    replace_thumbnail_in_s3,
    upload_subtitle_to_s3,
)
from cloudsync.exceptions import TransferError
from cloudsync.conftest import MockBoto, MockClientMC
from ui.constants import VideoStatus
from ui.factories import (
    CollectionFactory,
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


@pytest.mark.parametrize(
    "error_str, expected_status",
    [
        ("", VideoStatus.TRANSCODE_FAILED_INTERNAL),
        (None, VideoStatus.TRANSCODE_FAILED_INTERNAL),
        ("foo", VideoStatus.TRANSCODE_FAILED_INTERNAL),
        ("1234foo", VideoStatus.TRANSCODE_FAILED_INTERNAL),
        ("1234 this is an internal error", VideoStatus.TRANSCODE_FAILED_INTERNAL),
        ("4123 this is a video error", VideoStatus.TRANSCODE_FAILED_VIDEO),
    ],
)
def test_get_error_type_from_et_error(error_str, expected_status):
    """Tests get_error_type_from_et_error for various input strings."""
    assert api.get_error_type_from_et_error(error_str) == expected_status


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
        template_path=None,
    )


@pytest.mark.parametrize(
    "session, expected_slug",
    [
        ("Session", "Prefix-Session"),
        (None, "Prefix"),
    ],
)
def test_lecture_collection_slug(session, expected_slug):
    """Tests for create_lecture_collection_slug with and without a session."""
    video_attrs = api.ParsedVideoAttributes(
        prefix="Prefix",
        session=session,
        record_date=None,
        record_date_str="",
        name="MIT-0.000-2020-Fall-lec-mit-0000-2020sep28-0000-L09.mp4",
    )
    assert api.create_lecture_collection_slug(video_attrs) == expected_slug


@pytest.mark.parametrize(
    "record_date, expected_title",
    [
        (datetime(2017, 1, 1), "Lecture - January 01, 2017"),
        (None, "Lecture - 2017jan01"),
    ],
)
def test_lecture_video_title(record_date, expected_title):
    """Tests for create_lecture_video_title with and without a parsed record date."""
    video_attrs = api.ParsedVideoAttributes(
        record_date=record_date,
        record_date_str="2017jan01",
        prefix="Prefix",
        session="Session",
        name="MIT-0.000-2020-Fall-lec-mit-0000-2020sep28-0000-L09.mp4",
    )
    assert api.create_lecture_video_title(video_attrs) == expected_title


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
        template_path=None,
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
        template_path=None,
    )
    assert len(video.encode_jobs.all()) == 1
    assert Video.objects.get(id=video.id).status == error_status


@pytest.mark.parametrize(
    "for_shorts,expected_template",
    [
        (True, "TRANSCODE_JOB_TEMPLATE_PORTRAIT"),
        (False, None),
    ],
)
def test_transcode_video_routes_shorts_to_portrait_template(
    mocker, for_shorts, expected_template
):
    """
    Videos in a for_shorts collection should be sent through the portrait
    MediaConvert template; every other video uses the default landscape one
    (signalled by template_path=None, which the transcoding library resolves
    via settings.TRANSCODE_JOB_TEMPLATE).
    """
    collection = CollectionFactory.create(for_shorts=for_shorts)
    video = VideoFactory.create(collection=collection, status=VideoStatus.UPLOADING)
    videofile = VideoFileFactory.create(video=video)

    mock_job = {"Job": {"Id": str(uuid.uuid4())}}
    mock_encoder = mocker.patch(
        "cloudsync.api.media_convert_job", return_value=mock_job
    )
    mocker.patch("ui.models.tasks")

    api.transcode_video(video, videofile)

    expected = getattr(settings, expected_template) if expected_template else None
    assert mock_encoder.call_args.kwargs["template_path"] == expected


def test_portrait_mediaconvert_outputs_are_taller_than_wide():
    """
    Guard against accidental landscape regression in the portrait template:
    every output that declares Width and Height must have Height > Width.
    """
    import json
    from pathlib import Path

    template_path = Path(settings.BASE_DIR) / "config" / "mediaconvert_portrait.json"
    template = json.loads(template_path.read_text())

    sized_outputs = [
        output
        for group in template["Settings"]["OutputGroups"]
        for output in group["Outputs"]
        if "Width" in output.get("VideoDescription", {})
        and "Height" in output["VideoDescription"]
    ]
    assert sized_outputs, "portrait template should declare sized outputs"
    for output in sized_outputs:
        vd = output["VideoDescription"]
        assert vd["Height"] > vd["Width"], (
            f"output {output.get('NameModifier')!r} is not portrait: "
            f"{vd['Width']}x{vd['Height']}"
        )


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
    Return a minimal in-memory JPEG file-like object using PIL (640×360,
    matching the default THUMBNAIL_UPLOAD_MAX_WIDTH/HEIGHT so no resize occurs).
    """
    buf = io.BytesIO()
    Image.new("RGB", (640, 360), color=(255, 0, 0)).save(buf, format="JPEG")
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
    assert thumbnail.max_height == 360

    # The object must exist in S3 under the same key
    obj = s3c.get_object(Bucket="thumb-bucket", Key="thumbnails/abc/thumb.jpg")
    assert obj["ResponseMetadata"]["HTTPStatusCode"] == 200


@mock_aws
@override_settings(VIDEO_CDN_DISTRIBUTION_ID="EDIST123")
def test_replace_thumbnail_in_s3_invalidates_cloudfront(mocker):
    """
    When VIDEO_CDN_DISTRIBUTION_ID is set, a CloudFront invalidation is issued.
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
    assert thumbnail.max_height == 360
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


# ---------------------------------------------------------------------------
# Tests for _s3_uri_to_key
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "uri, expected",
    [
        ("s3://my-bucket/transcoded/abc/video.m3u8", "transcoded/abc/video.m3u8"),
        ("s3://bucket/a/b/c/d/file.ts", "a/b/c/d/file.ts"),
        ("s3://bucket/file.mp4", "file.mp4"),
        ("", ""),
        ("s3://bucket", ""),
        ("s3://bucket/", ""),
    ],
)
def test_s3_uri_to_key(uri, expected):
    """_s3_uri_to_key extracts the S3 key from a URI, returning '' for degenerate inputs."""
    assert _s3_uri_to_key(uri) == expected


# ---------------------------------------------------------------------------
# Tests for _collect_output_keys
# ---------------------------------------------------------------------------


def test_collect_output_keys_empty():
    """Empty output groups list returns an empty list."""
    assert _collect_output_keys([]) == []


def test_collect_output_keys_hls_group():
    """
    HLS groups: playlist paths are collected and a directory wildcard is appended
    for the segment files. The wildcard is only added once per directory.
    """
    output_groups = [
        {
            "type": "HLS_GROUP",
            "playlistFilePaths": ["s3://bucket/transcoded/abc/video.m3u8"],
            "outputDetails": [
                {"outputFilePaths": ["s3://bucket/transcoded/abc/seg0.ts"]},
                {"outputFilePaths": ["s3://bucket/transcoded/abc/seg1.ts"]},
            ],
        }
    ]
    keys = _collect_output_keys(output_groups)
    assert "transcoded/abc/video.m3u8" in keys
    assert "transcoded/abc/seg0.ts" in keys
    assert "transcoded/abc/seg1.ts" in keys
    # Wildcard for directory should appear exactly once
    assert keys.count("transcoded/abc/*") == 1


def test_collect_output_keys_file_group():
    """
    FILE_GROUP outputs: paths are collected but no wildcard is appended.
    """
    output_groups = [
        {
            "type": "FILE_GROUP",
            "playlistFilePaths": [],
            "outputDetails": [
                {"outputFilePaths": ["s3://bucket/transcoded/abc/video.mp4"]},
            ],
        }
    ]
    keys = _collect_output_keys(output_groups)
    assert keys == ["transcoded/abc/video.mp4"]
    # No wildcards for file groups
    assert not any(k.endswith("/*") for k in keys)


def test_collect_output_keys_deduplicates_wildcards():
    """
    Multiple segments in the same directory must not produce duplicate wildcards.
    """
    output_groups = [
        {
            "type": "HLS_GROUP",
            "playlistFilePaths": [],
            "outputDetails": [
                {
                    "outputFilePaths": [
                        "s3://b/dir/seg0.ts",
                        "s3://b/dir/seg1.ts",
                        "s3://b/dir/seg2.ts",
                    ]
                },
            ],
        }
    ]
    keys = _collect_output_keys(output_groups)
    assert keys.count("dir/*") == 1


def test_collect_output_keys_mixed_groups():
    """A mix of HLS and FILE groups returns keys from all groups."""
    output_groups = [
        {
            "type": "HLS_GROUP",
            "playlistFilePaths": ["s3://bucket/hls/index.m3u8"],
            "outputDetails": [],
        },
        {
            "type": "FILE_GROUP",
            "playlistFilePaths": [],
            "outputDetails": [
                {"outputFilePaths": ["s3://bucket/mp4/video.mp4"]},
            ],
        },
    ]
    keys = _collect_output_keys(output_groups)
    assert "hls/index.m3u8" in keys
    assert "mp4/video.mp4" in keys


def test_collect_output_keys_strips_retranscode_folder():
    """
    Keys whose S3 paths begin with RETRANSCODE_FOLDER (``retranscode/``) are
    stripped to their served equivalents so that CloudFront invalidation targets
    the paths that the player actually fetches after move_s3_objects relocates
    the files.  Keys that do not contain the prefix are returned unchanged.
    """
    output_groups = [
        {
            "type": "HLS_GROUP",
            "playlistFilePaths": [
                "s3://bucket/retranscode/transcoded/abc/__index.m3u8"
            ],
            "outputDetails": [
                {
                    "outputFilePaths": [
                        "s3://bucket/retranscode/transcoded/abc/seg0.ts",
                        "s3://bucket/retranscode/transcoded/abc/seg1.ts",
                    ]
                },
            ],
        },
        {
            "type": "FILE_GROUP",
            "playlistFilePaths": [],
            "outputDetails": [
                {
                    "outputFilePaths": [
                        "s3://bucket/retranscode/transcoded/abc/video.mp4"
                    ]
                },
            ],
        },
    ]
    keys = _collect_output_keys(output_groups)

    # Retranscode prefix must be stripped from every key
    assert not any("retranscode/" in k for k in keys)

    # HLS playlist
    assert "transcoded/abc/__index.m3u8" in keys
    # HLS segments
    assert "transcoded/abc/seg0.ts" in keys
    assert "transcoded/abc/seg1.ts" in keys
    # Wildcard derived from the stripped path (not the retranscode path)
    assert "transcoded/abc/*" in keys
    assert keys.count("transcoded/abc/*") == 1
    # MP4
    assert "transcoded/abc/video.mp4" in keys


# ---------------------------------------------------------------------------
# Tests for _invalidate_cloudfront_paths
# ---------------------------------------------------------------------------


@override_settings(VIDEO_CDN_DISTRIBUTION_ID="DIST123")
def test_invalidate_cloudfront_paths_sends_invalidation(mocker):
    """When VIDEO_CDN_DISTRIBUTION_ID is set and keys are provided, a batch invalidation is created."""
    mock_cf = mocker.MagicMock()
    mocker.patch("cloudsync.api.boto3").client.return_value = mock_cf

    _invalidate_cloudfront_paths(["transcoded/abc/video.m3u8", "transcoded/abc/*"])

    mock_cf.create_invalidation.assert_called_once()
    call_kwargs = mock_cf.create_invalidation.call_args[1]
    assert call_kwargs["DistributionId"] == "DIST123"
    items = call_kwargs["InvalidationBatch"]["Paths"]["Items"]
    assert "/transcoded/abc/video.m3u8" in items
    assert "/transcoded/abc/*" in items
    assert call_kwargs["InvalidationBatch"]["Paths"]["Quantity"] == 2


@pytest.mark.parametrize(
    "dist_id, keys",
    [
        ("", ["some/key"]),  # dist not configured
        ("DIST123", []),  # empty key list
    ],
)
def test_invalidate_cloudfront_paths_no_op(mocker, settings, dist_id, keys):
    """No CloudFront call is made when the dist is unset or the key list is empty."""
    settings.VIDEO_CDN_DISTRIBUTION_ID = dist_id
    mock_boto3 = mocker.patch("cloudsync.api.boto3")
    _invalidate_cloudfront_paths(keys)
    mock_boto3.client.assert_not_called()


@override_settings(VIDEO_CDN_DISTRIBUTION_ID="DIST123")
def test_invalidate_cloudfront_paths_swallows_exceptions(mocker):
    """
    If the CloudFront API call raises, the exception is caught and logged
    rather than propagated to the caller.
    """
    mock_cf = mocker.MagicMock()
    mock_cf.create_invalidation.side_effect = Exception("CF error")
    mocker.patch("cloudsync.api.boto3").client.return_value = mock_cf

    # Must not raise
    _invalidate_cloudfront_paths(["transcoded/abc/video.m3u8"])


# --- S3Transfer: resumable range-based multipart upload to S3 ---

BUCKET = "test-upload-bucket"
KEY = "abcd1234/video.mp4"
PART = 5 * 1024 * 1024  # S3 minimum part size, keeps test bodies small


@pytest.fixture(autouse=True)
def use_small_transfer_parts(monkeypatch):
    """Keep S3Transfer test payloads small while production uses its fixed constant."""
    monkeypatch.setattr(api, "S3_TRANSFER_PART_SIZE", PART, raising=False)


@pytest.fixture
def s3_client():
    """A moto-backed S3 client with the upload bucket already created."""
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket=BUCKET)
        yield client


class FakeFetcher:
    """
    In-memory stand-in for ``dropbox_api.fetch_shared_link_range``.

    Records each requested range and returns a 206 response carrying the matching slice of
    ``body``. ``always_raise`` makes every call raise (transport-failure tests); ``script``
    supplies per-call overrides (an exception instance to raise, otherwise a normal slice)
    consumed in order before falling back to the default slice response.
    """

    def __init__(
        self,
        body=b"",
        *,
        always_raise=None,
        script=None,
        content_type="application/binary",
    ):
        self.body = body
        self.always_raise = always_raise
        self.content_type = content_type
        self.ranges = []
        self._script = list(script or [])

    def __call__(self, start, end, timeout=None):
        self.ranges.append(f"bytes={start}-{end}")
        if self.always_raise is not None:
            raise self.always_raise
        if self._script:
            action = self._script.pop(0)
            if isinstance(action, Exception):
                raise action
        return SimpleNamespace(
            status_code=206,
            content=self.body[start : end + 1],
            headers={
                "Content-Range": f"bytes {start}-{end}/{len(self.body)}",
                "Content-Type": self.content_type,
            },
        )


def make_transfer(s3_client, fetcher, *, total, progress_callback=None):
    """Construct a transfer with test defaults."""
    return S3Transfer(
        bucket=BUCKET,
        key=KEY,
        content_type="video/mp4",
        total=total,
        s3_client=s3_client,
        range_fetcher=fetcher,
        progress_callback=progress_callback,
    )


def test_small_file_uses_put_object(s3_client):
    """A file at or below the part size is uploaded in a single PUT, no multipart."""
    body = os.urandom(2000)
    make_transfer(s3_client, FakeFetcher(body), total=len(body)).run()

    obj = s3_client.get_object(Bucket=BUCKET, Key=KEY)
    assert obj["Body"].read() == body
    assert obj["ContentType"] == "video/mp4"
    # no multipart upload was created
    assert s3_client.list_multipart_uploads(Bucket=BUCKET).get("Uploads", []) == []


def test_large_file_multipart_assembles_correctly(s3_client):
    """A multi-part file is fetched by range and reassembled byte-for-byte in S3."""
    body = os.urandom(PART * 2 + 1234)  # three parts: two full + remainder
    make_transfer(s3_client, FakeFetcher(body), total=len(body)).run()

    obj = s3_client.get_object(Bucket=BUCKET, Key=KEY)
    assert obj["Body"].read() == body
    # ContentType comes from the passed value, not the ranged "application/binary"
    assert obj["ContentType"] == "video/mp4"


def test_fetches_correct_byte_ranges(s3_client):
    """Each part requests the exact, contiguous byte range."""
    total = PART * 2 + 10
    fetcher = FakeFetcher(os.urandom(total))
    make_transfer(s3_client, fetcher, total=total).run()

    assert fetcher.ranges == [
        f"bytes=0-{PART - 1}",
        f"bytes={PART}-{2 * PART - 1}",
        f"bytes={2 * PART}-{total - 1}",
    ]


def test_progress_callback_reports_cumulative(s3_client):
    """The progress callback is invoked with cumulative bytes uploaded and the total."""
    total = PART * 2
    calls = []
    make_transfer(
        s3_client,
        FakeFetcher(os.urandom(total)),
        total=total,
        progress_callback=lambda up, tot: calls.append((up, tot)),
    ).run()

    assert calls[-1] == (total, total)
    assert [up for up, _ in calls] == [PART, total]


# --- C1: within-execution resilience (per-range retry, abort cleanup) ---


def test_retries_range_on_transient_error_then_succeeds(s3_client, mocker):
    """A transient error on a range is retried, and only that range is re-fetched."""
    sleep = mocker.patch("cloudsync.api.time.sleep")
    body = os.urandom(2000)
    fetcher = FakeFetcher(body, script=[requests.exceptions.ConnectionError()])

    make_transfer(s3_client, fetcher, total=len(body)).run()

    assert s3_client.get_object(Bucket=BUCKET, Key=KEY)["Body"].read() == body
    sleep.assert_called_once()


def test_exhausted_retries_aborts_multipart_and_raises(s3_client, mocker):
    """When retries are exhausted mid-upload, the multipart upload is aborted and the error raised."""
    mocker.patch("cloudsync.api.time.sleep")
    fetcher = FakeFetcher(always_raise=requests.exceptions.ConnectionError())

    with pytest.raises(requests.exceptions.RequestException):
        make_transfer(s3_client, fetcher, total=PART * 2).run()

    # no orphaned in-progress multipart upload is left behind
    assert s3_client.list_multipart_uploads(Bucket=BUCKET).get("Uploads", []) == []


def test_fetch_range_wrong_byte_count_retries_then_raises(s3_client, mocker):
    """If the fetcher returns fewer bytes than requested (e.g. Dropbox ignored Range), it retries and raises."""
    mocker.patch("cloudsync.api.time.sleep")
    full_body = os.urandom(PART * 2)

    def bad_fetcher(start, end):
        # Simulates Dropbox returning 200 with the full body instead of the requested range.
        return SimpleNamespace(
            status_code=200,
            content=full_body,
            headers={"Content-Type": "video/mp4"},
        )

    with pytest.raises(TransferError, match="expected .* bytes"):
        make_transfer(s3_client, bad_fetcher, total=PART).run()


def test_fetch_range_wrong_byte_count_retries_then_succeeds(s3_client, mocker):
    """After a wrong-byte-count response, a successful retry with correct bytes completes the upload."""
    mocker.patch("cloudsync.api.time.sleep")
    body = os.urandom(2000)
    full_body = os.urandom(len(body) * 2)
    calls = []

    def fetcher(start, end):
        calls.append((start, end))
        if len(calls) == 1:
            # First attempt: return wrong size (full body instead of the range).
            return SimpleNamespace(
                status_code=200,
                content=full_body,
                headers={"Content-Type": "video/mp4"},
            )
        return SimpleNamespace(
            status_code=206,
            content=body[start : end + 1],
            headers={"Content-Range": f"bytes {start}-{end}/{len(body)}"},
        )

    make_transfer(s3_client, fetcher, total=len(body)).run()
    assert s3_client.get_object(Bucket=BUCKET, Key=KEY)["Body"].read() == body


# --- C2: cross-execution resume + size discovery ---


def test_resumes_existing_multipart_upload(s3_client):
    """An interrupted upload resumes: completed parts are kept, only missing parts re-fetched."""
    body = os.urandom(PART * 3)  # exactly three parts
    create = s3_client.create_multipart_upload(
        Bucket=BUCKET, Key=KEY, ContentType="video/mp4"
    )
    uid = create["UploadId"]
    s3_client.upload_part(
        Bucket=BUCKET, Key=KEY, PartNumber=1, UploadId=uid, Body=body[0:PART]
    )
    s3_client.upload_part(
        Bucket=BUCKET, Key=KEY, PartNumber=2, UploadId=uid, Body=body[PART : 2 * PART]
    )
    fetcher = FakeFetcher(body)

    make_transfer(s3_client, fetcher, total=len(body)).run()

    # only the missing third part is fetched
    assert fetcher.ranges == [f"bytes={2 * PART}-{3 * PART - 1}"]
    # object assembles correctly from the two pre-seeded parts plus the fetched one
    assert s3_client.get_object(Bucket=BUCKET, Key=KEY)["Body"].read() == body


def test_multiple_uploads_for_key_resolved_to_one(s3_client):
    """When several in-progress uploads exist for the key, the run leaves none behind."""
    body = os.urandom(PART * 2)
    s3_client.create_multipart_upload(Bucket=BUCKET, Key=KEY, ContentType="video/mp4")
    s3_client.create_multipart_upload(Bucket=BUCKET, Key=KEY, ContentType="video/mp4")
    assert len(s3_client.list_multipart_uploads(Bucket=BUCKET)["Uploads"]) == 2

    make_transfer(s3_client, FakeFetcher(body), total=len(body)).run()

    assert s3_client.list_multipart_uploads(Bucket=BUCKET).get("Uploads", []) == []
    assert s3_client.get_object(Bucket=BUCKET, Key=KEY)["Body"].read() == body


def test_part_size_drift_restarts_fresh(s3_client):
    """A completed part whose size no longer matches part_size forces a clean restart."""
    body = os.urandom(PART * 2 + 100)  # three parts at PART
    create = s3_client.create_multipart_upload(
        Bucket=BUCKET, Key=KEY, ContentType="video/mp4"
    )
    # part 1 is not the last part but is the wrong size -> boundaries no longer align
    s3_client.upload_part(
        Bucket=BUCKET,
        Key=KEY,
        PartNumber=1,
        UploadId=create["UploadId"],
        Body=os.urandom(PART + 1024 * 1024),
    )
    fetcher = FakeFetcher(body)

    make_transfer(s3_client, fetcher, total=len(body)).run()

    # all three parts re-fetched from scratch
    assert len(fetcher.ranges) == 3
    assert s3_client.get_object(Bucket=BUCKET, Key=KEY)["Body"].read() == body


def test_discovers_total_when_not_provided(s3_client):
    """With total=None the size is discovered from a ranged request's Content-Range."""
    body = os.urandom(2000)
    make_transfer(s3_client, FakeFetcher(body), total=None).run()

    assert s3_client.get_object(Bucket=BUCKET, Key=KEY)["Body"].read() == body


def test_discovers_total_retries_on_transient_error(s3_client, mocker):
    """_discover_total retries on RequestException and succeeds on the next attempt."""
    mocker.patch("cloudsync.api.time.sleep")
    body = os.urandom(2000)
    calls = []

    def fetcher(start, end):
        calls.append((start, end))
        if len(calls) == 1:
            raise requests.exceptions.ConnectionError("transient")
        return SimpleNamespace(
            status_code=206,
            content=body[start : end + 1],
            headers={"Content-Range": f"bytes {start}-{end}/{len(body)}"},
        )

    make_transfer(s3_client, fetcher, total=None).run()
    assert s3_client.get_object(Bucket=BUCKET, Key=KEY)["Body"].read() == body


def test_discovers_total_raises_on_200(s3_client, mocker):
    """_discover_total raises TransferError if Dropbox returns 200 (ignoring Range) for the discovery probe."""
    mocker.patch("cloudsync.api.time.sleep")
    body = os.urandom(2000)

    def fetcher(start, end):
        return SimpleNamespace(
            status_code=200,
            content=body,
            headers={"Content-Type": "video/mp4"},
        )

    with pytest.raises(TransferError, match="expected 206"):
        make_transfer(s3_client, fetcher, total=None).run()
