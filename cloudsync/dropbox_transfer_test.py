"""Tests for cloudsync.dropbox_transfer (resumable Dropbox -> S3 transfer)."""

import os
import re

import boto3
import pytest
import requests
from moto import mock_aws

from cloudsync.dropbox_transfer import DropboxToS3Transfer, upload_lock

SRC = "https://www.dropbox.com/scl/fi/abc123/video.mp4?rlkey=k&dl=1"
BUCKET = "test-upload-bucket"
KEY = "abcd1234/video.mp4"
PART = 5 * 1024 * 1024  # S3 minimum part size, keeps test bodies small


@pytest.fixture
def s3_client():
    """A moto-backed S3 client with the upload bucket already created."""
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket=BUCKET)
        yield client


def register_ranged(reqmock, url, body, content_type="application/binary"):
    """Register a Dropbox-like endpoint: 206 + Content-Range for Range requests, 200 otherwise."""

    def _callback(request, context):
        rng = request.headers.get("Range")
        if rng:
            match = re.match(r"bytes=(\d+)-(\d+)", rng)
            start, end = int(match.group(1)), int(match.group(2))
            chunk = body[start : end + 1]
            context.status_code = 206
            context.headers["Content-Range"] = f"bytes {start}-{end}/{len(body)}"
            context.headers["Accept-Ranges"] = "bytes"
            context.headers["Content-Type"] = content_type
            return chunk
        context.status_code = 200
        context.headers["Content-Type"] = content_type
        return body

    reqmock.get(url, content=_callback)


def make_transfer(s3_client, *, total, part_size=PART, **kwargs):
    """Construct a transfer with test defaults."""
    return DropboxToS3Transfer(
        source_url=SRC,
        bucket=BUCKET,
        key=KEY,
        content_type="video/mp4",
        total=total,
        s3_client=s3_client,
        part_size=part_size,
        **kwargs,
    )


def ranges_requested(reqmock):
    """The list of Range header values across all requests, in order."""
    return [
        r.headers["Range"] for r in reqmock.request_history if r.headers.get("Range")
    ]


def test_small_file_uses_put_object(s3_client, reqmocker):
    """A file at or below the part size is uploaded in a single PUT, no multipart."""
    body = os.urandom(2000)
    register_ranged(reqmocker, SRC, body)

    make_transfer(s3_client, total=len(body)).run()

    obj = s3_client.get_object(Bucket=BUCKET, Key=KEY)
    assert obj["Body"].read() == body
    assert obj["ContentType"] == "video/mp4"
    # no multipart upload was created
    assert s3_client.list_multipart_uploads(Bucket=BUCKET).get("Uploads", []) == []


def test_large_file_multipart_assembles_correctly(s3_client, reqmocker):
    """A multi-part file is fetched by range and reassembled byte-for-byte in S3."""
    body = os.urandom(PART * 2 + 1234)  # three parts: two full + remainder
    register_ranged(reqmocker, SRC, body)

    make_transfer(s3_client, total=len(body)).run()

    obj = s3_client.get_object(Bucket=BUCKET, Key=KEY)
    assert obj["Body"].read() == body
    # ContentType comes from the passed value, not the ranged "application/binary"
    assert obj["ContentType"] == "video/mp4"


def test_fetches_correct_byte_ranges(s3_client, reqmocker):
    """Each part requests the exact, contiguous byte range."""
    total = PART * 2 + 10
    register_ranged(reqmocker, SRC, os.urandom(total))

    make_transfer(s3_client, total=total).run()

    assert ranges_requested(reqmocker) == [
        f"bytes=0-{PART - 1}",
        f"bytes={PART}-{2 * PART - 1}",
        f"bytes={2 * PART}-{total - 1}",
    ]


def test_progress_callback_reports_cumulative(s3_client, reqmocker):
    """The progress callback is invoked with cumulative bytes uploaded and the total."""
    total = PART * 2
    register_ranged(reqmocker, SRC, os.urandom(total))
    calls = []

    make_transfer(
        s3_client,
        total=total,
        progress_callback=lambda up, tot: calls.append((up, tot)),
    ).run()

    assert calls[-1] == (total, total)
    assert [up for up, _ in calls] == [PART, total]


# --- C1: within-execution resilience (per-range retry, abort cleanup, redirects) ---


def test_retries_range_on_transient_error_then_succeeds(s3_client, reqmocker, mocker):
    """A transient error on a range is retried, and only that range is re-fetched."""
    sleep = mocker.patch("cloudsync.dropbox_transfer.time.sleep")
    body = os.urandom(2000)
    reqmocker.get(
        SRC,
        [
            {"exc": requests.exceptions.ConnectionError},
            {"content": body, "status_code": 206},
        ],
    )

    make_transfer(s3_client, total=len(body), max_range_attempts=3).run()

    assert s3_client.get_object(Bucket=BUCKET, Key=KEY)["Body"].read() == body
    sleep.assert_called_once()


def test_exhausted_retries_aborts_multipart_and_raises(s3_client, reqmocker, mocker):
    """When retries are exhausted mid-upload, the multipart upload is aborted and the error raised."""
    mocker.patch("cloudsync.dropbox_transfer.time.sleep")
    reqmocker.get(SRC, exc=requests.exceptions.ConnectionError)

    with pytest.raises(requests.exceptions.RequestException):
        make_transfer(s3_client, total=PART * 2, max_range_attempts=2).run()

    # no orphaned in-progress multipart upload is left behind
    assert s3_client.list_multipart_uploads(Bucket=BUCKET).get("Uploads", []) == []


