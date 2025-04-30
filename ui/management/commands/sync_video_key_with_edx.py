"""Management command to sync video keys with edX"""

from urllib.parse import urlencode
import requests
from django.core.management.base import BaseCommand

from ui.models import Collection, Video


class Command(BaseCommand):
    """Sync video keys with edX"""

    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument(
            "--collection_ids",
            type=int,
            nargs="*",
            help="The ids of the Collections that you want to sync video keys with edX",
        )

    def handle(self, *args, **options):
        collection_ids = options["collection_ids"]
        collections = Collection.objects.all()
        if collection_ids:
            collections = collections.filter(id__in=collection_ids)

        for collection in collections:
            course_videos = []
            for edx_endpoint in collection.edx_endpoints.all():
                edx_endpoint.refresh_access_token()
                course_videos_query = urlencode(
                    {
                        "course": collection.edx_course_id,
                    }
                )
                try:
                    resp = requests.get(
                        edx_endpoint.full_api_url + f"?{course_videos_query}",
                        headers={
                            "Authorization": f"JWT {edx_endpoint.access_token}",
                        },
                    )
                    resp.raise_for_status()
                    course_videos.extend(resp.json().get("results", []))
                    while resp.json().get("next"):
                        resp = requests.get(
                            resp.json().get("next"),
                            headers={
                                "Authorization": f"JWT {edx_endpoint.access_token}",
                            },
                        )
                        course_videos.extend(resp.json().get("results", []))
                except requests.exceptions.RequestException as exc:
                    self.stdout.write(
                        self.style.ERROR(
                            f"Can not get videos from edX for collection {collection.title}"
                        )
                    )
                    self.stdout.write(self.style.ERROR(str(exc)))

            for vid in course_videos:
                vid_key = (
                    vid.get("encoded_videos", [{}])[0].get("url", "").split("/")[-2]
                )
                Video.objects.filter(
                    title=vid.get("client_video_id"), key=vid_key
                ).update(key=vid.get("edx_video_id"))
                self.stdout.write(
                    f"Updated video key for {vid.get('client_video_id')} to {vid.get('edx_video_id')}"
                )

            self.stdout.write(
                f"Synced video keys for collection {collection.title} with edX"
            )
