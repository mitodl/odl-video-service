"""
conftest for pytest in this module
"""

import pytest
from rest_framework.test import APIClient


@pytest.fixture
def apiclient():
    """
    Special client for rest requests
    """
    return APIClient()


@pytest.fixture
def mock_kc_client(mocker):
    """Mock for the KeycloakManager client"""
    return mocker.patch("ui.keycloak_utils.get_keycloak_client", autospec=True)


@pytest.fixture
def mock_keycloak(mocker):
    """Mock for the KeycloakManager"""
    return mocker.patch("ui.keycloak_utils.KeycloakManager")


@pytest.fixture
def mock_user_groups(mocker):
    """Return a fake user groups"""
    mocked = mocker.patch("ui.utils.user_groups")
    mocked.return_value = set()
    return mocked


@pytest.fixture
def ga_client_mocks(mocker):
    """Return mocker with patches for objects used for google api clients"""
    mocks = {
        "build": mocker.patch("ui.utils.build"),
        "ServiceAccountCredentials": mocker.patch("ui.utils.ServiceAccountCredentials"),
    }
    return mocks


@pytest.fixture(autouse=True)
def disable_keycloak(settings):
    """
    Disable Keycloak for all tests by default.
    This fixture automatically runs for every test.
    """
    settings.USE_KEYCLOAK = False
    settings.LOGIN_URL = "/login/"
    return settings