def test_follows_redirect_preserving_range_header(s3_client, reqmocker):
    """The Range header survives Dropbox's 302 to the signed CDN URL."""
    cdn = "https://abc.dl.dropboxusercontent.com/cd/0/get/xyz/file?dl=1"
    body = os.urandom(2000)
    reqmocker.get(SRC, status_code=302, headers={"Location": cdn})
    register_ranged(reqmocker, cdn, body)

    make_transfer(s3_client, total=len(body)).run()

    assert s3_client.get_object(Bucket=BUCKET, Key=KEY)["Body"].read() == body
    cdn_requests = [r for r in reqmocker.request_history if r.url.startswith(cdn[:40])]
    assert (
        cdn_requests
        and cdn_requests[0].headers.get("Range") == f"bytes=0-{len(body) - 1}"
    )


# --- C2: cross-execution resume + size discovery ---


def test_resumes_existing_multipart_upload(s3_client, reqmocker):
    """An interrupted upload resumes: completed parts are kept, only missing parts re-fetched."""
    body = os.urandom(PART * 3)  # exactly three parts
    create = s3_client.create_multipart_upload(
        Bucket=BUCKET, Key=KEY, ContentType="video/mp4"
    )
    uid = create["UploadId"]
    s3_client.upload_part(
        Bucket=BUCKET, Key=KEY, PartNumber=1, UploadId=uid, Body=body[0:PART]
    )
    s3_client.upload_part(
        Bucket=BUCKET, Key=KEY, PartNumber=2, UploadId=uid, Body=body[PART : 2 * PART]
    )
    register_ranged(reqmocker, SRC, body)

    make_transfer(s3_client, total=len(body)).run()

    # only the missing third part is fetched
    assert ranges_requested(reqmocker) == [f"bytes={2 * PART}-{3 * PART - 1}"]
    # object assembles correctly from the two pre-seeded parts plus the fetched one
    assert s3_client.get_object(Bucket=BUCKET, Key=KEY)["Body"].read() == body


def test_multiple_uploads_for_key_resolved_to_one(s3_client, reqmocker):
    """When several in-progress uploads exist for the key, the run leaves none behind."""
    body = os.urandom(PART * 2)
    s3_client.create_multipart_upload(Bucket=BUCKET, Key=KEY, ContentType="video/mp4")
    s3_client.create_multipart_upload(Bucket=BUCKET, Key=KEY, ContentType="video/mp4")
    assert len(s3_client.list_multipart_uploads(Bucket=BUCKET)["Uploads"]) == 2
    register_ranged(reqmocker, SRC, body)

    make_transfer(s3_client, total=len(body)).run()

    assert s3_client.list_multipart_uploads(Bucket=BUCKET).get("Uploads", []) == []
    assert s3_client.get_object(Bucket=BUCKET, Key=KEY)["Body"].read() == body


def test_part_size_drift_restarts_fresh(s3_client, reqmocker):
    """A completed part whose size no longer matches part_size forces a clean restart."""
    body = os.urandom(PART * 2 + 100)  # three parts at PART
    create = s3_client.create_multipart_upload(
        Bucket=BUCKET, Key=KEY, ContentType="video/mp4"
    )
    # part 1 is not the last part but is the wrong size -> boundaries no longer align
    s3_client.upload_part(
        Bucket=BUCKET,
        Key=KEY,
        PartNumber=1,
        UploadId=create["UploadId"],
        Body=os.urandom(PART + 1024 * 1024),
    )
    register_ranged(reqmocker, SRC, body)

    make_transfer(s3_client, total=len(body)).run()

    # all three parts re-fetched from scratch
    assert len(ranges_requested(reqmocker)) == 3
    assert s3_client.get_object(Bucket=BUCKET, Key=KEY)["Body"].read() == body


def test_discovers_total_when_not_provided(s3_client, reqmocker):
    """With total=None the size is discovered from a ranged request's Content-Range."""
    body = os.urandom(2000)
    register_ranged(reqmocker, SRC, body)

    make_transfer(s3_client, total=None).run()

    assert s3_client.get_object(Bucket=BUCKET, Key=KEY)["Body"].read() == body


# --- upload lock (serializes concurrent runs of the same upload under acks_late) ---


class FakeRedis:
    """Minimal redis stand-in for the lock: set() returns truthy only when it 'acquires'."""

    def __init__(self, acquire=True):
        self._acquire = acquire
        self.set_calls = []
        self.deleted = []

    def set(self, key, value, nx=False, ex=None):  # noqa: A003
        self.set_calls.append((key, value, nx, ex))
        return True if self._acquire else None

    def delete(self, key):
        self.deleted.append(key)


def test_upload_lock_acquired_yields_true_and_releases():
    """When the lock is acquired it yields True and is released on exit."""
    redis = FakeRedis(acquire=True)
    with upload_lock(redis, "lock-key", 60) as acquired:
        assert acquired is True
    assert redis.set_calls == [("lock-key", b"1", True, 60)]
    assert redis.deleted == ["lock-key"]


def test_upload_lock_not_acquired_yields_false_and_does_not_release():
    """When the lock is already held it yields False and does not delete the key."""
    redis = FakeRedis(acquire=False)
    with upload_lock(redis, "lock-key", 60) as acquired:
        assert acquired is False
    assert redis.deleted == []
