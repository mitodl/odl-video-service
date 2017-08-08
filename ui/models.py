"""
Models for UI app
"""
import os
import datetime
from uuid import uuid4

import pytz
import boto3
from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.conf import settings
from dj_elastictranscoder.models import EncodeJob

from ui import utils
from ui.constants import VideoStatus
from ui.encodings import EncodingNames
from ui.tasks import delete_s3_objects

TRANSCODE_PREFIX = 'transcoded'


class MoiraList(models.Model):
    """
    Model for Moira
    """
    name = models.CharField(max_length=250)

    def members(self):
        """Members"""
        moira = utils.get_moira_client()
        return moira.list_members(self.name)

    def __str__(self):
        return self.name

    def __repr__(self):
        return '<MoiraList: {self.name!r}>'.format(self=self)


class Video(models.Model):
    """
    Represents an uploaded video, primarily in terms of metadata (source url, title, etc).
    The actual video files (original and encoded) are represented by the VideoFile model.
    """
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    title = models.CharField(max_length=250, blank=True)
    description = models.TextField(blank=True)
    source_url = models.URLField()
    moira_lists = models.ManyToManyField(MoiraList, blank=True)
    status = models.TextField(
        null=False,
        default=VideoStatus.CREATED,
        choices=[(status, status) for status in VideoStatus.ALL_STATUSES],
        max_length=30,
    )
    s3_subkey = models.UUIDField(unique=True, null=False, blank=False, default=uuid4)
    encode_jobs = GenericRelation(EncodeJob)
    multiangle = models.BooleanField(null=False, default=False)

    def get_s3_key(self):
        """
        Avoid duplicate S3 keys/filenames when transferring videos from Dropbox

        Args:
            user_id (str): The user who is uploading a new video
            key (str): The base key to check for duplicates

        Returns:
            str: A unique S3 key including the user id as a virtual subfolder
        """
        _, extension = os.path.splitext(self.source_url.split('/')[-1])
        newkey = '{user}/{uuid}/video{ext}'.format(
            user=self.creator.id, uuid=str(self.s3_subkey), ext=extension)
        return newkey

    def transcode_key(self, preset=None):
        """
        Get the S3 key for a video playlist file

        Args:
            encoding(str): The encoding preset to use (should be one included in settings.ET_PRESET_IDS)

        Returns:
            str: The S3 key to used for the encoded file.
        """
        original_s3_key = self.videofile_set.get(encoding='original').s3_object_key
        if not preset:
            return original_s3_key
        output_template = '{prefix}/{s3key}_{preset}'
        basename, _ = os.path.splitext(original_s3_key)
        return output_template.format(prefix=TRANSCODE_PREFIX, s3key=basename, preset=preset)

    def update_status(self, status):
        """
        Assign and save the status of a Video

        Args:
            status(str): The status to assign the video
        """
        self.status = status
        self.save()

    def save(self, *args, **kwargs):  # pylint: disable=arguments-differ
        """
        Overridden method to run a preventive validation before saving the object.
        """
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title or "<untitled video>"

    def __repr__(self):
        return '<Video: {self.title!r} {self.s3_subkey!r}>'.format(self=self)


class VideoS3(models.Model):
    """
    Abstract class with methods/properties common to both VideoFile and VideoThumbnail models
    """

    created_at = models.DateTimeField(auto_now_add=True)
    s3_object_key = models.TextField(unique=True, blank=False, null=False)
    bucket_name = models.CharField(max_length=63, blank=False, null=False)
    video = models.ForeignKey(Video, on_delete=models.CASCADE)
    preset_id = models.CharField(max_length=128, blank=True, null=True)

    @property
    def s3_object(self):
        """
        Get the S3 Object for the video

            Returns:
                s3.Object: Video file's S3 object
        """
        s3 = boto3.resource('s3')
        return s3.Object(self.bucket_name, self.s3_object_key)

    @property
    def s3_url(self):
        """
        URL for the Video S3 object

        Returns:
            str: URL
        """
        return "https://{domain}/{bucket}/{key}".format(
            domain=settings.AWS_S3_DOMAIN,
            bucket=self.bucket_name,
            key=self.s3_object_key,
        )

    @property
    def s3_basename(self):
        """
        The S3 object key without any file extensions

        Returns:
            str: S3 base key name
        """
        return os.path.splitext(self.s3_object_key)[0]

    @property
    def cloudfront_url(self):
        """
        Get the Cloudfront URL for the video

        Returns:
            str: Cloudfront unsigned URL
        """
        distribution = settings.VIDEO_CLOUDFRONT_DIST
        if not distribution:
            raise RuntimeError("Missing required setting: VIDEO_CLOUDFRONT_DIST")
        return "https://{dist}.cloudfront.net/{key}".format(
            dist=distribution,
            key=self.s3_object_key
        )

    @property
    def cloudfront_signed_url(self):
        """
        Get a signed Cloudfront URL with a default expiration date of 2 hours from
        when this property is called.
        """
        expires = datetime.datetime.now(tz=pytz.UTC) + datetime.timedelta(hours=2)
        return utils.get_cloudfront_signed_url(
            s3_key=self.s3_object_key,
            expires=expires,
        )

    def delete_from_s3(self):
        """
        Delete the S3 object for this this thumbnail
        """
        delete_s3_objects.delay(self.bucket_name, self.s3_object_key)

    class Meta:
        abstract = True


class VideoFile(VideoS3):
    """
    A file associated with a Video object, either the original upload or a transcoded file.
    """
    encoding = models.CharField(max_length=128, default=EncodingNames.ORIGINAL)

    def delete_from_s3(self):
        """
        HLS encoding creates multiple S3 objects, use this method to delete them all.
        """
        if self.encoding == EncodingNames.HLS:
            key = os.path.dirname(self.s3_object_key)
            delete_s3_objects.delay(self.bucket_name, key, as_filter=True)
        else:
            super().delete_from_s3()

    def __str__(self):
        return '{}: {} encoding'.format(self.video.title, self.encoding)

    def __repr__(self):
        return '<VideoFile: {self.video.title!r} {self.s3_object_key!r} {self.encoding!r}>'.format(self=self)


class VideoThumbnail(VideoS3):
    """
    A thumbnail associated with a video object; the number of thumbnails for a video
    will depend on the length of the video.
    """
    max_width = models.IntegerField(null=True, blank=True)
    max_height = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return '{}: {}'.format(self.video.title, self.s3_object_key)

    def __repr__(self):
        return '<VideoThumbnail: {self.s3_object_key!r} {self.max_width!r} {self.max_height!r}>'.format(self=self)
