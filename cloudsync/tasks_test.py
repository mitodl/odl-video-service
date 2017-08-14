"""
Tests for tasks
"""
import io
import os

import boto3
import pytest
from botocore.exceptions import ClientError
import celery
from dj_elastictranscoder.models import EncodeJob
from django.conf import settings
from django.test import override_settings
from mock import PropertyMock
from moto import mock_s3

from cloudsync.conftest import MockBoto
from cloudsync.tasks import stream_to_s3, transcode_from_s3, VideoTask, update_video_statuses, monitor_watch_bucket
from ui.factories import (
    VideoFactory,
    VideoFileFactory,
    UserFactory,
)
from ui.encodings import EncodingNames
from ui.models import Video
from ui.constants import VideoStatus

pytestmark = pytest.mark.django_db


@pytest.fixture()
def video():
    """Fixture to create a video"""
    return VideoFactory()


@pytest.fixture()
def videofile():
    """Fixture to create a videofile"""
    return VideoFileFactory()


@pytest.fixture(scope="module")
def user():
    """Fixture to create a user"""
    return UserFactory()


# pylint: disable=redefined-outer-name


def test_empty_video_id():
    """
    Tests that an empty video id does not give a result
    """
    result = stream_to_s3("")  # pylint: disable=no-value-for-parameter
    assert not result


def test_happy_path(mocker, reqmocker, mock_video_headers, video):
    """
    Test that a file can be uploaded to a mocked S3 bucket.
    """
    mock_video_file = io.BytesIO(os.urandom(6250000))
    reqmocker.get(
        video.source_url,
        headers=mock_video_headers,
        body=mock_video_file,
    )
    mock_boto3 = mocker.patch('cloudsync.tasks.boto3')
    mock_bucket = mock_boto3.resource.return_value.Bucket.return_value
    stream_to_s3(video.id)  # pylint: disable=no-value-for-parameter

    mock_bucket.upload_fileobj.assert_called_with(
        Fileobj=mocker.ANY,
        Key=video.get_s3_key(),
        ExtraArgs={"ContentType": "video/mp4"},
        Callback=mocker.ANY,
        Config=mocker.ANY
    )
    fileobj = mock_bucket.upload_fileobj.call_args[1]['Fileobj']
    # compare the first 50 bytes of each
    actual = fileobj.read(50)
    mock_video_file.seek(0)
    expected = fileobj.read(50)
    assert actual == expected
    assert Video.objects.get(id=video.id).status == VideoStatus.UPLOADING


def test_upload_failure(mocker, reqmocker, mock_video_headers, video):
    """
    Test that video status is updated properly after an upload failure
    """
    mock_video_file = io.BytesIO(os.urandom(6250000))
    reqmocker.get(
        video.source_url,
        headers=mock_video_headers,
        body=mock_video_file,
    )
    mocker.patch('cloudsync.tasks.boto3')
    mocker.patch('cloudsync.tasks.requests.models.Response.raise_for_status', side_effect=Exception())
    with pytest.raises(Exception):
        stream_to_s3(video.id)  # pylint: disable=no-value-for-parameter
    assert Video.objects.get(id=video.id).status == VideoStatus.UPLOAD_FAILED


def test_transcode_failure(mocker, videofile):
    """
    Test transcode task, verify there is an EncodeJob associated with the video to encode
    """
    video = videofile.video
    job_result = {'Job': {'Id': '1498220566931-qtmtcu', 'Status': 'Error'}, 'Error': {'Code': 200, 'Message': 'FAIL'}}
    mocker.patch.multiple('cloudsync.tasks.settings',
                          ET_PRESET_IDS=('1351620000001-000061', '1351620000001-000040', '1351620000001-000020'),
                          AWS_REGION='us-east-1', ET_PIPELINE_ID='foo')
    mocker.patch('cloudsync.api.VideoTranscoder.encode',
                 side_effect=ClientError(error_response=job_result, operation_name='ReadJob'))
    mocker.patch('dj_elastictranscoder.transcoder.Session')
    mocker.patch('celery.app.task.Task.update_state')
    mocker.patch('ui.utils.boto3', MockBoto)
    mocker.patch('cloudsync.api.get_et_job',
                 return_value=job_result['Job'])
    # Transcode the video
    with pytest.raises(ClientError):
        transcode_from_s3(video.id)  # pylint: disable=no-value-for-parameter
    assert video.encode_jobs.count() == 1
    assert Video.objects.get(id=video.id).status == VideoStatus.TRANSCODE_FAILED


