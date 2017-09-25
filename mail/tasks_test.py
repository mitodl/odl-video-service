"""
Tests for Task module
"""
from urllib.parse import urljoin

import pytest
from django.conf import settings
from django.urls import reverse

from mail import tasks
from mail.models import NotificationEmail
from ui.constants import VideoStatus
from ui.factories import VideoFactory, MoiraListFactory

pytestmark = pytest.mark.django_db


# pylint: disable=protected-access


@pytest.fixture(autouse=True)
def mocker_defaults(mocker):
    """
    Sets default settings to safe defaults
    """
    mocker.patch('mail.tasks.has_common_lists', return_value=False)


def test_get_recipients_for_video(mocker):
    """
    Tests the _get_recipients_for_video api
    """
    lists = MoiraListFactory.create_batch(2)
    video = VideoFactory(collection__admin_lists=lists)
    list_emails = ['{}@mit.edu'.format(mlist.name) for mlist in video.collection.admin_lists.all()]
    mocker.patch('mail.tasks.has_common_lists', return_value=False)
    assert tasks._get_recipients_for_video(video) == list_emails + [video.collection.owner.email]
    mocker.patch('mail.tasks.has_common_lists', return_value=True)
    assert tasks._get_recipients_for_video(video) == list_emails


def test_send_notification_email_wrong_status(mocker):
    """
    Tests send_notification_email with a status that does not require sending an email
    """
    mocked_mailgun = mocker.patch('mail.api.MailgunClient', autospec=True)
    mocked__get_recipients_for_video = mocker.patch('mail.tasks._get_recipients_for_video', autospec=True)
    assert VideoStatus.UPLOADING not in tasks.STATUS_TO_NOTIFICATION
    video = VideoFactory(status=VideoStatus.UPLOADING)
    tasks.send_notification_email(video)
    assert mocked_mailgun.send_individual_email.call_count == 0
    assert mocked__get_recipients_for_video.call_count == 0


def test_send_notification_email_no_recipients(mocker):
    """
    Tests send_notification_email for a video that has no recipients
    """
    mocked_mailgun = mocker.patch('mail.api.MailgunClient', autospec=True)
    mocked__get_recipients_for_video = mocker.patch(
        'mail.tasks._get_recipients_for_video',
        autospec=True,
        return_value=[]
    )
    assert VideoStatus.COMPLETE in tasks.STATUS_TO_NOTIFICATION
    video = VideoFactory(status=VideoStatus.COMPLETE)
    tasks.send_notification_email(video)
    assert mocked_mailgun.send_individual_email.call_count == 0
    mocked__get_recipients_for_video.assert_called_once_with(video)


def test_send_notification_email_no_mail_template(mocker):
    """
    Tests send_notification_email for a video with a status not correspondent to a email template
    """
    mocked_mailgun = mocker.patch('mail.api.MailgunClient', autospec=True)
    assert VideoStatus.COMPLETE in tasks.STATUS_TO_NOTIFICATION
    video = VideoFactory(status=VideoStatus.COMPLETE)
    NotificationEmail.objects.filter(
        notification_type=tasks.STATUS_TO_NOTIFICATION[VideoStatus.COMPLETE]).delete()
    tasks.send_notification_email(video)
    assert mocked_mailgun.send_individual_email.call_count == 0


def test_send_notification_email_happy_path(mocker):
    """
    Tests send_notification_email with happy path
    """
    mocked_mailgun = mocker.patch('mail.api.MailgunClient', autospec=True)
    assert VideoStatus.COMPLETE in tasks.STATUS_TO_NOTIFICATION
    video = VideoFactory(status=VideoStatus.COMPLETE)
    tasks.send_notification_email(video)
    email_template = NotificationEmail.objects.get(
        notification_type=tasks.STATUS_TO_NOTIFICATION[VideoStatus.COMPLETE])
    mocked_mailgun.send_individual_email.assert_called_once_with(
        email_template.email_subject.format(video_title=video.title),
        email_template.email_body.format(
            video_title=video.title,
            video_url=urljoin(
                settings.ODL_VIDEO_BASE_URL,
                reverse('video-detail', kwargs={'video_key': video.hexkey})
            ),
            support_email=settings.EMAIL_SUPPORT
        ),
        recipient=video.collection.owner.email,
        raise_for_status=True,
    )


def test_async_send_notification_email_no_video(mocker):
    """
    Tests async_send_notification_email for a video_id that does not exist
    """
    mocked_send_email = mocker.patch('mail.tasks.send_notification_email', autospec=True)
    video = VideoFactory(status=VideoStatus.COMPLETE)
    tasks.async_send_notification_email.delay(video.id + 10000)
    assert mocked_send_email.call_count == 0


def test_async_send_notification_email_happy_path(mocker):
    """
    Tests async_send_notification_email with happy path
    """
    mocked_send_email = mocker.patch('mail.tasks.send_notification_email', autospec=True)
    video = VideoFactory(status=VideoStatus.COMPLETE)
    tasks.async_send_notification_email.delay(video.id)
    mocked_send_email.assert_called_once_with(video)
