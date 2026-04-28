"""
Backfill VideoShorts from a CSV (local path or URL) into an OVS collection.

The CSV must contain the columns ``publication_date``, ``title``, and
``dropbox_link``. Rows are processed in ascending ``publication_date`` order so
that each created Video's ``created_at`` reflects the original publish order.

Each row is dispatched through the same code path used by the Dropbox Chooser
upload flow (``ui.api.process_dropbox_data``), which creates the Video and
VideoFile records and chains the streaming S3 upload + transcode Celery tasks.

Re-runs are safe: rows whose normalized Dropbox URL already exists as a Video
in the target collection are skipped, so a partially-completed run can be
resumed simply by re-invoking the command with the same CSV.

Existing Videos in a failed state are re-dispatched in place by default — no
new Video / VideoFile records are created — so a partial run can be resumed
just by re-running the command. A Video stuck in ``UPLOADING`` past
``--stuck-uploading-hours`` (default 6) is also treated as a failure and
re-dispatched through the full upload+transcode chain. Pass ``--skip-failed``
to disable retries entirely and skip any row whose Video already exists.

Two more operational flags help inspect and pace runs:

* ``--report-failures`` walks the CSV and prints status / EncodeJob details
  for any matching Videos in a failed state. Does no uploads.
* ``--throttle-seconds N`` sleeps N seconds between actual dispatches to keep
  Dropbox / boto3 / MediaConvert from being overwhelmed.
"""

import csv
import time
from collections import Counter
from datetime import timedelta
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import requests
from celery import chain
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.utils.dateparse import parse_date

from cloudsync import tasks
from ui import api, models
from ui.constants import VideoStatus

REQUIRED_COLUMNS = {"publication_date", "title", "dropbox_link"}

FAILED_STATUSES = frozenset(
    {
        VideoStatus.UPLOAD_FAILED,
        VideoStatus.TRANSCODE_FAILED_INTERNAL,
        VideoStatus.TRANSCODE_FAILED_VIDEO,
        VideoStatus.RETRANSCODE_FAILED,
        VideoStatus.ERROR,
    }
)


def _is_stuck_uploading(video, threshold):
    """
    Determine if a Video is stuck in UPLOADING for too long.
    """
    return (
        video.status == VideoStatus.UPLOADING
        and video.updated_at < timezone.now() - threshold
    )


def _normalize_dropbox_url(url):
    """Coerce a Dropbox share URL into a direct-download URL."""
    parsed = urlparse(url)
    hostname = (parsed.hostname or "").lower()
    if hostname != "dropbox.com" and not hostname.endswith(".dropbox.com"):
        return url

    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query["dl"] = "1"
    return urlunparse(parsed._replace(query=urlencode(query)))


def _read_csv_lines(source):
    """Read all CSV lines (decoded) from a local path or an HTTP(S) URL."""
    if source.startswith(("http://", "https://")):
        response = requests.get(source, timeout=60)
        response.raise_for_status()
        return response.text.splitlines()
    with open(source, encoding="utf-8") as fh:
        return fh.read().splitlines()


def _format_encode_job_message(message):
    """
    Pull the most useful AWS error fields out of an EncodeJob.message JSON.
    """
    if not isinstance(message, dict):
        return repr(message)
    job = message.get("Job") or message.get("detail") or {}
    code = job.get("ErrorCode") or job.get("errorCode")
    msg = job.get("ErrorMessage") or job.get("errorMessage")
    if code is not None or msg is not None:
        return f"ErrorCode={code} ErrorMessage={msg!r}"
    err = message.get("Error") or {}
    if err:
        return f"AWS Error: code={err.get('Code')} message={err.get('Message')!r}"
    return f"<message keys: {sorted(message.keys())}>"


