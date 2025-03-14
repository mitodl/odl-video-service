"""
Tests for Task module
"""

import textwrap
from collections import defaultdict

import pytest
from django.conf import settings

from mail import tasks
from mail.api import context_for_video, render_email_templates
from mail.constants import STATUS_TO_NOTIFICATION, STATUSES_THAT_TRIGGER_DEBUG_EMAIL
from ui.constants import VideoStatus
from ui.factories import MoiraListFactory, VideoFactory

pytestmark = pytest.mark.django_db


# pylint: disable=protected-access


@pytest.fixture(autouse=True)
def mocker_defaults(mocker):
    """
    Sets default settings to safe defaults
    """
    mocker.patch("mail.tasks.has_common_lists", return_value=False)
    mocker.patch("mail.tasks.get_moira_client")


def test_get_recipients_for_video(mocker):
    """
    Tests the _get_recipients_for_video api
    """
    mock_client = mocker.patch("mail.tasks.get_moira_client")
    lists = MoiraListFactory.create_batch(3)
    video = VideoFactory(collection__admin_lists=lists)
    list_attributes = [[{"mailList": False}], [{"mailList": True}], None]
    list_emails = ["{}@mit.edu".format(lists[1].name)]
    mocker.patch("mail.tasks.has_common_lists", return_value=False)
    mock_client().client.service.getListAttributes.side_effect = list_attributes
    assert tasks._get_recipients_for_video(video) == list_emails + [
        video.collection.owner.email
    ]
    mocker.patch("mail.tasks.has_common_lists", return_value=True)
    mock_client().client.service.getListAttributes.side_effect = list_attributes
    assert tasks._get_recipients_for_video(video) == list_emails


def test_send_notification_email_wrong_status(mocker):
    """
    Tests send_notification_email with a status that does not require sending an email
    """
    mocked_mailgun = mocker.patch("mail.api.MailgunClient", autospec=True)
    mocked__get_recipients_for_video = mocker.patch(
        "mail.tasks._get_recipients_for_video", autospec=True
    )
    assert VideoStatus.UPLOADING not in tasks.STATUS_TO_NOTIFICATION
    video = VideoFactory(status=VideoStatus.UPLOADING)
    tasks.send_notification_email(video)
    assert mocked_mailgun.send_individual_email.call_count == 0
    assert mocked__get_recipients_for_video.call_count == 0


def test_send_notification_email_no_recipients(mocker):
    """
    Tests send_notification_email for a video that has no recipients
    """
    mocked_mailgun = mocker.patch("mail.api.MailgunClient", autospec=True)
    mocked__get_recipients_for_video = mocker.patch(
        "mail.tasks._get_recipients_for_video", autospec=True, return_value=[]
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
    mocked_mailgun = mocker.patch("mail.api.MailgunClient", autospec=True)
    mock_log = mocker.patch("mail.tasks.log.error")
    video = VideoFactory(status=VideoStatus.RETRANSCODING)
    tasks.send_notification_email(video)
    assert mocked_mailgun.send_individual_email.call_count == 0
    mock_log.assert_called_once_with(
        "Unexpected video status",
        video_hexkey=video.hexkey,
        video_status="Retranscoding",
    )


def test_send_notification_email_happy_path(mocker):
    """
    Tests send_notification_email with happy path
    """
    mocked_mailgun = mocker.patch("mail.api.MailgunClient", autospec=True)
    assert VideoStatus.COMPLETE in tasks.STATUS_TO_NOTIFICATION
    video = VideoFactory(status=VideoStatus.COMPLETE)
    subject, text, html = render_email_templates(
        STATUS_TO_NOTIFICATION[VideoStatus.COMPLETE], context_for_video(video)
    )
    tasks.send_notification_email(video)
    mocked_mailgun.send_batch.assert_called_once_with(
        **{
            "subject": subject,
            "html_body": html,
            "text_body": text,
            "recipients": [(video.collection.owner.email, {})],
            "sender_address": settings.EMAIL_SUPPORT,
            "raise_for_status": True,
        }
    )


def test_async_send_notification_email_no_video(mocker):
    """
    Tests async_send_notification_email for a video_id that does not exist
    """
    mocked_send_email = mocker.patch(
        "mail.tasks.send_notification_email", autospec=True
    )
    video = VideoFactory(status=VideoStatus.COMPLETE)
    tasks.async_send_notification_email.delay(video.id + 10000)
    assert mocked_send_email.call_count == 0


def test_async_send_notification_email_happy_path(mocker):
    """
    Tests async_send_notification_email with happy path
    """
    mocked_send_email = mocker.patch(
        "mail.tasks.send_notification_email", autospec=True
    )
    video = VideoFactory(status=VideoStatus.COMPLETE)
    tasks.async_send_notification_email.delay(video.id)
    mocked_send_email.assert_called_once_with(video)


@pytest.mark.parametrize("status", STATUSES_THAT_TRIGGER_DEBUG_EMAIL)
def test_sends_debug_emails(mocker, status):
    """
    Tests send_notification_email with statuses that should trigger sending a
    separate email to support.
    """
    mocked_mailgun = mocker.patch("mail.api.MailgunClient", autospec=True)
    mocked_send_debug_email = mocker.patch(
        "mail.tasks._send_debug_email", autospec=True
    )
    video = VideoFactory(status=status)
    tasks.send_notification_email(video)
    mocked_send_debug_email.assert_called_once_with(
        video=video, email_kwargs=mocked_mailgun.send_batch.call_args[1]
    )


def test_send_debug_email(mocker):
    """
    Tests sends debug email to support.
    """
    mocked_mailgun = mocker.patch("mail.api.MailgunClient", autospec=True)
    mocked_generate_debug_email_body = mocker.patch(
        "mail.tasks._generate_debug_email_body"
    )
    mock_email_kwargs = defaultdict(mocker.MagicMock)
    video = VideoFactory()
    tasks._send_debug_email(video=video, email_kwargs=mock_email_kwargs)
    mocked_generate_debug_email_body.assert_called_once_with(
        video=video, email_kwargs=mock_email_kwargs
    )
    mocked_mailgun.send_individual_email.assert_called_once_with(
        **{
            "subject": "DEBUG:{}".format(mock_email_kwargs["subject"]),
            "html_body": None,
            "text_body": mocked_generate_debug_email_body.return_value,
            "recipient": settings.EMAIL_SUPPORT,
        }
    )


def test_generate_debug_email_body(mocker):
    """
    Tests generation of debug email body.
    """
    email_kwargs = defaultdict(mocker.MagicMock)
    video = VideoFactory()
    expected_body = textwrap.dedent(
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
    actual_body = tasks._generate_debug_email_body(
        video=video, email_kwargs=email_kwargs
    )
    assert actual_body == expected_body
