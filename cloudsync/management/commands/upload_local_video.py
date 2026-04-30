"""
Upload a locally-staged video file into the OVS upload bucket and kick off
transcoding for an existing Video record.

Used to recover Videos whose original ``stream_to_s3`` chain stalled — for
example when Dropbox starts gating shared links behind a sign-in wall and the
streaming download hangs. The operator manually downloads the file, then runs
this command pointing at the file and the existing Video's UUID.

By default the command refuses to overwrite an existing S3 object — pass
``--force`` to overwrite (e.g. when re-uploading the same Video after a
known-bad upload).
"""

import mimetypes
import os

import boto3
from botocore.exceptions import ClientError
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from cloudsync.tasks import transcode_from_s3
from ui.constants import VideoStatus
from ui.encodings import EncodingNames
from ui.models import Video, VideoFile


def _existing_object_size(bucket, key):
    """Return the size of an S3 object at ``key``, or None if it doesn't exist."""
    try:
        return bucket.Object(key).content_length
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") in {"404", "NoSuchKey"}:
            return None
        raise


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
        parser.add_argument(
            "--force",
            action="store_true",
            help=(
                "Overwrite an existing S3 object at the destination key. "
                "Without this, the command refuses to clobber an existing "
                "object — guards against typo'd --video-key."
            ),
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
        except ValidationError as exc:
            raise CommandError(
                f"Video key {options['video_key']!r} is invalid"
            ) from exc
        try:
            video_file = video.videofile_set.get(encoding=EncodingNames.ORIGINAL)
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

        bucket = boto3.resource("s3").Bucket(video_file.bucket_name)
        existing_size = _existing_object_size(bucket, video_file.s3_object_key)
        if existing_size is not None:
            note = f"S3 object already exists ({existing_size} bytes)"
            if options["force"]:
                self.stdout.write(
                    self.style.WARNING(f"  {note}; --force given, will overwrite.")
                )
            elif not options["dry_run"]:
                raise CommandError(
                    f"{note} at s3://{video_file.bucket_name}/{video_file.s3_object_key}. "
                    f"Re-run with --force to overwrite, "
                    f"or double-check --video-key {options['video_key']!r}."
                )
            else:
                self.stdout.write(f"  {note}; would require --force to overwrite.")

        if options["dry_run"]:
            self.stdout.write(
                self.style.WARNING("DRY-RUN: no upload, no transcode dispatch")
            )
            return

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
