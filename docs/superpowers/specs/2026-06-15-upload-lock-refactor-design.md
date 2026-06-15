# Upload Lock Refactor: Replace Hand-Rolled Lock with `redis.lock.Lock`

## Problem

`upload_lock` in `cloudsync/api.py` is a hand-rolled Redis distributed lock that stores raw Lua
(`_RELEASE_LOCK_SCRIPT`) in application code for atomic compare-and-delete on release. The lock
also uses a fixed 1-hour TTL with no renewal, so a long upload risks the TTL expiring mid-transfer
— allowing a redelivered worker to acquire the lock while the original is still running, with the
original worker eventually doing a no-op release against the correct lock.

## Solution

Replace the hand-rolled lock and its Lua script with `redis.lock.Lock` from redis-py (already a
transitive dependency via Celery). Add TTL renewal at each part-fetch checkpoint so the lock stays
alive only as long as active progress is being made.

## Changes

### `cloudsync/api.py`

- Delete `_RELEASE_LOCK_SCRIPT` and the `upload_lock` function entirely.

### `cloudsync/tasks.py`

Use `redis.lock.Lock` directly at the call site in `stream_to_s3`:

```python
lock = self.app.backend.client.lock(lock_key, timeout=SOURCE_TRANSFER_LOCK_TTL_SECONDS)
if not lock.acquire(blocking=False):
    raise self.retry(countdown=SOURCE_TRANSFER_LOCK_RETRY_COUNTDOWN)
try:
    run_transfer()
finally:
    try:
        lock.release()
    except Exception:
        log.warning("failed to release upload lock", lock_key=lock_key)
```

Extend the lock in the `fetch_range` closure before each Dropbox HTTP request:

```python
def fetch_range(start, end):
    lock.extend(SOURCE_TRANSFER_LOCK_TTL_SECONDS)
    return dropbox_api.fetch_shared_link_range(...)
```

Lower `SOURCE_TRANSFER_LOCK_TTL_SECONDS` from 3600 to 600. With per-part renewal, 10 minutes is
generous for one 32 MB part. On worker crash, the orphaned lock now expires within 10 minutes
rather than up to 1 hour.

### `cloudsync/api_test.py`

- Remove `upload_lock` import and its two tests (`test_upload_lock_acquired_yields_true_and_releases`,
  `test_upload_lock_not_acquired_yields_false_and_does_not_release`,
  `test_upload_lock_expired_does_not_delete_new_owner`).
- Remove `FakeRedis` class.
- `TransferError` import remains — it is used by the new `_fetch_range` byte-count tests added earlier this session.

### `cloudsync/tasks_test.py`

The existing tests mock `upload_lock` via `mocker.patch("cloudsync.tasks.upload_lock", ...)`.
Replace this with a mock of `redis.lock.Lock` on the backend client. The `_lock_yielding` helper
is removed; tests mock `lock.acquire()` to return `True` or `False` as appropriate.

## Behavior Preserved

- A second worker that cannot acquire the lock retries via `self.retry()` (unchanged).
- On successful completion or on exception, the lock is released. If the TTL has already expired
  and a new owner holds the lock, `release()` is a no-op (compare-and-delete inside redis-py
  returns 0 silently).
- The multipart upload resume logic (`_resume_or_create`) is unchanged.

## What This Does Not Change

- `S3Transfer` in `api.py` is unchanged.
- The `acks_late=True` / `reject_on_worker_lost=True` task configuration is unchanged.
- The number of retries and retry countdown are unchanged.
