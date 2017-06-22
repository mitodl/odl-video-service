"""
conftest for pytest in this module
"""
import io
import os
import pytest
import requests_mock
import botocore.session
from botocore.stub import Stubber, ANY


@pytest.fixture
def reqmocker():
    """Fixture for requests mock"""
    with requests_mock.Mocker() as m:
        yield m


@pytest.fixture
def mock_video_url():
    """Mocks video url"""
    return "http://example.com/video.mp4"


@pytest.fixture
def mock_video_headers():
    """mocks video headers"""
    disp = "inline; filename=video.mp4; filename*=UTF-8''video.mp4"
    return {
        "Content-Type": "video/mp4",
        "Content-Length": "6250000",
        "Content-Disposition": disp,
    }


@pytest.fixture
def mock_video_file():
    """Mocks video file"""
    # 50 MB of random noise
    return io.BytesIO(os.urandom(6250000))


@pytest.fixture
def mocked_video_request(
        reqmocker, mock_video_url, mock_video_headers, mock_video_file):  # pylint: disable=redefined-outer-name
    """Mocks video request"""
    reqmocker.get(
        mock_video_url,
        headers=mock_video_headers,
        body=mock_video_file,
    )
    return mock_video_file


@pytest.fixture
def stub_aws_upload():
    """Mocks upload to AWS"""
    s3 = botocore.session.get_session().create_client('s3')
    stubber = Stubber(s3)
    expected_params = {
        'Bucket': 'video-s3',
        'Key': 'video.mp4',
        'ContentType': 'video/mp4',
        'Body': ANY,
    }
    stubber.add_response('put_object', {}, expected_params)
    stubber.activate()
    yield stubber
    stubber.deactivate()
