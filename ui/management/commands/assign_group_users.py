"""Management command to assign existing Keycloak users to a single Keycloak group.

This command is intentionally scoped to one group per run and runs synchronously —
it's designed for small, targeted assignments (e.g. adding a handful of users to
``odl-engineering``), not bulk migration.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from ui.management.commands.keycloak_command_utils import (
    add_keycloak_arguments,
    build_keycloak_manager,
    keycloak_config_from_options,
    parse_comma_list,
    print_summary,
    record_exception,
)


class Command(BaseCommand):
    help = "Assign existing Keycloak users to a single Keycloak group"

    def add_arguments(self, parser):
        add_keycloak_arguments(parser)
        parser.add_argument(
            "--group",
            required=True,
            help="Target Keycloak group name (exactly one per run)",
        )
        parser.add_argument(
            "--users",
            required=True,
            help="Comma-separated list of user emails",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be done without making API changes",
        )

    def handle(self, *args, **options):
        keycloak_config = keycloak_config_from_options(options)
        users = parse_comma_list(options["users"])
        if not users:
            raise CommandError("--users must include at least one email")

        group_name = options["group"]
        if "," in group_name:
            raise CommandError("--group accepts exactly one group name per run")

        try:
            manager = build_keycloak_manager(keycloak_config)
            manager.get_groups()
        except Exception as exc:  # noqa: BLE001
            raise CommandError(f"Failed to connect to Keycloak: {exc}") from exc

        group = manager.find_group_by_name(group_name)
        if not group:
            raise CommandError(f"Keycloak group '{group_name}' does not exist")

        summary = {
            "assigned": 0,
            "existing_skipped": 0,
            "missing_users": 0,
            "failed": 0,
            "errors": [],
        }
        total = len(users)

        for index, email in enumerate(users, start=1):
            keycloak_user = manager.find_user_by_email(email)
            if not keycloak_user:
                summary["missing_users"] += 1
                self.stdout.write(
                    self.style.WARNING(
                        f"[{index}/{total}] skipping missing Keycloak user: {email}"
                    )
                )
                continue

            if options["dry_run"]:
                self.stdout.write(
                    f"[{index}/{total}] [DRY RUN] would assign {email} to {group_name}"
                )
                continue

            try:
                manager.add_user_to_group(keycloak_user["id"], group["id"])
                summary["assigned"] += 1
                self.stdout.write(f"[{index}/{total}] assigned {email}")
            except Exception as exc:  # noqa: BLE001
                record_exception(summary, email, exc)

        print_summary(self, summary, "Group assignment")

        if summary["failed"] > 0:
            raise CommandError("One or more user assignments failed")
