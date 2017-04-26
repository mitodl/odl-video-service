import pytest
from boto3.resources.base import ServiceResource
from django.db import IntegrityError
from django.contrib.auth.models import User
from ui.models import Video


pytestmark = pytest.mark.django_db


def test_s3_object_uniqueness(user, video):
    video2 = Video(
        creator=user,
        s3_object_key=video.s3_object_key,
        source_url="https://example.com/context.mp4",
    )
    with pytest.raises(IntegrityError):
        video2.save()


def test_video_aws_integration(video):
    s3_obj = video.s3_object
    assert isinstance(s3_obj, ServiceResource)
    assert s3_obj.key == video.s3_object_key
    s3_url = video.s3_url
    assert isinstance(s3_url, str)
    assert s3_url.startswith("https://s3.amazonaws.com/")
    cf_url = video.cloudfront_url
    assert isinstance(cf_url, str)
    assert cf_url.startswith("https://video-cf.cloudfront.net/")
    assert callable(video.cloudfront_signed_url)

