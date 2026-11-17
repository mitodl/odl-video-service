"""Tests for the Keycloak management commands.

Helpers used by these tests (``conflict_error`` and the ``manager_mock``
fixture) live in ``conftest.py`` alongside the sibling utils test module.
"""

from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from ui.factories import UserFactory
from ui.management.commands.conftest import conflict_error

pytestmark = pytest.mark.django_db


def _keycloak_args():
    return {
        "keycloak_url": "http://kc.odl.local:7080",
        "keycloak_realm": "ovs-local",
        "keycloak_client_id": "odl-video-app",
        "keycloak_client_secret": "odl-video-secret-2025",
    }


def test_assign_group_users_skips_missing_and_existing_membership(manager_mock):
    """Assignment command should skip missing users and 409 membership conflicts."""
    manager_mock.find_group_by_name.return_value = {
        "id": "group-id",
        "name": "odl-engineering",
    }
    manager_mock.find_user_by_email.side_effect = [
        None,
        {"id": "existing-user"},
        {"id": "new-user"},
    ]
    manager_mock.add_user_to_group.side_effect = [conflict_error(), True]

    out = StringIO()
    call_command(
        "assign_group_users",
        group="odl-engineering",
        users="missing@example.com,existing@example.com,new@example.com",
        **_keycloak_args(),
        stdout=out,
    )

    output = out.getvalue()
    assert "Group assignment completed" in output
    assert "Assigned: 1" in output
    assert "Existing skipped: 1" in output
    assert "Missing users skipped: 1" in output


def test_assign_group_users_fails_on_keycloak_connection_error(manager_mock):
    """Surface a CommandError if the Keycloak connection probe fails."""
    manager_mock.get_groups.side_effect = RuntimeError("unreachable")

    with pytest.raises(CommandError, match="Failed to connect to Keycloak"):
        call_command(
            "assign_group_users",
            group="odl-group",
            users="user@example.com",
            **_keycloak_args(),
        )


@pytest.mark.parametrize(
    "group,users,match",
    [
        ("odl-group", " , ", "--users must include at least one email"),
        (
            "odl-a,odl-b",
            "user@example.com",
            "--group accepts exactly one group name per run",
        ),
    ],
    ids=["empty-users", "multi-group"],
)
def test_assign_group_users_rejects_bad_arguments(group, users, match):
    """--users must be non-empty and --group must be a single name."""
    with pytest.raises(CommandError, match=match):
        call_command("assign_group_users", group=group, users=users, **_keycloak_args())


def test_assign_group_users_fails_when_group_missing(manager_mock):
    """Missing Keycloak group raises a CommandError."""
    manager_mock.find_group_by_name.return_value = None

    with pytest.raises(CommandError, match="does not exist"):
        call_command(
            "assign_group_users",
            group="ghost-group",
            users="user@example.com",
            **_keycloak_args(),
        )


def test_assign_group_users_dry_run_does_not_call_add(manager_mock):
    """Dry-run must not call add_user_to_group for existing users."""
    manager_mock.find_group_by_name.return_value = {"id": "g", "name": "odl-group"}
    manager_mock.find_user_by_email.return_value = {"id": "u"}

    out = StringIO()
    call_command(
        "assign_group_users",
        group="odl-group",
        users="user@example.com",
        dry_run=True,
        **_keycloak_args(),
        stdout=out,
    )

    assert "[DRY RUN] would assign user@example.com" in out.getvalue()
    manager_mock.add_user_to_group.assert_not_called()


def test_assign_group_users_raises_when_any_assignment_fails(manager_mock):
    """A non-conflict assignment failure must raise CommandError after the summary."""
    manager_mock.find_group_by_name.return_value = {"id": "g", "name": "odl-group"}
    manager_mock.find_user_by_email.return_value = {"id": "u"}
    manager_mock.add_user_to_group.side_effect = RuntimeError("server down")

    with pytest.raises(CommandError, match="One or more user assignments failed"):
        call_command(
            "assign_group_users",
            group="odl-group",
            users="user@example.com",
            **_keycloak_args(),
        )


# ---------------------------------------------------------------------------
# create_keycloak_social_auth
# ---------------------------------------------------------------------------


