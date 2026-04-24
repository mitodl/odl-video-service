"""Tests for Keycloak migration management commands.

Helpers used by these tests (``FakeAsyncResult``, ``conflict_error``, and the
``manager_mock`` fixture) live in ``conftest.py`` alongside the sibling utils
test module.
"""

from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from ui.factories import CollectionFactory, KeycloakGroupFactory, UserFactory
from ui.management.commands.conftest import FakeAsyncResult, conflict_error

pytestmark = pytest.mark.django_db


def _keycloak_args():
    return {
        "keycloak_url": "http://kc.odl.local:7080",
        "keycloak_realm": "ovs-local",
        "keycloak_client_id": "odl-video-app",
        "keycloak_client_secret": "odl-video-secret-2025",
    }


def _patch_group_delay(mocker, **kwargs):
    return mocker.patch(
        "ui.management.commands.migrate_moira_to_keycloak.migrate_keycloak_groups_chunk.delay",
        **kwargs,
    )


def _patch_user_delay(mocker, **kwargs):
    return mocker.patch(
        "ui.management.commands.migrate_users_to_keycloak.migrate_keycloak_users_chunk.delay",
        **kwargs,
    )


def test_migrate_moira_to_keycloak_dry_run_does_not_dispatch_tasks(
    mocker, manager_mock
):
    """Dry run should not dispatch async Celery migration tasks."""
    mocker.patch(
        "ui.management.commands.migrate_moira_to_keycloak.get_ovs_keycloak_group_names",
        return_value=["odl-group-a"],
    )
    delay_mock = _patch_group_delay(mocker)

    out = StringIO()
    call_command(
        "migrate_moira_to_keycloak",
        dry_run=True,
        **_keycloak_args(),
        stdout=out,
    )

    assert "DRY RUN" in out.getvalue()
    delay_mock.assert_not_called()


def test_migrate_moira_to_keycloak_non_dry_run_dispatches_async_tasks(
    mocker, manager_mock
):
    """Non-dry-run group migration should dispatch chunk tasks."""
    mocker.patch(
        "ui.management.commands.migrate_moira_to_keycloak.get_ovs_keycloak_group_names",
        return_value=["odl-group-b"],
    )
    delay_mock = _patch_group_delay(
        mocker,
        return_value=FakeAsyncResult(
            {"created": 1, "existing_skipped": 0, "failed": 0, "errors": []}
        ),
    )

    out = StringIO()
    call_command(
        "migrate_moira_to_keycloak",
        dry_run=False,
        **_keycloak_args(),
        stdout=out,
    )

    assert "Group migration completed" in out.getvalue()
    delay_mock.assert_called_once()


def test_migrate_users_to_keycloak_dispatches_async_chunks(mocker, manager_mock):
    """User migration should support users + usernames selectors and dispatch chunks."""
    user_by_email = UserFactory.create(
        email="email-target@example.com", username="email_target"
    )
    user_by_username = UserFactory.create(
        email="username-target@example.com", username="username_target"
    )
    delay_mock = _patch_user_delay(
        mocker,
        return_value=FakeAsyncResult(
            {"created": 2, "existing_skipped": 0, "failed": 0, "errors": []}
        ),
    )

    out = StringIO()
    call_command(
        "migrate_users_to_keycloak",
        users=user_by_email.email,
        usernames=user_by_username.username,
        **_keycloak_args(),
        stdout=out,
    )

    assert "User migration completed" in out.getvalue()
    delay_mock.assert_called_once()


def test_migrate_users_to_keycloak_defaults_to_all_users(mocker, manager_mock):
    """When no selectors are provided, command should migrate all users."""
    UserFactory.create(email="all-a@example.com", username="all_a")
    UserFactory.create(email="all-b@example.com", username="all_b")
    delay_mock = _patch_user_delay(
        mocker,
        return_value=FakeAsyncResult(
            {
                "created": 2,
                "existing_skipped": 0,
                "invalid_skipped": 0,
                "failed": 0,
                "errors": [],
            }
        ),
    )

    out = StringIO()
    call_command("migrate_users_to_keycloak", **_keycloak_args(), stdout=out)

    output = out.getvalue()
    assert "defaulting to all Django users" in output
    assert "Selected 2 Django users" in output
    delay_mock.assert_called_once()


def test_migrate_users_to_keycloak_continues_when_chunk_fails(mocker, manager_mock):
    """Command should continue and summarize when a chunk result retrieval fails."""
    UserFactory.create(email="ok@example.com", username="ok_user")
    delay_mock = _patch_user_delay(
        mocker,
        return_value=FakeAsyncResult(raise_on_get=RuntimeError("backend unavailable")),
    )

    out = StringIO()
    call_command(
        "migrate_users_to_keycloak",
        users="ok@example.com",
        **_keycloak_args(),
        stdout=out,
    )

    output = out.getvalue()
    assert "One or more user chunks failed" in output
    assert "User migration completed" in output
    delay_mock.assert_called_once()


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


