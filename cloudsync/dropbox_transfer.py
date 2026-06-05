"""
Resumable, bounded-memory transfer of a Dropbox shared-link file to S3.

``stream_to_s3`` historically piped Dropbox -> S3 in lockstep over a single connection with a
60s read timeout and no retries, so any mid-transfer stall permanently failed multi-GB uploads.
This module instead drives an S3 multipart upload by fetching the source in byte ranges, so a
stall costs a single part re-fetch (~one ``part_size``) rather than restarting the whole upload.
"""

import contextlib
import math
import random
import re
import time

import requests
import structlog
from botocore.exceptions import ClientError

log = structlog.get_logger(__name__)

# S3 requires every part except the last to be at least 5 MiB.
S3_MIN_PART_SIZE = 5 * 1024 * 1024


class TransferError(Exception):
    """Raised when the source returns an unexpected response and cannot be transferred."""


@contextlib.contextmanager
def upload_lock(redis_client, lock_key, ttl):
    """
    Best-effort distributed lock serializing concurrent runs of the same upload.

    Under ``acks_late`` a long upload can be redelivered to a second worker while the first is
    still running; this lock keeps them from racing the same multipart upload. Yields ``True``
    if acquired (and releases on exit), ``False`` otherwise.
    """
    acquired = bool(redis_client.set(lock_key, b"1", nx=True, ex=ttl))
    try:
        yield acquired
    finally:
        if acquired:
            try:
                redis_client.delete(lock_key)
            except Exception:  # noqa: BLE001 - releasing the lock must never mask the result
                log.warning("failed to release upload lock", lock_key=lock_key)


