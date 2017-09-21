"""
Tests for api
"""
import os
import io
from types import SimpleNamespace

import boto3
import pytest
from botocore.exceptions import ClientError
from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from django.test import override_settings
from moto import mock_s3

from cloudsync import api
from cloudsync.api import upload_subtitle_to_s3
from cloudsync.conftest import MockClientET, MockBoto
from cloudsync.exceptions import VideoFilenameError
from ui.constants import VideoStatus
from ui.factories import (
    VideoFactory,
    EncodeJobFactory,
    VideoFileFactory,
    UserFactory)
from ui.models import Video

pytestmark = pytest.mark.django_db

# pylint: disable=redefined-outer-name


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
    filename = 'subtitles.vtt'
    file_data = SimpleUploadedFile(filename, bytes(1024))
    return SimpleNamespace(name=filename, data=file_data)


def test_get_error_type_from_et_erro():
    """
    Tests get_error_type_from_et_error
    """
    # weird strings
    for str_error in ('', None, 'foo', '1234foo', ):
        assert api.get_error_type_from_et_error(str_error) == VideoStatus.TRANSCODE_FAILED_INTERNAL

    # actual error like string that should be an internal error
    assert api.get_error_type_from_et_error(
        '1234 this is an internal error') == VideoStatus.TRANSCODE_FAILED_INTERNAL

    # actual error like string that should be a video error
    assert api.get_error_type_from_et_error(
        '4123 this is a video error') == VideoStatus.TRANSCODE_FAILED_VIDEO


def test_refresh_status_video_job_status_error(mocker):
    """
    Verify that Video.job_status property returns the status of its encoding job
    """
    video = VideoFactory(status=VideoStatus.TRANSCODING)
    encodejob = EncodeJobFactory(video=video)
    MockClientET.job = {
        'Job': {
            'Id': '1498220566931-qtmtcu',
            'Status': 'Error',
            'Output': {
                'StatusDetail': ('4000 45585321-f360-4557-aef7-91d46460eac5: '
                                 'Amazon Elastic Transcoder could not interpret the media file.')
            }
        }
    }
    mocker.patch('ui.utils.boto3', MockBoto)
    api.refresh_status(video, encodejob)
    assert video.status == VideoStatus.TRANSCODE_FAILED_VIDEO


def test_refresh_status_video_job_status_complete(mocker):
    """
    Verify that Video.job_status property returns the status of its encoding job
    """
    video = VideoFactory(status=VideoStatus.TRANSCODING)
    encodejob = EncodeJobFactory(video=video)
    MockClientET.job = {'Job': {'Id': '1498220566931-qtmtcu', 'Status': 'Complete'}}
    mocker.patch('ui.utils.boto3', MockBoto)
    mocker.patch('cloudsync.api.process_transcode_results')
    api.refresh_status(video, encodejob)
    assert video.status == VideoStatus.COMPLETE


def test_refresh_status_video_job_othererror(mocker):
    """
    Verify that refresh_status does not raise ClientError
    """
    video = VideoFactory(status=VideoStatus.TRANSCODING)
    EncodeJobFactory(video=video)
    video.status = VideoStatus.TRANSCODING
    mocker.patch('ui.utils.boto3', MockBoto)
    error = Exception("unexpected exception")
    mocker.patch('ui.utils.get_transcoder_client', return_value=MockClientET(error=error))
    with pytest.raises(Exception):
        api.refresh_status(video)


