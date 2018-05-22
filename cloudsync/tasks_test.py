"""
Tests for tasks
"""
import io
import os
import random
import string

import boto3
import pytest
from botocore.exceptions import ClientError
import celery
from dj_elastictranscoder.models import EncodeJob
from django.conf import settings
from django.test import override_settings
from googleapiclient.errors import HttpError, ResumableUploadError
from mock import PropertyMock, call
from moto import mock_s3
from requests import HTTPError

from cloudsync.conftest import MockBoto, MockHttpErrorResponse
from cloudsync.exceptions import TranscodeTargetDoesNotExist
from cloudsync.tasks import (
    VideoTask,
    stream_to_s3,
    transcode_from_s3,
    update_video_statuses,
    monitor_watch_bucket,
    upload_youtube_videos,
    upload_youtube_caption,
    update_youtube_statuses,
    remove_youtube_video, remove_youtube_caption)
from cloudsync.youtube import API_QUOTA_ERROR_MSG
from ui.factories import (
    VideoFactory,
    VideoFileFactory,
    UserFactory,
    VideoSubtitleFactory,
    YouTubeVideoFactory,
    CollectionFactory)
from ui.models import Video, YouTubeVideo
from ui.constants import VideoStatus, YouTubeStatus, StreamSource

pytestmark = pytest.mark.django_db


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


# pylint: disable=redefined-outer-name,unused-argument,no-value-for-parameter,unused-variable


def test_empty_video_id():
    """
    Tests that an empty video id does not give a result
    """
    result = stream_to_s3("")
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
    stream_to_s3(video.id)

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
    mocker.patch('ui.models.tasks.async_send_notification_email')
    mock_update = mocker.patch('cloudsync.tasks.stream_to_s3.update_state')
    mock_video_file = io.BytesIO(os.urandom(6250000))
    reqmocker.get(
        video.source_url,
        headers=mock_video_headers,
        body=mock_video_file,
        status_code=500,
        reason='access denied'
    )
    mocker.patch('cloudsync.tasks.boto3')
    with pytest.raises(HTTPError):
        stream_to_s3(video.id)
    assert Video.objects.get(id=video.id).status == VideoStatus.UPLOAD_FAILED
    mock_update.assert_called_once()
    assert mock_update.call_args == call(state='FAILURE', task_id=None)


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
    mocker.patch('ui.models.tasks')
    mocker.patch('cloudsync.api.get_et_job',
                 return_value=job_result['Job'])
    # Transcode the video
    with pytest.raises(ClientError):
        transcode_from_s3(video.id)
    assert video.encode_jobs.count() == 1
    assert Video.objects.get(id=video.id).status == VideoStatus.TRANSCODE_FAILED_INTERNAL


def test_transcode_target_does_not_exist():
    """
    Test transcode task, verify exception is thrown when target does not exist.
    """
    nonexistent_video_id = 12345
    with pytest.raises(TranscodeTargetDoesNotExist):
        transcode_from_s3(nonexistent_video_id)


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
    transcode_from_s3(video.id)
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


def test_update_video_statuses_nojob(mocker, video):
    """Test NoEncodeJob error handling"""
    mocker.patch('cloudsync.tasks.refresh_status',
                 side_effect=EncodeJob.DoesNotExist())
    mocker.patch('ui.models.tasks')
    video.update_status(VideoStatus.TRANSCODING)
    update_video_statuses()
    assert VideoStatus.TRANSCODE_FAILED_INTERNAL == Video.objects.get(id=video.id).status


def test_update_video_statuses_clienterror(mocker, video):
    """Test NoEncodeJob error handling"""
    job_result = {'Job': {'Id': '1498220566931-qtmtcu', 'Status': 'Error'}, 'Error': {'Code': 200, 'Message': 'FAIL'}}
    mocker.patch('cloudsync.tasks.refresh_status',
                 side_effect=ClientError(error_response=job_result, operation_name='ReadJob'))
    mocker.patch('ui.models.tasks')
    video.update_status(VideoStatus.TRANSCODING)
    update_video_statuses()
    assert VideoStatus.TRANSCODE_FAILED_INTERNAL == Video.objects.get(id=video.id).status


def test_stream_to_s3_no_video():
    """Test DoesNotExistError"""
    with pytest.raises(Video.DoesNotExist):
        stream_to_s3(999999)