class DropboxToS3Transfer:
    """
    Transfer a remote file to S3 by fetching it in byte ranges and uploading multipart.

    The caller supplies ``content_type`` and ``total`` (typically read from the source's
    response headers); ``total`` may be ``None``, in which case it is discovered from a
    ranged request's ``Content-Range``.
    """

    def __init__(
        self,
        *,
        source_url,
        bucket,
        key,
        content_type,
        total,
        s3_client,
        part_size,
        session=None,
        max_range_attempts=5,
        connect_timeout=30,
        read_timeout=120,
        backoff_base=2,
        backoff_max=60,
        progress_callback=None,
    ):
        self.source_url = source_url
        self.bucket = bucket
        self.key = key
        self.content_type = content_type
        self.total = total
        self.s3 = s3_client
        self.part_size = max(part_size, S3_MIN_PART_SIZE)
        self.session = session or requests.Session()
        self.max_range_attempts = max_range_attempts
        self.timeout = (connect_timeout, read_timeout)
        self.backoff_base = backoff_base
        self.backoff_max = backoff_max
        self.progress_callback = progress_callback
        self.bytes_done = 0

    def run(self):
        """Transfer the source to S3, choosing the single-PUT or multipart path by size."""
        total = self.total if self.total is not None else self._discover_total()
        if total <= self.part_size:
            self._put_single(total)
        else:
            self._multipart(total)

    def _put_single(self, total):
        """Upload a small file in one PUT."""
        body = self._fetch_range(0, total - 1)
        self.s3.put_object(
            Bucket=self.bucket, Key=self.key, Body=body, ContentType=self.content_type
        )
        self._report(len(body), total)

    def _multipart(self, total):
        """Upload a large file as an S3 multipart upload, one byte range per part."""
        num_parts = math.ceil(total / self.part_size)
        upload_id, completed = self._resume_or_create(num_parts)
        try:
            parts = {n: etag for n, (etag, _size) in completed.items()}
            self.bytes_done = sum(size for _etag, size in completed.values())
            for part_number in range(1, num_parts + 1):
                if part_number in parts:
                    continue
                start = (part_number - 1) * self.part_size
                end = min(start + self.part_size, total) - 1
                body = self._fetch_range(start, end)
                response = self.s3.upload_part(
                    Bucket=self.bucket,
                    Key=self.key,
                    PartNumber=part_number,
                    UploadId=upload_id,
                    Body=body,
                )
                parts[part_number] = response["ETag"]
                self.bytes_done += len(body)
                self._report(self.bytes_done, total)
            self.s3.complete_multipart_upload(
                Bucket=self.bucket,
                Key=self.key,
                UploadId=upload_id,
                MultipartUpload={
                    "Parts": [
                        {"PartNumber": n, "ETag": parts[n]} for n in sorted(parts)
                    ]
                },
            )
        except Exception:
            # Drop already-uploaded parts so they don't linger and incur storage cost.
            # A hard worker kill bypasses this; the bucket lifecycle rule is the backstop.
            self._abort(upload_id)
            raise

    def _resume_or_create(self, num_parts):
        """
        Adopt an in-progress multipart upload for this key if one exists, else create one.

        Returns ``(upload_id, completed)`` where ``completed`` maps part number ->
        ``(etag, size)`` for parts already uploaded. Older duplicate uploads for the key are
        aborted; an adopted upload whose part sizes no longer match ``part_size`` is discarded
        and restarted so byte boundaries stay aligned.
        """
        existing = self._existing_uploads_for_key()
        if existing:
            chosen = existing[0]["UploadId"]
            for older in existing[1:]:
                self._abort(older["UploadId"])
            completed = self._completed_parts(chosen)
            if self._has_size_drift(completed, num_parts):
                log.info("multipart part size drift; restarting upload", key=self.key)
                self._abort(chosen)
            else:
                return chosen, completed
        return self._create_upload(), {}

    def _existing_uploads_for_key(self):
        """In-progress multipart uploads for this exact key, newest first."""
        response = self.s3.list_multipart_uploads(Bucket=self.bucket, Prefix=self.key)
        uploads = [u for u in response.get("Uploads", []) if u["Key"] == self.key]
        return sorted(uploads, key=lambda u: u["Initiated"], reverse=True)

    def _completed_parts(self, upload_id):
        """Map of part number -> (etag, size) for parts already uploaded to ``upload_id``."""
        parts = {}
        marker = 0
        while True:
            response = self.s3.list_parts(
                Bucket=self.bucket,
                Key=self.key,
                UploadId=upload_id,
                PartNumberMarker=marker,
            )
            for part in response.get("Parts", []):
                parts[part["PartNumber"]] = (part["ETag"], part["Size"])
            if not response.get("IsTruncated"):
                return parts
            marker = response["NextPartNumberMarker"]

    def _has_size_drift(self, completed, num_parts):
        """True if any non-final completed part no longer matches the configured part size."""
        for part_number, (_etag, size) in completed.items():
            if part_number > num_parts:
                return True
            if part_number < num_parts and size != self.part_size:
                return True
        return False

    def _create_upload(self):
        """Create a new multipart upload and return its id."""
        return self.s3.create_multipart_upload(
            Bucket=self.bucket, Key=self.key, ContentType=self.content_type
        )["UploadId"]

    def _abort(self, upload_id):
        """Abort a multipart upload, logging (not raising) if the abort itself fails."""
        try:
            self.s3.abort_multipart_upload(
                Bucket=self.bucket, Key=self.key, UploadId=upload_id
            )
        except ClientError:
            log.exception("failed to abort multipart upload", key=self.key)

    def _fetch_range(self, start, end):
        """
        Fetch ``bytes=start-end`` from the source with retries and exponential backoff.

        Each attempt re-requests the stable ``source_url`` and follows its redirect, so an
        expired signed CDN URL is re-resolved for free. The last error is raised once the
        attempt budget is exhausted (e.g. a permanently revoked link).
        """
        headers = {"Range": f"bytes={start}-{end}"}
        last_error = None
        for attempt in range(1, self.max_range_attempts + 1):
            try:
                response = self.session.get(
                    self.source_url, headers=headers, timeout=self.timeout
                )
                if response.status_code not in (200, 206):
                    raise TransferError(
                        f"unexpected status {response.status_code} for bytes {start}-{end}"
                    )
                return response.content
            except (requests.exceptions.RequestException, TransferError) as exc:
                last_error = exc
                if attempt >= self.max_range_attempts:
                    break
                log.warning(
                    "retrying dropbox range fetch",
                    start=start,
                    end=end,
                    attempt=attempt,
                    error=str(exc),
                )
                self._sleep_backoff(attempt)
        raise last_error

    def _sleep_backoff(self, attempt):
        """Sleep for an exponentially growing, jittered delay before the next attempt."""
        delay = min(self.backoff_max, self.backoff_base * (2 ** (attempt - 1)))
        time.sleep(delay + random.uniform(0, delay / 2))

    def _discover_total(self):
        """Determine the total size from a ranged request's Content-Range header."""
        response = self.session.get(
            self.source_url, headers={"Range": "bytes=0-0"}, timeout=self.timeout
        )
        match = re.match(
            r"bytes \d+-\d+/(\d+)", response.headers.get("Content-Range", "")
        )
        if not match:
            raise TransferError("could not determine total size of source")
        return int(match.group(1))

    def _report(self, uploaded, total):
        """Invoke the progress callback, if any, with cumulative bytes and the total."""
        if self.progress_callback:
            self.progress_callback(uploaded, total)
