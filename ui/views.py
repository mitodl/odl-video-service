import os
import json
import boto3
from datetime import datetime, timedelta
from django.views.decorators.http import require_POST
from django.shortcuts import render
from django.http import JsonResponse
from rest_framework import viewsets
from cloudsync.tasks import stream_to_s3
from ui.util import cloudfront_signed_url
from ui.models import Video
from ui.serializers import (
    VideoSerializer, DropboxFileSerializer, CloudFrontSignedURLSerializer
)


def index(request):
    return render(request, "index.html")


def upload(request):
    dropbox_key = os.environ.get("DROPBOX_APP_KEY")
    if not dropbox_key:
        raise RuntimeError("Missing required env var: DROPBOX_APP_KEY")
    context = {
        "dropbox_key": dropbox_key,
    }
    return render(request, "upload.html", context)


def view(request):
    cloudfront_dist = os.environ.get("VIDEO_CLOUDFRONT_DIST")
    if not cloudfront_dist:
        raise RuntimeError("Missing required env var: VIDEO_CLOUDFRONT_DIST")
    s3 = boto3.resource('s3')
    bucket_name = os.environ.get("VIDEO_S3_BUCKET", "odl-video-service")
    bucket = s3.Bucket(bucket_name)
    context = {
        "cloudfront_dist": cloudfront_dist,
        "bucket_objects": bucket.objects.all(),
    }
    return render(request, "view.html", context)


@require_POST
def stream(request):
    data = json.loads(request.body.decode('utf-8'))
    serializer = DropboxFileSerializer(data=data, many=True)
    serializer.is_valid(raise_exception=True)
    videos = serializer.save()

    async_results = {
        video.s3_object_key: stream_to_s3.delay(video.source_url)
        for video in videos
    }
    return JsonResponse({
        name: result.id
        for name, result in async_results.items()
    })


@require_POST
def generate_signed_url(request):
    data = json.loads(request.body.decode('utf-8'))
    serializer = CloudFrontSignedURLSerializer(data=data)
    serializer.is_valid(raise_exception=True)
    key = serializer.validated_data["key"]
    expires_at = serializer.calculated_expiration()
    signed_url = cloudfront_signed_url(key=key, expires_at=expires_at)
    return JsonResponse({
        "url": signed_url,
        "expires_at": expires_at.isoformat(),
    })


class VideoViewSet(viewsets.ModelViewSet):
    queryset = Video.objects.all()
    serializer_class = VideoSerializer
