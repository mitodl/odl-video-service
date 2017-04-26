import pytest
import boto3
from cloudsync.tasks import stream_to_s3


def test_empty_url():
    result = stream_to_s3("")
    assert not result

# @pytest.mark.reqmocker
# @pytest.mark.mocked_video_request
def test_happy_path(
        mocker,
        reqmocker, mock_video_url, mock_video_headers, mock_video_file
    ):
    reqmocker.get(
        mock_video_url,
        headers=mock_video_headers,
        body=mock_video_file,
    )
    mock_boto3 = mocker.patch('cloudsync.tasks.boto3')
    mock_bucket = mock_boto3.resource.return_value.Bucket.return_value

    stream_to_s3(mock_video_url)

    mock_bucket.upload_fileobj.assert_called_with(
        Fileobj=mocker.ANY,
        Key="video.mp4",
        ExtraArgs={"ContentType": "video/mp4"},
        Callback=mocker.ANY,
    )
    fileobj = mock_bucket.upload_fileobj.call_args[1]['Fileobj']
    # compare the first 50 bytes of each
    actual = fileobj.read(50)
    mock_video_file.seek(0)
    expected = fileobj.read(50)
    assert actual == expected