@mock_s3
@override_settings(LECTURE_CAPTURE_USER='admin')
def test_monitor_watch(mocker, user):
    """Test the Watch bucket monitor task"""
    UserFactory(username='admin')
    mocker.patch.multiple('cloudsync.tasks.settings',
                          ET_PRESET_IDS=('1351620000001-000061',), ENVIRONMENT='test',
                          AWS_REGION='us-east-1', ET_PIPELINE_ID='foo')
    mock_encoder = mocker.patch('cloudsync.api.VideoTranscoder.encode')
    s3 = boto3.resource('s3')
    s3c = boto3.client('s3')
    filename = 'MIT-6.046-2017-Spring-lec-mit-0000-2017apr06-0404-L01.mp4'
    s3c.create_bucket(Bucket=settings.VIDEO_S3_WATCH_BUCKET)
    s3c.create_bucket(Bucket=settings.VIDEO_S3_BUCKET)
    bucket = s3.Bucket(settings.VIDEO_S3_WATCH_BUCKET)
    bucket.upload_fileobj(io.BytesIO(os.urandom(6250000)), filename)
    assert s3c.get_object(Bucket=bucket.name, Key=filename) is not None
    monitor_watch_bucket.delay()
    new_video = Video.objects.get(source_url__endswith=filename)
    new_videofile = new_video.original_video
    mock_encoder.assert_called_once_with(
        {
            "Key": new_videofile.s3_object_key
        }, [{
            "Key": "transcoded/" + new_video.hexkey + "/video_1351620000001-000061",
            "PresetId": "1351620000001-000061",
            "SegmentDuration": "10.0",
            "ThumbnailPattern": "thumbnails/" + new_video.hexkey + "/video_thumbnail_{count}"
        }],
        Playlists=[{
            "Format": "HLSv3",
            "Name": "transcoded/" + new_video.hexkey + "/video__index",
            "OutputKeys": ["transcoded/" + new_video.hexkey + "/video_1351620000001-000061"]
        }],
        UserMetadata={
            'pipeline': 'odl-video-service-test'
        }
    )
    assert new_videofile.bucket_name == settings.VIDEO_S3_BUCKET
    with pytest.raises(ClientError):
        s3c.get_object(Bucket=bucket.name, Key=filename)


@mock_s3
@override_settings(LECTURE_CAPTURE_USER='admin')
def test_monitor_watch_badname(mocker):
    """
    Test no video is created for a file with a bad name, but other filenames are processed
    """
    UserFactory(username='admin')
    mocker.patch.multiple('cloudsync.tasks.settings',
                          ET_PRESET_IDS=('1351620000001-000061', '1351620000001-000040', '1351620000001-000020'),
                          AWS_REGION='us-east-1', ET_PIPELINE_ID='foo')
    mock_encoder = mocker.patch('cloudsync.api.VideoTranscoder.encode')
    s3 = boto3.resource('s3')
    s3c = boto3.client('s3')
    s3c.create_bucket(Bucket=settings.VIDEO_S3_WATCH_BUCKET)
    s3c.create_bucket(Bucket=settings.VIDEO_S3_BUCKET)
    filenames = (
        'MIT-6.046-2017-Spring-lec-mit-0000-2017apr06-0404-L01.mp4',
        'Bad Name.mp4',
        'MIT-6.046-lec-mit-0000-2017apr06-0404.mp4'
    )
    bucket = s3.Bucket(settings.VIDEO_S3_WATCH_BUCKET)
    for filename in filenames:
        bucket.upload_fileobj(io.BytesIO(os.urandom(6250000)), filename)
    monitor_watch_bucket.delay()
    assert mock_encoder.call_count == 2
    assert not Video.objects.filter(source_url__endswith=filenames[1])
    assert Video.objects.get(source_url__endswith=filenames[0])
    assert Video.objects.get(source_url__endswith=filenames[2])


