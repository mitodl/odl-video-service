"""Tests for the pure helpers in ``keycloak_command_utils``.

These tests target the utility functions independently of any management
command; command-level behavior lives in ``keycloak_commands_test.py``.
"""

from io import StringIO

import pytest
import requests

from ui.management.commands.conftest import conflict_error
from ui.management.commands.keycloak_command_utils import (
    keycloak_config_from_options,
    parse_comma_list,
    print_summary,
    record_exception,
)

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("", []),
        (None, []),
        (" a , b ,, a , c ,b", ["a", "b", "c"]),
    ],
)
def test_parse_comma_list_handles_blanks_and_duplicates(raw, expected):
    """Blank entries and duplicates are dropped; order is preserved."""
    assert parse_comma_list(raw) == expected


def test_keycloak_config_from_options_prefers_options_then_settings(settings):
    """Explicit options win; missing options fall back to Django settings."""
    settings.KEYCLOAK_SERVER_URL = "http://kc.settings:7080"
    settings.KEYCLOAK_REALM = "settings-realm"
    settings.KEYCLOAK_SVC_ADMIN = "settings-admin"
    settings.KEYCLOAK_SVC_ADMIN_PASSWORD = "settings-pw"

    assert keycloak_config_from_options({}) == {
        "keycloak_url": "http://kc.settings:7080",
        "realm": "settings-realm",
        "client_id": "settings-admin",
        "client_secret": "settings-pw",
    }

    assert keycloak_config_from_options(
        {
            "keycloak_url": "http://kc.override:7080",
            "keycloak_realm": "override-realm",
            "keycloak_client_id": "override-client",
            "keycloak_client_secret": "override-secret",
        }
    ) == {
        "keycloak_url": "http://kc.override:7080",
        "realm": "override-realm",
        "client_id": "override-client",
        "client_secret": "override-secret",
    }


def _http_error(status_code, text):
    response = type("Response", (), {"status_code": status_code, "text": text})()
    return requests.exceptions.HTTPError(response=response)


@pytest.mark.parametrize(
    "exc,expected_bucket,expected_error",
    [
        (conflict_error(), "existing_skipped", None),
        (_http_error(500, "boom"), "failed", "http-id: boom"),
        (RuntimeError("kaboom"), "failed", "http-id: kaboom"),
    ],
    ids=["conflict-409", "http-non-409", "generic-exception"],
)
def test_record_exception_classifies_by_exception_type(
    exc, expected_bucket, expected_error
):
    """409 -> existing_skipped; other HTTPError -> response text; anything else -> str(exc)."""
    summary = {"existing_skipped": 0, "failed": 0, "errors": []}

    record_exception(summary, "http-id", exc)

    assert summary[expected_bucket] == 1
    if expected_error is None:
        assert summary["errors"] == []
    else:
        assert summary["errors"] == [expected_error]


def test_print_summary_emits_labels_and_errors(mocker):
    """print_summary writes known labels present in the dict and any error list."""
    command = mocker.Mock()
    command.stdout = StringIO()
    command.style.SUCCESS = lambda s: s
    command.style.WARNING = lambda s: s
    command.stdout.write = lambda s: StringIO.write(command.stdout, s + "\n")

    print_summary(
        command,
        {"assigned": 2, "failed": 1, "errors": ["x: broken"]},
        "Test run",
    )

    output = command.stdout.getvalue()
    assert "Test run completed" in output
    assert "Assigned: 2" in output
    assert "Failed: 1" in output
    assert "Errors:" in output
    assert "- x: broken" in output