@mock_s3
def test_process_transcode_results(mocker):
    """
    Verify that a videofile object is created for each output in the job JSON, and a thumbnail
    is created for each S3 object in the appropriate bucket virtual subfolder.
    """
    videofile = VideoFileFactory()
    video = videofile.video
    # We need to create the thumbnail bucket since this is all in the Moto virtual AWS account
    conn = boto3.resource('s3', region_name='us-east-1')
    bucket = conn.create_bucket(Bucket=settings.VIDEO_S3_THUMBNAIL_BUCKET)

    # Throw a fake thumbnail in the bucket:
    data = io.BytesIO(b'00000001111111')
    bucket.upload_fileobj(
        data, 'thumbnails/1/05a06f21-7625-4c20-b416-ae161f31722a/lastjedi_00001.jpg')

    job = {'Id': '1498765896748-e0p0qr',
           'Input': {'Key': '1/05a06f21-7625-4c20-b416-ae161f31722a/lastjedi.mp4'},
           'Inputs': [{'Key': '1/05a06f21-7625-4c20-b416-ae161f31722a/lastjedi.mp4'}],
           'Output': {'Id': '1',
                      'Key': 'transcoded/1/05a06f21-7625-4c20-b416-ae161f31722a/lastjedi_1498700489769-iyi2t4',
                      'PresetId': '1498700489769-iyi2t4',
                      'SegmentDuration': '10.0',
                      'Status': 'Complete'},
           'Outputs': [{'Id': '1',
                        'Key': 'transcoded/1/05a06f21-7625-4c20-b416-ae161f31722a/lastjedi_1498700489769-iyi2t4',
                        'PresetId': '1498700489769-iyi2t4',
                        'SegmentDuration': '10.0',
                        'Status': 'Complete',
                        'ThumbnailPattern': 'thumbnails/1/05a06f21-7625-4c20-b416-ae161f31722a/lastjedi_{count}',
                        'Watermarks': [],
                        'Width': 1280},
                       {'Id': '2',
                        'Key': 'transcoded/1/05a06f21-7625-4c20-b416-ae161f31722a/lastjedi_1498700403561-zc5oo5',
                        'PresetId': '1498700403561-zc5oo5',
                        'SegmentDuration': '10.0',
                        'Status': 'Complete',
                        'Watermarks': [],
                        'Width': 1280},
                       {'Id': '3',
                        'Key': 'transcoded/1/05a06f21-7625-4c20-b416-ae161f31722a/lastjedi_1498700578799-qvvjor',
                        'PresetId': '1498700578799-qvvjor',
                        'SegmentDuration': '10.0',
                        'Status': 'Complete',
                        'Watermarks': [],
                        'Width': 854},
                       {'Id': '4',
                        'Key': 'transcoded/1/05a06f21-7625-4c20-b416-ae161f31722a/lastjedi_1498700649488-6t9m3h',
                        'PresetId': '1498700649488-6t9m3h',
                        'SegmentDuration': '10.0',
                        'Status': 'Complete',
                        'Watermarks': [],
                        'Width': 640}],
           'PipelineId': '1497455687488-evsuze',
           'Playlists': [{'Format': 'HLSv4',
                          'Name': 'transcoded/1/05a06f21-7625-4c20-b416-ae161f31722a/lastjedi__index',
                          'OutputKeys': [
                              'transcoded/1/05a06f21-7625-4c20-b416-ae161f31722a/lastjedi_1498700489769-iyi2t4',
                              'transcoded/1/05a06f21-7625-4c20-b416-ae161f31722a/lastjedi_1498700403561-zc5oo5',
                              'transcoded/1/05a06f21-7625-4c20-b416-ae161f31722a/lastjedi_1498700578799-qvvjor',
                              'transcoded/1/05a06f21-7625-4c20-b416-ae161f31722a/lastjedi_1498700649488-6t9m3h'],
                          'Status': 'Complete'}],
           'Status': 'Complete'}

    MockClientET.preset = {'Preset': {'Thumbnails': {'MaxHeight': 190, 'MaxWidth': 100}}}
    mocker.patch('ui.utils.get_transcoder_client', return_value=MockClientET())
    api.process_transcode_results(video, job)
    assert len(video.videofile_set.all()) == 2
    assert len(video.videothumbnail_set.all()) == 1


