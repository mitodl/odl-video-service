"""
conftest for pytest in this module
"""
import pytest

from odl_video import settings
from ui.encodings import EncodingNames
from ui.models import Video, VideoFile


@pytest.fixture
@pytest.mark.django_db
def user(django_user_model):
    """
    Fixture to create an user
    """
    User = django_user_model
    obj = User(username="example", email="example@mit.edu")
    obj.set_password("ex4mple")
    obj.save()
    return obj


@pytest.fixture
def video(user):  # pylint: disable=redefined-outer-name
    """
    Fixture to create a video
    """
    obj = Video(
        creator=user,
        source_url="https://dl.dropboxusercontent.com/1/view/abc123/BigBuckBunny.m4v",
        title="Big Buck Bunny",
        description="Open source video from Blender",
    )
    obj.save()
    return obj


@pytest.fixture
@pytest.mark.django_db
def videofile(video):  # pylint: disable=redefined-outer-name
    """
    Fixture to create a video file
    """
    obj = VideoFile(
        video=video,
        s3_object_key=video.s3_key,
        encoding=EncodingNames.ORIGINAL,
        bucket_name=settings.VIDEO_S3_BUCKET
    )
    obj.save()
    return obj
