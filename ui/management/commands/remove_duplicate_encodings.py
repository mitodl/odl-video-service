"""
Django management command for removing duplicate video encodings.

This command scans VideoFile objects and removes duplicate encodings for videos,
keeping only the most recent record (by updated timestamp) for each video-encoding combination.
It handles S3 file cleanup automatically via Django signals.

Usage:
    python manage.py remove_duplicate_encodings --all
    python manage.py remove_duplicate_encodings --video-ids <video_id1> <video_id2> ...
    python manage.py remove_duplicate_encodings --collection-ids <collection_id1> <collection_id2> ...

Examples:
    # Remove duplicates for all videos
    python manage.py remove_duplicate_encodings --all

    # Remove duplicates for specific videos
    python manage.py remove_duplicate_encodings --video-ids 123 456 789

    # Remove duplicates for all videos in specific collections
    python manage.py remove_duplicate_encodings --collection-ids 10 20 30

The command will:
1. Find VideoFile objects with duplicate encodings for each video
2. Keep the latest record (highest updated timestamp) for each video-encoding pair
3. Delete older duplicate records (S3 cleanup happens automatically via Django signals)
4. Provide detailed logging of all operations

This is useful for cleaning up duplicate encodings that may occur during retranscoding
or when the transcoding process creates multiple VideoFile records for the same encoding.
"""

from django.core.management.base import BaseCommand
from django.db.models import Count
from django.db import transaction

from ui.models import Video, VideoFile, Collection


