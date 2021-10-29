"""Factories for UI app"""
from datetime import datetime

import pytz
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from factory import (
    Faker,
    Sequence,
    SubFactory,
    LazyAttribute,
    Trait,
    post_generation,
)
from factory.django import DjangoModelFactory
from factory.fuzzy import FuzzyText, FuzzyInteger
import faker
from dj_elastictranscoder.models import EncodeJob

from ui.constants import YouTubeStatus
from ui.encodings import EncodingNames
from ui import models

FAKE = faker.Factory.create()


class UserFactory(DjangoModelFactory):
    """Factory for User"""

    username = Sequence(lambda n: "user_%d" % n)
    email = FuzzyText(suffix="@example.com")

    class Meta:
        model = get_user_model()


class EdxEndpointFactory(DjangoModelFactory):
    """Factory for EdxEndpoint model"""

    name = Faker("slug")
    base_url = Faker("url")
    access_token = Faker("sha1")
    hls_api_path = Faker("uri_path")
    is_global_default = False
    client_id = Faker("slug")
    secret_key = Faker("sha1")

    class Meta:
        model = models.EdxEndpoint


class CollectionFactory(DjangoModelFactory):
    """
    Factory for a Collection
    """

    title = FuzzyText(prefix="Collection ")
    description = FAKE.text()
    owner = SubFactory(UserFactory)
    schedule_retranscode = False
    edx_course_id = Sequence(lambda n: "course-v1:fake+course+%d" % n)

    class Meta:
        model = models.Collection

    @post_generation
    def admin_lists(
        self, create, extracted, **kwargs
    ):  # pylint:disable=unused-argument
        """Post-generation hook to handle admin_lists (if provided)"""
        if create and extracted:
            # An object was created and admin_lists were passed in
            for moira_list in extracted:
                self.admin_lists.add(moira_list)

    @post_generation
    def view_lists(self, create, extracted, **kwargs):  # pylint:disable=unused-argument
        """Post-generation hook to handle admin_lists (if provided)"""
        if create and extracted:
            # An object was created and view_lists were passed in
            for moira_list in extracted:
                self.view_lists.add(moira_list)


class CollectionEdxEndpointFactory(DjangoModelFactory):
    """Factory for CollectionEdxEndpoint model"""

    collection = SubFactory(CollectionFactory)
    edx_endpoint = SubFactory(EdxEndpointFactory)

    class Meta:
        model = models.CollectionEdxEndpoint


class VideoFactory(DjangoModelFactory):
    """
    Factory for a Video
    """

    collection = SubFactory(CollectionFactory)
    title = FuzzyText(prefix="Video ")
    description = Faker("text")
    source_url = "{url}{file_name}".format(
        url=FAKE.url(), file_name=FAKE.file_name("video")
    )
    multiangle = False
    schedule_retranscode = False

    class Meta:
        model = models.Video

    class Params:
        """Params for the factory"""

        unencoded = Trait(status="Complete")

    @post_generation
    def view_lists(self, create, extracted, **kwargs):  # pylint:disable=unused-argument
        """Post-generation hook to handle admin_lists (if provided)"""
        if create and extracted:
            # An object was created and view_lists were passed in
            for moira_list in extracted:
                self.view_lists.add(moira_list)


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

        unencoded = Trait(video=SubFactory(VideoFactory, unencoded=True))
        hls = Trait(encoding=EncodingNames.HLS)


class VideoThumbnailFactory(DjangoModelFactory):
    """
    Factory for a VideoThumbnail
    """

    video = SubFactory(VideoFactory)
    s3_object_key = LazyAttribute(
        lambda obj: "{}/{}".format(obj.video.hexkey, FAKE.file_name("image"))
    )
    bucket_name = settings.VIDEO_S3_BUCKET
    max_width = FuzzyInteger(low=1)
    max_height = FuzzyInteger(low=1)

    class Meta:
        model = models.VideoThumbnail


class VideoSubtitleFactory(DjangoModelFactory):
    """
    Factory for a VideoSubtitle
    """

    video = SubFactory(VideoFactory)
    language = "en"
    s3_object_key = LazyAttribute(
        lambda obj: obj.video.subtitle_key(
            datetime.now(tz=pytz.UTC), language=obj.language
        )
    )
    bucket_name = settings.VIDEO_S3_SUBTITLE_BUCKET
    filename = FuzzyText()

    class Meta:
        model = models.VideoSubtitle


class YouTubeVideoFactory(DjangoModelFactory):
    """
    Factory for a YouTubeVideo
    """

    video = SubFactory(VideoFactory)
    status = YouTubeStatus.SUCCEEDED
    id = FuzzyText(length=11)

    class Meta:
        model = models.YouTubeVideo


class EncodeJobFactory(DjangoModelFactory):
    """
    Factory for a EncodeJob
    """

    video = SubFactory(VideoFactory)
    id = FuzzyText()
    object_id = LazyAttribute(lambda obj: obj.video.pk)
    content_type = LazyAttribute(
        lambda obj: ContentType.objects.get_for_model(obj.video)
    )

    class Meta:
        model = EncodeJob
        exclude = ("video",)


class MoiraListFactory(DjangoModelFactory):
    """
    Factory for a MoiraList
    """

    name = FuzzyText()

    class Meta:
        model = models.MoiraList
