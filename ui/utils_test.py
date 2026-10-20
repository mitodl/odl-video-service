"""Tests for utils methods"""

import pytest
import responses
from django.contrib.auth.models import AnonymousUser

from odl_video.test_utils import MockResponse
from ui import factories
from ui.exceptions import KeycloakException
from ui.keycloak_utils import KeycloakManager
from ui.utils import (
    _groups_from_social_auth,
    get_error_response_summary_dict,
    get_keycloak_client,
    group_members,
    has_common_groups,
    multi_urljoin,
    partition,
    partition_to_lists,
    query_lists,
    send_refresh_request,
    user_groups,
)

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "missing_setting",
    [
        "KEYCLOAK_SERVER_URL",
        "KEYCLOAK_REALM",
        "KEYCLOAK_SVC_ADMIN",
        "KEYCLOAK_SVC_ADMIN_PASSWORD",
    ],
)
def test_get_keycloak_client_missing_settings(mock_keycloak, settings, missing_setting):
    """Test that the correct error is returned if a required setting is missing"""
    # Set all required settings
    settings.KEYCLOAK_SERVER_URL = "https://keycloak.example.com"
    settings.KEYCLOAK_REALM = "test-realm"
    settings.KEYCLOAK_SVC_ADMIN = "admin"
    settings.KEYCLOAK_SVC_ADMIN_PASSWORD = "password"

    # Now remove the one we want to test
    setattr(settings, missing_setting, None)

    with pytest.raises(ValueError) as err:
        get_keycloak_client()
        assert not mock_keycloak.called
        assert missing_setting in str(err.value)


def test_get_keycloak_client_success(mock_keycloak, settings):
    """Test that a client is returned from get_keycloak_client"""
    settings.KEYCLOAK_SERVER_URL = "https://keycloak.example.com"
    settings.KEYCLOAK_REALM = "test-realm"
    settings.KEYCLOAK_SVC_ADMIN = "odl-video-app"
    settings.KEYCLOAK_SVC_ADMIN_PASSWORD = "test-secret"

    get_keycloak_client()
    mock_keycloak.assert_called_once_with(
        keycloak_url=settings.KEYCLOAK_SERVER_URL,
        realm=settings.KEYCLOAK_REALM,
        client_id=settings.KEYCLOAK_SVC_ADMIN,
        client_secret=settings.KEYCLOAK_SVC_ADMIN_PASSWORD,
    )


@responses.activate
def test_get_admin_token_uses_client_credentials():
    """get_admin_token() must use client_credentials grant against the configured realm."""
    realm = "test-realm"
    base_url = "https://keycloak.example.com"
    token_url = f"{base_url}/realms/{realm}/protocol/openid-connect/token"

    responses.add(
        responses.POST,
        token_url,
        json={"access_token": "tok-abc123"},
        status=200,
    )

    manager = KeycloakManager(
        keycloak_url=base_url,
        realm=realm,
        client_id="odl-video-app",
        client_secret="secret",
    )
    token = manager.get_admin_token()

    assert token == "tok-abc123"
    assert manager.access_token == "tok-abc123"
    assert len(responses.calls) == 1
    body = dict(pair.split("=") for pair in responses.calls[0].request.body.split("&"))
    assert body["grant_type"] == "client_credentials"
    assert body["client_id"] == "odl-video-app"
    assert body["client_secret"] == "secret"


def test_query_lists(mock_keycloak):
    """
    Test that expected lists are returned.
    """
    group_names = ["test_group01", "test_group02"]
    mock_keycloak.return_value.get_user_groups.return_value = group_names
    other_user = factories.UserFactory(email="someone@mit.edu")
    assert sorted(query_lists(other_user)) == sorted(group_names)


def test_query_lists_no_lists(mock_keycloak):
    """
    Test that an empty list is returned if Keycloak returns no groups
    """
    mock_keycloak.return_value.get_user_groups.return_value = []
    other_user = factories.UserFactory(email="someone@mit.edu")
    assert query_lists(other_user) == []


def test_query_lists_error(mock_keycloak):
    """
    Test that a Keycloak exception is raised if keycloak client call fails
    """
    # Mock the get_user_groups method to raise an KeycloakException
    mock_keycloak.return_value.get_user_groups.side_effect = KeycloakException(
        "Mock Exception"
    )
    with pytest.raises(KeycloakException):
        query_lists(factories.UserFactory())