def test_transcode_starting(mocker, videofile):
    """
    Test that video status is updated properly after a transcode failure
    """
    video = videofile.video
    mocker.patch.multiple('cloudsync.tasks.settings',
                          ET_PRESET_IDS=('1351620000001-000061', '1351620000001-000040', '1351620000001-000020'),
                          AWS_REGION='us-east-1', ET_PIPELINE_ID='foo')
    mocker.patch('cloudsync.api.VideoTranscoder.encode')
    mocker.patch('dj_elastictranscoder.transcoder.Session')
    mocker.patch('celery.app.task.Task.update_state')
    mocker.patch('cloudsync.api.process_transcode_results')
    mocker.patch('ui.utils.boto3', MockBoto)
    mocker.patch('cloudsync.api.get_et_job',
                 return_value={'Id': '1498220566931-qtmtcu', 'Status': 'Complete'})
    transcode_from_s3(video.id)  # pylint: disable=no-value-for-parameter
    assert video.encode_jobs.count() == 1
    assert Video.objects.filter(id=video.id, status=VideoStatus.TRANSCODING).count() == 1


def test_video_task_chain(mocker):
    """
    Test that video task get_task_id method returns the correct id from the chain.
    """
    def ctx():
        """ Return a mock context object """
        return celery.app.task.Context({
            'lang': 'py',
            'task': 'cloudsync.tasks.stream_to_s3',
            'id': '1853b857-84d8-4af4-8b19-1c307c1e07d5',
            'chain': [{
                'task': 'cloudsync.tasks.transcode_from_s3',
                'args': [351],
                'kwargs': {},
                'options': {
                    'task_id': '1a859e5a-8f71-4e01-9349-5ebc6dc66631'
                }
            }]
        })
    mocker.patch('cloudsync.tasks.VideoTask.request', new_callable=PropertyMock, return_value=ctx())
    task = VideoTask()
    assert task.get_task_id() == task.request.chain[0]['options']['task_id']


def test_video_task_bad_chain(mocker):
    """
    Test that video task get_task_id method returns the task.id if the chain is not valid.
    """
    def ctx():
        """ Return a mock context object """
        return celery.app.task.Context({
            'lang': 'py',
            'task': 'cloudsync.tasks.stream_to_s3',
            'id': '1853b857-84d8-4af4-8b19-1c307c1e07d5',
            'chain': [{
                'task': 'cloudsync.tasks.transcode_from_s3',
                'args': [351],
                'kwargs': {},
                'options': {}
            }]
        })
    mocker.patch('cloudsync.tasks.VideoTask.request', new_callable=PropertyMock, return_value=ctx())
    task = VideoTask()
    assert task.get_task_id() is None


def test_video_task_no_chain(mocker):
    """
    Test that video task get_task_id method returns the task.id if the chain is not present.
    """
    def ctx():
        """ Return a mock context object """
        return celery.app.task.Context({
            'lang': 'py',
            'task': 'cloudsync.tasks.stream_to_s3',
            'id': '1853b857-84d8-4af4-8b19-1c307c1e07d5',
        })
    mocker.patch('cloudsync.tasks.VideoTask.request', new_callable=PropertyMock, return_value=ctx())
    task = VideoTask()
    assert task.get_task_id() == task.request.id


def test_update_video_statuses_nojob(mocker, video):  # pylint: disable=unused-argument
    """Test NoEncodeJob error handling"""
    mocker.patch('cloudsync.tasks.refresh_status',
                 side_effect=EncodeJob.DoesNotExist())
    video.update_status(VideoStatus.TRANSCODING)
    update_video_statuses()  # pylint: disable=no-value-for-parameter
    assert VideoStatus.TRANSCODE_FAILED == Video.objects.get(id=video.id).status


def test_update_video_statuses_clienterror(mocker, video):  # pylint: disable=unused-argument
    """Test NoEncodeJob error handling"""
    job_result = {'Job': {'Id': '1498220566931-qtmtcu', 'Status': 'Error'}, 'Error': {'Code': 200, 'Message': 'FAIL'}}
    mocker.patch('cloudsync.tasks.refresh_status',
                 side_effect=ClientError(error_response=job_result, operation_name='ReadJob'))
    video.update_status(VideoStatus.TRANSCODING)
    update_video_statuses()  # pylint: disable=no-value-for-parameter
    assert VideoStatus.TRANSCODE_FAILED == Video.objects.get(id=video.id).status