@pytest.mark.parametrize('source', [StreamSource.CLOUDFRONT, StreamSource.YOUTUBE, None])
@pytest.mark.parametrize('max_uploads', [2, 4])
def test_upload_youtube_videos(mocker, source, max_uploads):
    """
    Test that the upload_youtube_videos task calls YouTubeApi.upload_video
    & creates a YoutubeVideo object for each public video, up to the max daily limit
    """
    settings.YT_DAILY_UPLOAD_LIMIT = max_uploads
    private_videos = VideoFactory.create_batch(2, is_public=False, status=VideoStatus.COMPLETE)
    VideoFactory.create_batch(3,
                              collection=CollectionFactory(stream_source=source),
                              is_public=True,
                              status=VideoStatus.COMPLETE)
    mock_uploader = mocker.patch('cloudsync.tasks.YouTubeApi.upload_video', return_value={
        'id': ''.join([random.choice(string.ascii_lowercase) for n in range(8)]),
        'status': {
            'uploadStatus': 'uploaded'
        }
    })
    upload_youtube_videos()
    assert mock_uploader.call_count == (min(3, max_uploads) if source != StreamSource.CLOUDFRONT else 0)
    for video in Video.objects.filter(is_public=True).order_by('-created_at')[:settings.YT_DAILY_UPLOAD_LIMIT]:
        if video.collection.stream_source != StreamSource.CLOUDFRONT:
            assert YouTubeVideo.objects.filter(video=video).first() is not None
        else:
            assert YouTubeVideo.objects.filter(video=video).first() is None
    for video in private_videos:
        assert YouTubeVideo.objects.filter(video=video).first() is None


def test_upload_youtube_videos_error(mocker):
    """
    Test that the YoutubeVideo object is deleted if an error occurs during upload, and all videos are processed
    """
    videos = VideoFactory.create_batch(3, is_public=True, status=VideoStatus.COMPLETE)
    mock_uploader = mocker.patch('cloudsync.tasks.YouTubeApi.upload_video', side_effect=OSError)
    upload_youtube_videos()
    assert mock_uploader.call_count == 3
    for video in videos:
        assert YouTubeVideo.objects.filter(video=video).first() is None


@pytest.mark.parametrize('msg', [API_QUOTA_ERROR_MSG, 'other error'])
def test_upload_youtube_quota_exceeded(mocker, msg):
    """
    Test that the YoutubeVideo object is deleted if an error occurs during upload,
    and the loop is halted if the quota is exceeded.
    """
    videos = VideoFactory.create_batch(3, is_public=True, status=VideoStatus.COMPLETE)
    mock_uploader = mocker.patch('cloudsync.tasks.YouTubeApi.upload_video',
                                 side_effect=ResumableUploadError(
                                     MockHttpErrorResponse(403), str.encode(msg, 'utf-8')))
    upload_youtube_videos()
    assert mock_uploader.call_count == (1 if msg == API_QUOTA_ERROR_MSG else 3)
    for video in videos:
        assert YouTubeVideo.objects.filter(video=video).first() is None


def test_remove_youtube_video(mocker, public_video):
    """
    Test that the remove_youtube_video task calls YouTubeApi.delete_video
    """
    mock_delete = mocker.patch('cloudsync.tasks.YouTubeApi.delete_video')
    yt_video = YouTubeVideoFactory(video=public_video)
    remove_youtube_video(yt_video.id)
    mock_delete.assert_called_once_with(yt_video.id)


def test_remove_youtube_video_404(mocker, public_video):
    """
    Test that the remove_youtube_video task does not raise an exception if a 404 error occurs
    """
    mock_delete = mocker.patch('cloudsync.tasks.YouTubeApi.delete_video',
                               side_effect=HttpError(MockHttpErrorResponse(404), b''))
    yt_video = YouTubeVideoFactory(video=public_video)
    remove_youtube_video(yt_video.id)
    mock_delete.assert_called_once_with(yt_video.id)


def test_remove_youtube_video_500(mocker, public_video):
    """
    Test that the remove_youtube_video task raises an exception if a 500 error occurs
    """
    mocker.patch('cloudsync.tasks.YouTubeApi.delete_video',
                 side_effect=HttpError(MockHttpErrorResponse(500), b''))
    yt_video = YouTubeVideoFactory(video=public_video)
    with pytest.raises(HttpError):
        remove_youtube_video(yt_video.id)


def test_upload_youtube_caption(mocker, public_video):
    """
    Test that the upload_youtube_caption task calls YouTubeApi.upload_caption with correct arguments
    """
    mocker.patch('cloudsync.tasks.YouTubeApi.upload_video')
    mock_uploader = mocker.patch('cloudsync.tasks.YouTubeApi.upload_caption')
    subtitle = VideoSubtitleFactory(video=public_video)
    yt_video = YouTubeVideoFactory(video=public_video)
    upload_youtube_caption(subtitle.id)
    mock_uploader.assert_called_once_with(subtitle, yt_video.id)