# ---------------------------------------------------------------------------
# Cross-command parametrized edge cases
# ---------------------------------------------------------------------------


# Commands that accept --chunk-size. assign_group_users does not.
_CHUNKED_COMMANDS = ["migrate_moira_to_keycloak", "migrate_users_to_keycloak"]

# Every command's handle() probes Keycloak via ``manager.get_groups()`` before
# doing any work, so connection failures are uniformly surfaced.
_ALL_COMMANDS = [
    ("migrate_moira_to_keycloak", {}),
    ("migrate_users_to_keycloak", {}),
    ("assign_group_users", {"group": "odl-group", "users": "user@example.com"}),
    ("migrate_collection_owners_to_keycloak_groups", {}),
]


@pytest.mark.parametrize("command_name", _CHUNKED_COMMANDS)
def test_commands_reject_non_positive_chunk_size(command_name):
    """--chunk-size <= 0 must fail fast for every command that accepts it."""
    with pytest.raises(CommandError, match="chunk-size must be greater than 0"):
        call_command(command_name, chunk_size=0, **_keycloak_args())


@pytest.mark.parametrize("command_name,extra_kwargs", _ALL_COMMANDS)
def test_commands_fail_on_keycloak_connection_error(
    manager_mock, command_name, extra_kwargs
):
    """Surface a CommandError if the Keycloak connection probe fails."""
    manager_mock.get_groups.side_effect = RuntimeError("unreachable")

    with pytest.raises(CommandError, match="Failed to connect to Keycloak"):
        call_command(command_name, **_keycloak_args(), **extra_kwargs)


# ---------------------------------------------------------------------------
# migrate_moira_to_keycloak edge cases
# ---------------------------------------------------------------------------


def test_migrate_moira_to_keycloak_warns_when_no_groups_match(mocker, manager_mock):
    """Empty selection should warn and return without dispatching tasks."""
    mocker.patch(
        "ui.management.commands.migrate_moira_to_keycloak.get_ovs_keycloak_group_names",
        return_value=[],
    )
    delay_mock = _patch_group_delay(mocker)

    out = StringIO()
    call_command("migrate_moira_to_keycloak", **_keycloak_args(), stdout=out)

    assert "No OVS KeycloakGroup objects matched" in out.getvalue()
    delay_mock.assert_not_called()


def test_migrate_moira_to_keycloak_reports_chunk_task_failures(mocker, manager_mock):
    """Task exceptions and non-dict payloads both route to the failed bucket."""
    mocker.patch(
        "ui.management.commands.migrate_moira_to_keycloak.get_ovs_keycloak_group_names",
        return_value=["group-a", "group-b"],
    )
    # One chunk raises; the other returns a non-dict payload.
    _patch_group_delay(
        mocker,
        side_effect=[
            FakeAsyncResult(raise_on_get=RuntimeError("backend unavailable")),
            FakeAsyncResult("not-a-dict"),
        ],
    )

    out = StringIO()
    call_command(
        "migrate_moira_to_keycloak", chunk_size=1, **_keycloak_args(), stdout=out
    )

    output = out.getvalue()
    assert "task failed (backend unavailable)" in output
    assert "task failed (not-a-dict)" in output
    assert "One or more group chunks failed" in output
    assert "Failed: 2" in output


# ---------------------------------------------------------------------------
# migrate_users_to_keycloak edge cases
# ---------------------------------------------------------------------------


def test_migrate_users_to_keycloak_skips_invalid_and_reports_no_matches(
    mocker, manager_mock
):
    """Users with missing/invalid email or username get counted and reported."""
    # Bypass factory-level email validation and assign invalid values directly.
    u1 = UserFactory.create(email="valid@example.com", username="valid_user")
    u1.email = ""
    u1.save(update_fields=["email"])
    u2 = UserFactory.create(email="good@example.com", username="good_user")
    u2.username = ""
    u2.save(update_fields=["username"])
    u3 = UserFactory.create(email="not-an-email", username="bad_email_user")
    u3.email = "not-an-email"
    u3.save(update_fields=["email"])

    delay_mock = _patch_user_delay(mocker)

    out = StringIO()
    call_command(
        "migrate_users_to_keycloak",
        usernames="valid_user,good_user,bad_email_user",
        **_keycloak_args(),
        stdout=out,
    )

    assert "No Django users matched the selection" in out.getvalue()
    delay_mock.assert_not_called()


