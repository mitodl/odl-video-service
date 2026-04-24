"""
ui celery tasks
"""

import celery
from celery import shared_task
from django.db.models import Q
from django.utils import timezone
from itertools import groupby

from mail.utils import chunks
import structlog
from odl_video.celery import app
from ui.keycloak_utils import KeycloakUser, build_keycloak_manager
from ui.management.commands.keycloak_command_utils import record_exception
from ui import api as ovs_api
from ui.api import update_video_on_edx
from ui.encodings import EncodingNames
from ui.models import VideoFile

log = structlog.get_logger(__name__)


@app.task
def post_video_to_edx(video_id):
    """Loads a VideoFile and calls our API method to add it to edX"""
    video_files = sorted(
        list(
            VideoFile.objects.filter(
                ~Q(encoding=EncodingNames.ORIGINAL), video=video_id
            ).select_related("video__collection")
        ),
        key=lambda vf: vf.id,
    )
    if not video_files:
        log.error("Video doesn't exist", video_id=video_id)
        return
    response_dict = ovs_api.post_video_to_edx(video_files)
    return [
        (endpoint.full_api_url, getattr(resp, "status_code", None))
        for endpoint, resp in response_dict.items()
    ]


@app.task
def batch_update_video_on_edx(video_keys, chunk_size=1000):
    """
    batch update videos on their associated edX endpoints

    Args:
        video_keys(list): A list of video UUID keys
        chunk_size(int): the chunk size in a batch API call
    """
    return celery.group(
        [
            batch_update_video_on_edx_chunked(chunk)
            for chunk in chunks(
                video_keys,
                chunk_size=chunk_size,
            )
        ]
    )


@app.task
def batch_update_video_on_edx_chunked(video_keys):
    """
    batch update videos on their associated edX endpoints in chunks

    Args:
        video_keys(list): A list of video UUID keys
    """
    response = {}
    for video_key in video_keys:
        response_dict = update_video_on_edx(video_key)
        for endpoint, resp in response_dict.items():
            if getattr(resp, "ok", None):
                response[endpoint] = "succeed"
            else:
                response[endpoint] = "failed"
    return response


@app.task
def post_collection_videos_to_edx(video_ids):
    """Post videos from a collection to edX.
    Args:
        video_ids (list): List of video IDs to post.
    """
    video_files = (
        VideoFile.objects.filter(
            ~Q(encoding=EncodingNames.ORIGINAL), video__id__in=video_ids
        )
        .select_related("video__collection")
        .order_by("video__id", "id")
    )

    for video_id, video_file_list in groupby(video_files, key=lambda vf: vf.video.id):
        video_file_list = list(video_file_list)
        responses = ovs_api.post_video_to_edx(video_file_list)
        log.info(
            "Posted collection video to edX",
            video_title=video_file_list[0].video.title,
            video_id=video_id,
            responses={
                endpoint.full_api_url: resp.status_code
                for endpoint, resp in responses.items()
            },
        )


def _empty_keycloak_migration_summary():
    return {
        "created": 0,
        "existing_skipped": 0,
        "invalid_skipped": 0,
        "failed": 0,
        "errors": [],
    }


@shared_task
def migrate_keycloak_groups_chunk(group_names, keycloak_config):
    """Create Keycloak groups for one chunk of group names. Always returns a summary dict."""
    manager = build_keycloak_manager(keycloak_config)
    summary = _empty_keycloak_migration_summary()

    for group_name in group_names:
        try:
            manager.create_group(
                group_name,
                attributes={
                    "source": ["ovs_keycloak_migration"],
                    "migrated_at": [str(timezone.now())],
                    "mail_list": ["true"],
                },
            )
            summary["created"] += 1
        except Exception as exc:  # noqa: BLE001
            record_exception(summary, f"group={group_name}", exc)

    return summary


@shared_task
def migrate_keycloak_users_chunk(users_payload, keycloak_config):
    """Create Keycloak users for one chunk of serialized Django users. Always returns a summary dict."""
    manager = build_keycloak_manager(keycloak_config)
    summary = _empty_keycloak_migration_summary()

    for payload in users_payload:
        email = (payload.get("email") or "").strip()
        username = (payload.get("username") or "").strip()
        if not email or not username:
            summary["invalid_skipped"] += 1
            summary["errors"].append(
                f"invalid user payload: id={payload.get('id')} username={username} email={email}"
            )
            continue

        try:
            manager.create_user(
                KeycloakUser(
                    username=username,
                    email=email,
                    first_name=payload.get("first_name", "") or "",
                    last_name=payload.get("last_name", "") or "",
                    # No password: users authenticate via federated SAML, not a
                    # local Keycloak credential.  Setting a temporary password
                    # causes Keycloak to add UPDATE_PASSWORD as a required action,
                    # prompting users to set a password even after SAML succeeds.
                    password=None,
                    temporary_password=False,
                    groups=[],
                    attributes={
                        "source": ["ovs_keycloak_migration"],
                        "django_user_id": [str(payload["id"])],
                    },
                )
            )
            summary["created"] += 1
        except Exception as exc:  # noqa: BLE001
            record_exception(summary, f"user={email}", exc)

    return summary
