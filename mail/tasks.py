"""Tasks for mail app"""

import textwrap

from celery import shared_task
from django.conf import settings

from mail import api
from mail.api import context_for_video, render_email_templates
from mail.constants import STATUS_TO_NOTIFICATION, STATUSES_THAT_TRIGGER_DEBUG_EMAIL
from odl_video import logging
from ui.utils import get_moira_client, has_common_lists

log = logging.getLogger(__name__)


def _get_recipients_for_video(video):
    """
    Returns a list of recipients that will receive notifications for a video.

    Args:
        video (ui.models.Video): a video object

    Returns:
        list: a list of strings representing emails
    """
    admin_lists = []
    moira_client = get_moira_client()
    for mlist in video.collection.admin_lists.values_list("name", flat=True):
        attributes = moira_client.client.service.getListAttributes(
            mlist, moira_client.proxy_id
        )
        if attributes and attributes[0]["mailList"]:
            admin_lists.append(mlist)
    recipients_list = [f"{alist}@mit.edu" for alist in admin_lists]
    owner = video.collection.owner
    if owner.email and not has_common_lists(owner, admin_lists):
        recipients_list.append(owner.email)
    return recipients_list


def send_notification_email(video):
    """
    Sends notification emails to the admin of the channels where a video belongs
    according to the video status.

    Args:
        video (ui.models.Video): a video object
    """
    if video.status not in STATUS_TO_NOTIFICATION.keys():  # noqa: SIM118
        log.error(
            "Unexpected video status",
            video_hexkey=video.hexkey,
            video_status=video.status,
        )
        return
    # get the list of emails
    recipients = _get_recipients_for_video(video)
    if not recipients:
        log.error(
            "No email sent, no valid recipient emails",
            video_hexkey=video.hexkey,
            video_status=video.status,
        )
        return
    try:
        email_template = STATUS_TO_NOTIFICATION[video.status]
        subject, text_body, html_body = render_email_templates(
            email_template, context_for_video(video)
        )
        email_kwargs = {
            "subject": subject,
            "html_body": html_body,
            "text_body": text_body,
            "recipients": [(recipient, {}) for recipient in recipients],
            "raise_for_status": True,
            "sender_address": settings.EMAIL_SUPPORT,
        }
        api.MailgunClient.send_batch(**email_kwargs)
        if video.status in STATUSES_THAT_TRIGGER_DEBUG_EMAIL:
            _send_debug_email(video=video, email_kwargs=email_kwargs)
    except:  # noqa: E722
        log.exception(
            "Impossible to send notification",
            video_hexkey=video.hexkey,
            video_status=video.status,
        )


@shared_task(bind=True)
def async_send_notification_email(self, video_id):  # noqa: ARG001
    """
    Asynchronous call to the function to send notifications for video status update.
    """
    # import done here to avoid circular imports
    from ui.models import Video

    try:
        video = Video.objects.get(id=video_id)
    except Video.DoesNotExist:
        log.error("Can not send notification for nonexistant video", video_id=video_id)  # noqa: TRY400
        return
    send_notification_email(video)


def _send_debug_email(video=None, email_kwargs=None):
    """
    Sends a debug email to the support email.
    """
    debug_email_kwargs = {
        "subject": "DEBUG:{}".format(email_kwargs["subject"]),
        "html_body": None,
        "text_body": _generate_debug_email_body(video=video, email_kwargs=email_kwargs),
        "recipient": settings.EMAIL_SUPPORT,
    }
    api.MailgunClient.send_individual_email(**debug_email_kwargs)


def _generate_debug_email_body(video=None, email_kwargs=None):
    """
    Generates body of debug email.
    """
    return textwrap.dedent(
        """
        --- DEBUG INFO ---
        Video: {video}
        Collection: {collection}
        Owner: {owner}

        --- DEBUG INFO FOR EMAIL SENT TO USER(S) ---

        <RECIPIENT(S)>:
        {recipient}
        </RECIPIENT(S)>:

        <SUBJECT>
        {subject}
        </SUBJECT>

        <BODY>
        {body}
        </BODY>
        """
    ).format(
        video=video,
        collection=video.collection,
        owner=video.collection.owner,
        recipient=email_kwargs["recipients"],
        subject=email_kwargs["subject"],
        body=email_kwargs["text_body"],
    )
