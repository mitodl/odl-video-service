"""Tests for the authenticated Dropbox download helper."""

import json

import pytest
import requests
from django.test import override_settings

from cloudsync import dropbox_api

CREDS = {
    "DROPBOX_KEY": "appkey",
    "DROPBOX_SECRET": "appsecret",  # pragma: allowlist secret
    "DROPBOX_REFRESH_TOKEN": "refreshtoken",  # pragma: allowlist secret
}

SHARED_LINK = "https://www.dropbox.com/scl/fi/x/v.mp4?rlkey=k&dl=0"


@pytest.fixture(autouse=True)
def _reset_token_cache():
    """Token cache is module-level global state; reset it around every test."""
    dropbox_api._token_cache.update(access_token=None, expires_at=0.0)
    yield
    dropbox_api._token_cache.update(access_token=None, expires_at=0.0)


@pytest.fixture
def mock_token(reqmocker):
    """Stub the Dropbox token endpoint for stream_shared_link tests."""
    reqmocker.post(
        dropbox_api.OAUTH_TOKEN_URL,
        json={"access_token": "tok", "expires_in": 14400},
    )


@override_settings(**CREDS)
def test_get_access_token_refreshes_and_caches(reqmocker):
    """The token is fetched once and then served from cache."""
    matcher = reqmocker.post(
        dropbox_api.OAUTH_TOKEN_URL,
        json={"access_token": "tok-123", "expires_in": 14400},
    )
    assert dropbox_api.get_access_token() == "tok-123"
    assert dropbox_api.get_access_token() == "tok-123"
    assert matcher.call_count == 1


@override_settings(**CREDS)
def test_get_access_token_rejected_raises(reqmocker):
    """A rejected refresh token raises DropboxAuthError."""
    reqmocker.post(dropbox_api.OAUTH_TOKEN_URL, status_code=400, text="bad token")
    with pytest.raises(dropbox_api.DropboxAuthError):
        dropbox_api.get_access_token()


@override_settings(**CREDS)
def test_get_access_token_refetches_when_stale(reqmocker):
    """An expired cached token triggers a fresh fetch."""
    reqmocker.post(
        dropbox_api.OAUTH_TOKEN_URL,
        [
            {"json": {"access_token": "tok-1", "expires_in": 14400}},
            {"json": {"access_token": "tok-2", "expires_in": 14400}},
        ],
    )
    assert dropbox_api.get_access_token() == "tok-1"
    dropbox_api._token_cache["expires_at"] = 0.0  # simulate expiry
    assert dropbox_api.get_access_token() == "tok-2"


@override_settings(**CREDS)
def test_get_access_token_malformed_response_raises(reqmocker):
    """A 200 response missing access_token is treated as an auth failure."""
    reqmocker.post(dropbox_api.OAUTH_TOKEN_URL, json={"unexpected": "body"})
    with pytest.raises(dropbox_api.DropboxAuthError):
        dropbox_api.get_access_token()


@override_settings(**CREDS)
def test_stream_shared_link_sends_auth_and_arg(mock_token, reqmocker):
    """The download is authenticated and names the shared link in Dropbox-API-Arg."""
    reqmocker.post(
        dropbox_api.SHARED_LINK_FILE_URL,
        content=b"video-bytes",
        headers={"Dropbox-API-Result": json.dumps({"name": "v.mp4", "size": 11})},
    )
    resp = dropbox_api.stream_shared_link(SHARED_LINK)
    assert resp.status_code == 200
    sent = reqmocker.request_history[-1]
    assert sent.headers["Authorization"] == "Bearer tok"
    assert json.loads(sent.headers["Dropbox-API-Arg"]) == {"url": SHARED_LINK}


@override_settings(**CREDS)
def test_stream_shared_link_http_error_raises(mock_token, reqmocker):
    """A non-2xx download raises requests.HTTPError for the caller to handle."""
    reqmocker.post(dropbox_api.SHARED_LINK_FILE_URL, status_code=409, text="not_found")
    with pytest.raises(requests.HTTPError):
        dropbox_api.stream_shared_link(SHARED_LINK)


