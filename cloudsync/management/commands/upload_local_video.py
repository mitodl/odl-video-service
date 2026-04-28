"""
Upload a locally-staged video file into the OVS upload bucket and kick off
transcoding for an existing Video record.

Used to recover Videos whose original ``stream_to_s3`` chain stalled — for
example when Dropbox starts gating shared links behind a sign-in wall and the
streaming download hangs. The operator manually downloads the file, then runs
this command pointing at the file and the existing Video's UUID.
"""

import mimetypes
import os

import boto3
from django.core.management.base import BaseCommand, CommandError

from cloudsync.tasks import transcode_from_s3
from ui.constants import VideoStatus
from ui.models import Video, VideoFile


class Command(BaseCommand):
    """Upload a local video file for an existing Video and trigger transcode."""

    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument(
            "--video-key",
            required=True,
            help="UUID key of the existing Video to upload for",
        )
        parser.add_argument(
            "--file",
            required=True,
            help="Path to the local video file (must be readable inside this container)",
        )
        parser.add_argument(
            "--content-type",
            default=None,
            help=(
                "Override the S3 ContentType. Default: guess from filename "
                "extension, falling back to video/mp4."
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Look up the Video and print what would happen, but don't upload or dispatch.",
        )

    def handle(self, *args, **options):
        local_path = options["file"]
        if not os.path.isfile(local_path):
            raise CommandError(f"File not found: {local_path}")

        try:
            video = Video.objects.get(key=options["video_key"])
        except Video.DoesNotExist as exc:
            raise CommandError(
                f"Video with key {options['video_key']!r} not found"
            ) from exc

        try:
            video_file = video.videofile_set.get(encoding="original")
        except VideoFile.DoesNotExist as exc:
            raise CommandError(
                f"Video {video.id} has no VideoFile with encoding='original' — "
                f"it doesn't look like it was created through the upload pipeline."
            ) from exc

        content_type = (
            options["content_type"]
            or mimetypes.guess_type(local_path)[0]
            or "video/mp4"
        )
        size_mb = os.path.getsize(local_path) / (1024 * 1024)

        self.stdout.write(
            self.style.SUCCESS(
                f"Video id={video.id} key={video.key} status={video.status} "
                f"title={video.title!r}"
            )
        )
        self.stdout.write(
            f"  source: {local_path} ({size_mb:.1f} MB, ContentType={content_type})"
        )
        self.stdout.write(
            f"  target: s3://{video_file.bucket_name}/{video_file.s3_object_key}"
        )

        if options["dry_run"]:
            self.stdout.write(
                self.style.WARNING("DRY-RUN: no upload, no transcode dispatch")
            )
            return

        bucket = boto3.resource("s3").Bucket(video_file.bucket_name)
        with open(local_path, "rb") as fh:
            bucket.upload_fileobj(
                Fileobj=fh,
                Key=video_file.s3_object_key,
                ExtraArgs={"ContentType": content_type},
            )
        self.stdout.write(self.style.SUCCESS("Upload complete."))

        video.update_status(VideoStatus.CREATED)

        try:
            transcode_from_s3.si(video.id).delay()
        except Exception as exc:
            raise CommandError(
                f"Upload succeeded but failed to dispatch transcode for video {video.id}"
            ) from exc
        self.stdout.write(
            self.style.SUCCESS(f"Dispatched transcode_from_s3 for video {video.id}")
        )
