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
