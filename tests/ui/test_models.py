import pytest
from django.db import IntegrityError
from django.contrib.auth.models import User
from ui.models import Video


pytestmark = pytest.mark.django_db


def test_s3_object_uniqueness(user, bunny):
    video = Video(
        creator=user,
        s3_object_key=bunny.s3_object_key,
        source_url="https://example.com/context.mp4",
    )
    with pytest.raises(IntegrityError):
        video.save()
