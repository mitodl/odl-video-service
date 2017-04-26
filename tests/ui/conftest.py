import pytest
from django.contrib.auth.models import User
from ui.models import Video


@pytest.fixture
@pytest.mark.django_db
def user():
    obj = User(username="example", email="example@mit.edu")
    obj.set_password("ex4mple")
    obj.save()
    return obj


@pytest.fixture
def video(user):
    obj = Video(
        creator=user,
        s3_object_key="BigBuckBunny.m4v",
        source_url="https://dl.dropboxusercontent.com/1/view/abc123/BigBuckBunny.m4v",
        title="Big Buck Bunny",
        description="Open source video from Blender",
    )
    obj.save()
    return obj