def test_stream_to_s3_no_video():
    """Test DoesNotExistError"""
    with pytest.raises(Video.DoesNotExist):
        stream_to_s3(999999)  # pylint: disable=no-value-for-parameter


@mock_s3
@override_settings(LECTURE_CAPTURE_USER='admin')
def test_monitor_watch(mocker, user):  # pylint: disable=unused-argument,redefined-outer-name
    """Test the Watch bucket monitor task"""
    UserFactory(username='admin')  # pylint: disable=unused-variable
    mocker.patch.multiple('cloudsync.tasks.settings',
                          ET_PRESET_IDS=('1351620000001-000061',),
                          AWS_REGION='us-east-1', ET_PIPELINE_ID='foo')
    mock_encoder = mocker.patch('cloudsync.api.VideoTranscoder.encode')
    s3 = boto3.resource('s3')
    s3c = boto3.client('s3')
    upload = 'MIT-6.046-2017-Spring-lec-mit-0000-2017apr06-0404-L01.mp4'
    s3c.create_bucket(Bucket=settings.VIDEO_S3_WATCH_BUCKET)
    s3c.create_bucket(Bucket=settings.VIDEO_S3_BUCKET)
    bucket = s3.Bucket(settings.VIDEO_S3_WATCH_BUCKET)
    bucket.upload_fileobj(io.BytesIO(os.urandom(6250000)), upload)
    assert s3c.get_object(Bucket=bucket.name, Key=upload) is not None
    monitor_watch_bucket.delay()
    new_video = Video.objects.get(title=upload)
    new_videofile = new_video.videofile_set.get(encoding=EncodingNames.ORIGINAL)
    mock_encoder.assert_called_once_with(
        {
            "Key": new_videofile.s3_object_key
        }, [{
            "Key": "transcoded/" + new_video.hexkey + "/video_1351620000001-000061",
            "PresetId": "1351620000001-000061",
            "SegmentDuration": "10.0",
            "ThumbnailPattern": "thumbnails/" + new_video.hexkey + "/video_thumbnail_{count}"
        }], Playlists=[{
            "Format": "HLSv3",
            "Name": "transcoded/" + new_video.hexkey + "/video__index",
            "OutputKeys": ["transcoded/" + new_video.hexkey + "/video_1351620000001-000061"]
        }])
    assert new_videofile.bucket_name == settings.VIDEO_S3_BUCKET
    with pytest.raises(ClientError):
        s3c.get_object(Bucket=bucket.name, Key=upload)


@mock_s3
@override_settings(LECTURE_CAPTURE_USER='admin')
def test_monitor_watch_badname(mocker):  # pylint: disable=unused-argument,redefined-outer-name
    """
    Test no video is created for a file with a bad name, but other filenames are processed
    """
    UserFactory(username='admin')  # pylint: disable=unused-variable
    mocker.patch.multiple('cloudsync.tasks.settings',
                          ET_PRESET_IDS=('1351620000001-000061', '1351620000001-000040', '1351620000001-000020'),
                          AWS_REGION='us-east-1', ET_PIPELINE_ID='foo')
    mock_encoder = mocker.patch('cloudsync.api.VideoTranscoder.encode')
    s3 = boto3.resource('s3')
    s3c = boto3.client('s3')
    s3c.create_bucket(Bucket=settings.VIDEO_S3_WATCH_BUCKET)
    s3c.create_bucket(Bucket=settings.VIDEO_S3_BUCKET)
    uploads = ('MIT-6.046-2017-Spring-lec-mit-0000-2017apr06-0404-L01.mp4',
               'Bad Name.mp4',
               'MIT-6.046-lec-mit-0000-2017apr06-0404.mp4')
    bucket = s3.Bucket(settings.VIDEO_S3_WATCH_BUCKET)
    for filename in uploads:
        bucket.upload_fileobj(io.BytesIO(os.urandom(6250000)), filename)
    monitor_watch_bucket.delay()
    assert mock_encoder.call_count == 2
    assert not Video.objects.filter(title=uploads[1])
    assert Video.objects.get(title=uploads[0])
    assert Video.objects.get(title=uploads[2])
