"""Management command to schedule retranscoding for collections with multiple filtering options"""

from datetime import datetime
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.utils.dateparse import parse_datetime
from django.utils import timezone

from ui.models import Collection, Video

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
            help="Collection IDs (UUID hex keys or primary keys) to retranscode",
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
            help="edX course ID - retranscode all collections with this course ID",
        )

        filter_group.add_argument(
            "--edx-endpoint",
            type=str,
            help="edX endpoint name - retranscode all collections using this endpoint",
        )

        filter_group.add_argument(
            "--created-after",
            type=str,
            help="Only include collections created after this date (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS format)",
        )

        filter_group.add_argument(
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

        if not collections:
            self.stdout.write(
                self.style.WARNING(
                    "No collections found matching the specified criteria."
                )
            )
            return

        # Display summary
        collection_count = collections.count()
        video_count = self._get_eligible_videos_count(collections, options)

        self.stdout.write(
            f"Found {collection_count} collection(s) with {video_count} eligible video(s)"
        )

        if options["dry_run"]:
            self._show_dry_run_details(collections, options)
            return

        # Schedule retranscoding
        retranscoded_collections = self._schedule_retranscoding(collections, options)

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully scheduled retranscoding for {retranscoded_collections} collection(s) "
                f"with {video_count} total video(s)"
            )
        )

    def _get_collections_queryset(self, options):
        """Get collections queryset based on filtering options"""
        base_queryset = Collection.objects.all()

        # Apply date filters if specified
        base_queryset = self._apply_date_filters(base_queryset, options)

        if options["ids"]:
            # Handle both UUID hex keys and primary keys
            ids = options["ids"]
            # Try to filter by hex key first, then by primary key
            collections_by_hex = base_queryset.filter(
                key__in=[id.replace("-", "") for id in ids]
            )
            collections_by_pk = base_queryset.filter(
                pk__in=[int(id) for id in ids if id.isdigit()]
            )
            return (collections_by_hex | collections_by_pk).distinct()

        elif options["all"]:
            return base_queryset

        elif options["owner"]:
            try:
                user = User.objects.get(username=options["owner"])
                return base_queryset.filter(owner=user)
            except User.DoesNotExist:
                raise CommandError(f"User '{options['owner']}' does not exist")

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
        try:
            # Try parsing as full datetime first
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
                pass

            raise CommandError(
                f"Invalid date format for --{argument_name}: '{date_string}'. "
                f"Use YYYY-MM-DD or YYYY-MM-DD HH:MM:SS format."
            )
        except Exception as e:
            raise CommandError(
                f"Error parsing --{argument_name} date '{date_string}': {str(e)}"
            )

    def _get_eligible_videos_count(self, collections, options):
        """Count videos eligible for retranscoding"""
        return Video.objects.filter(collection__in=collections).count()

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
        for collection in collections:
            videos = self._get_eligible_videos_for_collection(collection, options)
            video_count = videos.count()
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

            self.stdout.write(f"  Eligible videos: {video_count}")

            if video_count > 0:
                # Show video details
                for video in videos[:5]:  # Limit to first 5 videos for brevity
                    self.stdout.write(f"    - {video.title} (Status: {video.status})")
                if video_count > 5:
                    self.stdout.write(f"    ... and {video_count - 5} more video(s)")

        self.stdout.write(f"\nTotal videos to be retranscoded: {total_videos}")

    def _get_eligible_videos_for_collection(self, collection, options):
        """Get videos eligible for retranscoding in a specific collection"""
        return collection.videos.all()

    def _schedule_retranscoding(self, collections, options):
        """Schedule retranscoding for collections"""
        retranscoded_collections = 0

        for collection in collections:
            videos = self._get_eligible_videos_for_collection(collection, options)

            if not videos.exists():
                self.stdout.write(
                    f"Skipping collection '{collection.title}' - no eligible videos"
                )
                continue

            # Check if already scheduled (unless force is used)
            if collection.schedule_retranscode:
                self.stdout.write(
                    f"Skipping collection '{collection.title}' - already scheduled for retranscoding"
                )
                continue

            # Schedule collection for retranscoding
            collection.schedule_retranscode = True
            collection.save()
            retranscoded_collections += 1

            video_count = videos.count()
            self.stdout.write(
                f"Scheduled retranscoding for collection '{collection.title}' "
                f"({video_count} eligible videos)"
            )

        return retranscoded_collections
