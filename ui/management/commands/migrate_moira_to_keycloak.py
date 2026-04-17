"""Management command to migrate OVS-stored groups to Keycloak groups."""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from ui.tasks import migrate_keycloak_groups_chunk
from ui.management.commands.keycloak_command_utils import (
    add_keycloak_arguments,
    build_keycloak_manager,
    chunked,
    get_ovs_keycloak_group_names,
    keycloak_config_from_options,
    parse_comma_list,
    print_summary,
)


class Command(BaseCommand):
    help = "Create Keycloak groups for OVS KeycloakGroup objects"

    def add_arguments(self, parser):
        add_keycloak_arguments(parser)
        parser.add_argument(
            "--limit-groups",
            "--limit-lists",
            dest="limit_groups",
            type=str,
            help="Comma-separated list of KeycloakGroup names to migrate",
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
            help="Number of groups per task chunk",
        )

    def handle(self, *args, **options):
        if options["chunk_size"] <= 0:
            raise CommandError("--chunk-size must be greater than 0")

        keycloak_config = keycloak_config_from_options(options)
        try:
            build_keycloak_manager(keycloak_config).get_groups()
        except Exception as exc:  # noqa: BLE001
            raise CommandError(f"Failed to connect to Keycloak: {exc}") from exc

        limit_groups = parse_comma_list(options.get("limit_groups"))
        group_names = get_ovs_keycloak_group_names(limit_lists=limit_groups)

        if not group_names:
            self.stdout.write(
                self.style.WARNING(
                    "No OVS KeycloakGroup objects matched the migration selection"
                )
            )
            return

        chunks = list(chunked(group_names, options["chunk_size"]))
        self.stdout.write(
            f"Selected {len(group_names)} OVS KeycloakGroup objects across {len(chunks)} chunks"
        )

        if options["dry_run"]:
            self.stdout.write(
                self.style.WARNING(
                    f"DRY RUN: would dispatch {len(chunks)} async group chunks"
                )
            )
            return

        summary = {"created": 0, "existing_skipped": 0, "failed": 0, "errors": []}

        async_results = [
            migrate_keycloak_groups_chunk.delay(chunk, keycloak_config)
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
            summary["failed"] += payload.get("failed", 0)
            summary["errors"].extend(payload.get("errors", []))

            self.stdout.write(
                f"chunk {index}/{total_chunks}: "
                f"created={payload.get('created', 0)} "
                f"skipped={payload.get('existing_skipped', 0)} "
                f"failed={payload.get('failed', 0)}"
            )

        print_summary(self, summary, "Group migration")

        if summary["failed"] > 0:
            self.stdout.write(
                self.style.WARNING(
                    "One or more group chunks failed; see summary errors above"
                )
            )
