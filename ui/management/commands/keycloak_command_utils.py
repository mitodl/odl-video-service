"""Shared helpers for Keycloak migration management commands."""

from __future__ import annotations

from typing import Iterable

import requests
from django.conf import settings
from django.db.models import Q

from ui.keycloak_utils import build_keycloak_manager, is_keycloak_conflict_error
from ui.models import KeycloakGroup

# Re-export so command modules keep a single import surface.
__all__ = [
    "add_keycloak_arguments",
    "build_keycloak_manager",
    "chunked",
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
        "--keycloak-admin-username",
        type=str,
        default=None,
        help="Keycloak admin username (defaults to settings.KEYCLOAK_SVC_ADMIN)",
    )
    parser.add_argument(
        "--keycloak-admin-password",
        type=str,
        default=None,
        help="Keycloak admin password (defaults to settings.KEYCLOAK_SVC_ADMIN_PASSWORD)",
    )


def keycloak_config_from_options(options):
    """Build a serializable Keycloak config from command options, falling back to settings."""
    return {
        "keycloak_url": options.get("keycloak_url") or settings.KEYCLOAK_SERVER_URL,
        "realm": options.get("keycloak_realm") or settings.KEYCLOAK_REALM,
        "admin_username": (
            options.get("keycloak_admin_username") or settings.KEYCLOAK_SVC_ADMIN
        ),
        "admin_password": (
            options.get("keycloak_admin_password")
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
    """Return Keycloak group names referenced by OVS collections/videos."""
    queryset = KeycloakGroup.objects.filter(
        Q(view_lists__isnull=False)
        | Q(admin_lists__isnull=False)
        | Q(video_view_lists__isnull=False)
    ).distinct()

    if limit_lists:
        queryset = queryset.filter(name__in=limit_lists)

    return list(queryset.values_list("name", flat=True))


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
