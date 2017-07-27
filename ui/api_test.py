"""
Tests for ui/api.py
"""

from io import BytesIO

import boto3
import pytest
from django.conf import settings
from moto import mock_s3

from cloudsync.conftest import MockClientET, MockBoto
from ui.api import process_transcode_results, refresh_status
from ui.constants import VideoStatus

pytestmark = pytest.mark.django_db


def test_video_job_status_error(mocker, video, encodejob):  # pylint: disable=unused-argument
    """
    Verify that Video.job_status property returns the status of its encoding job
    """
    video.status = VideoStatus.TRANSCODING
    MockClientET.job = {'Job': {'Id': '1498220566931-qtmtcu', 'Status': 'Error'}}
    mocker.patch('ui.utils.boto3', MockBoto)
    refresh_status(video, encodejob)
    assert video.status == VideoStatus.TRANSCODE_FAILED


def test_video_job_status_complete(mocker, video, encodejob):  # pylint: disable=unused-argument
    """
    Verify that Video.job_status property returns the status of its encoding job
    """
    video.status = VideoStatus.TRANSCODING
    MockClientET.job = {'Job': {'Id': '1498220566931-qtmtcu', 'Status': 'Complete'}}
    mocker.patch('ui.utils.boto3', MockBoto)
    mocker.patch('ui.api.process_transcode_results')
    refresh_status(video, encodejob)
    assert video.status == VideoStatus.COMPLETE


def test_video_job_othererror(mocker, video, encodejob):  # pylint: disable=unused-argument
    """
    Verify that refresh_status does not raise ClientError
    """
    video.status = VideoStatus.TRANSCODING
    mocker.patch('ui.utils.boto3', MockBoto)
    error = Exception("unexpected exception")
    mocker.patch('ui.utils.get_transcoder_client',
                 return_value=MockClientET(error=error))
    with pytest.raises(Exception):
        refresh_status(video)


@mock_s3
def test_process_transcode_results(mocker, video, videofile):  # pylint: disable=unused-argument,redefined-outer-name
    """
    Verify that a videofile object is created for each output in the job JSON, and a thumbnail
    is created for each S3 object in the appropriate bucket virtual subfolder.
    """
    # We need to create the thumbnail bucket since this is all in the Moto virtual AWS account
    conn = boto3.resource('s3', region_name='us-east-1')
    bucket = conn.create_bucket(Bucket=settings.VIDEO_S3_THUMBNAIL_BUCKET)

    # Throw a fake thumbnail in the bucket:
    data = BytesIO(b'00000001111111')
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
    process_transcode_results(video, job)
    assert len(video.videofile_set.all()) == 2
    assert len(video.videothumbnail_set.all()) == 1
