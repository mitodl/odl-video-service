# Resumable Dropbox → S3 Transfer for `stream_to_s3`

**Status:** Draft — design approved 2026-06-04, pending implementation plan.
**Author:** Matt Bertrand (with Claude Code)
**Sentry issue:** [ODL-VIDEO-SERVICE-3AK](https://mit-office-of-digital-learning.sentry.io/issues/ODL-VIDEO-SERVICE-3AK)

## 1. Problem

Dropbox uploads frequently fail in production with:

```
ReadTimeoutError: HTTPSConnectionPool(host='dl.dropboxusercontent.com', port=443): Read timed out.
  cloudsync/tasks.py:138 in stream_to_s3
```

`stream_to_s3` (`cloudsync/tasks.py:93-148`) is a **single-connection passthrough pipe**: it opens one streaming `requests.get(source_url, stream=True, timeout=60)` and hands the raw socket straight to S3 via `bucket.upload_fileobj(Fileobj=response.raw, ...)`. One Celery worker therefore holds an open Dropbox connection for the entire transfer of a multi-GB file, pulling bytes from Dropbox and pushing them to S3 in lockstep.

### Root cause

1. **The 60s timeout is a per-read gap limit, not a total budget.** With `stream=True`, the clock resets on each socket read but trips if Dropbox goes >60s without sending the next chunk. Over a long transfer the probability of *at least one* such stall approaches 1, so failures cluster on large files and during any Dropbox slowness/throttling.
2. **Zero retries.** `stream_to_s3` is a plain `@shared_task` with no `autoretry_for`/`max_retries`. A single transient `ReadTimeoutError` permanently sets `UPLOAD_FAILED`; recovery is manual (`cloudsync/management/commands/upload_local_video.py`).
3. **Restart-from-zero.** Even with a retry, `response.raw` is forward-only, so any retry re-downloads the whole file from byte 0.

### Evidence (Sentry issue ODL-VIDEO-SERVICE-3AK)

- **17 events, first seen 2026-06-03 14:58, last 2026-06-04 20:20** — a sudden spike, 16 in a ~4h burst on 6/3.
- **Spans releases 0.90.1, 0.91.0, 0.92.0** → not a code regression; environmental.
- **Bursts contain simultaneous failures** (3 events at `16:14:39`, 2 at `18:17:04`, distinct `celery_task_id`s) → signature of a **batch upload**: `add_videos_from_dropbox` (`ui/api.py:35-52`) fires one `stream_to_s3` chain per submitted link, all at once. Sample file: `..._OL_DELTA_Open_Seminar_Series_..._04.mp4`.
- **The crash event shows `response: <Response [200]>` and `content_type: 'video/mp4'`**, with the timeout firing deep in the S3 multipart read loop (`s3transfer/upload.py → fileobj.read() → urllib3 … Read timed out`). The download is a **valid 200 that stalls mid-body** — *not* a sign-in-wall HTML interstitial. (This contradicts the hypothesis in `upload_local_video.py`'s docstring; gating is not what is firing here.)
- **Single worker, embedded beat:** `server_name: ovs-celery-…`, `sys.argv: celery -A odl_video worker -B`. No `--concurrency` flag and no queue routing/rate limits exist anywhere in `odl_video/settings.py`. Total simultaneous Dropbox pulls ≈ `replicas × prefork-concurrency`, unbounded.

**Synthesis:** a batch of large videos streams through workers as lockstep Dropbox→S3 pipes. Under concurrent load (and likely Dropbox throttling the burst), Dropbox pauses mid-file >60s, urllib3 raises `ReadTimeoutError`, and with zero retries every transient stall becomes a permanent `UPLOAD_FAILED`. The links are valid, which is exactly why a resumable, retrying transfer fixes it.

### Why not "add more workers"

It does not touch the zero-retry bug, the bottleneck is the throttled remote (not local CPU), and more workers means *more* simultaneous Dropbox pulls → harder throttling → more timeouts. The lever that helps is capping concurrency, not raising it.

### Why not "download to local disk first" (approach B)

The current code already streams with bounded memory (`upload_fileobj` + `TransferConfig` read `response.raw` in ~256 KB IO chunks and upload 32 MB parts, ≤10 in flight — peak a few hundred MB, never the whole file). Downloading whole multi-GB files to ephemeral pod disk would *add* a resource requirement we don't have today — a regression. Rejected.

## 2. Feasibility verification

A live probe of a real Dropbox `/scl/fi/...?dl=1` link with a **non-zero** range:

```
curl -sS -L -H 'Range: bytes=1048576-2097151' <source_url>
→ 302 → https://<id>.dl.dropboxusercontent.com/cd/0/get/...
→ HTTP/2 206
   accept-ranges: bytes
   content-range: bytes 1048576-2097151/5142852467
   content-length: 1048576       # exactly 1 MiB at the requested offset
```

Confirms: Dropbox honors true offset ranges (`206` + `Accept-Ranges` + correct `Content-Range`), the `Range` header survives the 302 redirect, and the sample file is **~4.79 GB** — restart-from-zero on these is genuinely costly. S3 multipart `upload_part` consumes arbitrary byte buffers. **C is buildable end-to-end.**

Three facts the probe surfaced that the design must handle:
- The `dl=1` link 302-redirects to an **ephemeral signed CDN URL** (`/cd/0/get/...`).
- Ranged responses return `content-type: application/binary`, not the real type.
- Pasted links carry an expiring `st=` token (confirm what `video.source_url` actually stores in prod — the Dropbox Chooser usually stores a stable `rlkey` link without `st`).

## 3. Goals / Non-goals

**Goals**
- A mid-transfer stall costs a single part re-fetch (~32 MB), not a full multi-GB restart.
- A worker kill / deploy mid-upload resumes from completed parts on redelivery.
- Bounded memory (~one part) regardless of file size; no whole-file disk usage.
- Preserve the existing progress bar, task signature, chain call sites, and status transitions.

**Non-goals**
- Switching off Dropbox shared links to the Dropbox API (separate effort).
- Global Celery queue/concurrency redesign (a `_PART_CONCURRENCY` knob defaulting to 1 is included; broader routing is out of scope).
- Fixing transcode-side transfers in `cloudsync/api.py`.

## 4. Chosen approach: C1 + C2

Replace the lockstep pipe with a **resumable, bounded-memory, part-by-part transfer** driven by ranged Dropbox GETs into a manually managed S3 multipart upload, with retries/backoff on every ranged fetch. Build **both** within-execution resume (C1) and cross-execution resume (C2).

## 5. Architecture & module boundaries

- **New module `cloudsync/dropbox_transfer.py`** — a `DropboxToS3Transfer` class holding transfer state (upload id, completed parts, bytes done) with a single `run()` entry point. Dependencies (boto3 S3 **client**, a `requests.Session`) are injected for testability. Uses `boto3.client("s3")` because the multipart API (`create_multipart_upload`, `upload_part`, `complete_multipart_upload`, `abort_multipart_upload`, `list_multipart_uploads`, `list_parts`) lives on the client, not the `Bucket` resource used today.
- **`stream_to_s3` (`cloudsync/tasks.py:93`) stays the thin orchestrator**: load `Video`, set `UPLOADING`, build the progress callback, call the transfer, map success/failure onto `VideoStatus` + `update_state`. Signature and call sites (`ui/api.py:51`, `ui/api.py:96`, `cloudsync/management/commands/backfill_shorts.py:304`) unchanged.
- **`parse_content_metadata` (`cloudsync/tasks.py:363`) hardened**: read `Content-Disposition`/`Content-Type` via `.get()` instead of `[]`, incidentally fixing the separate `KeyError: 'content-disposition'` issue (ODL-VIDEO-SERVICE-39C).
- **`AWS_S3_UPLOAD_TRANSFER_CONFIG` untouched** — still used by three call sites in `cloudsync/api.py`.

## 6. Transfer algorithm (data flow)

```
1. Resolve metadata: GET source_url (stream=True), read headers only
   → content_type, total (Content-Length), file_name; close without reading body.
   Fallback if Content-Length missing: ranged GET bytes=0-0, read total from Content-Range.
   Fallback if total still unknown: legacy single streaming upload_fileobj (defensive).

2. Small-file path: if total <= part_size → single GET + put_object(ContentType); done.
   (No multipart, so resume discovery is skipped.)

3. Resume discovery (see §7): adopt an in-progress multipart upload for this Key if one exists.

4. create_multipart_upload(Bucket, Key, ContentType) → UploadId   (unless resuming)

5. For part_number 1..N, SEQUENTIALLY (part_size default 32 MB, enforced >= 5 MiB),
   skipping part_numbers already completed:
     start = (part_number-1)*part_size; end = min(start+part_size, total)-1
     buf  = fetch_range(source_url, start, end)        # retries — §8
     etag = upload_part(PartNumber, UploadId, Body=buf)
     record {PartNumber, ETag}; bytes_done += len(buf)
     update_state("PROGRESS", {"uploaded": bytes_done, "total": total})

6. complete_multipart_upload(UploadId, Parts=[ordered {PartNumber, ETag}])
```

**Deliberate choices**
- **Sequential parts (default `_PART_CONCURRENCY=1`).** Bursty 32 MB fetches replace one sustained stream and avoid re-creating the Dropbox throttling that caused the incident. The knob exists but raising it is documented as risky.
- **Always GET the stable `source_url` with the `Range` header and follow the 302.** This auto-refreshes the ephemeral signed CDN URL on every part (probe confirmed `Range` survives the redirect), so no URL caching/expiry handling is needed. Content-type comes from step 1, never the `application/binary` ranged 206.
- **S3 limits:** part ≥ 5 MiB except the last, ≤ 10,000 parts; at 32 MB that caps objects at 320 GB (ample).

## 7. Resumability

### C1 — within-execution
Per-range retry inside one task run (§8). A stall on part K re-fetches only part K. No persistence, no Celery semantics change. Fully covers the observed mid-transfer-stall failure mode.

### C2 — cross-execution
`stream_to_s3` start sequence:

```
1. Resolve metadata (total, content_type).
2. list_multipart_uploads(Bucket, Prefix=Key); match Key == video.get_s3_key():
     - several matches → adopt MOST-RECENTLY-INITIATED, abort the older ones.
     - adopted → list_parts() → completed {PartNumber, ETag, Size}.
3. Part-size drift guard: if any completed part's Size != configured part_size
   (except the last) → abort & start fresh (config changed between runs).
4. Transfer loop (§6) skipping completed part_numbers; reuse existing ETags.
5. complete with existing + new ETags.
```

- **Celery semantics:** set `acks_late=True` + `reject_on_worker_lost=True` on `stream_to_s3` so a worker killed mid-upload redelivers the task and step 2 resumes from S3. The task can therefore run twice; resume is idempotent, so this is safe.
- **Double-run guard:** a Redis `SET nx ex` lock keyed on the video Key (TTL’d), using the Redis already configured as broker/result backend, prevents two concurrent runs racing the same UploadId under `acks_late`. The transfer runs inside the lock; if the lock is held, the task retries later.
- **Completed-but-unacked edge:** if a worker dies *after* `complete` but before ack, no in-progress MPU exists, so the redelivered run re-uploads from scratch (rare; idempotent). An optional `head_object` size-check could skip it, **but** `replace_video_from_dropbox` (`ui/api.py:61-97`) intentionally re-uploads to the same Key — so any such skip must compare against the *expected new* size, not merely "object exists." This optimization is documented here but **not** implemented by default to avoid wrongly skipping a same-Key replacement.

## 8. Error handling & cleanup

- **Per-range fetch:** per-attempt timeout `(connect, read) = (30, 120)` (tuple, replacing bare `60`). Retry on `requests.exceptions.RequestException` (covers `ConnectionError`, `ReadTimeout`, `ChunkedEncodingError`) and on any non-`200/206` status, with exponential backoff + jitter, max attempts `_MAX_RANGE_ATTEMPTS` (default 5).
- **URL expiry:** handled implicitly — each part re-GETs the stable `source_url` and follows a fresh 302. Only a revoked/expired *stable* link (403/404 on `source_url` itself) is unrecoverable → permanent fail.
- **Per-part upload:** botocore already retries transient S3 errors; add a thin manual retry on `ClientError`/`EndpointConnectionError`.
- **Failure cleanup:** on exhausted retries or any unexpected error → `abort_multipart_upload(UploadId)` (delete uploaded parts), then `video.update_status(UPLOAD_FAILED)` + `update_state(FAILURE)` + raise (current behavior preserved).
- **Infra backstop (one ops action):** an S3 lifecycle rule `AbortIncompleteMultipartUpload` after 1 day on the upload bucket, to reap parts orphaned by a hard kill that never reached the `abort` call. (1 day is safe — a single upload completes in minutes, not days.)

## 9. Configuration (new settings, `odl_video/settings.py`, via `get_int`/`get_bool`)

| Setting | Default | Notes |
|---|---|---|
| `DROPBOX_TRANSFER_PART_SIZE_MB` | 32 | enforced ≥ 5 |
| `DROPBOX_TRANSFER_MAX_RANGE_ATTEMPTS` | 5 | per-range retry cap |
| `DROPBOX_TRANSFER_BACKOFF_BASE_SECONDS` | 2 | exponential base |
| `DROPBOX_TRANSFER_BACKOFF_MAX_SECONDS` | 60 | backoff cap |
| `DROPBOX_TRANSFER_CONNECT_TIMEOUT` | 30 | requests connect timeout |
| `DROPBOX_TRANSFER_READ_TIMEOUT` | 120 | requests read timeout |
| `DROPBOX_TRANSFER_PART_CONCURRENCY` | 1 | >1 risks Dropbox throttling |

`AWS_S3_UPLOAD_TRANSFER_CONFIG` is left unchanged.

## 10. Testing plan

New `cloudsync/dropbox_transfer_test.py` + `cloudsync/tasks_test.py` updates, using `moto.mock_aws` (real S3 multipart) + `requests-mock` (ranged Dropbox), with `time.sleep` patched.

**Core**
- Multi-part happy path: size → 3 parts incl. a short last part; assert per-part `Range` headers requested, parts uploaded, completed object present in moto at correct size.
- Small-file path: total ≤ part_size → `put_object`, no multipart.
- Ranged 206 returns `application/binary` → final object `ContentType` comes from metadata (`video/mp4`).
- Missing `Content-Disposition` → no `KeyError`.
- Progress: `update_state` called with cumulative `{uploaded, total}` per part.

**C1 retries**
- Range times out once then succeeds → only that range refetched, no duplicate part.
- Retries exhausted → `abort_multipart_upload` called (no in-progress upload / object absent in moto), `UPLOAD_FAILED`, raises.
- 302 → 206 redirect preserves the `Range` header.
- Expired CDN URL on first attempt → re-resolve via `source_url` succeeds.

**C2 resume**
- Pre-seed an MPU with parts 1–2 in moto → task fetches only 3..N and completes with all ETags.
- Multiple in-progress MPUs for Key → newest adopted, older aborted.
- Part-size drift (existing parts sized differently) → abort + restart fresh.
- Redis lock held → task defers/retries; not held → proceeds.
- `acks_late` / `reject_on_worker_lost` asserted on the task.

## 11. Call sites unaffected

`stream_to_s3(self, video_id)` keeps its signature; the two `chain(...)` dispatches in `ui/api.py` and the `backfill_shorts` management command need no change.

## 12. Rollout & validation

1. Ship behind the existing settings (defaults above) — no feature flag needed; behavior change is internal to `stream_to_s3`.
2. Add the S3 `AbortIncompleteMultipartUpload` lifecycle rule to the upload bucket in the
   Pulumi infra repo (`DaysAfterInitiation: 1`). Separate small infra PR, not a code dependency —
   our explicit `abort` (§8) covers handled failures; this reaps orphans from hard kills.
   Note: `put-bucket-lifecycle-configuration` replaces the whole config, so merge with any
   existing rules rather than overwriting.
3. Confirm what `video.source_url` stores in prod (stable `rlkey` link vs. expiring `st`).
4. Watch ODL-VIDEO-SERVICE-3AK after deploy; a re-upload of a known-large file is the manual smoke test.

## 13. Open questions

- Confirm prod `source_url` format (Chooser link stability).
- Decide whether to implement the size-aware `head_object` idempotency skip (§7) or leave the rare full re-upload.