def test_extract_title():
    """
    Test that a correctly formatted title is returned for a video file.
    """
    filenames = (('MIT-6.046-2017-Spring-lec-mit-0000-2017apr06-0404-L01.mp4', 'MIT-6.046-2017-Spring-L01'),
                 ('MIT-6.046-2018-Fall-lec-mit-0000-2017apr06-0404.mp4', 'MIT-6.046-2018-Fall'),
                 ('MIT-6.046-lec-mit-0000-2017apr06-0404.mp4', 'MIT-6.046'),
                 ('MIT-6.046-lec-mit-0000-2017apr06-0404-L02.mp4', 'MIT-6.046-L02'),
                 ('MIT-STS.001-2015-Fall-lec-mit-0000-2015dec21-2222-L03_2.mp4', 'MIT-STS.001-2015-Fall-L03'),
                 ('MIT-HST.969-2018-Spring-lec-mit-0000-2018mar09-0001-L01.mp4', 'MIT-HST.969-2018-Spring-L01'),
                 ('NUS-7.S939-2019-Spring-lec-mit-0000-2019apr02-1210-L05.mp4', 'NUS-7.S939-2019-Spring-L05'),
                 ('MIT-Adhoc-lec-mit-0000-2017aug10-0954-2-190.mp4', 'MIT-Adhoc-2-190'),
                 ('MIT-18.test-lec-mit-0000-2017aug10-0956-L01.mp4', 'MIT-18.test-L01'),
                 ('MIT-18.test-lec-mit-0000-2017aug10-0956.mp4', 'MIT-18.test'),
                 ('MIT-Simons Lecture Series-lec-mit-0000-2017aug10-0956-2-10.mp4', 'MIT-Simons Lecture Series-2-10'),
                 ('/&*3:<>俺正和-lec-mit-0000-2017aug10-0956.mp4', '/&*3:<>俺正和'))
    for filename, title in filenames:
        assert api.extract_title(filename) == title


def test_extract_bad_title():
    """Assert that a VideoFilenameError is raised for a bad filename"""
    bad_names = ('MIT-6.046-1510-L01.mp4',  # Missing -lec-mit-0000
                 'Completely random name.mp4',  # No similarity to expected format
                 'MIT-6.046-lec-mit-0000-2017apr06-L01')  # no extension

    for name in bad_names:
        with pytest.raises(VideoFilenameError):
            api.extract_title(name)


@mock_s3
@override_settings(LECTURE_CAPTURE_USER='admin')
def test_watch_nouser():
    """
    Test that an exception is correctly handled when the LECTURE_CAPTURE_USER doesn't exist
    """
    s3 = boto3.resource('s3')
    s3c = boto3.client('s3')
    upload = 'MIT-6.046-2017-Spring-lec-mit-0000-2017apr06-0404-L01.mp4'
    s3c.create_bucket(Bucket=settings.VIDEO_S3_WATCH_BUCKET)
    bucket = s3.Bucket(settings.VIDEO_S3_WATCH_BUCKET)
    bucket.upload_fileobj(io.BytesIO(os.urandom(6250000)), upload)
    with pytest.raises(User.DoesNotExist):
        api.process_watch_file(upload)
    assert not Video.objects.filter(title=upload).exists()


@mock_s3
@override_settings(LECTURE_CAPTURE_USER='admin')
def test_watch_s3_error():
    """Test that an AWS S3 ClientError is correctly handled"""
    UserFactory(username='admin')  # pylint: disable=unused-variable
    s3 = boto3.resource('s3')
    s3c = boto3.client('s3')
    upload = 'MIT-6.046-2017-Spring-lec-mit-0000-2017apr06-0404-L01.mp4'
    s3c.create_bucket(Bucket=settings.VIDEO_S3_WATCH_BUCKET)
    bucket = s3.Bucket(settings.VIDEO_S3_WATCH_BUCKET)
    bucket.upload_fileobj(io.BytesIO(os.urandom(6250000)), upload)
    with transaction.atomic():
        with pytest.raises(ClientError):
            api.process_watch_file(upload)
    assert not Video.objects.filter(title=upload).exists()


