"""Management command to schedule retranscoding for collections with multiple filtering options"""

from datetime import datetime
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count
from django.utils.dateparse import parse_datetime
from django.utils import timezone

from ui.models import Collection

User = get_user_model()


class Command(BaseCommand):
    """Schedule retranscoding for collections based on various filtering criteria"""

    help = __doc__

    def add_arguments(self, parser):
        # Mutually exclusive group for filtering options
        filter_group = parser.add_mutually_exclusive_group(required=True)

        filter_group.add_argument(
            "--ids",
            nargs="+",
            type=str,
            help="Collection IDs (primary keys) to retranscode. Provide one or more IDs separated by spaces (e.g., --ids 123 456 789)",
        )

        filter_group.add_argument(
            "--all",
            action="store_true",
            help="Schedule retranscoding for all collections",
        )

        filter_group.add_argument(
            "--owner",
            type=str,
            help="Username of the collection owner - retranscode all collections by this user",
        )

        filter_group.add_argument(
            "--course-ids",
            nargs="+",
            type=str,
            help="edX course IDs - retranscode all collections with these course IDs. Provide one or more course IDs separated by spaces (e.g., --course-ids course-v1:MIT+6.00x+2023 course-v1:MIT+8.01x+2023)",
        )

        filter_group.add_argument(
            "--edx-endpoint",
            type=str,
            help="edX endpoint name - retranscode all collections using this endpoint",
        )

        parser.add_argument(
            "--created-after",
            type=str,
            help="Only include collections created after this date (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS format)",
        )

        parser.add_argument(
            "--created-before",
            type=str,
            help="Only include collections created before this date (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS format)",
        )

        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be retranscoded without actually scheduling retranscoding",
        )

    def handle(self, *args, **options):
        # Get collections based on filtering criteria
        collections = self._get_collections_queryset(options)

        if not collections.exists():
            self.stdout.write(
                self.style.WARNING(
                    "No collections found matching the specified criteria."
                )
            )
            return

        # Display summary
        collection_count = collections.count()
        video_count = self._get_videos_count(collections)

        self.stdout.write(
            f"Found {collection_count} collection(s) with {video_count} video(s)"
        )
        if video_count == 0:
            self.stdout.write(
                self.style.WARNING("No videos found in the selected collections.")
            )
            return

        if options["dry_run"]:
            self._show_dry_run_details(collections, options)
            return

        # Schedule retranscoding
        updated_count = self._schedule_retranscoding(collections)

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully scheduled retranscoding for {updated_count} collection(s)."
            )
        )

    def _get_collections_queryset(self, options):
        """Get collections queryset based on filtering options"""
        base_queryset = Collection.objects.prefetch_related(
            "edx_endpoints", "videos"
        ).all()

        # Apply date filters if specified
        base_queryset = self._apply_date_filters(base_queryset, options)

        if options["ids"]:
            ids = options["ids"]
            invalid_ids = [
                collection_id for collection_id in ids if not collection_id.isdigit()
            ]
            if invalid_ids:
                raise CommandError(
                    f"Invalid collection ID(s) provided: {', '.join(invalid_ids)}. All IDs must be integers."
                )

            collections_by_pk = base_queryset.filter(
                pk__in=[int(collection_id) for collection_id in ids]
            )
            return collections_by_pk.distinct()

        elif options["all"]:
            return base_queryset

        elif options["owner"]:
            try:
                user = User.objects.get(username=options["owner"])
                return base_queryset.filter(owner=user)
            except User.DoesNotExist as exc:
                raise CommandError(f"User '{options['owner']}' does not exist") from exc

        elif options["course_ids"]:
            return base_queryset.filter(edx_course_id__in=options["course_ids"])

        elif options["edx_endpoint"]:
            return base_queryset.filter(
                edx_endpoints__name=options["edx_endpoint"]
            ).distinct()

        return base_queryset

    def _apply_date_filters(self, queryset, options):
        """Apply created_at date filters to the queryset"""
        if options.get("created_after"):
            created_after = self._parse_date(options["created_after"], "created-after")
            queryset = queryset.filter(created_at__gte=created_after)

        if options.get("created_before"):
            created_before = self._parse_date(
                options["created_before"], "created-before"
            )
            queryset = queryset.filter(created_at__lte=created_before)

        return queryset

    def _parse_date(self, date_string, argument_name):
        """Parse date string and return timezone-aware datetime"""
        parsed_date = parse_datetime(date_string)
        if parsed_date:
            # If no timezone info, assume UTC
            if timezone.is_naive(parsed_date):
                parsed_date = timezone.make_aware(parsed_date, timezone.utc)
            return parsed_date

        # Try parsing as date only (YYYY-MM-DD)
        try:
            parsed_date = datetime.strptime(date_string, "%Y-%m-%d")
            # For "created-after", use start of day; for "created-before", use end of day
            if argument_name == "created-before":
                parsed_date = parsed_date.replace(
                    hour=23, minute=59, second=59, microsecond=999999
                )
            return timezone.make_aware(parsed_date, timezone.utc)
        except ValueError:
            raise CommandError(
                f"Invalid date format for --{argument_name}: '{date_string}'. "
                f"Use YYYY-MM-DD or YYYY-MM-DD HH:MM:SS format."
            )

    def _get_videos_count(self, collections):
        """Count videos for retranscoding"""
        result = collections.aggregate(total=Count("videos"))
        return result["total"] or 0

    def _show_dry_run_details(self, collections, options):
        """Show detailed information about what would be retranscoded"""
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(
            "DRY RUN - Collections and videos that would be retranscoded:"
        )
        self.stdout.write("=" * 80)

        # Show applied filters
        if options.get("created_after"):
            self.stdout.write(f"Filter: Created after {options['created_after']}")
        if options.get("created_before"):
            self.stdout.write(f"Filter: Created before {options['created_before']}")
        if options.get("created_after") or options.get("created_before"):
            self.stdout.write("")

        total_videos = 0
        for collection in (
            collections.select_related("owner")
            .annotate(video_count=Count("videos"))
            .iterator()
        ):
            video_count = collection.video_count
            total_videos += video_count

            self.stdout.write(f"\nCollection: {collection.title}")
            self.stdout.write(f"  ID: {collection.pk}")
            self.stdout.write(f"  Key: {collection.hexkey}")
            self.stdout.write(f"  Owner: {collection.owner.username}")
            self.stdout.write(
                f"  Created: {collection.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}"
            )
            if collection.edx_course_id:
                self.stdout.write(f"  Course ID: {collection.edx_course_id}")

            endpoints = collection.edx_endpoints.all()
            if endpoints:
                self.stdout.write(
                    f"  edX Endpoints: {', '.join([ep.name for ep in endpoints])}"
                )

            self.stdout.write(f"  Videos: {video_count}")

            if video_count > 0:
                # Show video details
                for video in collection.videos.all()[
                    :5
                ]:  # Limit to first 5 videos for brevity
                    self.stdout.write(f"    - {video.title} (Status: {video.status})")
                if video_count > 5:
                    self.stdout.write(f"    ... and {video_count - 5} more video(s)")

        self.stdout.write(f"\nTotal videos to be retranscoded: {total_videos}")

    def _schedule_retranscoding(self, collections):
        """Schedule retranscoding for collections"""
        collections_to_update_pks = []
        for collection in collections.annotate(video_count=Count("videos")).iterator():
            if collection.video_count == 0:
                self.stdout.write(
                    f"Skipping collection '{collection.title}' - no videos"
                )
                continue

            if collection.schedule_retranscode:
                self.stdout.write(
                    f"Skipping collection '{collection.title}' - already scheduled for retranscoding"
                )
                continue

            collections_to_update_pks.append(collection.pk)

            video_count = collection.video_count
            self.stdout.write(
                f"Scheduled retranscoding for collection '{collection.title}' "
                f"({video_count} videos)"
            )

        # Bulk update collections to set schedule_retranscode=True
        updated_count = 0
        if collections_to_update_pks:
            updated_count = Collection.objects.filter(
                pk__in=collections_to_update_pks
            ).update(schedule_retranscode=True)

        return updated_count
