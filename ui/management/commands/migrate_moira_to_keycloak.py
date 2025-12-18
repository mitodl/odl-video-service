"""
Management command to migrate MOIRA lists and users to Keycloak
"""

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.conf import settings
from django.utils import timezone
import logging
import re
import time

from ui.keycloak_utils import KeycloakManager, KeycloakUser
from ui.models import Collection, KeycloakGroup, Video
from ui.moira_util import get_moira_client, list_members

logger = logging.getLogger(__name__)
User = get_user_model()


class Command(BaseCommand):
    help = "Migrate MOIRA lists and users to Keycloak groups and users"

    def add_arguments(self, parser):
        parser.add_argument(
            "--keycloak-url",
            type=str,
            default=getattr(
                settings, "KEYCLOAK_SERVER_URL", "http://kc.odl.local:7080"
            ),
            help="Keycloak server URL",
        )
        parser.add_argument(
            "--keycloak-realm",
            type=str,
            default=getattr(settings, "KEYCLOAK_REALM", "ovs-local"),
            help="Keycloak realm name",
        )
        parser.add_argument(
            "--keycloak-admin-username",
            type=str,
            default="admin",
            help="Keycloak admin username",
        )
        parser.add_argument(
            "--keycloak-admin-password",
            type=str,
            default="admin",
            help="Keycloak admin password",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be done without making changes",
        )
        parser.add_argument(
            "--skip-user-creation",
            action="store_true",
            help="Skip creating users in Keycloak (only create groups)",
        )
        parser.add_argument(
            "--default-password",
            type=str,
            default="MoiraToKeycloak25!",
            help="Default password for migrated users",
        )
        parser.add_argument(
            "--limit-lists",
            type=str,
            help="Comma-separated list of MOIRA list names to migrate (migrate all if not specified)",
        )

    def handle(self, *args, **options):
        """Main command handler"""
        self.dry_run = options["dry_run"]
        self.skip_user_creation = options["skip_user_creation"]
        self.default_password = options["default_password"]

        # Parse limit_lists
        self.limit_lists = None
        if options["limit_lists"]:
            self.limit_lists = [
                name.strip() for name in options["limit_lists"].split(",")
            ]
            self.stdout.write(f"Limiting migration to lists: {self.limit_lists}")

        # Initialize Keycloak manager
        try:
            self.kc_manager = KeycloakManager(
                keycloak_url=options["keycloak_url"],
                realm=options["keycloak_realm"],
                admin_username=options["keycloak_admin_username"],
                admin_password=options["keycloak_admin_password"],
            )
            # Test connection
            self.kc_manager.get_groups()
            self.stdout.write(
                self.style.SUCCESS("✓ Connected to Keycloak successfully")
            )
        except Exception as e:
            raise CommandError(f"Failed to connect to Keycloak: {e}")

        if self.dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN MODE - No changes will be made")
            )

        # Get all MOIRA lists used in the system
        moira_lists = self.get_all_moira_lists()

        if not moira_lists:
            self.stdout.write(self.style.WARNING("No MOIRA lists found in the system"))
            return

        self.stdout.write(f"Found {len(moira_lists)} unique MOIRA lists in the system")

        # Migrate each MOIRA list
        migration_summary = {
            "groups_created": 0,
            "groups_existed": 0,
            "users_created": 0,
            "users_existed": 0,
            "django_users_created": 0,
            "errors": [],
            "timing": {
                "total_time": 0,
                "moira_list_fetch_time": 0,
                "group_creation_time": 0,
                "member_fetch_time": 0,
                "user_migration_time": 0,
            },
        }

        migration_start_time = time.time()

        for moira_list in moira_lists:
            try:
                result = self.migrate_moira_list(moira_list)

                migration_summary["groups_created"] += result["group_created"]
                migration_summary["groups_existed"] += result["group_existed"]
                migration_summary["users_created"] += result["users_created"]
                migration_summary["users_existed"] += result["users_existed"]
                migration_summary["django_users_created"] += result[
                    "django_users_created"
                ]

                # Aggregate timing information
                migration_summary["timing"]["moira_list_fetch_time"] += result[
                    "timing"
                ].get("moira_list_fetch_time", 0)
                migration_summary["timing"]["group_creation_time"] += result[
                    "timing"
                ].get("group_creation_time", 0)
                migration_summary["timing"]["member_fetch_time"] += result[
                    "timing"
                ].get("member_fetch_time", 0)
                migration_summary["timing"]["user_migration_time"] += result[
                    "timing"
                ].get("user_migration_time", 0)

            except Exception as e:
                error_msg = f"Failed to migrate list '{moira_list.name}': {e}"
                migration_summary["errors"].append(error_msg)
                self.stdout.write(self.style.ERROR(error_msg))

        migration_summary["timing"]["total_time"] = time.time() - migration_start_time

        # Print summary
        self.print_migration_summary(migration_summary)

        # Ask about removing MOIRA usage
        if not self.dry_run and migration_summary["groups_created"] > 0:
            self.stdout.write("\n" + "=" * 60)
            self.stdout.write("IMPORTANT: After verifying the migration:")
            self.stdout.write("1. Update your Django authentication pipeline")
            self.stdout.write("2. Remove MOIRA-related code and dependencies")
            self.stdout.write(
                "3. Update collection/video permissions to use Keycloak groups"
            )
            self.stdout.write("=" * 60)

    def get_all_moira_lists(self):
        """Get all unique MOIRA lists used in the system"""
        moira_lists = set()

        # Get lists from collections
        for collection in Collection.objects.all():
            moira_lists.update(collection.view_lists.all())
            moira_lists.update(collection.admin_lists.all())

        # Get lists from videos
        for video in Video.objects.filter(view_lists__isnull=False):
            moira_lists.update(video.view_lists.all())

        # Filter by limit_lists if specified
        if self.limit_lists:
            moira_lists = {ml for ml in moira_lists if ml.name in self.limit_lists}

        return list(moira_lists)

    def migrate_moira_list(self, kc_group: KeycloakGroup):
        """Migrate a single MOIRA list to Keycloak"""
        self.stdout.write(f"\nMigrating MOIRA list: {kc_group.name}")

        result = {
            "group_created": 0,
            "group_existed": 0,
            "users_created": 0,
            "users_existed": 0,
            "django_users_created": 0,
            "timing": {
                "moira_list_fetch_time": 0,
                "group_creation_time": 0,
                "member_fetch_time": 0,
                "user_migration_time": 0,
            },
        }

        # 1. Create Keycloak group if it doesn't exist
        group_start_time = time.time()
        group = self.kc_manager.find_group_by_name(kc_group.name)
        if group:
            self.stdout.write(f"  Group '{kc_group.name}' already exists in Keycloak")
            result["group_existed"] = 1
        else:
            if not self.dry_run:
                moira_fetch_start = time.time()
                moira_client = get_moira_client()
                list_attributes = moira_client.client.service.getListAttributes(
                    kc_group.name, moira_client.proxy_id
                )
                result["timing"]["moira_list_fetch_time"] = (
                    time.time() - moira_fetch_start
                )
                self.stdout.write(
                    f"  ⏱️  MOIRA list fetch time: {result['timing']['moira_list_fetch_time']:.2f}s"
                )
                mail_list = (
                    [str(list_attributes[0].mailList).lower()]
                    if list_attributes
                    else []
                )
                group = self.kc_manager.create_group(
                    kc_group.name,
                    attributes={
                        "source": ["moira_migration"],
                        "original_moira_list": [kc_group.name],
                        "migrated_at": [str(timezone.now())],
                        "mail_list": mail_list,
                    },
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  ✓ Created group '{kc_group.name}' in Keycloak"
                    )
                )
            else:
                self.stdout.write(
                    f"  [DRY RUN] Would create group '{kc_group.name}' in Keycloak"
                )
            result["group_created"] = 1

        result["timing"]["group_creation_time"] = time.time() - group_start_time
        self.stdout.write(
            f"  ⏱️  Total group operation time: {result['timing']['group_creation_time']:.2f}s"
        )

        if self.skip_user_creation:
            self.stdout.write("  Skipping user creation (--skip-user-creation)")
            return result

        # 2. Get MOIRA list members
        member_fetch_start = time.time()
        try:
            moira_members = [m for m in list_members(kc_group.name) if m]
            result["timing"]["member_fetch_time"] = time.time() - member_fetch_start
            self.stdout.write(f"  Found {len(moira_members)} members in MOIRA list")
            self.stdout.write(
                f"  ⏱️  Member fetch time: {result['timing']['member_fetch_time']:.2f}s"
            )
        except Exception as e:
            result["timing"]["member_fetch_time"] = time.time() - member_fetch_start
            self.stdout.write(self.style.ERROR(f"  Failed to get MOIRA members: {e}"))
            return result

        # 3. Create users and add to group
        user_migration_start = time.time()
        for member in moira_members:
            try:
                user_result = self.migrate_moira_user(member, kc_group.name, group)
                result["users_created"] += user_result["keycloak_user_created"]
                result["users_existed"] += user_result["keycloak_user_existed"]
                result["django_users_created"] += user_result["django_user_created"]
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"    Failed to migrate user '{member}': {e}")
                )

        result["timing"]["user_migration_time"] = time.time() - user_migration_start
        if moira_members:
            avg_time_per_user = result["timing"]["user_migration_time"] / len(
                moira_members
            )
            self.stdout.write(
                f"  ⏱️  User migration time: {result['timing']['user_migration_time']:.2f}s ({avg_time_per_user:.2f}s per user)"
            )

        list_total_time = (
            result["timing"]["group_creation_time"]
            + result["timing"]["member_fetch_time"]
            + result["timing"]["user_migration_time"]
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"  ✓ Total time for '{kc_group.name}': {list_total_time:.2f}s"
            )
        )

        return result

    def migrate_moira_user(
        self, member: str, moira_list_name: str, keycloak_group: dict
    ):
        """Migrate a single MOIRA user to Keycloak and Django"""
        result = {
            "keycloak_user_created": 0,
            "keycloak_user_existed": 0,
            "django_user_created": 0,
        }

        # Parse member info (could be username or email)
        username, email = self.parse_moira_member(member)

        # 1. Create/update Django user
        django_user, django_created = self.get_or_create_django_user(username, email)
        if django_created:
            result["django_user_created"] = 1
            self.stdout.write(f"    ✓ Created Django user: {username}")
        else:
            self.stdout.write(f"    Django user exists: {username}")

        if self.dry_run:
            self.stdout.write(
                f"    [DRY RUN] Would create/update Keycloak user: {username} email: {email}"
            )
            return result

        # 2. Create/update Keycloak user
        keycloak_user = self.kc_manager.find_user_by_email(email)
        if keycloak_user:
            self.stdout.write(f"    Keycloak user exists: {username}")
            result["keycloak_user_existed"] = 1
        else:
            # Create new Keycloak user
            kc_user_data = KeycloakUser(
                username=username,
                email=email,
                first_name=django_user.first_name or username.split(".")[0].title(),
                last_name=django_user.last_name
                or (username.split(".")[1].title() if "." in username else ""),
                password=self.default_password,
                temporary_password=True,
                groups=[moira_list_name],
                attributes={
                    "source": ["moira_migration"],
                    "original_moira_list": [moira_list_name],
                    "django_user_id": [str(django_user.id)],
                },
            )

            keycloak_user = self.kc_manager.create_user(kc_user_data)
            self.stdout.write(
                self.style.SUCCESS(f"    ✓ Created Keycloak user: {username}")
            )
            result["keycloak_user_created"] = 1

        # 3. Add user to group (if not already added during creation)
        if keycloak_group and result["keycloak_user_existed"]:
            try:
                self.kc_manager.add_user_to_group(
                    keycloak_user["id"], keycloak_group["id"]
                )
                self.stdout.write(f"    ✓ Added {username} to group {moira_list_name}")
            except Exception as e:
                # User might already be in group
                if "409" not in str(e):  # Not a conflict error
                    raise e

        return result

    def parse_moira_member(self, member: str):
        """Parse MOIRA member string to username and email"""
        if "@" in member:
            # It's an email
            email = member
            username = member.split("@")[0]
        else:
            # It's a username, assume MIT email
            username = member
            email = f"{username}@mit.edu"

        # Clean up username (remove dots, make lowercase)
        username = re.sub(r"[^a-zA-Z0-9._-]", "", username.lower())

        return username, email

    def get_or_create_django_user(self, username: str, email: str):
        """Get or create Django user"""
        if self.dry_run:
            # In dry run, just check if user exists
            try:
                user = User.objects.get(username=username)
                return user, False
            except User.DoesNotExist:
                return None, True

        try:
            # Try to find by username first
            user = User.objects.get(username=username)
            return user, False
        except User.DoesNotExist:
            pass

        try:
            # Try to find by email
            user = User.objects.get(email=email)
            return user, False
        except User.DoesNotExist:
            pass

        # Create new user
        user = User.objects.create_user(
            username=username,
            email=email,
            first_name=username.split(".")[0].title()
            if "." in username
            else username.title(),
            last_name=username.split(".")[1].title()
            if "." in username and len(username.split(".")) > 1
            else "",
        )
        return user, True

    def print_migration_summary(self, summary):
        """Print migration summary"""
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("MIGRATION SUMMARY"))
        self.stdout.write("=" * 60)

        self.stdout.write(f"Groups created in Keycloak: {summary['groups_created']}")
        self.stdout.write(f"Groups already existed: {summary['groups_existed']}")

        if not self.skip_user_creation:
            self.stdout.write(f"Users created in Keycloak: {summary['users_created']}")
            self.stdout.write(
                f"Users already existed in Keycloak: {summary['users_existed']}"
            )
            self.stdout.write(
                f"Django users created: {summary['django_users_created']}"
            )

        if summary["errors"]:
            self.stdout.write(f"\nErrors encountered: {len(summary['errors'])}")
            for error in summary["errors"]:
                self.stdout.write(self.style.ERROR(f"  - {error}"))

        # Print timing information
        self.stdout.write("\n" + "-" * 60)
        self.stdout.write(self.style.SUCCESS("TIMING BREAKDOWN"))
        self.stdout.write("-" * 60)
        timing = summary["timing"]
        self.stdout.write(f"Total migration time: {timing['total_time']:.2f}s")
        self.stdout.write(
            f"  - MOIRA list fetch time: {timing['moira_list_fetch_time']:.2f}s"
        )
        self.stdout.write(
            f"  - Group creation time: {timing['group_creation_time']:.2f}s"
        )
        self.stdout.write(f"  - Member fetch time: {timing['member_fetch_time']:.2f}s")
        self.stdout.write(
            f"  - User migration time: {timing['user_migration_time']:.2f}s"
        )

        if summary["users_created"] + summary["users_existed"] > 0:
            total_users = summary["users_created"] + summary["users_existed"]
            avg_time = (
                timing["user_migration_time"] / total_users if total_users > 0 else 0
            )
            self.stdout.write(f"\nAverage time per user: {avg_time:.2f}s")

        self.stdout.write("=" * 60)