@mock_s3
@override_settings(LECTURE_CAPTURE_USER='admin')
def test_watch_filename_error():
    """Test that a bad filename raises a VideoFilenameError"""
    UserFactory(username='admin')  # pylint: disable=unused-variable
    s3 = boto3.resource('s3')
    s3c = boto3.client('s3')
    upload = 'Bad filename.mp4'
    s3c.create_bucket(Bucket=settings.VIDEO_S3_WATCH_BUCKET)
    s3c.create_bucket(Bucket=settings.VIDEO_S3_BUCKET)
    bucket = s3.Bucket(settings.VIDEO_S3_WATCH_BUCKET)
    bucket.upload_fileobj(io.BytesIO(os.urandom(6250000)), upload)
    with transaction.atomic():
        with pytest.raises(VideoFilenameError):
            api.process_watch_file(upload)
    assert not Video.objects.filter(title=upload).exists()


@mock_s3
@override_settings(LECTURE_CAPTURE_USER='admin')
def test_process_watch(mocker):
    """Test that a file with valid filename is processed"""
    mocker.patch.multiple('cloudsync.tasks.settings',
                          ET_PRESET_IDS=('1351620000001-000061', '1351620000001-000040', '1351620000001-000020'),
                          AWS_REGION='us-east-1', ET_PIPELINE_ID='foo')
    mock_encoder = mocker.patch('cloudsync.api.VideoTranscoder.encode')
    UserFactory(username='admin')  # pylint: disable=unused-variable
    s3 = boto3.resource('s3')
    s3c = boto3.client('s3')
    upload = 'MIT-6.046-2017-Spring-lec-mit-0000-2017apr06-0404-L01.mp4'
    s3c.create_bucket(Bucket=settings.VIDEO_S3_WATCH_BUCKET)
    s3c.create_bucket(Bucket=settings.VIDEO_S3_BUCKET)
    bucket = s3.Bucket(settings.VIDEO_S3_WATCH_BUCKET)
    bucket.upload_fileobj(io.BytesIO(os.urandom(6250000)), upload)
    api.process_watch_file(upload)
    videos = Video.objects.filter(title=upload)
    assert videos.count() == 1
    new_video = videos[0]
    videofile = new_video.videofile_set.first()
    mock_encoder.assert_called_once_with(
        {
            "Key": videofile.s3_object_key
        },
        [{
            "Key": "transcoded/" + new_video.hexkey + "/video_1351620000001-000061",
            "PresetId": "1351620000001-000061",
            "SegmentDuration": "10.0",
            "ThumbnailPattern": "thumbnails/" + new_video.hexkey + "/video_thumbnail_{count}"
        }, {
            "Key": "transcoded/" + new_video.hexkey + "/video_1351620000001-000040",
            "PresetId": "1351620000001-000040",
            "SegmentDuration": "10.0"
        }, {
            "Key": "transcoded/" + new_video.hexkey + "/video_1351620000001-000020",
            "PresetId": "1351620000001-000020",
            "SegmentDuration": "10.0"
        }],
        Playlists=[{
            "Format": "HLSv3",
            "Name": "transcoded/" + new_video.hexkey + "/video__index",
            "OutputKeys": [
                "transcoded/" + new_video.hexkey + "/video_1351620000001-000061",
                "transcoded/" + new_video.hexkey + "/video_1351620000001-000040",
                "transcoded/" + new_video.hexkey + "/video_1351620000001-000020"
            ]
        }])


