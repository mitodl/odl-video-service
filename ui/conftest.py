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
