"""Tests for odl_video.pipeline"""

from unittest.mock import MagicMock

import pytest

from odl_video.pipeline import assign_user_groups


@pytest.fixture
def mock_user():
    """A user-like mock with default non-privileged flags."""
    user = MagicMock()
    user.username = "testuser"
    user.is_superuser = False
    user.is_staff = False
    return user


@pytest.fixture
def make_kwargs():
    """Build the kwargs that assign_user_groups expects from social-auth."""

    def _make(groups=None, with_social=True):
        if not with_social:
            return {}
        social_user = MagicMock()
        social_user.extra_data = {} if groups is None else {"user_groups": list(groups)}
        return {"social": social_user}

    return _make


@pytest.mark.parametrize(
    ("groups", "expected_superuser", "expected_staff"),
    [
        (["/Admin"], True, True),
        (["/admin"], True, True),
        (["/admin", "/staff"], True, True),
        (["/Staff"], False, True),
        (["/staff"], False, True),
    ],
)
def test_admin_and_staff_groups_assign_privileges(
    mock_user, make_kwargs, groups, expected_superuser, expected_staff
):
    """Admin/Staff keycloak groups map to the expected Django flags."""
    result = assign_user_groups(None, None, None, user=mock_user, **make_kwargs(groups))
    assert mock_user.is_superuser is expected_superuser
    assert mock_user.is_staff is expected_staff
    mock_user.save.assert_called_once()
    assert result == {"user": mock_user}


@pytest.mark.parametrize("starting_superuser", [True, False])
@pytest.mark.parametrize("starting_staff", [True, False])
@pytest.mark.parametrize(
    ("groups", "with_social"),
    [
        pytest.param(["/other"], True, id="other-group"),
        pytest.param([], True, id="empty-groups"),
        pytest.param(None, True, id="no-user_groups-key"),
        pytest.param(None, False, id="no-social-user"),
    ],
)
def test_non_admin_staff_group_preserves_existing_privileges(
    mock_user, make_kwargs, starting_superuser, starting_staff, groups, with_social
):
    """When the user is not in the Admin/Staff groups, existing flags are preserved."""
    mock_user.is_superuser = starting_superuser
    mock_user.is_staff = starting_staff

    assign_user_groups(
        None,
        None,
        None,
        user=mock_user,
        **make_kwargs(groups=groups, with_social=with_social),
    )

    assert mock_user.is_superuser is starting_superuser
    assert mock_user.is_staff is starting_staff
    mock_user.save.assert_not_called()


@pytest.mark.parametrize(
    ("starting_superuser", "starting_staff", "groups"),
    [
        (True, True, ["/admin"]),
        (False, True, ["/staff"]),
    ],
)
def test_no_save_when_privileges_unchanged(
    mock_user, make_kwargs, starting_superuser, starting_staff, groups
):
    """If the assigned flags already match the user, save() is skipped."""
    mock_user.is_superuser = starting_superuser
    mock_user.is_staff = starting_staff

    assign_user_groups(None, None, None, user=mock_user, **make_kwargs(groups))

    mock_user.save.assert_not_called()


def test_save_exception_is_caught_and_logged(mock_user, make_kwargs, mocker):
    """Errors raised by user.save() are logged, not propagated."""
    mock_user.save.side_effect = Exception("db error")
    mock_logger = mocker.patch("odl_video.pipeline.logger")

    assign_user_groups(None, None, None, user=mock_user, **make_kwargs(["/admin"]))

    mock_logger.error.assert_called_once()
