"""
conftest for pytest in this module
"""
import pytest

from dj_elastictranscoder.models import EncodeJob
from django.contrib.contenttypes.models import ContentType

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
        s3_subkey='e5c876ed-e1f9-4e62-9a2f-4a68b27c7973'
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
        s3_object_key=video.s3_key(),
        encoding=EncodingNames.ORIGINAL,
        bucket_name=settings.VIDEO_S3_BUCKET
    )
    obj.save()
    return obj


@pytest.fixture
@pytest.mark.django_db
def encodejob(video):  # pylint: disable=redefined-outer-name
    """EncodeJob fixture"""
    obj = EncodeJob(
        id='dfl13123jkldff-asdas',
        content_type=ContentType.objects.get_for_model(video),
        object_id=video.pk
    )
    obj.save()
    return obj
