"""Shared pytest fixtures and helpers for the keycloak command test suite."""

import pytest
import requests


_COMMAND_MANAGER_TARGETS = (
    "ui.management.commands.keycloak_command_utils.build_keycloak_manager",
    "ui.management.commands.migrate_moira_to_keycloak.build_keycloak_manager",
    "ui.management.commands.migrate_users_to_keycloak.build_keycloak_manager",
    "ui.management.commands.assign_group_users.build_keycloak_manager",
    "ui.management.commands.migrate_collection_owners_to_keycloak_groups.build_keycloak_manager",
)


class FakeAsyncResult:
    """Test double for a Celery AsyncResult.

    ``ready_after`` lets a result reply "not ready" for N probes before flipping
    to ready. ``raise_on_get`` makes ``.get()`` raise, emulating a task whose
    result retrieval fails (broker down, deserialization error, etc.).
    """

    def __init__(self, payload=None, ready_after=0, raise_on_get=None):
        self._payload = payload
        self._ready_after = ready_after
        self._ready_calls = 0
        self._raise_on_get = raise_on_get

    def ready(self):
        self._ready_calls += 1
        return self._ready_calls > self._ready_after

    def get(self, propagate=False, timeout=None):
        if self._raise_on_get is not None:
            raise self._raise_on_get
        return self._payload


def conflict_error():
    """Return a fake Keycloak 409 HTTPError for use in ``side_effect`` lists."""
    response = type("Response", (), {"status_code": 409, "text": "conflict"})()
    return requests.exceptions.HTTPError(response=response)


@pytest.fixture
def manager_mock(mocker):
    """A Keycloak manager mock patched into every command module's import site."""
    manager = mocker.Mock()
    manager.get_groups.return_value = []
    for target in _COMMAND_MANAGER_TARGETS:
        mocker.patch(target, return_value=manager)
    return manager