def test_create_keycloak_social_auth_creates_bindings():
    """Happy path: creates a UserSocialAuth record for each eligible user."""
    from social_django.models import UserSocialAuth

    u1 = UserFactory.create(email="alice@example.com")
    u2 = UserFactory.create(email="bob@example.com")

    out = StringIO()
    call_command("create_keycloak_social_auth", stdout=out)

    assert UserSocialAuth.objects.filter(
        user=u1, provider="keycloak", uid="alice@example.com", id_key="email"
    ).exists()
    assert UserSocialAuth.objects.filter(
        user=u2, provider="keycloak", uid="bob@example.com", id_key="email"
    ).exists()
    assert "Created: 2" in out.getvalue()


def test_create_keycloak_social_auth_skips_existing_binding():
    """Users who already have a Keycloak binding are skipped without error."""
    from social_django.models import UserSocialAuth

    user = UserFactory.create(email="bound@example.com")
    UserSocialAuth.objects.create(
        user=user, provider="keycloak", uid="bound@example.com", extra_data={}
    )

    out = StringIO()
    call_command("create_keycloak_social_auth", users="bound@example.com", stdout=out)

    assert (
        UserSocialAuth.objects.filter(
            provider="keycloak", uid="bound@example.com"
        ).count()
        == 1
    )
    assert "Already bound" in out.getvalue()


def test_create_keycloak_social_auth_skips_user_with_no_email():
    """Users with no email address are counted and skipped."""
    from social_django.models import UserSocialAuth

    user = UserFactory.create(email="")
    user.email = ""
    user.save(update_fields=["email"])

    out = StringIO()
    call_command("create_keycloak_social_auth", usernames=user.username, stdout=out)

    assert not UserSocialAuth.objects.filter(user=user, provider="keycloak").exists()
    assert "No email" in out.getvalue()


def test_create_keycloak_social_auth_skips_uid_already_bound_to_different_user():
    """When a UID is already owned by another user, the new binding is skipped."""
    from social_django.models import UserSocialAuth

    owner = UserFactory.create(email="shared@example.com")
    newcomer = UserFactory.create(email="shared@example.com")
    UserSocialAuth.objects.create(
        user=owner, provider="keycloak", uid="shared@example.com", extra_data={}
    )

    out = StringIO()
    call_command("create_keycloak_social_auth", usernames=newcomer.username, stdout=out)

    # Still only one binding for that UID
    assert (
        UserSocialAuth.objects.filter(
            provider="keycloak", uid="shared@example.com"
        ).count()
        == 1
    )
    assert "UID conflict" in out.getvalue() or "different user" in out.getvalue()


def test_create_keycloak_social_auth_dry_run_does_not_write():
    """Dry-run reports what would be done but creates no records."""
    from social_django.models import UserSocialAuth

    user = UserFactory.create(email="dryrun@example.com")

    out = StringIO()
    call_command(
        "create_keycloak_social_auth",
        users="dryrun@example.com",
        dry_run=True,
        stdout=out,
    )

    assert not UserSocialAuth.objects.filter(user=user, provider="keycloak").exists()
    output = out.getvalue()
    assert "DRY RUN" in output
    assert "Created: 1" in output


def test_create_keycloak_social_auth_filters_by_email():
    """--users selector restricts processing to the specified emails."""
    from social_django.models import UserSocialAuth

    target = UserFactory.create(email="target@example.com")
    other = UserFactory.create(email="other@example.com")

    out = StringIO()
    call_command("create_keycloak_social_auth", users="target@example.com", stdout=out)

    assert UserSocialAuth.objects.filter(user=target, provider="keycloak").exists()
    assert not UserSocialAuth.objects.filter(user=other, provider="keycloak").exists()


def test_create_keycloak_social_auth_filters_by_username():
    """--usernames selector restricts processing to the specified usernames."""
    from social_django.models import UserSocialAuth

    target = UserFactory.create(username="the_target", email="the_target@example.com")
    other = UserFactory.create(username="the_other", email="the_other@example.com")

    out = StringIO()
    call_command("create_keycloak_social_auth", usernames="the_target", stdout=out)

    assert UserSocialAuth.objects.filter(user=target, provider="keycloak").exists()
    assert not UserSocialAuth.objects.filter(user=other, provider="keycloak").exists()


def test_create_keycloak_social_auth_warns_no_matching_users():
    """No matching users produces a warning and exits cleanly."""
    out = StringIO()
    call_command("create_keycloak_social_auth", users="nobody@example.com", stdout=out)
    assert "No Django users matched" in out.getvalue()
