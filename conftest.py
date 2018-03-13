"""
Pytest configuration file for the entire application
"""
# pylint: disable=redefined-outer-name
import warnings

import pytest


@pytest.fixture(autouse=True)
def warnings_as_errors():
    """
    Convert warnings to errors. This should only affect unit tests, letting pylint and other plugins
    raise DeprecationWarnings without erroring.
    """
    try:
        warnings.resetwarnings()
        warnings.simplefilter('error')
        # For celery
        warnings.simplefilter('ignore', category=ImportWarning)
        warnings.filterwarnings(
            "ignore",
            message="'async' and 'await' will become reserved keywords in Python 3.7",
            category=DeprecationWarning,
        )

        yield
    finally:
        warnings.resetwarnings()
