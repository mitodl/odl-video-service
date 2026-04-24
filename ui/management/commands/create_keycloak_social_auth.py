"""Management command to pre-create Keycloak social-auth bindings for existing users.

When users are migrated to Keycloak and then log in via OIDC for the first time,
social-auth looks for an existing ``UserSocialAuth(provider="keycloak", uid=<email>)``
record to determine which Django user to associate with the session.  If no such
record exists, social-auth creates a *new* Django user, resulting in duplicate
accounts.

This command pre-creates those bindings so that migrated users are correctly
matched to their existing Django accounts on first Keycloak login.

The UID is the user's email address, matching the ``SOCIAL_AUTH_KEYCLOAK_ID_KEY``
Django setting (set to ``"email"``) and the Keycloak backend's ``id_key()`` resolution.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError
from django.db.models import Q

from social_django.models import UserSocialAuth

User = get_user_model()

KEYCLOAK_PROVIDER = "keycloak"


class Command(BaseCommand):
    help = (
        "Pre-create Keycloak social-auth bindings for existing Django users so that "
        "migrated users are matched to their existing accounts on first OIDC login."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--users",
            type=str,
            default=None,
            help="Comma-separated list of user emails to process (default: all users)",
        )
        parser.add_argument(
            "--usernames",
            type=str,
            default=None,
            help="Comma-separated list of Django usernames to process",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be created without writing to the database",
        )

    def handle(self, *args, **options):
        emails = _parse_comma_list(options["users"])
        usernames = _parse_comma_list(options["usernames"])

        queryset = User.objects.all()
        if emails or usernames:
            selector = Q()
            if emails:
                selector |= Q(email__in=emails)
            if usernames:
                selector |= Q(username__in=usernames)
            queryset = queryset.filter(selector)
        else:
            self.stdout.write(
                self.style.WARNING(
                    "No --users/--usernames selector provided; processing all Django users"
                )
            )

        # Fetch all at once; this is pure DB work with no external calls.
        users = list(queryset.distinct().only("id", "email", "username"))

        if not users:
            self.stdout.write(
                self.style.WARNING("No Django users matched the selection")
            )
            return

        # Pre-fetch existing bindings to avoid per-user queries.
        existing_uids = set(
            UserSocialAuth.objects.filter(provider=KEYCLOAK_PROVIDER).values_list(
                "uid", flat=True
            )
        )

        summary = {
            "created": 0,
            "already_bound": 0,
            "uid_conflict": 0,
            "no_email": 0,
            "failed": 0,
            "errors": [],
        }

        for user in users:
            email = (user.email or "").strip()

            if not email:
                summary["no_email"] += 1
                self.stdout.write(
                    self.style.WARNING(
                        f"skipping user {user.username!r}: no email address"
                    )
                )
                continue

            # Check whether this user already has a Keycloak binding (by user FK).
            if UserSocialAuth.objects.filter(
                user=user, provider=KEYCLOAK_PROVIDER
            ).exists():
                summary["already_bound"] += 1
                self.stdout.write(
                    f"skipping {email}: already has a Keycloak social-auth binding"
                )
                continue

            # Check whether another user already owns this UID.
            if email in existing_uids:
                summary["uid_conflict"] += 1
                summary["errors"].append(
                    f"{email}: UID already bound to a different user"
                )
                self.stdout.write(
                    self.style.WARNING(
                        f"skipping {email}: UID already bound to a different user"
                    )
                )
                continue

            if options["dry_run"]:
                self.stdout.write(
                    f"  [DRY RUN] would create UserSocialAuth(provider={KEYCLOAK_PROVIDER!r}, uid={email!r}) for {user.username!r}"
                )
                summary["created"] += 1
                continue

            try:
                UserSocialAuth.objects.create(
                    user=user,
                    provider=KEYCLOAK_PROVIDER,
                    uid=email,
                    extra_data={},
                )
                existing_uids.add(email)
                summary["created"] += 1
                self.stdout.write(f"created binding for {email}")
            except IntegrityError as exc:
                summary["failed"] += 1
                summary["errors"].append(f"{email}: {exc}")
                self.stdout.write(
                    self.style.WARNING(f"failed to create binding for {email}: {exc}")
                )

        _print_summary(self, summary, options["dry_run"])

        if summary["failed"] > 0:
            raise CommandError(
                "One or more bindings could not be created; see errors above"
            )


def _parse_comma_list(value):
    if not value:
        return []
    seen = set()
    result = []
    for item in value.split(","):
        item = item.strip()
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result


def _print_summary(command, summary, dry_run):
    label = "Dry-run summary" if dry_run else "Social-auth binding creation completed"
    command.stdout.write(command.style.SUCCESS(label))
    command.stdout.write(f"  Created: {summary['created']}")
    command.stdout.write(f"  Already bound (skipped): {summary['already_bound']}")
    command.stdout.write(f"  No email (skipped): {summary['no_email']}")
    if summary["uid_conflict"]:
        command.stdout.write(
            command.style.WARNING(
                f"  UID conflicts (skipped): {summary['uid_conflict']}"
            )
        )
    if summary["failed"]:
        command.stdout.write(command.style.WARNING(f"  Failed: {summary['failed']}"))
    if summary["errors"]:
        command.stdout.write(command.style.WARNING("Errors:"))
        for error in summary["errors"]:
            command.stdout.write(command.style.WARNING(f"  - {error}"))
