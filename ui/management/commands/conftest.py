"""Shared pytest fixtures and helpers for the keycloak command test suite."""

import pytest
import requests

_COMMAND_MANAGER_TARGETS = (
    "ui.management.commands.keycloak_command_utils.build_keycloak_manager",
    "ui.management.commands.assign_group_users.build_keycloak_manager",
)


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
