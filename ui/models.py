import os
import urllib.parse
import boto3
from django.db import models


class Video(models.Model):
    s3_object_key = models.TextField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    title = models.CharField(max_length=250, blank=True)
    description = models.TextField(blank=True)
    source_url = models.URLField()

    @property
    def s3_object(self):
        bucket_name = os.environ.get("VIDEO_S3_BUCKET", "odl-video-service")
        s3 = boto3.resource('s3')
        return s3.Object(bucket_name, self.s3_object_key)

    @property
    def s3_url(self):
        bucket_name = os.environ.get("VIDEO_S3_BUCKET", "odl-video-service")
        encoded_key = urllib.parse.quote_plus(self.s3_object_key)
        return "https://s3.amazonaws.com/{bucket}/{key}".format(
            bucket=bucket_name,
            key=encoded_key,
        )

    @property
    def cloudfront_url(self):
        distribution = os.environ.get("VIDEO_CLOUDFRONT_DIST")
        if not distribution:
            raise RuntimeError("Missing required env var: VIDEO_CLOUDFRONT_DIST")
        encoded_key = urllib.parse.quote_plus(self.s3_object_key)
        return "https://{dist}.cloudfront.net/{key}".format(
            dist=distribution,
            key=encoded_key,
        )

    def __str__(self):
        return self.title or ""

    def __repr__(self):
        return '<Video {self.title!r} {self.s3_object_key!r}>'.format(self=self)