def test_transcode_job(mocker, videofile):
    """
    Test that video status is updated properly after a transcode job is successfully created
    """
    new_video = videofile.video
    mocker.patch.multiple('cloudsync.tasks.settings',
                          ET_PRESET_IDS=('1351620000001-000040', '1351620000001-000020'),
                          AWS_REGION='us-east-1', ET_PIPELINE_ID='foo')
    mock_encoder = mocker.patch('cloudsync.api.VideoTranscoder.encode')
    api.transcode_video(new_video, videofile)  # pylint: disable=no-value-for-parameter
    mock_encoder.assert_called_once_with(
        {
            "Key": videofile.s3_object_key
        }, [{
            "Key": "transcoded/" + new_video.hexkey + "/video_1351620000001-000040",
            "PresetId": "1351620000001-000040",
            "SegmentDuration": "10.0",
            "ThumbnailPattern": "thumbnails/" + new_video.hexkey + "/video_thumbnail_{count}"
        }, {
            "Key": "transcoded/" + new_video.hexkey + "/video_1351620000001-000020",
            "PresetId": "1351620000001-000020",
            "SegmentDuration": "10.0"
        }],
        Playlists=[{
            "Format": "HLSv3",
            "Name": "transcoded/" + new_video.hexkey + "/video__index",
            "OutputKeys": [
                "transcoded/" + new_video.hexkey + "/video_1351620000001-000040",
                "transcoded/" + new_video.hexkey + "/video_1351620000001-000020"
            ]
        }]
    )
    assert len(new_video.encode_jobs.all()) == 1
    assert Video.objects.get(id=new_video.id).status == VideoStatus.TRANSCODING


def test_transcode_job_failure(mocker, videofile):
    """
    Test that video status is updated properly after a transcode job creation fails
    """
    new_video = videofile.video
    job_result = {'Job': {'Id': '1498220566931-qtmtcu', 'Status': 'Error'}, 'Error': {'Code': 200, 'Message': 'FAIL'}}
    mocker.patch.multiple('cloudsync.tasks.settings',
                          ET_PRESET_IDS=('1351620000001-000020',),
                          AWS_REGION='us-east-1', ET_PIPELINE_ID='foo')
    mock_encoder = mocker.patch('cloudsync.api.VideoTranscoder.encode',
                                side_effect=ClientError(error_response=job_result, operation_name='ReadJob'))
    with pytest.raises(ClientError):
        api.transcode_video(new_video, videofile)
    mock_encoder.assert_called_once_with(
        {
            "Key": videofile.s3_object_key
        }, [{
            "Key": "transcoded/" + new_video.hexkey + "/video_1351620000001-000020",
            "PresetId": "1351620000001-000020",
            "SegmentDuration": "10.0",
            "ThumbnailPattern": "thumbnails/" + new_video.hexkey + "/video_thumbnail_{count}"
        }],
        Playlists=[{
            "Format": "HLSv3",
            "Name": "transcoded/" + new_video.hexkey + "/video__index",
            "OutputKeys": ["transcoded/" + new_video.hexkey + "/video_1351620000001-000020"]
        }]
    )
    assert len(new_video.encode_jobs.all()) == 1
    assert Video.objects.get(id=new_video.id).status == VideoStatus.TRANSCODE_FAILED_INTERNAL


def test_upload_subtitle_to_s3(mocker, video, file_object):
    """
    Test that a VideoSubtitle object is returned after a .vtt upload to S3
    """
    mocker.patch('cloudsync.api.boto3')
    subtitle_data = {"video": video.hexkey, "language": "en", "filename": file_object.name}
    subtitle = upload_subtitle_to_s3(subtitle_data, file_object.data)
    assert subtitle.filename == file_object.name
    assert subtitle.video == video
    assert subtitle.language == "en"


def test_upload_subtitle_to_s3_no_video(mocker, file_object):
    """
    Test that a VideoSubtitle object is not returned with .vtt upload to S3 missing video key
    """
    mocker.patch('cloudsync.api.boto3')
    subtitle_data = {"video": None, "language": "en", "filename": file_object.name}
    assert upload_subtitle_to_s3(subtitle_data, file_object.data) is None


def test_upload_subtitle_to_s3_bad_video(mocker, file_object):
    """
    Test that a VideoSubtitle object raises Exception after a .vtt upload to S3 with nonexistent video key
    """
    mocker.patch('cloudsync.api.boto3')
    subtitle_data = {"video": "12345678123456781234567812345678", "language": "en", "filename": file_object.name}
    with pytest.raises(Video.DoesNotExist):
        upload_subtitle_to_s3(subtitle_data, file_object.data)
