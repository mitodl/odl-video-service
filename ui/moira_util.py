"""Utils for ui app"""

import os
from collections import namedtuple
from functools import lru_cache

from django.conf import settings
from django.core.cache import caches
from mit_moira import Moira

from odl_video import logging
from ui.exceptions import MoiraException

log = logging.getLogger(__name__)

MoiraUser = namedtuple("MoiraUser", "username type")
MOIRA_CACHE_KEY = "moira_lists_{user_id}"
cache = caches["redis"]


@lru_cache(1)  # memoize this function
def get_moira_client():
    """
    Gets a moira client.

    Returns:
        Moira: A moira client
    """

    _check_files_exist(
        [settings.MIT_WS_CERTIFICATE_FILE, settings.MIT_WS_PRIVATE_KEY_FILE]
    )
    try:
        return Moira(settings.MIT_WS_CERTIFICATE_FILE, settings.MIT_WS_PRIVATE_KEY_FILE)
    except Exception as exc:
        raise MoiraException(
            "Something went wrong with creating a moira client"
        ) from exc


def _check_files_exist(paths):
    """Checks that files exist at given paths."""
    errors = []
    for path in paths:
        if not os.path.isfile(path):
            errors.append("File missing: expected path '{}'".format(path))
    if errors:
        raise RuntimeError("\n".join(errors))


def list_members(list_name):
    """
    Get a set of all moira users against given list name

    Args:
        list_name (str): name of list.

    Returns:
        list_users(list): A list of users
    """
    moira = get_moira_client()
    try:
        list_users = moira.list_members(list_name)
        return list_users
    except Exception as exc:
        raise MoiraException(
            "Something went wrong with getting moira-users for %s" % list_name
        ) from exc


def write_to_file(filename, contents):
    """
    Write content to a file in binary mode, creating directories if necessary

    Args:
        filename (str): The full-path filename to write to.
        contents (bytes): What to write to the file.

    """
    if not os.path.exists(os.path.dirname(filename)):
        os.makedirs(os.path.dirname(filename))
    with open(filename, "wb") as infile:
        infile.write(contents)


def write_x509_files():
    """Write the x509 certificate and key to files"""
    write_to_file(settings.MIT_WS_CERTIFICATE_FILE, settings.MIT_WS_CERTIFICATE)
    write_to_file(settings.MIT_WS_PRIVATE_KEY_FILE, settings.MIT_WS_PRIVATE_KEY)
