"""
conftest for pytest in this module
"""
import pytest
from ui.models import Video


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
        s3_object_key="BigBuckBunny.m4v",
        source_url="https://dl.dropboxusercontent.com/1/view/abc123/BigBuckBunny.m4v",
        title="Big Buck Bunny",
        description="Open source video from Blender",
    )
    obj.save()
    return obj