class Command(BaseCommand):
    """Backfill VideoShorts into an OVS collection from a CSV."""

    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv",
            required=True,
            help="Path or URL to a CSV with columns: publication_date, title, dropbox_link",
        )
        parser.add_argument(
            "--collection-key",
            required=True,
            help="UUID key of the target Collection (the OVS shorts collection)",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Process only the first N rows (after publication_date sort)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate and print rows without creating Videos or dispatching tasks",
        )
        parser.add_argument(
            "--throttle-seconds",
            type=float,
            default=5.0,
            help=(
                "Seconds to sleep between dispatches (default 5). "
                "Skipped after the last row and in --dry-run / --report-failures."
            ),
        )
        parser.add_argument(
            "--report-failures",
            action="store_true",
            help=(
                "Inspect existing Videos for the CSV rows and print a report "
                "of those in a failed status (with EncodeJob details). "
                "Does not upload or dispatch anything."
            ),
        )
        parser.add_argument(
            "--skip-failed",
            action="store_true",
            help=(
                "Skip rows whose Video already exists, even if it's in a "
                "failed state. By default, failed Videos are re-dispatched "
                "in place (upload+transcode for UPLOAD_FAILED; transcode-only "
                "for the other failed states)."
            ),
        )
        parser.add_argument(
            "--stuck-uploading-hours",
            type=float,
            default=6.0,
            help=(
                "Treat a Video stuck in UPLOADING for longer than this many "
                "hours as a failure (default 6) — the worker likely died "
                "mid-upload and the chain will never complete on its own."
            ),
        )

    def handle(self, *args, **options):
        try:
            collection = models.Collection.objects.get(key=options["collection_key"])
        except models.Collection.DoesNotExist as exc:
            raise CommandError(
                f"Collection with key {options['collection_key']} not found"
            ) from exc

        rows = self._load_and_validate_rows(options["csv"])
        rows.sort(key=lambda row: row["_publication_date"])

        if options["limit"] is not None:
            rows = rows[: options["limit"]]

        if options["report_failures"]:
            self._report_failures(
                collection,
                rows,
                stuck_threshold=timedelta(hours=options["stuck_uploading_hours"]),
            )
            return

        self.stdout.write(
            self.style.SUCCESS(
                f"Processing {len(rows)} row(s) into collection "
                f"'{collection.title}' ({collection.key})"
            )
        )

        stuck_threshold = timedelta(hours=options["stuck_uploading_hours"])
        dispatched = 0
        retried = 0
        skipped = 0
        total = len(rows)
        for index, row in enumerate(rows, start=1):
            link = _normalize_dropbox_url(row["dropbox_link"])
            prefix = f"[{index}/{total}] {row['publication_date']} {row['title']}"
            existing = models.Video.objects.filter(
                collection=collection, source_url=link
            ).first()

            outcome = self._handle_row(
                existing=existing,
                collection=collection,
                link=link,
                title=row["title"],
                prefix=prefix,
                options=options,
                stuck_threshold=stuck_threshold,
            )
            if outcome == "created":
                dispatched += 1
            elif outcome == "retried":
                retried += 1
            else:
                skipped += 1

            is_last = index == total
            if (
                outcome in ("created", "retried")
                and not options["dry_run"]
                and not is_last
                and options["throttle_seconds"] > 0
            ):
                time.sleep(options["throttle_seconds"])

        verb = "previewed" if options["dry_run"] else "dispatched"
        self.stdout.write(
            self.style.SUCCESS(
                f"Done. {dispatched} new {verb}, {retried} retried, {skipped} skipped."
            )
        )

    def _handle_row(
        self, *, existing, collection, link, title, prefix, options, stuck_threshold
    ):
        """
        Decide what to do for one CSV row and (unless dry-run) dispatch.
        Returns one of: "created", "retried", "skipped".
        """
        if existing is None:
            if options["dry_run"]:
                self.stdout.write(f"DRY-RUN CREATE {prefix} -> {link}")
                return "created"
            try:
                api.process_dropbox_data(
                    {
                        "collection": str(collection.key),
                        "files": [{"link": link, "name": title}],
                    }
                )
            except Exception as exc:
                raise CommandError(
                    f"Failed to dispatch create for {prefix} -> {link}"
                ) from exc
            self.stdout.write(self.style.SUCCESS(f"DISPATCHED {prefix}"))
            return "created"

        is_stuck = _is_stuck_uploading(existing, stuck_threshold)
        is_failure = existing.status in FAILED_STATUSES or is_stuck

        if not is_failure or options["skip_failed"]:
            note = "stuck-uploading" if is_stuck else f"status={existing.status}"
            self.stdout.write(self.style.WARNING(f"SKIP (exists, {note}) {prefix}"))
            return "skipped"

        needs_upload = existing.status == VideoStatus.UPLOAD_FAILED or is_stuck
        if needs_upload:
            mode = "RETRY upload+transcode"
            if is_stuck:
                mode += " (stuck UPLOADING)"
        else:
            # transcode-only retry covers TRANSCODE_FAILED_INTERNAL,
            # TRANSCODE_FAILED_VIDEO, RETRANSCODE_FAILED, and ERROR.
            # The S3 original is already in place.
            mode = "RETRY transcode"

        if options["dry_run"]:
            self.stdout.write(f"DRY-RUN {mode} (was {existing.status}) {prefix}")
            return "retried"

        # Reset to CREATED before re-dispatch — transcode_video skips its
        # status flip for *_FAILED states (cloudsync/api.py), so without
        # this the operator-visible status never moves off "...failed".
        prior_status = existing.status
        existing.update_status(VideoStatus.CREATED)
        try:
            if needs_upload:
                chain(
                    tasks.stream_to_s3.s(existing.id),
                    tasks.transcode_from_s3.si(existing.id),
                ).delay()
            else:
                tasks.transcode_from_s3.si(existing.id).delay()
        except Exception as exc:
            raise CommandError(
                f"Failed to dispatch retry for video {existing.id} "
                f"(was {prior_status!r})"
            ) from exc
        self.stdout.write(self.style.SUCCESS(f"{mode} {prefix}"))
        return "retried"

    def _report_failures(self, collection, rows, *, stuck_threshold):
        """Walk the CSV and print failure details for any matching Videos."""
        counts = Counter()
        examined = 0
        total = len(rows)
        for index, row in enumerate(rows, start=1):
            link = _normalize_dropbox_url(row["dropbox_link"])
            video = models.Video.objects.filter(
                collection=collection, source_url=link
            ).first()
            if video is None:
                continue
            examined += 1
            stuck = _is_stuck_uploading(video, stuck_threshold)
            if video.status not in FAILED_STATUSES and not stuck:
                continue

            label = "stuck-uploading" if stuck else video.status
            counts[label] += 1
            prefix = f"[{index}/{total}] {row['publication_date']} {row['title']}"
            self.stdout.write(self.style.ERROR(prefix))
            status_line = f"        video_id: {video.id}  status: {video.status}"
            if stuck:
                age = timezone.now() - video.updated_at
                hours = age.total_seconds() / 3600
                status_line += f"  (stuck {hours:.1f}h)"
            self.stdout.write(status_line)

            jobs = list(video.encode_jobs.all())
            if jobs:
                self.stdout.write(f"        encode_jobs: {len(jobs)}")
                for job in jobs:
                    detail = _format_encode_job_message(job.message)
                    self.stdout.write(
                        f"          - id={job.id}  state={job.get_state_display()}"
                        f"  {detail}"
                    )
            elif video.status in (VideoStatus.UPLOAD_FAILED, VideoStatus.UPLOADING):
                self.stdout.write(
                    "        (no EncodeJob — inspect celery / Sentry logs)"
                )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"Examined {examined} existing Video(s) of {total} row(s); "
                f"{sum(counts.values())} in a failed state."
            )
        )
        for status, count in sorted(counts.items()):
            self.stdout.write(f"  {status}: {count}")

    def _load_and_validate_rows(self, source):
        """Read, validate, and parse all CSV rows up-front so we fail fast."""
        reader = csv.DictReader(_read_csv_lines(source))
        if reader.fieldnames is None:
            raise CommandError(f"CSV at {source} is empty")
        missing = REQUIRED_COLUMNS - set(reader.fieldnames)
        if missing:
            raise CommandError(f"CSV is missing required column(s): {sorted(missing)}")

        rows = []
        for line_no, row in enumerate(reader, start=2):
            parsed_date = parse_date((row.get("publication_date") or "").strip())
            if parsed_date is None:
                raise CommandError(
                    f"Row {line_no}: unparseable publication_date "
                    f"{row.get('publication_date')!r} (expected YYYY-MM-DD)"
                )
            if not (row.get("title") or "").strip():
                raise CommandError(f"Row {line_no}: title is empty")
            if not (row.get("dropbox_link") or "").strip():
                raise CommandError(f"Row {line_no}: dropbox_link is empty")
            row["_publication_date"] = parsed_date
            row["title"] = row["title"].strip()
            row["dropbox_link"] = row["dropbox_link"].strip()
            rows.append(row)
        return rows
