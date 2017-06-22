"""
Models for UI app
"""
import os
import urllib.parse
import boto3
from django.db import models
from django.conf import settings
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
    Model for Video
    """
    s3_object_key = models.TextField(unique=True)
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    title = models.CharField(max_length=250, blank=True)
    description = models.TextField(blank=True)
    source_url = models.URLField()
    moira_lists = models.ManyToManyField(MoiraList)

    @property
    def s3_object(self):
        """s3 object"""
        bucket_name = os.environ.get("VIDEO_S3_BUCKET", "odl-video-service")
        s3 = boto3.resource('s3')
        return s3.Object(bucket_name, self.s3_object_key)

    @property
    def s3_url(self):
        """s3 url"""
        bucket_name = os.environ.get("VIDEO_S3_BUCKET", "odl-video-service")
        encoded_key = urllib.parse.quote_plus(self.s3_object_key)
        return "https://s3.amazonaws.com/{bucket}/{key}".format(
            bucket=bucket_name,
            key=encoded_key,
        )

    @property
    def cloudfront_url(self):
        """cloudfront url"""
        distribution = os.environ.get("VIDEO_CLOUDFRONT_DIST")
        if not distribution:
            raise RuntimeError("Missing required env var: VIDEO_CLOUDFRONT_DIST")
        encoded_key = urllib.parse.quote_plus(self.s3_object_key)
        return "https://{dist}.cloudfront.net/{key}".format(
            dist=distribution,
            key=encoded_key,
        )

    def cloudfront_signed_url(self, expires):
        """cloudfront signed url"""
        return make_cloudfront_signed_url(
            key=self.s3_object_key,
            expires=expires,
        )

    def __str__(self):
        return self.title or "<untitled video>"

    def __repr__(self):
        return '<Video: {self.title!r} {self.s3_object_key!r}>'.format(self=self)
