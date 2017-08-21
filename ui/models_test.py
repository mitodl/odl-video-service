"""
Tests for the UI models
"""
import os
import uuid

import boto3
import pytest
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from mail import tasks
from ui.factories import (
    VideoFactory,
    VideoFileFactory,
    CollectionFactory,
    UserFactory,
    MoiraListFactory)
from ui.constants import VideoStatus
from ui.models import Collection

pytestmark = pytest.mark.django_db


FAKE_RSA = b'''O\xd3\x91\x01\xf0\x14\xfe\xbf\x12\xb7\xde\xfe\xd83\xf2\x08\xf5x\x93\x12Z)\x0c\x95\xf757\xb5\\>
\xc0\xd9\x9bf\x1aVM\xbe\x10\xa9C\xe8\xb0\xfei\x11L\xbf\xdei\xadk70$O\x88%T\r\x8c\x9f\x8a\xf8U>\xa1\xfd(\xac.\xa3\xff\xf9
\x02\x06\x03\xe0\x19,\xb4\x93\xd79MO\x81\xd8\xad\x1de\xb8$\xa4\xdb\x04Q\xa8\xed\x02\x9cY\xb7\xa2\xa1k+b\x00\xcc\x15\x94
\xe5\xb3B\x0f\x88ZH\x91\xc3\xfe\xa99$I\xdf\xa7i\x08\xec\xd5\xe2\x88\xd6-x\xac_\x8f:_\xb5$,\\\x05I\x00&t\x7f\xae>\xc1\xab
[\xc2\xf9\x15\x1a\xde\x98V}\xab\xeb\xfd\x89D_\x14\xb1?\x92\xeeR=\xc2\x19%X\xb3\xef\xce\x19\x852\xfc)\xa4\xe3x\xcdE\x8bb
\xbeI=#\xac\x12GW|\xef\xa5oi\xc1\xe3\xa0\x87\x1d_Aa\xa1-\xb1\x95\rd\xb8\x16.\x1fc\x88\xbdZ4\xb2]\x8d&87\x8cjy\xb0Y<\xf2)
\xff3\xbe\x8f\xbf\x91\xdc\xcb\x1c'''


# pylint: disable=redefined-outer-name

@pytest.fixture
def video():
    """Fixture to create a video"""
    return VideoFactory()


@pytest.fixture
def videofile():
    """Fixture to create a video file"""
    return VideoFileFactory()


@pytest.fixture
def moiralist():
    """Fixture to create a moira list"""
    return MoiraListFactory()


def test_s3_object_uniqueness(videofile):
    """
    Test that a videoFile with duplicate s3_object_key value should raise an IntegrityError on save
    """
    with pytest.raises(IntegrityError):
        VideoFileFactory(
            video=videofile.video,
            s3_object_key=videofile.s3_object_key,
        )


def test_video_model_s3keys(video):
    """
    Test that the Video.s3_subkey and get_s3_key properties return expected values
    """
    assert isinstance(video.key, uuid.UUID)
    s3key = video.get_s3_key()
    assert s3key is not None
    _, extension = os.path.splitext(video.source_url.split('/')[-1])
    assert s3key == '{uuid}/video{extension}'.format(uuid=video.hexkey, extension=extension)


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


def test_signed_url_spaces(mocker):
    """
    Test that filename spaces are represented as '%20's in cloudfront link
    """
    mocker.patch(
        'ui.utils.rsa_signer',
        return_value=FAKE_RSA
    )
    videofile = VideoFileFactory(
        s3_object_key="video with spaces.mp4",
        bucket_name=settings.VIDEO_S3_BUCKET
    )
    signed_url = videofile.cloudfront_signed_url
    assert 'video%20with%20spaces.mp4' in signed_url


def test_video_transcode_key(videofile):
    """
    Test that the Video.transcode_key method returns expected results
    """
    preset = 'pre01'
    assert videofile.video.transcode_key(preset) == 'transcoded/{uuid}/video_{preset}'.format(
        uuid=str(videofile.video.hexkey), preset=preset)


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


def test_video_update_status_email(video, mocker):
    """
    Tests the Video.update_status method to sends emails with some statuses
    """
    mocked_send_email = mocker.patch(
        'mail.tasks.async_send_notification_email',
        return_value=FAKE_RSA,
        autospec=True
    )
    for video_status in tasks.STATUS_TO_NOTIFICATION:
        video.update_status(video_status)
        mocked_send_email.delay.assert_called_once_with(video.id)
        mocked_send_email.reset_mock()

    # email is not sent for other statuses
    video.update_status(VideoStatus.TRANSCODING)
    assert mocked_send_email.delay.call_count == 0


def test_video_hexkey(video):
    """
    Tests the collection hexkey property method
    """
    assert video.hexkey == video.key.hex


def test_collection_hexkey():
    """
    Tests the collection hexkey property method
    """
    collection = CollectionFactory()
    assert collection.hexkey == collection.key.hex


def test_collection_for_for_owner():
    """
    Tests the for_owner Collection method
    """
    owner = UserFactory()
    collections = [CollectionFactory(owner=owner) for _ in range(5)]
    extra_collection = CollectionFactory()
    qset = Collection.for_owner(owner)
    assert qset.count() == 5
    assert list(qset) == collections
    assert extra_collection not in qset


def test_moira_members(mocker, moiralist):
    """
    Tests the MoiraList.members method
    """
    member_list = ['joe', 'nancy', 'nancy', 'foo', 'bar', 'bar@mit.edu']
    mock_client = mocker.patch('ui.models.utils.get_moira_client')
    mock_client().list_members.return_value = member_list
    assert mock_client().list_members.called_once_with(moiralist.name)
    assert moiralist.members() == set(member_list)
