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
def mock_moira(mocker):
    """Return a fake mit_moira.Moira object"""
    return mocker.patch('ui.utils.Moira')


@pytest.fixture
def mock_moira_client(mocker):
    """Return a fake moira client"""
    return mocker.patch('ui.utils.get_moira_client', autospec=True)


@pytest.fixture
def mock_user_moira_lists(mocker):
    """Return a fake moira client"""
    mocked = mocker.patch('ui.utils.user_moira_lists')
    mocked.return_value = set()
    return mocked


@pytest.fixture
def ga_client_mocks(mocker):
    """Return mocker with patches for objects used for google api clients"""
    mocks = {
        'build': mocker.patch('ui.utils.build'),
        'ServiceAccountCredentials': mocker.patch(
            'ui.utils.ServiceAccountCredentials'),
    }
    return mocks
