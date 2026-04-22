"""Tests for the pure helpers in ``keycloak_command_utils``.

These tests target the utility functions independently of any management
command; command-level behavior lives in ``keycloak_commands_test.py``.
"""

from io import StringIO

import pytest
import requests

from ui.factories import KeycloakGroupFactory
from ui.management.commands.conftest import FakeAsyncResult, conflict_error
from ui.management.commands.keycloak_command_utils import (
    chunked,
    drain_async_chunks,
    get_ovs_keycloak_group_names,
    keycloak_config_from_options,
    parse_comma_list,
    print_summary,
    record_exception,
)

pytestmark = pytest.mark.django_db


def test_get_ovs_keycloak_group_names_returns_all_groups():
    """All KeycloakGroup names should be returned regardless of Collection/Video references."""
    KeycloakGroupFactory.create(name="group-a")
    KeycloakGroupFactory.create(name="group-b")
    KeycloakGroupFactory.create(name="group-c")

    assert sorted(get_ovs_keycloak_group_names()) == ["group-a", "group-b", "group-c"]


def test_get_ovs_keycloak_group_names_honors_limit_lists():
    """``limit_lists`` should restrict the result to the named groups."""
    KeycloakGroupFactory.create(name="group-a")
    KeycloakGroupFactory.create(name="group-b")
    KeycloakGroupFactory.create(name="group-c")

    assert sorted(
        get_ovs_keycloak_group_names(limit_lists=["group-a", "group-c", "missing"])
    ) == ["group-a", "group-c"]


def test_drain_async_chunks_yields_in_completion_order(mocker):
    """Slow first chunk must not block collection of later chunks that finish first."""
    # Chunk 1 isn't ready until the third ready() probe; chunks 2 and 3 are
    # ready immediately. A submission-order drain would return 1, 2, 3 — we
    # expect 2, 3, 1.
    slow = FakeAsyncResult({"id": 1}, ready_after=2)
    fast_a = FakeAsyncResult({"id": 2})
    fast_b = FakeAsyncResult({"id": 3})

    mocker.patch(
        "ui.management.commands.keycloak_command_utils.time.sleep", return_value=None
    )

    completed = list(drain_async_chunks([slow, fast_a, fast_b]))

    assert [(idx, payload["id"], is_error) for idx, payload, is_error in completed] == [
        (2, 2, False),
        (3, 3, False),
        (1, 1, False),
    ]


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


@pytest.mark.parametrize(
    "items,size,expected",
    [
        ([1, 2, 3, 4], 2, [[1, 2], [3, 4]]),
        ([1, 2, 3, 4, 5], 2, [[1, 2], [3, 4], [5]]),
        ([], 3, []),
    ],
)
def test_chunked_splits_into_batches(items, size, expected):
    """chunked yields exact-multiple batches plus any remainder."""
    assert list(chunked(items, size)) == expected


def test_chunked_rejects_non_positive_size():
    """size <= 0 must raise ValueError."""
    with pytest.raises(ValueError):
        list(chunked([1, 2], 0))


def test_keycloak_config_from_options_prefers_options_then_settings(settings):
    """Explicit options win; missing options fall back to Django settings."""
    settings.KEYCLOAK_SERVER_URL = "http://kc.settings:7080"
    settings.KEYCLOAK_REALM = "settings-realm"
    settings.KEYCLOAK_SVC_ADMIN = "settings-admin"
    settings.KEYCLOAK_SVC_ADMIN_PASSWORD = "settings-pw"

    assert keycloak_config_from_options({}) == {
        "keycloak_url": "http://kc.settings:7080",
        "realm": "settings-realm",
        "admin_username": "settings-admin",
        "admin_password": "settings-pw",
    }

    assert keycloak_config_from_options(
        {
            "keycloak_url": "http://kc.override:7080",
            "keycloak_realm": "override-realm",
            "keycloak_admin_username": "override-admin",
            "keycloak_admin_password": "override-pw",
        }
    ) == {
        "keycloak_url": "http://kc.override:7080",
        "realm": "override-realm",
        "admin_username": "override-admin",
        "admin_password": "override-pw",
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
