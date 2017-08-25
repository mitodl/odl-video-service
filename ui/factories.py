"""Factories for UI app"""

from dj_elastictranscoder.models import EncodeJob
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from factory import (
    Faker,
    Sequence,
    SubFactory,
    LazyAttribute,
    Trait,
)
from factory.django import DjangoModelFactory
from factory.fuzzy import FuzzyText, FuzzyInteger
import faker

from ui.encodings import EncodingNames
from ui import models

FAKE = faker.Factory.create()


class UserFactory(DjangoModelFactory):
    """Factory for User"""
    username = Sequence(lambda n: "user_%d" % n)
    email = FuzzyText(suffix='@example.com')

    class Meta:
        model = get_user_model()


class CollectionFactory(DjangoModelFactory):
    """
    Factory for a Collection
    """
    title = FuzzyText(prefix="Collection ")
    description = FAKE.text()
    owner = SubFactory(UserFactory)

    class Meta:
        model = models.Collection


class VideoFactory(DjangoModelFactory):
    """
    Factory for a Video
    """
    collection = SubFactory(CollectionFactory)
    title = FuzzyText(prefix="Video ")
    description = Faker('text')
    source_url = '{url}{file_name}'.format(url=FAKE.url(), file_name=FAKE.file_name('video'))
    multiangle = False

    class Meta:
        model = models.Video

    class Params:
        """Params for the factory"""
        unencoded = Trait(
            status='Complete'
        )


class VideoFileFactory(DjangoModelFactory):
    """
    Factory for a VideoFile
    """
    video = SubFactory(VideoFactory)
    s3_object_key = LazyAttribute(lambda obj: obj.video.get_s3_key())
    bucket_name = settings.VIDEO_S3_BUCKET
    encoding = EncodingNames.ORIGINAL

    class Meta:
        model = models.VideoFile

    class Params:
        """Params for the factory"""
        unencoded = Trait(
            video=SubFactory(VideoFactory, unencoded=True)
        )
        hls = Trait(
            encoding=EncodingNames.HLS
        )


class VideoThumbnailFactory(DjangoModelFactory):
    """
    Factory for a VideoThumbnail
    """
    video = SubFactory(VideoFactory)
    s3_object_key = LazyAttribute(lambda obj: '{}/{}'.format(obj.video.hexkey, FAKE.file_name('image')))
    bucket_name = settings.VIDEO_S3_BUCKET
    max_width = FuzzyInteger(low=1)
    max_height = FuzzyInteger(low=1)

    class Meta:
        model = models.VideoThumbnail


class EncodeJobFactory(DjangoModelFactory):
    """
    Factory for a EncodeJob
    """
    video = SubFactory(VideoFactory)
    id = FuzzyText()
    object_id = LazyAttribute(lambda obj: obj.video.pk)
    content_type = LazyAttribute(lambda obj: ContentType.objects.get_for_model(obj.video))

    class Meta:
        model = EncodeJob
        exclude = ('video',)


class MoiraListFactory(DjangoModelFactory):
    """
    Factory for a MoiraList
    """
    name = FuzzyText()

    class Meta:
        model = models.MoiraList