def test_user_groups_anonymous():
    """
    Test that empty set is returned for anonymous user
    """
    assert user_groups(AnonymousUser()) == set()


# ---------------------------------------------------------------------------
# _groups_from_social_auth and user_groups (token-claim cache)
# ---------------------------------------------------------------------------


def _make_social_auth(user, user_groups_value):
    """Create a social_django.UserSocialAuth record for the given user."""
    from social_django.models import UserSocialAuth

    return UserSocialAuth.objects.create(
        user=user,
        provider="keycloak",
        uid=user.email,
        extra_data={"user_groups": user_groups_value}
        if user_groups_value is not None
        else {},
    )


@pytest.mark.parametrize(
    "groups_value,expected",
    [
        (["/admin-list", "/staff-list"], {"admin-list", "staff-list"}),
        (["/Admin"], {"Admin"}),
        # nested path: leaf name only
        (["/parent/child-group"], {"child-group"}),
        # trailing slashes stripped before split
        (["/trailingslash/"], {"trailingslash"}),
        # mixed valid and invalid entries
        (["/valid", 42, None, ""], {"valid"}),
    ],
    ids=["top-level-two", "single-top", "nested-path", "trailing-slash", "mixed-types"],
)
def test_groups_from_social_auth_normalises_paths(groups_value, expected):
    """Full-path group names are normalised to bare leaf names."""
    user = factories.UserFactory()
    _make_social_auth(user, groups_value)
    assert _groups_from_social_auth(user) == expected


def test_groups_from_social_auth_no_social_record():
    """Returns None when the user has no Keycloak social-auth record."""
    user = factories.UserFactory()
    assert _groups_from_social_auth(user) is None


@pytest.mark.parametrize(
    "extra_data",
    [
        {},
        {"user_groups": None},
        {"user_groups": "not-a-list"},
        {"user_groups": 42},
    ],
    ids=["missing-key", "null-value", "string-value", "int-value"],
)
def test_groups_from_social_auth_unusable_cache(extra_data):
    """Returns None for all unusable cache states so caller falls back to live API."""
    from social_django.models import UserSocialAuth

    user = factories.UserFactory()
    UserSocialAuth.objects.create(
        user=user, provider="keycloak", uid=user.email, extra_data=extra_data
    )
    assert _groups_from_social_auth(user) is None


def test_groups_from_social_auth_empty_paths_only():
    """Returns None when all paths normalise to empty strings."""
    user = factories.UserFactory()
    _make_social_auth(user, ["/", "//", ""])
    assert _groups_from_social_auth(user) is None


def test_user_groups_uses_social_auth_cache(mock_keycloak):
    """user_groups reads from extra_data and does NOT call the Keycloak API."""
    user = factories.UserFactory()
    _make_social_auth(user, ["/odl-staff", "/odl-admin"])

    result = user_groups(user)

    assert result == {"odl-staff", "odl-admin"}
    mock_keycloak.return_value.get_user_groups.assert_not_called()


def test_user_groups_falls_back_to_live_api_when_no_social_auth(mock_keycloak):
    """user_groups falls back to live API when no social-auth record exists."""
    user = factories.UserFactory()
    mock_keycloak.return_value.get_user_groups.return_value = ["live-group"]

    result = user_groups(user)

    assert result == {"live-group"}
    mock_keycloak.return_value.get_user_groups.assert_called_once()


def test_user_groups_falls_back_when_cache_unusable(mock_keycloak):
    """user_groups falls back to live API when extra_data is missing user_groups."""
    from social_django.models import UserSocialAuth

    user = factories.UserFactory()
    UserSocialAuth.objects.create(
        user=user, provider="keycloak", uid=user.email, extra_data={}
    )
    mock_keycloak.return_value.get_user_groups.return_value = ["fallback-group"]

    result = user_groups(user)

    assert result == {"fallback-group"}
    mock_keycloak.return_value.get_user_groups.assert_called_once()


def test_user_groups_memoises_result(mock_keycloak):
    """user_groups calls the backing store only once per user object instance."""
    user = factories.UserFactory()
    _make_social_auth(user, ["/odl-staff"])

    first = user_groups(user)
    second = user_groups(user)

    assert first == second == {"odl-staff"}
    # social-auth path never touches Keycloak; but also only one DB lookup
    mock_keycloak.return_value.get_user_groups.assert_not_called()
    assert hasattr(user, "_keycloak_groups_cache")


