"""Tasks for mail app"""
import logging
from urllib.parse import urljoin

from django.conf import settings
from django.urls.base import reverse
from celery import shared_task

from mail import api
from mail.models import NotificationEmail
from ui.constants import VideoStatus
from ui.utils import has_common_lists

log = logging.getLogger(__name__)


def _get_recipients_for_video(video):
    """
    Returns a list of recipients that will receive notifications for a video.

    Args:
        video (ui.models.Video): a video object

    Returns:
        list: a list of strings representing emails
    """
    admin_lists = video.collection.admin_lists.values_list('name', flat=True)
    recipients_list = ['{}@mit.edu'.format(mlist) for mlist in admin_lists]
    owner = video.collection.owner
    if owner.email and not has_common_lists(owner, admin_lists):
        recipients_list.append(owner.email)
    return recipients_list


STATUS_TO_NOTIFICATION = {
    VideoStatus.COMPLETE: NotificationEmail.SUCCESS,
    VideoStatus.TRANSCODE_FAILED_INTERNAL: NotificationEmail.OTHER_ERROR,
    VideoStatus.TRANSCODE_FAILED_VIDEO: NotificationEmail.INVALID_INPUT_ERROR,
    VideoStatus.UPLOAD_FAILED: NotificationEmail.OTHER_ERROR,
}


def send_notification_email(video):
    """
    Sends notification emails to the admin of the channels where a video belongs
    according to the video status.

    Args:
        video (ui.models.Video): a video object
    """
    if video.status not in STATUS_TO_NOTIFICATION.keys():
        log.error("Tried to send notifications for video %s with status %s", video.hexkey, video.status)
        return
    # get the list of emails
    recipients = _get_recipients_for_video(video)
    if not recipients:
        log.error("No email was sent because there were no "
                  "valid recipient emails for video %s with status %s", video.hexkey, video.status)
        return
    try:
        email_template = NotificationEmail.objects.get(notification_type=STATUS_TO_NOTIFICATION[video.status])
    except NotificationEmail.DoesNotExist:
        log.error("No template found for error %s", STATUS_TO_NOTIFICATION[video.status])
        return

    try:
        api.MailgunClient.send_individual_email(
            email_template.email_subject.format(video_title=video.title),
            email_template.email_body.format(
                video_title=video.title,
                video_url=urljoin(
                    settings.ODL_VIDEO_BASE_URL,
                    reverse('video-detail', kwargs={'video_key': video.hexkey})
                ),
                support_email=settings.EMAIL_SUPPORT
            ),
            recipient=', '.join(recipients),
            raise_for_status=True,
        )
    except:  # pylint: disable=bare-except
        log.exception('Impossible to send notification for video %s with status %s', video.hexkey, video.status)


@shared_task(bind=True)
def async_send_notification_email(self, video_id):  # pylint: disable=unused-argument
    """
    Asynchronous call to the function to send notifications for video status update.
    """
    # import done here to avoid circular imports
    from ui.models import Video
    try:
        video = Video.objects.get(id=video_id)
    except Video.DoesNotExist:
        log.error('tried to send notification for non existing video with id=%s', video_id)
        return
    send_notification_email(video)
