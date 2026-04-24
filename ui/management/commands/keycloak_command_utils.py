"""Shared helpers for Keycloak migration management commands."""

from __future__ import annotations

import time
from typing import Iterable

import requests
from django.conf import settings

from ui.keycloak_utils import build_keycloak_manager, is_keycloak_conflict_error
from ui.models import KeycloakGroup

# Re-export so command modules keep a single import surface.
__all__ = [
    "add_keycloak_arguments",
    "build_keycloak_manager",
    "chunked",
    "drain_async_chunks",
    "get_ovs_keycloak_group_names",
    "is_keycloak_conflict_error",
    "keycloak_config_from_options",
    "parse_comma_list",
    "print_summary",
    "record_exception",
]


def add_keycloak_arguments(parser):
    """Add Keycloak connection arguments. Values default from Django settings when omitted."""
    parser.add_argument(
        "--keycloak-url",
        type=str,
        default=None,
        help="Keycloak server URL (defaults to settings.KEYCLOAK_SERVER_URL)",
    )
    parser.add_argument(
        "--keycloak-realm",
        type=str,
        default=None,
        help="Keycloak realm name (defaults to settings.KEYCLOAK_REALM)",
    )
    parser.add_argument(
        "--keycloak-client-id",
        type=str,
        default=None,
        help="Keycloak service account client ID (defaults to settings.KEYCLOAK_SVC_ADMIN)",
    )
    parser.add_argument(
        "--keycloak-client-secret",
        type=str,
        default=None,
        help="Keycloak service account client secret (defaults to settings.KEYCLOAK_SVC_ADMIN_PASSWORD)",
    )


def keycloak_config_from_options(options):
    """Build a serializable Keycloak config from command options, falling back to settings."""
    return {
        "keycloak_url": options.get("keycloak_url") or settings.KEYCLOAK_SERVER_URL,
        "realm": options.get("keycloak_realm") or settings.KEYCLOAK_REALM,
        "client_id": (options.get("keycloak_client_id") or settings.KEYCLOAK_SVC_ADMIN),
        "client_secret": (
            options.get("keycloak_client_secret")
            or settings.KEYCLOAK_SVC_ADMIN_PASSWORD
        ),
    }


def parse_comma_list(value):
    """Parse a comma-separated option into a deduplicated list preserving order."""
    if not value:
        return []

    seen = set()
    parsed = []
    for raw_value in value.split(","):
        item = raw_value.strip()
        if not item or item in seen:
            continue
        seen.add(item)
        parsed.append(item)
    return parsed


def chunked(items: Iterable, chunk_size: int):
    """Yield successive chunks of ``chunk_size`` from ``items``."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be > 0")

    chunk = []
    for item in items:
        chunk.append(item)
        if len(chunk) == chunk_size:
            yield chunk
            chunk = []

    if chunk:
        yield chunk


def get_ovs_keycloak_group_names(limit_lists=None):
    """Return names of OVS KeycloakGroup rows, optionally restricted to ``limit_lists``."""
    queryset = KeycloakGroup.objects.all()

    if limit_lists:
        queryset = queryset.filter(name__in=limit_lists)

    return list(queryset.values_list("name", flat=True))


def drain_async_chunks(async_results, *, poll_interval=1.0):
    """Yield ``(index, payload_or_exc, is_error)`` as chunk tasks complete.

    Avoids head-of-line blocking: a slow chunk 1 does not delay collection of
    faster chunks that finish later. ``index`` is the 1-based chunk index from
    the original dispatch order so log messages and error summaries stay
    consistent with the submission order the caller already used.
    """
    pending = dict(enumerate(async_results, start=1))
    while pending:
        ready_indices = [idx for idx, res in pending.items() if res.ready()]
        if not ready_indices:
            time.sleep(poll_interval)
            continue
        for idx in ready_indices:
            result = pending.pop(idx)
            try:
                yield idx, result.get(propagate=False, timeout=1), False
            except Exception as exc:  # noqa: BLE001
                yield idx, exc, True


def record_exception(summary, identifier, exc):
    """Classify an exception into the shared summary dict.

    Treats HTTP 409 as an existing-resource skip; everything else is a failure.
    """
    if is_keycloak_conflict_error(exc):
        summary["existing_skipped"] += 1
        return
    if isinstance(exc, requests.exceptions.HTTPError) and exc.response is not None:
        detail = exc.response.text
    else:
        detail = str(exc)
    summary["failed"] += 1
    summary["errors"].append(f"{identifier}: {detail}")


_SUMMARY_LABELS = (
    ("assigned", "Assigned"),
    ("created", "Created"),
    ("existing_skipped", "Existing skipped"),
    ("invalid_skipped", "Invalid records skipped"),
    ("missing_groups", "Missing groups skipped"),
    ("missing_users", "Missing users skipped"),
    ("failed", "Failed"),
)


def print_summary(command, summary, label):
    """Write a standard summary block to ``command.stdout``."""
    command.stdout.write(command.style.SUCCESS(f"{label} completed"))
    for key, display in _SUMMARY_LABELS:
        if key in summary:
            command.stdout.write(f"  {display}: {summary[key]}")

    if summary.get("errors"):
        command.stdout.write(command.style.WARNING("Errors:"))
        for error in summary["errors"]:
            command.stdout.write(command.style.WARNING(f"  - {error}"))