def test_has_common_groups(mocker):
    """
    Test that has_common_groups returns the correct boolean value
    """
    mock_user_groups = mocker.patch("ui.utils.user_groups")
    mock_user_groups.return_value = {"a", "b"}
    user = factories.UserFactory()
    assert has_common_groups(user, ["b", "c"]) is True
    assert has_common_groups(user, ["c"]) is False


def test_group_members_exception(mock_keycloak):
    """
    Test that an HTTPError exception is raised if keycloak client call fails
    """
    mock_keycloak.return_value.get_group_members_by_name.side_effect = (
        KeycloakException("Mock Exception")
    )
    with pytest.raises(KeycloakException):
        group_members("group_name")


@pytest.mark.parametrize(
    "url_base,url_parts,trailing,expected",
    [
        ("http://mit.edu", ["a", "b"], False, "http://mit.edu/a/b"),
        ("http://mit.edu", ["a", "b/c/d", "e"], False, "http://mit.edu/a/b/c/d/e"),
        ("http://mit.edu/", ["/a/", "/b"], False, "http://mit.edu/a/b"),
        ("http://mit.edu", ["a", "b"], True, "http://mit.edu/a/b/"),
        ("http://mit.edu", ["a", "b/"], False, "http://mit.edu/a/b/"),
    ],
)
def test_multi_urljoin(url_base, url_parts, trailing, expected):
    """multi_urljoin should construct a valid URL from a base string and an arbitrary number of URL parts"""
    assert multi_urljoin(url_base, *url_parts, add_trailing_slash=trailing) == expected


def test_partition():
    """
    Assert that partition splits an iterable into two iterables according to a condition
    """
    nums = [1, 2, 1, 3, 1, 4, 0, None, None]
    not_ones, ones = partition(nums, lambda n: n == 1)
    assert list(not_ones) == [2, 3, 4, 0, None, None]
    assert list(ones) == [1, 1, 1]
    # The default predicate is the standard Python bool() function
    falsey, truthy = partition(nums)
    assert list(falsey) == [0, None, None]
    assert list(truthy) == [1, 2, 1, 3, 1, 4]


def test_partition_to_lists():
    """
    Assert that partition_to_lists splits an iterable into two lists according to a condition
    """
    nums = [1, 2, 1, 3, 1, 4, 0, None, None]
    not_ones, ones = partition_to_lists(nums, lambda n: n == 1)
    assert not_ones == [2, 3, 4, 0, None, None]
    assert ones == [1, 1, 1]
    # The default predicate is the standard Python bool() function
    falsey, truthy = partition_to_lists(nums)
    assert falsey == [0, None, None]
    assert truthy == [1, 2, 1, 3, 1, 4]


@pytest.mark.parametrize(
    "content,content_type,exp_summary_content",
    [
        ['{"bad": "response"}', "application/json", '{"bad": "response"}'],
        ["plain text", "text/plain", "plain text"],
        ["<div>HTML content</div>", "text/html; charset=utf-8", "(HTML body ignored)"],
    ],
)
def test_get_error_response_summary(content, content_type, exp_summary_content):
    """
    get_error_response_summary should provide a summary of an error HTTP response object with the correct bits of
    information depending on the type of content.
    """
    status_code = 400
    url = "http://example.com"
    mock_response = MockResponse(
        status_code=status_code, content=content, content_type=content_type, url=url
    )
    assert get_error_response_summary_dict(mock_response) == {
        "content": exp_summary_content,
        "url": url,
        "code": status_code,
    }


def test_send_refresh_request(mocker):
    """
    send_refresh_request should send a post request with clint_id and client_secret
    to get a new JWT access token
    """
    client_secret = "secrets"
    client_id = "clientid"
    url = "http://test.url"
    mock_post = mocker.patch("ui.utils.requests.post")
    send_refresh_request(url, client_id, client_secret)
    expected_token_url = f"{url}/oauth2/access_token/"
    expected_data = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "token_type": "JWT",
    }
    mock_post.assert_called_once_with(expected_token_url, data=expected_data)
