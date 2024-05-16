"""
conftest for pytest in this module
"""

from io import BytesIO

import botocore.session
import pytest
from botocore.stub import ANY, Stubber


@pytest.fixture()
def mock_video_headers():
    """Mocks video headers"""  # noqa: D401
    disp = "inline; filename=video.mp4; filename*=UTF-8''video.mp4"
    return {
        "Content-Type": "video/mp4",
        "Content-Length": "6250000",
        "Content-Disposition": disp,
    }


@pytest.fixture()
def mocked_video_request(
    reqmocker, mock_video_url, mock_video_headers, mock_video_file
):
    """Mocks video request"""  # noqa: D401
    reqmocker.get(
        mock_video_url,
        headers=mock_video_headers,
        body=mock_video_file,
    )
    return mock_video_file


@pytest.fixture()
def stub_aws_upload():
    """Mocks upload to AWS"""  # noqa: D401
    s3 = botocore.session.get_session().create_client("s3")
    stubber = Stubber(s3)
    expected_params = {
        "Bucket": "video-s3",
        "Key": "video.mp4",
        "ContentType": "video/mp4",
        "Body": ANY,
    }
    stubber.add_response("put_object", {}, expected_params)
    stubber.activate()
    yield stubber
    stubber.deactivate()


@pytest.fixture(autouse=True)
def youtube_mock(mocker):  # noqa: PT004
    """
    Mocks calls for youtube api tests
    """  # noqa: D401
    mocker.patch("cloudsync.youtube.boto3")
    mocker.patch("cloudsync.youtube.Credentials")
    mocker.patch("cloudsync.youtube.build")
    mocker.patch(
        "cloudsync.youtube.SeekableBufferedInputBase", return_value=BytesIO(b"123")
    )


class MockClientET:
    """
    Mock boto3 ElasticTranscoder client, because ElasticTranscode isn't supported by moto yet
    """  # noqa: E501

    job = None
    preset = None
    error = None

    def __init__(self, *args, **kwargs):  # noqa: ARG002
        """Mock __init__"""
        if "error" in kwargs:
            self.error = kwargs["error"]

    def read_job(self, **kwargs):  # noqa: ARG002
        """Mock read_job method"""
        if self.error:
            raise self.error
        return self.job

    def read_preset(self, *args, **kwargs):  # noqa: ARG002
        """Mock read_preset method"""
        if self.error:
            raise self.error
        return self.preset


class MockBoto:
    """
    Mock boto3 class for returning mock elastictranscoder client
    """

    def client(*args, **kwargs):  # noqa: ARG002
        """Return a mock client"""
        if args[0] == "elastictranscoder":  # noqa: RET503
            return MockClientET()


class MockHttpErrorResponse:
    """
    Mock googleapiclient.HttpError response
    """

    def __init__(self, status, reason="mock reason"):
        self.status = status
        self.reason = reason