def test_migrate_users_to_keycloak_dry_run_does_not_dispatch(mocker, manager_mock):
    """Dry-run should report what would happen and dispatch nothing."""
    UserFactory.create(email="dry@example.com", username="dry_user")
    delay_mock = _patch_user_delay(mocker)

    out = StringIO()
    call_command(
        "migrate_users_to_keycloak",
        users="dry@example.com",
        dry_run=True,
        **_keycloak_args(),
        stdout=out,
    )

    assert "DRY RUN" in out.getvalue()
    delay_mock.assert_not_called()


def test_migrate_users_to_keycloak_reports_mixed_valid_and_invalid(
    mocker, manager_mock
):
    """Mixed invalid+valid selection dispatches valid users and reports skip count."""
    valid = UserFactory.create(email="good@example.com", username="good_user")
    bad = UserFactory.create(email="ok@example.com", username="bad_user")
    bad.email = ""
    bad.save(update_fields=["email"])

    delay_mock = _patch_user_delay(
        mocker,
        return_value=FakeAsyncResult(
            {
                "created": 1,
                "existing_skipped": 0,
                "invalid_skipped": 0,
                "failed": 0,
                "errors": [],
            }
        ),
    )

    out = StringIO()
    call_command(
        "migrate_users_to_keycloak",
        usernames=f"{valid.username},{bad.username}",
        **_keycloak_args(),
        stdout=out,
    )

    output = out.getvalue()
    assert "Selected 1 Django users" in output
    assert "Skipped 1 users with missing/invalid username or email" in output
    delay_mock.assert_called_once()


def test_migrate_users_to_keycloak_reports_non_dict_payload(mocker, manager_mock):
    """Non-dict chunk payloads route to the failed bucket."""
    UserFactory.create(email="user@example.com", username="user_bad_payload")
    _patch_user_delay(mocker, return_value=FakeAsyncResult("not-a-dict"))

    out = StringIO()
    call_command(
        "migrate_users_to_keycloak",
        users="user@example.com",
        **_keycloak_args(),
        stdout=out,
    )

    output = out.getvalue()
    assert "task failed (not-a-dict)" in output
    assert "One or more user chunks failed" in output


# ---------------------------------------------------------------------------
# assign_group_users edge cases
# ---------------------------------------------------------------------------


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
# migrate_collection_owners_to_keycloak_groups
# ---------------------------------------------------------------------------


def test_migrate_collection_owners_warns_when_no_pairs(manager_mock):
    """No collections with admin_lists should warn and return without API calls."""
    out = StringIO()
    call_command(
        "migrate_collection_owners_to_keycloak_groups",
        **_keycloak_args(),
        stdout=out,
    )

    assert "No collection owner" in out.getvalue()
    manager_mock.find_group_by_name.assert_not_called()
    manager_mock.add_user_to_group.assert_not_called()


def test_migrate_collection_owners_dry_run(manager_mock):
    """Dry-run should list assignments without calling add_user_to_group."""
    owner = UserFactory.create(email="owner@example.com")
    group = KeycloakGroupFactory.create(name="odl-admin")
    CollectionFactory.create(owner=owner, admin_lists=[group])

    out = StringIO()
    call_command(
        "migrate_collection_owners_to_keycloak_groups",
        dry_run=True,
        **_keycloak_args(),
        stdout=out,
    )

    output = out.getvalue()
    assert "DRY RUN" in output
    assert "owner@example.com" in output
    assert "odl-admin" in output
    manager_mock.add_user_to_group.assert_not_called()


def test_migrate_collection_owners_assigns_owner_to_admin_group(manager_mock):
    """Happy path: owner found in Keycloak, group found, assignment made."""
    owner = UserFactory.create(email="owner@example.com")
    group = KeycloakGroupFactory.create(name="odl-admin")
    CollectionFactory.create(owner=owner, admin_lists=[group])

    manager_mock.find_group_by_name.return_value = {"id": "gid", "name": "odl-admin"}
    manager_mock.find_user_by_email.return_value = {"id": "uid"}

    out = StringIO()
    call_command(
        "migrate_collection_owners_to_keycloak_groups",
        **_keycloak_args(),
        stdout=out,
    )

    output = out.getvalue()
    assert "Collection owner group assignment completed" in output
    assert "Assigned: 1" in output
    manager_mock.add_user_to_group.assert_called_once_with("uid", "gid")


