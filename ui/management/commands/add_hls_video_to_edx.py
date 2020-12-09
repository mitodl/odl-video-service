"""Management command to attempt to add an HLS video to edX via API call"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from ui.api import post_hls_to_edx
from ui.models import VideoFile
from ui.encodings import EncodingNames
from ui.utils import get_error_response_summary_dict

User = get_user_model()


class Command(BaseCommand):
    """Attempts to add an HLS video to edX via API call"""

    help = __doc__

    def add_arguments(self, parser):

        group = parser.add_mutually_exclusive_group()
        group.add_argument(
            "--video-file-id",
            type=int,
            help="The id of the VideoFile that you want to add to edX",
        )
        group.add_argument(
            "--edx-course-id",
            type=str,
            help="The edx_course_id value for the Collection that the video file belongs to",
        )
        parser.add_argument(
            "--video-title",
            type=str,
            help="The video title of the video file you want to add to edX",
        )

    def handle(self, *args, **options):
        if not options["video_file_id"] and not any(
            (options["edx_course_id"], options["video_title"])
        ):
            raise CommandError(
                "Please provide --video-file-id or at least one of --edx-course-id and --video-title"
            )
        if options["video_file_id"] and options["video_title"]:
            raise CommandError(
                "Please provide --video-file-id or --video-title, not both"
            )

        filters = dict(encoding=EncodingNames.HLS)
        if options["video_file_id"]:
            filters["pk"] = options["video_file_id"]
        else:
            if options["edx_course_id"]:
                filters["video__collection__edx_course_id"] = options["edx_course_id"]
            if options["video_title"]:
                filters["video__title"] = options["video_title"]
        video_files = list(VideoFile.objects.filter(**filters).all())
        if not video_files:
            raise CommandError(
                "No HLS-encoded VideoFiles found that match the given parameters ({})".format(
                    filters
                )
            )

        self.stdout.write("Attempting to post video(s) to edX...")
        for video_file in video_files:
            response_dict = post_hls_to_edx(video_file)
            good_responses = {
                endpoint: resp
                for endpoint, resp in response_dict.items()
                if getattr(resp, "ok", None)
            }
            bad_responses = {
                endpoint: resp
                for endpoint, resp in response_dict.items()
                if endpoint not in good_responses
            }
            for _, resp in good_responses.items():
                self.stdout.write(
                    self.style.SUCCESS(
                        "Video successfully added to edX – VideoFile: {} ({}), edX url: {}".format(
                            video_file.video.title,
                            video_file.pk,
                            resp.url,
                        )
                    )
                )
            for edx_endpoint, resp in bad_responses.items():
                resp_summary = (
                    None if resp is None else get_error_response_summary_dict(resp)
                )
                self.stdout.write(
                    self.style.ERROR(
                        "Request to add HLS video to edX failed – "
                        "VideoFile: {} ({}), edX url: {}, API response: {}".format(
                            video_file.video.title,
                            video_file.pk,
                            edx_endpoint.full_api_url,
                            resp_summary,
                        )
                    )
                )
