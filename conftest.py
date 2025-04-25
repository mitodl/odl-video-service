"""
Pytest configuration file for the entire application
"""

import warnings

import pytest
import requests_mock


@pytest.fixture(autouse=True)
def warnings_as_errors():
    """
    Convert warnings to errors. This should only affect unit tests, letting pylint and other plugins
    raise DeprecationWarnings without erroring.
    """
    try:
        warnings.resetwarnings()
        warnings.simplefilter("error")
        # For celery
        warnings.simplefilter("ignore", category=ImportWarning)
        # For deprecated functions
        warnings.simplefilter("ignore", category=DeprecationWarning)
        yield
    finally:
        warnings.resetwarnings()


@pytest.fixture
def reqmocker():
    """Fixture for requests mock"""
    with requests_mock.Mocker() as m:
        yield m
