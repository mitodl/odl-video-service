import os
import json
import iso8601
import boto3
from datetime import datetime, timedelta
from django.views.decorators.http import require_POST
from django.shortcuts import render
from django.http import JsonResponse
from cloudsync.tasks import stream_to_s3
from ui.util import cloudfront_signed_url


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
    dropbox_files = json.loads(request.body.decode('utf-8'))
    results = {
        dropbox_file['name']: stream_to_s3.delay(dropbox_file['link'])
        for dropbox_file in dropbox_files
    }
    return JsonResponse({
        name: result.id
        for name, result in results.items()
    })


@require_POST
def generate_signed_url(request):
    data = json.loads(request.body.decode('utf-8'))
    if "key" not in data:
        return JsonResponse({
            "message": 'missing "key"'
        }, status_code=400)
    key = data["key"]
    if "expires_at" in data:
        expires_at = iso8601.parse_date(data["expires_at"])
    else:
        expires_at = datetime.utcnow() + timedelta(hours=2)
    signed_url = cloudfront_signed_url(key=key, expires_at=expires_at)
    return JsonResponse({
        "url": signed_url,
        "expires_at": expires_at.isoformat(),
    })