def test_migrate_collection_owners_deduplicates_pairs(manager_mock):
    """Same owner across multiple collections with the same group produces one assignment."""
    owner = UserFactory.create(email="shared@example.com")
    group = KeycloakGroupFactory.create(name="shared-group")
    CollectionFactory.create(owner=owner, admin_lists=[group])
    CollectionFactory.create(owner=owner, admin_lists=[group])

    manager_mock.find_group_by_name.return_value = {"id": "gid", "name": "shared-group"}
    manager_mock.find_user_by_email.return_value = {"id": "uid"}

    out = StringIO()
    call_command(
        "migrate_collection_owners_to_keycloak_groups",
        **_keycloak_args(),
        stdout=out,
    )

    assert "Assigned: 1" in out.getvalue()
    manager_mock.add_user_to_group.assert_called_once()


def test_migrate_collection_owners_skips_missing_group(manager_mock):
    """Missing Keycloak group is counted and skipped."""
    owner = UserFactory.create(email="owner@example.com")
    group = KeycloakGroupFactory.create(name="ghost-group")
    CollectionFactory.create(owner=owner, admin_lists=[group])

    manager_mock.find_group_by_name.return_value = None

    out = StringIO()
    call_command(
        "migrate_collection_owners_to_keycloak_groups",
        **_keycloak_args(),
        stdout=out,
    )

    output = out.getvalue()
    assert "skipping missing Keycloak group" in output
    manager_mock.add_user_to_group.assert_not_called()


def test_migrate_collection_owners_skips_missing_user(manager_mock):
    """Missing Keycloak user is counted and skipped without raising."""
    owner = UserFactory.create(email="ghost@example.com")
    group = KeycloakGroupFactory.create(name="odl-admin")
    CollectionFactory.create(owner=owner, admin_lists=[group])

    manager_mock.find_group_by_name.return_value = {"id": "gid", "name": "odl-admin"}
    manager_mock.find_user_by_email.return_value = None

    out = StringIO()
    call_command(
        "migrate_collection_owners_to_keycloak_groups",
        **_keycloak_args(),
        stdout=out,
    )

    output = out.getvalue()
    assert "skipping missing Keycloak user" in output
    manager_mock.add_user_to_group.assert_not_called()


def test_migrate_collection_owners_counts_conflict_as_existing(manager_mock):
    """HTTP 409 when adding to group is treated as existing membership (skipped, not failed)."""
    owner = UserFactory.create(email="owner@example.com")
    group = KeycloakGroupFactory.create(name="odl-admin")
    CollectionFactory.create(owner=owner, admin_lists=[group])

    manager_mock.find_group_by_name.return_value = {"id": "gid", "name": "odl-admin"}
    manager_mock.find_user_by_email.return_value = {"id": "uid"}
    manager_mock.add_user_to_group.side_effect = conflict_error()

    out = StringIO()
    call_command(
        "migrate_collection_owners_to_keycloak_groups",
        **_keycloak_args(),
        stdout=out,
    )

    output = out.getvalue()
    assert "Existing skipped: 1" in output
    assert "Failed: 0" in output
    manager_mock.add_user_to_group.assert_called_once()


def test_migrate_collection_owners_raises_on_assignment_failure(manager_mock):
    """Non-conflict assignment failure raises CommandError after summary."""
    owner = UserFactory.create(email="owner@example.com")
    group = KeycloakGroupFactory.create(name="odl-admin")
    CollectionFactory.create(owner=owner, admin_lists=[group])

    manager_mock.find_group_by_name.return_value = {"id": "gid", "name": "odl-admin"}
    manager_mock.find_user_by_email.return_value = {"id": "uid"}
    manager_mock.add_user_to_group.side_effect = RuntimeError("server error")

    with pytest.raises(CommandError, match="One or more group assignments failed"):
        call_command(
            "migrate_collection_owners_to_keycloak_groups",
            **_keycloak_args(),
        )


def test_migrate_collection_owners_limit_groups_filters_pairs(manager_mock):
    """--limit-groups restricts which admin groups are considered."""
    owner = UserFactory.create(email="owner@example.com")
    group_a = KeycloakGroupFactory.create(name="group-a")
    group_b = KeycloakGroupFactory.create(name="group-b")
    CollectionFactory.create(owner=owner, admin_lists=[group_a, group_b])

    manager_mock.find_group_by_name.return_value = {"id": "gid", "name": "group-a"}
    manager_mock.find_user_by_email.return_value = {"id": "uid"}

    out = StringIO()
    call_command(
        "migrate_collection_owners_to_keycloak_groups",
        limit_groups="group-a",
        **_keycloak_args(),
        stdout=out,
    )

    assert "Assigned: 1" in out.getvalue()
    manager_mock.add_user_to_group.assert_called_once()


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
        user=u1, provider="keycloak", uid="alice@example.com"
    ).exists()
    assert UserSocialAuth.objects.filter(
        user=u2, provider="keycloak", uid="bob@example.com"
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
