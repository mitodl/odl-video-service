"""Management command to update video to edX via API call"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from ui.constants import VideoStatus
from ui.models import CollectionEdxEndpoint, Video
from ui.tasks import batch_update_video_on_edx, batch_update_video_on_edx_chunked
from ui.utils import now_in_utc

User = get_user_model()


class Command(BaseCommand):
    """Update video to edX via API call"""

    help = __doc__

    def add_arguments(self, parser):

        parser.add_argument(
            "--video-key",
            type=str,
            help="The UUID key of the Video that you want to update on its configured edX endpoint",
        )
        parser.add_argument(
            "--chunk-size",
            type=int,
            default=1000,
            help="specify the chunk size in a batch API call, default to 1000",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="Update all of videos to their configured edX endpoints (this may take a long time)",
        )

    def handle(self, *args, **options):
        if not options["video_key"] and not options["all"]:
            raise CommandError("Please provide either --video-id or --all")

        if options["video_key"]:
            video_key = options["video_key"]
            video = Video.objects.filter(key=video_key).first()
            if video is None:
                raise CommandError("This video key doesn't exist")
            response = batch_update_video_on_edx_chunked([video_key])
            self.stdout.write(
                "Video updated to edX {} - edx url: {} \n".format(
                    list(response.values())[0], list(response.keys())[0]
                )
            )
        elif options["all"]:
            collection_ids = CollectionEdxEndpoint.objects.values_list("id", flat=True)
            video_keys = list(
                Video.objects.filter(
                    collection__id__in=collection_ids, status=VideoStatus.COMPLETE
                ).values_list("key", flat=True)
            )

            self.stdout.write("Updating video(s) to edX...\n")
            task = batch_update_video_on_edx.delay(video_keys, options["chunk_size"])
            start = now_in_utc()

            self.stdout.write(f"Started celery task {task} to update videos on edx")

            result = task.get()
            if "failed" in list(result["kwargs"]["tasks"][0].values()):
                self.stderr.write(f"Result: {result}")
                raise CommandError("Failed to update some video(s) to edX")

            total_seconds = (now_in_utc() - start).total_seconds()
            self.stdout.write(
                "Updating video(s) to edX finished, took {} seconds.....\n".format(
                    total_seconds
                )
            )
