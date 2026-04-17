"""Management command to migrate Django users to Keycloak users."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email
from django.db.models import Q

from ui.tasks import migrate_keycloak_users_chunk
from ui.management.commands.keycloak_command_utils import (
    add_keycloak_arguments,
    build_keycloak_manager,
    chunked,
    keycloak_config_from_options,
    parse_comma_list,
    print_summary,
)

User = get_user_model()


class Command(BaseCommand):
    help = "Create Keycloak users from Django users using async chunked Celery tasks"

    def add_arguments(self, parser):
        add_keycloak_arguments(parser)
        parser.add_argument(
            "--users",
            type=str,
            help="Comma-separated list of user emails to migrate",
        )
        parser.add_argument(
            "--usernames",
            type=str,
            help="Comma-separated list of Django usernames to migrate",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be done without dispatching Celery tasks",
        )
        parser.add_argument(
            "--chunk-size",
            type=int,
            default=100,
            help="Number of users per task chunk",
        )
        parser.add_argument(
            "--default-password",
            type=str,
            default="ChangeMe123!",
            help="Temporary password for newly created Keycloak users",
        )

    def handle(self, *args, **options):
        if options["chunk_size"] <= 0:
            raise CommandError("--chunk-size must be greater than 0")

        emails = parse_comma_list(options["users"])
        usernames = parse_comma_list(options["usernames"])

        keycloak_config = keycloak_config_from_options(options)
        try:
            build_keycloak_manager(keycloak_config).get_groups()
        except Exception as exc:  # noqa: BLE001
            raise CommandError(f"Failed to connect to Keycloak: {exc}") from exc

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
                    "No --users/--usernames selector provided; defaulting to all Django users"
                )
            )

        users_payload = list(
            queryset.distinct().values(
                "id", "username", "email", "first_name", "last_name"
            )
        )

        valid_users_payload = []
        invalid_skipped = 0
        for payload in users_payload:
            email = (payload.get("email") or "").strip()
            username = (payload.get("username") or "").strip()
            if not email or not username:
                invalid_skipped += 1
                continue
            try:
                validate_email(email)
            except ValidationError:
                invalid_skipped += 1
                continue
            valid_users_payload.append(payload)

        if not valid_users_payload:
            self.stdout.write(
                self.style.WARNING("No Django users matched the selection")
            )
            return

        chunks = list(chunked(valid_users_payload, options["chunk_size"]))
        self.stdout.write(
            f"Selected {len(valid_users_payload)} Django users across {len(chunks)} chunks"
        )
        if invalid_skipped:
            self.stdout.write(
                self.style.WARNING(
                    f"Skipped {invalid_skipped} users with missing/invalid username or email"
                )
            )

        if options["dry_run"]:
            self.stdout.write(
                self.style.WARNING(
                    f"DRY RUN: would dispatch {len(chunks)} async user chunks"
                )
            )
            return

        summary = {
            "created": 0,
            "existing_skipped": 0,
            "invalid_skipped": invalid_skipped,
            "failed": 0,
            "errors": [],
        }

        async_results = [
            migrate_keycloak_users_chunk.delay(
                chunk, keycloak_config, options["default_password"]
            )
            for chunk in chunks
        ]

        total_chunks = len(chunks)
        for index, result in enumerate(async_results, start=1):
            try:
                payload = result.get(propagate=False)
            except Exception as exc:  # noqa: BLE001
                summary["failed"] += 1
                summary["errors"].append(f"chunk {index}: {exc}")
                self.stdout.write(
                    self.style.WARNING(
                        f"chunk {index}/{total_chunks}: task failed ({exc})"
                    )
                )
                continue

            if not isinstance(payload, dict):
                summary["failed"] += 1
                summary["errors"].append(f"chunk {index}: {payload}")
                self.stdout.write(
                    self.style.WARNING(
                        f"chunk {index}/{total_chunks}: task failed ({payload})"
                    )
                )
                continue

            summary["created"] += payload.get("created", 0)
            summary["existing_skipped"] += payload.get("existing_skipped", 0)
            summary["invalid_skipped"] += payload.get("invalid_skipped", 0)
            summary["failed"] += payload.get("failed", 0)
            summary["errors"].extend(payload.get("errors", []))

            self.stdout.write(
                f"chunk {index}/{total_chunks}: "
                f"created={payload.get('created', 0)} "
                f"skipped={payload.get('existing_skipped', 0)} "
                f"invalid={payload.get('invalid_skipped', 0)} "
                f"failed={payload.get('failed', 0)}"
            )

        print_summary(self, summary, "User migration")

        if summary["failed"] > 0:
            self.stdout.write(
                self.style.WARNING(
                    "One or more user chunks failed; see summary errors above"
                )
            )
