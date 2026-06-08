"""
Authenticated downloads of Dropbox shared links.
"""

import json
import time

import requests
from django.conf import settings

OAUTH_TOKEN_URL = "https://api.dropbox.com/oauth2/token"
SHARED_LINK_FILE_URL = "https://content.dropboxapi.com/2/sharing/get_shared_link_file"

# Dropbox access tokens last ~4h; refresh a few minutes early.
_TOKEN_EXPIRY_BUFFER_SECONDS = 300
# (connect, read) timeouts for the streamed download.
_DOWNLOAD_TIMEOUT = (60, 300)

_token_cache = {"access_token": None, "expires_at": 0.0}


class DropboxAuthError(Exception):
    """Raised when Dropbox rejects the service-account credentials."""


def get_access_token(force_refresh=False):
    """Return a cached access token, refreshing from the refresh token when stale."""
    now = time.monotonic()
    if (
        not force_refresh
        and _token_cache["access_token"]
        and now < _token_cache["expires_at"]
    ):
        return _token_cache["access_token"]

    resp = requests.post(
        OAUTH_TOKEN_URL,
        data={
            "grant_type": "refresh_token",
            "refresh_token": settings.DROPBOX_REFRESH_TOKEN,
        },
        auth=(settings.DROPBOX_KEY, settings.DROPBOX_SECRET),
        timeout=30,
    )
    if resp.status_code != 200:
        raise DropboxAuthError(
            f"Dropbox token refresh failed ({resp.status_code}): {resp.text}"
        )
    try:
        payload = resp.json()
        access_token = payload["access_token"]
    except (ValueError, KeyError) as exc:
        raise DropboxAuthError(
            f"Dropbox token response missing access_token: {resp.text}"
        ) from exc
    _token_cache["access_token"] = access_token
    _token_cache["expires_at"] = (
        now + payload.get("expires_in", 14400) - _TOKEN_EXPIRY_BUFFER_SECONDS
    )
    return access_token


def _download(url, access_token):
    """Issue the streamed download request with the given bearer token."""
    return requests.post(
        SHARED_LINK_FILE_URL,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Dropbox-API-Arg": json.dumps({"url": url}),
        },
        stream=True,
        timeout=_DOWNLOAD_TIMEOUT,
    )


def stream_shared_link(url):
    """Stream an authenticated Dropbox shared-link download; raises HTTPError on failure."""
    response = _download(url, get_access_token())
    if response.status_code == 401:
        # The cached token may have been revoked before its expiry; force a
        # refresh and retry once before giving up.
        response.close()
        response = _download(url, get_access_token(force_refresh=True))
    response.raise_for_status()
    return response
