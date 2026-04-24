"""Management command to assign collection owners to their collection's admin groups in Keycloak.

OVS has no explicit user→group membership table. The one derivable mapping is:
  Collection.owner  →  Collection.admin_lists (KeycloakGroups)

A collection owner should be a member of every admin group that governs that
collection. This command reconstructs that mapping from the OVS database and
performs the corresponding group-membership assignments in Keycloak.

Both the Keycloak user (by owner email) and the Keycloak group (by group name)
must already exist in Keycloak before the assignment can be made. Run
``migrate_users_to_keycloak`` and ``migrate_moira_to_keycloak`` first.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from ui.models import Collection
from ui.management.commands.keycloak_command_utils import (
    add_keycloak_arguments,
    build_keycloak_manager,
    keycloak_config_from_options,
    parse_comma_list,
    print_summary,
    record_exception,
)


def get_owner_admin_group_pairs(limit_groups=None):
    """Return deduplicated (owner_email, group_name) pairs from Collection data.

    Each pair means the collection owner should be a member of that admin group.
    Only collections that have at least one admin_list entry are included.
    """
    qs = (
        Collection.objects.select_related("owner")
        .prefetch_related("admin_lists")
        .filter(admin_lists__isnull=False)
        .distinct()
    )

    seen = set()
    pairs = []
    for collection in qs:
        email = (collection.owner.email or "").strip()
        if not email:
            continue
        for group in collection.admin_lists.all():
            if limit_groups and group.name not in limit_groups:
                continue
            key = (email, group.name)
            if key not in seen:
                seen.add(key)
                pairs.append(key)
    return pairs


class Command(BaseCommand):
    help = (
        "Assign collection owners to their collection's Keycloak admin groups. "
        "Requires users and groups to already exist in Keycloak."
    )

    def add_arguments(self, parser):
        add_keycloak_arguments(parser)
        parser.add_argument(
            "--limit-groups",
            type=str,
            default=None,
            help="Comma-separated list of group names to restrict assignments to",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be done without making API changes",
        )

    def handle(self, *args, **options):
        keycloak_config = keycloak_config_from_options(options)
        try:
            manager = build_keycloak_manager(keycloak_config)
            manager.get_groups()
        except Exception as exc:  # noqa: BLE001
            raise CommandError(f"Failed to connect to Keycloak: {exc}") from exc

        limit_groups = parse_comma_list(options.get("limit_groups"))
        pairs = get_owner_admin_group_pairs(
            limit_groups=set(limit_groups) if limit_groups else None
        )

        if not pairs:
            self.stdout.write(
                self.style.WARNING(
                    "No collection owner → admin group pairs found in OVS database"
                )
            )
            return

        self.stdout.write(
            f"Found {len(pairs)} unique owner → admin group assignment(s) to process"
        )

        if options["dry_run"]:
            for email, group_name in pairs:
                self.stdout.write(f"  [DRY RUN] would assign {email} → {group_name}")
            self.stdout.write(
                self.style.WARNING(
                    f"DRY RUN: {len(pairs)} assignment(s) would be attempted"
                )
            )
            return

        summary = {
            "assigned": 0,
            "existing_skipped": 0,
            "missing_users": 0,
            "missing_groups": 0,
            "failed": 0,
            "errors": [],
        }
        total = len(pairs)

        for index, (email, group_name) in enumerate(pairs, start=1):
            group = manager.find_group_by_name(group_name)
            if not group:
                summary["missing_groups"] += 1
                self.stdout.write(
                    self.style.WARNING(
                        f"[{index}/{total}] skipping missing Keycloak group: {group_name}"
                    )
                )
                continue

            keycloak_user = manager.find_user_by_email(email)
            if not keycloak_user:
                summary["missing_users"] += 1
                self.stdout.write(
                    self.style.WARNING(
                        f"[{index}/{total}] skipping missing Keycloak user: {email}"
                    )
                )
                continue

            try:
                manager.add_user_to_group(keycloak_user["id"], group["id"])
                summary["assigned"] += 1
                self.stdout.write(f"[{index}/{total}] assigned {email} → {group_name}")
            except Exception as exc:  # noqa: BLE001
                record_exception(summary, f"{email} → {group_name}", exc)

        print_summary(self, summary, "Collection owner group assignment")

        if summary["failed"] > 0:
            raise CommandError("One or more group assignments failed")