class Command(BaseCommand):
    help = """
    Remove duplicate video encodings, keeping only the latest record for each video-encoding combination
    """

    def add_arguments(self, parser):
        parser.add_argument(
            "--video-ids",
            type=int,
            nargs="+",
            help="Process duplicates for specific video IDs (space-separated)",
        )
        parser.add_argument(
            "--collection-ids",
            type=int,
            nargs="+",
            help="Process duplicates for all videos in specific collection IDs (space-separated)",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="Process duplicates for all videos in the system",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be deleted without actually deleting",
        )

    def handle(self, *args, **options):  # noqa: ARG002
        video_ids = options.get("video_ids", [])
        collection_ids = options.get("collection_ids", [])
        all_videos = options.get("all", False)
        dry_run = options.get("dry_run", False)

        # Validation: Exactly one option must be provided
        provided_options = sum([bool(video_ids), bool(collection_ids), all_videos])
        if provided_options != 1:
            self.stderr.write(
                self.style.ERROR(
                    "Error: You must specify exactly one of --video-ids, --collection-ids, or --all.\n"
                    "Examples:\n"
                    "  python manage.py remove_duplicate_encodings --all\n"
                    "  python manage.py remove_duplicate_encodings --video-ids 123 456 789\n"
                    "  python manage.py remove_duplicate_encodings --collection-ids 10 20 30"
                )
            )
            return

        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN MODE: No changes will be made.")
            )

        # Build the base queryset
        videos_queryset = Video.objects.all()

        if video_ids:
            # Validate that all video IDs exist
            existing_videos = Video.objects.filter(id__in=video_ids)
            existing_video_ids = set(existing_videos.values_list("id", flat=True))
            missing_video_ids = set(video_ids) - existing_video_ids

            if missing_video_ids:
                self.stderr.write(
                    self.style.ERROR(
                        f"The following video IDs do not exist: {sorted(missing_video_ids)}"
                    )
                )
                return

            videos_queryset = existing_videos
            self.stdout.write(
                self.style.SUCCESS(
                    f"Processing duplicates for {len(video_ids)} videos: {sorted(video_ids)}"
                )
            )

        elif collection_ids:
            # Validate that all collection IDs exist
            existing_collections = Collection.objects.filter(id__in=collection_ids)
            existing_collection_ids = set(
                existing_collections.values_list("id", flat=True)
            )
            missing_collection_ids = set(collection_ids) - existing_collection_ids

            if missing_collection_ids:
                self.stderr.write(
                    self.style.ERROR(
                        f"The following collection IDs do not exist: {sorted(missing_collection_ids)}"
                    )
                )
                return

            videos_queryset = Video.objects.filter(collection_id__in=collection_ids)
            video_count = videos_queryset.count()
            collection_titles = list(
                existing_collections.values_list("title", flat=True)
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f"Processing duplicates for {len(collection_ids)} collections: {sorted(collection_ids)}\n"
                    f"Collections: {', '.join(collection_titles[:3])}{'...' if len(collection_titles) > 3 else ''}\n"
                    f"Total videos: {video_count}"
                )
            )

        else:  # --all
            video_count = videos_queryset.count()
            self.stdout.write(
                self.style.SUCCESS(
                    f"Processing duplicates for all {video_count} videos in the system..."
                )
            )

        total_duplicates_removed = 0
        total_videos_processed = 0

        for video in videos_queryset:
            duplicates_removed = self.process_video_duplicates(video, dry_run)
            if duplicates_removed > 0:
                total_duplicates_removed += duplicates_removed
                total_videos_processed += 1

        # Summary
        if total_duplicates_removed > 0:
            action = "would be removed" if dry_run else "removed"
            self.stdout.write(
                self.style.SUCCESS(
                    f"\nSummary: {total_duplicates_removed} duplicate VideoFile records {action} "
                    f"from {total_videos_processed} videos."
                )
            )
        else:
            self.stdout.write(self.style.SUCCESS("\nNo duplicate encodings found."))

    def process_video_duplicates(self, video: Video, dry_run: bool = False) -> int:
        """
        Process duplicates for a single video.

        Args:
            video: The Video object to process
            dry_run: If True, only show what would be deleted

        Returns:
            int: Number of duplicates removed
        """
        duplicates_removed = 0

        # Find encoding types that have duplicates for this video
        duplicate_encodings = (
            VideoFile.objects.filter(video=video)
            .values("encoding")
            .annotate(count=Count("id"))
            .filter(count__gt=1)
        )

        for encoding_info in duplicate_encodings:
            encoding = encoding_info["encoding"]
            count = encoding_info["count"]

            # Get all VideoFiles for this video-encoding combination, ordered by updated timestamp
            video_files = VideoFile.objects.filter(
                video=video, encoding=encoding
            ).order_by("updated_at")

            # Convert to list to support negative indexing and get the latest file
            video_files_list = list(video_files)
            files_to_delete = video_files_list[:-1]  # All except the last one
            latest_file = video_files_list[-1] if video_files_list else None

            if files_to_delete:
                self.stdout.write(
                    self.style.WARNING(
                        f"Video '{video.title}' (ID: {video.id}) - Encoding '{encoding}': "
                        f"{count} duplicates found"
                    )
                )

                for file_to_delete in files_to_delete:
                    if dry_run:
                        self.stdout.write(
                            f"  [DRY RUN] Would delete VideoFile ID: {file_to_delete.id}, "
                            f"S3 key: {file_to_delete.s3_object_key}, "
                            f"Created: {file_to_delete.created_at} "
                            f"Updated: {file_to_delete.updated_at}"
                        )
                    else:
                        self.stdout.write(
                            f"  Deleting VideoFile ID: {file_to_delete.id}, "
                            f"S3 key: {file_to_delete.s3_object_key}, "
                            f"Created: {file_to_delete.created_at} "
                            f"Updated: {file_to_delete.updated_at}"
                        )
                        try:
                            with transaction.atomic():
                                # Delete the VideoFile (S3 cleanup happens via Django signals)
                                file_to_delete.delete()
                            duplicates_removed += 1
                        except Exception as exc:
                            self.stderr.write(
                                self.style.ERROR(
                                    f"  Failed to delete VideoFile ID {file_to_delete.id}: {exc}"
                                )
                            )

                if not dry_run:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  Kept latest VideoFile ID: {latest_file.id}, "
                            f"S3 key: {latest_file.s3_object_key}, "
                            f"Created: {latest_file.created_at} "
                            f"Updated: {latest_file.updated_at}"
                        )
                    )

        return duplicates_removed
