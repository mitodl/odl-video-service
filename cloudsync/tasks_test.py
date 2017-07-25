"""
Tests for tasks
"""
import pytest
from cloudsync.conftest import MockClientET, MockBoto
from cloudsync.tasks import stream_to_s3, transcode_from_s3, Transcoder
from ui.conftest import user, video, videofile  # pylint: disable=unused-import


def test_empty_url():
    """
    Tests that an empty URL does not give a result
    """
    result = stream_to_s3("", "no_url")  # pylint: disable=no-value-for-parameter
    assert not result


@pytest.mark.django_db
def test_happy_path(mocker, reqmocker, mock_video_url, mock_video_headers, mock_video_file):
    """
    Test that a file can be uploaded to a mocked S3 bucket.
    """
    reqmocker.get(
        mock_video_url,
        headers=mock_video_headers,
        body=mock_video_file,
    )
    mock_boto3 = mocker.patch('cloudsync.tasks.boto3')
    mock_bucket = mock_boto3.resource.return_value.Bucket.return_value
    stream_to_s3(mock_video_url, 'video.mp4')  # pylint: disable=no-value-for-parameter

    mock_bucket.upload_fileobj.assert_called_with(
        Fileobj=mocker.ANY,
        Key="video.mp4",
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


def test_transcode(mocker, user, video, videofile):  # pylint: disable=unused-argument,redefined-outer-name
    """
    Test transcode task, verify there is an EncodeJob associated with the video to encode
    """
    mocker.patch.multiple('cloudsync.tasks.settings',
                          ET_PRESET_IDS=('1351620000001-000061', '1351620000001-000040', '1351620000001-000020'),
                          AWS_REGION='us-east-1', ET_PIPELINE_ID='foo')
    mocker.patch('cloudsync.tasks.Transcoder.encode')
    mocker.patch.object(Transcoder, 'message', {'Job': {'Id': 'foo'}}, create=True)
    MockClientET.preset = {'Preset': {'Thumbnails': {'MaxHeight': 190, 'MaxWidth': 100}, 'Container': 'mp4'}}
    mocker.patch('ui.utils.boto3', MockBoto)

    # Transcode the video
    transcode_from_s3(video.id)  # pylint: disable=no-value-for-parameter
    assert len(video.encode_jobs.all()) == 1
