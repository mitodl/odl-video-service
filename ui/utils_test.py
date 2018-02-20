"""Tests for utils methods"""
from tempfile import NamedTemporaryFile
import pytest
from zeep.exceptions import Fault

from ui import factories
from ui.exceptions import MoiraException
from ui.utils import write_to_file, get_moira_client, user_moira_lists, has_common_lists

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
    list_names = ['test_moira_list01', 'test_moira_list02']
    mock_moira_client.return_value.user_lists.return_value = list_names
    other_user = factories.UserFactory(email='someone@mit.edu')
    assert user_moira_lists(other_user) == list_names


def test_user_no_moira_lists(mock_moira_client):
    """
    Test that an empty list is returned by user_moira_lists if Moira throws a java NPE
    """
    mock_moira_client.return_value.user_lists.side_effect = Fault('java.lang.NullPointerException')
    other_user = factories.UserFactory(email='someone@mit.edu')
    assert user_moira_lists(other_user) == []


def test_user_moira_lists_error(mock_moira_client):
    """
    Test that a Moira exception is raised if moira client call fails with anything other than a java NPE
    """
    mock_moira_client.return_value.user_lists.side_effect = Fault("Not a java NPE")
    other_user = factories.UserFactory()
    with pytest.raises(MoiraException):
        user_moira_lists(other_user)


@pytest.mark.parametrize(['member', 'members', 'is_member'], [
    ['person1@mit.edu', ['person2', 'person3'], False],
    ['person1@mit.edu', ['person2', 'person1'], True],
    ['person1@gmail.com', ['person1@gmail.com', 'person3'], True],
    ['person1@gmail.com', ['person1', 'person3'], False],
    ['person1@mit.edu', [], False]
])
def test_has_common_lists(mock_moira_client, member, members, is_member):
    """
    Test that has_common_lists returns the correct boolean value
    """
    mock_moira_client.return_value.list_members.return_value = members
    user = factories.UserFactory(username=member, email=member)
    assert has_common_lists(user, ['mock_list1', 'mock_list2']) is is_member


def test_has_common_lists_error(mock_moira_client):
    """
    Test that a Moira exception is raised if moira client list_members call fails
    """
    mock_moira_client.return_value.list_members.side_effect = OSError
    with pytest.raises(MoiraException) as exc:
        has_common_lists(factories.UserFactory(), ['mock_list1', 'mock_list2'])
    assert exc.match('Something went wrong with getting moira-list members')
