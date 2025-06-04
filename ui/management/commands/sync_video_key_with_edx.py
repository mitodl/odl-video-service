"""Management command to sync video keys with edX"""

from datetime import datetime
from urllib.parse import urlencode
import requests
from django.core.management.base import BaseCommand
import uuid

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
            self.stdout.write(
                f"Syncing video keys for collection {collection.title} with edX"
            )
            course_videos = []
            for edx_endpoint in collection.edx_endpoints.all():
                self.stdout.write(
                    f"Getting videos from edX for collection {collection.title} using endpoint {edx_endpoint.name}"
                )
                try:
                    edx_endpoint.refresh_access_token()
                except Exception as exc:
                    self.stdout.write(
                        self.style.ERROR(
                            f"Can not refresh access token for edX endpoint {edx_endpoint.name} and url {edx_endpoint.base_url}"
                        )
                    )
                    self.stdout.write(self.style.ERROR(str(exc)))
                    continue

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

            latest_videos_by_created_at = {}
            for video in course_videos:
                url = (video.get("encoded_videos") or [{}])[0].get("url", "/")
                try:
                    key = url.split("/")[-2]
                except IndexError:
                    self.stdout.write(
                        self.style.ERROR(
                            f"BAD URL: Could not extract video key from URL {url} for video {video.get('client_video_id')}"
                        )
                    )
                    continue

                # verify if key is a valid UUID
                try:
                    uuid.UUID(key)
                except ValueError:
                    self.stdout.write(
                        self.style.ERROR(
                            f"Invalid video key {key} for video {video.get('client_video_id')}"
                        )
                    )
                    continue

                created = datetime.fromisoformat(video.get("created", "1970-01-01"))
                if key and (
                    key not in latest_videos_by_created_at
                    or created
                    > datetime.fromisoformat(
                        latest_videos_by_created_at[key].get("created", "1970-01-01")
                    )
                ):
                    latest_videos_by_created_at[key] = video

            for vid_key, vid in latest_videos_by_created_at.items():
                Video.objects.filter(
                    title=vid.get("client_video_id"), key=vid_key
                ).update(key=vid.get("edx_video_id"))
                self.stdout.write(
                    f"Updated video key for {vid.get('client_video_id')} to {vid.get('edx_video_id')}"
                )

            self.stdout.write(
                f"Synced video keys for collection {collection.title} with edX"
            )
