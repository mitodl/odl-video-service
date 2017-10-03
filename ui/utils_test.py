"""Tests for utils methods"""
from tempfile import NamedTemporaryFile
from urllib3.exceptions import SSLError

import pytest

from ui import factories
from ui.utils import write_to_file, get_moira_client, user_moira_lists


# pylint: disable=unused-argument

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("key_file, cert_file", [
    (NamedTemporaryFile(), None),
    (None, NamedTemporaryFile()),
    (None, None),
])
def test_get_moira_client_missing_secrets(mock_moira, settings, key_file, cert_file):
    """Test that the correct error is returned if a key file is missing"""
    settings.MIT_WS_PRIVATE_KEY_FILE = 'bad/file/path' if not key_file else key_file.name
    settings.MIT_WS_CERTIFICATE_FILE = 'bad/file/path' if not cert_file else cert_file.name
    with pytest.raises(RuntimeError) as err:
        get_moira_client()
        assert not mock_moira.called
        if key_file is None:
            assert settings.MIT_WS_PRIVATE_KEY_FILE in str(err)
        if cert_file is None:
            assert settings.MIT_WS_CERTIFICATE_FILE in str(err)


def test_get_moira_client_success(mock_moira, settings):
    """Test that a client is returned from get_moira_client"""
    tempfile1, tempfile2 = (NamedTemporaryFile(), NamedTemporaryFile())
    settings.MIT_WS_PRIVATE_KEY_FILE = tempfile1.name
    settings.MIT_WS_CERTIFICATE_FILE = tempfile2.name
    get_moira_client()
    assert mock_moira.called_once_with(settings.MIT_WS_CERTIFICATE_FILE, settings.MIT_WS_PRIVATE_KEY_FILE)


def test_write_to_file():
    """Test that write_to_file creates a file with the correct contents"""
    content = b'-----BEGIN CERTIFICATE-----\nMIID5DCCA02gAwIBAgIRTUTVwsj4Vy+l6+XTYjnIQ==\n-----END CERTIFICATE-----'
    with NamedTemporaryFile() as outfile:
        write_to_file(outfile.name, content)
        with open(outfile.name, 'rb') as infile:
            assert infile.read() == content


def test_user_moira_lists(mock_moira_client):
    """
    Test that the correct list is returned by user_moira_lists
    """
    moira_list = factories.MoiraListFactory()
    mock_moira_client.return_value.user_lists.return_value = [moira_list.name]
    other_user = factories.UserFactory(email='someone@mit.edu')
    lists = user_moira_lists(other_user)
    assert lists == [moira_list.name]


def test_user_moira_lists_error(mock_moira_client):
    """
    Test that an empty list is returned if the Moira client can't connect
    """
    mock_moira_client.side_effect = SSLError()
    other_user = factories.UserFactory()
    lists = user_moira_lists(other_user)
    assert lists == []
