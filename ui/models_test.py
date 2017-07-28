"""
Tests for the UI models
"""
import uuid

import boto3
import pytest
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from ui.constants import VideoStatus
from ui.models import Video, VideoFile

pytestmark = pytest.mark.django_db


FAKE_RSA = b'''O\xd3\x91\x01\xf0\x14\xfe\xbf\x12\xb7\xde\xfe\xd83\xf2\x08\xf5x\x93\x12Z)\x0c\x95\xf757\xb5\\>
\xc0\xd9\x9bf\x1aVM\xbe\x10\xa9C\xe8\xb0\xfei\x11L\xbf\xdei\xadk70$O\x88%T\r\x8c\x9f\x8a\xf8U>\xa1\xfd(\xac.\xa3\xff\xf9
\x02\x06\x03\xe0\x19,\xb4\x93\xd79MO\x81\xd8\xad\x1de\xb8$\xa4\xdb\x04Q\xa8\xed\x02\x9cY\xb7\xa2\xa1k+b\x00\xcc\x15\x94
\xe5\xb3B\x0f\x88ZH\x91\xc3\xfe\xa99$I\xdf\xa7i\x08\xec\xd5\xe2\x88\xd6-x\xac_\x8f:_\xb5$,\\\x05I\x00&t\x7f\xae>\xc1\xab
[\xc2\xf9\x15\x1a\xde\x98V}\xab\xeb\xfd\x89D_\x14\xb1?\x92\xeeR=\xc2\x19%X\xb3\xef\xce\x19\x852\xfc)\xa4\xe3x\xcdE\x8bb
\xbeI=#\xac\x12GW|\xef\xa5oi\xc1\xe3\xa0\x87\x1d_Aa\xa1-\xb1\x95\rd\xb8\x16.\x1fc\x88\xbdZ4\xb2]\x8d&87\x8cjy\xb0Y<\xf2)
\xff3\xbe\x8f\xbf\x91\xdc\xcb\x1c'''


def test_s3_object_uniqueness(videofile):
    """
    Test that a videoFile with duplicate s3_object_key value should raise an IntegrityError on save
    """
    video2 = VideoFile(
        video=videofile.video,
        s3_object_key=videofile.s3_object_key,
        bucket_name=settings.VIDEO_S3_BUCKET
    )
    with pytest.raises(IntegrityError):
        video2.save()


def test_video_model_s3keys(user):
    """
    Test that the Video.s3_subkey and get_s3_key properties return expected values
    """
    new_video = Video(source_url="http://fake.com/fake.mp4", creator=user)
    assert isinstance(new_video.s3_subkey, uuid.UUID)
    s3key = new_video.get_s3_key()
    assert s3key is not None
    assert s3key == '{user}/{uuid}/video.mp4'.format(user=user.id, uuid=new_video.s3_subkey)


def test_video_aws_integration(videofile):
    """
    Tests video aws integration
    """
    s3_obj = videofile.s3_object
    assert isinstance(s3_obj, boto3.resources.base.ServiceResource)
    assert s3_obj.key == videofile.s3_object_key
    s3_url = videofile.s3_url
    assert isinstance(s3_url, str)
    assert s3_url.startswith("https://{}/".format(settings.AWS_S3_DOMAIN))
    cf_url = videofile.cloudfront_url
    assert isinstance(cf_url, str)
    assert cf_url.startswith("https://video-cf.cloudfront.net/")


def test_signed_url_spaces(video, mocker):
    """
    Test that filename spaces are represented as '%20's in cloudfront link
    """
    mocker.patch(
        'ui.utils.rsa_signer',
        return_value=FAKE_RSA
    )
    videofile = VideoFile(
        video=video,
        s3_object_key="video with spaces.mp4",
        bucket_name=settings.VIDEO_S3_BUCKET
    )
    signed_url = videofile.cloudfront_signed_url
    assert 'video%20with%20spaces.mp4' in signed_url


def test_video_transcode_key(user, video, videofile):  # pylint: disable=unused-argument,redefined-outer-name
    """
    Test that the Video.transcode_key method returns expected results
    """
    preset = 'pre01'
    assert video.transcode_key(preset) == 'transcoded/{user}/{uuid}/video_{preset}'.format(
        user=user.id, uuid=str(video.s3_subkey), preset=preset)


def test_video_status(video):
    """
    Tests that a video cannnot have a status different from he allowed
    """
    for status in VideoStatus.ALL_STATUSES:
        video.status = status
        video.save()
    with pytest.raises(ValidationError):
        video.status = 'foostatus'
        video.save()