@override_settings(**CREDS)
def test_stream_shared_link_retries_after_401(reqmocker):
    """A 401 refreshes the cached token and retries the download once."""
    token_matcher = reqmocker.post(
        dropbox_api.OAUTH_TOKEN_URL,
        [
            {"json": {"access_token": "stale", "expires_in": 14400}},
            {"json": {"access_token": "fresh", "expires_in": 14400}},
        ],
    )
    reqmocker.post(
        dropbox_api.SHARED_LINK_FILE_URL,
        [
            {"status_code": 401, "text": "expired_access_token"},
            {
                "content": b"video-bytes",
                "headers": {
                    "Dropbox-API-Result": json.dumps({"name": "v.mp4", "size": 11})
                },
            },
        ],
    )
    resp = dropbox_api.stream_shared_link(SHARED_LINK)
    assert resp.status_code == 200
    assert token_matcher.call_count == 2
    assert reqmocker.request_history[-1].headers["Authorization"] == "Bearer fresh"


@override_settings(**CREDS)
def test_stream_shared_link_raises_when_retry_still_401(reqmocker):
    """A 401 that persists after refreshing the token surfaces as HTTPError."""
    reqmocker.post(
        dropbox_api.OAUTH_TOKEN_URL,
        json={"access_token": "tok", "expires_in": 14400},
    )
    reqmocker.post(
        dropbox_api.SHARED_LINK_FILE_URL,
        status_code=401,
        text="expired_access_token",
    )
    with pytest.raises(requests.HTTPError):
        dropbox_api.stream_shared_link(SHARED_LINK)


@override_settings(**CREDS)
def test_fetch_shared_link_range_sends_range_and_returns_partial(mock_token, reqmocker):
    """A ranged fetch sends a Range header and returns the 206 response for the caller."""
    reqmocker.post(
        dropbox_api.SHARED_LINK_FILE_URL,
        content=b"0123456789"[2:6],
        status_code=206,
        headers={"Content-Range": "bytes 2-5/10"},
    )
    resp = dropbox_api.fetch_shared_link_range(SHARED_LINK, 2, 5)
    assert resp.status_code == 206
    assert resp.content == b"2345"
    sent = reqmocker.request_history[-1]
    assert sent.headers["Range"] == "bytes=2-5"
    assert sent.headers["Authorization"] == "Bearer tok"
    assert json.loads(sent.headers["Dropbox-API-Arg"]) == {"url": SHARED_LINK}


@override_settings(**CREDS)
def test_fetch_shared_link_range_retries_after_401(reqmocker):
    """A 401 on a ranged fetch refreshes the token and retries once."""
    reqmocker.post(
        dropbox_api.OAUTH_TOKEN_URL,
        [
            {"json": {"access_token": "stale", "expires_in": 14400}},
            {"json": {"access_token": "fresh", "expires_in": 14400}},
        ],
    )
    reqmocker.post(
        dropbox_api.SHARED_LINK_FILE_URL,
        [
            {"status_code": 401, "text": "expired_access_token"},
            {"content": b"abcd", "status_code": 206},
        ],
    )
    resp = dropbox_api.fetch_shared_link_range(SHARED_LINK, 0, 3)
    assert resp.status_code == 206
    assert resp.content == b"abcd"
    assert reqmocker.request_history[-1].headers["Authorization"] == "Bearer fresh"


@override_settings(**CREDS)
def test_fetch_shared_link_range_raises_on_error_status(mock_token, reqmocker):
    """A non-partial error status (e.g. revoked link) surfaces as HTTPError."""
    reqmocker.post(dropbox_api.SHARED_LINK_FILE_URL, status_code=409, text="not_found")
    with pytest.raises(requests.HTTPError):
        dropbox_api.fetch_shared_link_range(SHARED_LINK, 0, 3)