def test_remove_youtube_caption(mocker, public_video):
    """
    Test that the upload_youtube_caption task calls YouTubeApi.upload_caption with correct arguments,
    and only for language captions that actually exist on Youtube
    """
    mock_delete = mocker.patch('cloudsync.tasks.YouTubeApi.delete_caption')
    mocker.patch('cloudsync.tasks.YouTubeApi.list_captions', return_value={
        'fr': 'foo',
        'en': 'bar'
    })
    YouTubeVideoFactory(video=public_video)
    VideoSubtitleFactory(video=public_video, language='en')
    VideoSubtitleFactory(video=public_video, language='fr')
    remove_youtube_caption(public_video.id, 'fr')
    remove_youtube_caption(public_video.id, 'zh')
    mock_delete.assert_called_once_with('foo')


def test_update_youtube_statuses(mocker):
    """
    Test that the correct number of YouTubeVideo objects have their statuses updated to the correct value
    and captions are uploaded for them.
    """
    mock_uploader = mocker.patch('cloudsync.tasks.YouTubeApi.upload_caption')
    mocker.patch('cloudsync.tasks.YouTubeApi.video_status', return_value=YouTubeStatus.PROCESSED)
    processing_videos = YouTubeVideoFactory.create_batch(2, status=YouTubeStatus.UPLOADED)
    completed_videos = YouTubeVideoFactory.create_batch(3, status=YouTubeStatus.PROCESSED)
    for yt_video in processing_videos + completed_videos:
        VideoSubtitleFactory(video=yt_video.video)
    update_youtube_statuses()
    assert mock_uploader.call_count == 2
    assert YouTubeVideo.objects.filter(status=YouTubeStatus.PROCESSED).count() == 5


def test_update_youtube_statuses_api_quota_exceeded(mocker):
    """
    Test that the update_youtube_statuses task stops without raising an error if the API quota is exceeded.
    """
    mock_video_status = mocker.patch('cloudsync.tasks.YouTubeApi.video_status',
                                     side_effect=HttpError(MockHttpErrorResponse(403),
                                                           str.encode(API_QUOTA_ERROR_MSG, 'utf-8')))
    YouTubeVideoFactory.create_batch(3, status=YouTubeStatus.UPLOADED)
    update_youtube_statuses()
    mock_video_status.assert_called_once()


def test_update_youtube_statuses_error(mocker):
    """
    Test that an error is raised if any error occurs other than exceeding daily API quota
    """
    mock_video_status = mocker.patch('cloudsync.tasks.YouTubeApi.video_status',
                                     side_effect=HttpError(MockHttpErrorResponse(403), b'other error'))
    YouTubeVideoFactory.create_batch(3, status=YouTubeStatus.UPLOADED)
    with pytest.raises(HttpError):
        update_youtube_statuses()
    mock_video_status.assert_called_once()


def test_update_youtube_statuses_dupe(mocker):
    """
    Test that the status of a potential dupe video is saved as 'failed'
    """
    mock_video_status = mocker.patch('cloudsync.tasks.YouTubeApi.video_status',
                                     side_effect=[IndexError, YouTubeStatus.PROCESSED, YouTubeStatus.UPLOADED])
    YouTubeVideoFactory.create_batch(3, status=YouTubeStatus.UPLOADED)
    update_youtube_statuses()
    assert mock_video_status.call_count == 3
    for status in [YouTubeStatus.FAILED, YouTubeStatus.PROCESSED, YouTubeStatus.UPLOADED]:
        assert len(YouTubeVideo.objects.filter(status=status).all()) == 1


def test_update_youtube_statuses_failed(mocker):
    """
    Test that the correct number of YouTubeVideo objects have their statuses updated to FAILED
    and no captions are uploaded.
    """
    mock_uploader = mocker.patch('cloudsync.tasks.YouTubeApi.upload_caption')
    mocker.patch('cloudsync.tasks.YouTubeApi.video_status', return_value=YouTubeStatus.FAILED)
    processing_videos = YouTubeVideoFactory.create_batch(2, status=YouTubeStatus.UPLOADED)
    for yt_video in processing_videos:
        VideoSubtitleFactory(video=yt_video.video)
    update_youtube_statuses()
    assert mock_uploader.call_count == 0
    assert YouTubeVideo.objects.filter(status=YouTubeStatus.FAILED).count() == 2
