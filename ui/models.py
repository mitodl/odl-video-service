"""
Models for UI app
"""
import os
import datetime
from uuid import uuid4

import boto3
import pytz
from django.db import models
from django.conf import settings

from ui.encodings import EncodingNames
from ui.util import cloudfront_signed_url as make_cloudfront_signed_url
from ui.util import get_moira_client


class MoiraList(models.Model):
    """
    Model for Moira
    """
    name = models.CharField(max_length=250)

    def members(self):
        """Members"""
        moira = get_moira_client()
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
    moira_lists = models.ManyToManyField(MoiraList)
    status = models.TextField(max_length=24, blank=True)
    s3_subkey = models.UUIDField(unique=True, null=False, blank=False, default=uuid4)

    def s3_key(self):
        """
        Avoid duplicate S3 keys/filenames when transferring videos from Dropbox

        Args:
            user_id (str): The user who is uploading a new video
            key (str): The base key to check for duplicates

        Returns:
            str: A unique S3 key including the user id as a virtual subfolder
        """
        basename, extension = os.path.splitext(self.source_url.split('/')[-1])
        newkey = '{user}/{uuid}/{base}{ext}'.format(
            user=self.creator.id, uuid=str(self.s3_subkey), base=basename, ext=extension)
        return newkey

    def __str__(self):
        return self.title or "<untitled video>"

    def __repr__(self):
        return '<Video: {self.title!r} {self.s3_subkey!r}>'.format(self=self)


class VideoFile(models.Model):
    """
    A file associated with a Video object, either the original upload or a transcoded file.
    """
    created_at = models.DateTimeField(auto_now_add=True)
    s3_object_key = models.TextField(unique=True, blank=False, null=False)
    bucket_name = models.CharField(max_length=63, blank=False, null=False)
    video = models.ForeignKey(Video, on_delete=models.CASCADE)
    encoding = models.CharField(max_length=128, default=EncodingNames.ORIGINAL)
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
        return make_cloudfront_signed_url(
            key=self.s3_object_key,
            expires=expires,
        )

    def __str__(self):
        return '{}: {} encoding'.format(self.video.title, self.encoding)

    def __repr__(self):
        return '<VideoFile: {self.video.title!r} {self.s3_object_key!r} {self.encoding!r}>'.format(self=self)
