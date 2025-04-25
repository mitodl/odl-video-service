"""
Provides functions for sending and retrieving data about in-app email
"""

import json
import re
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.template.loader import render_to_string
from django.urls import reverse
from rest_framework import status

from mail.exceptions import SendBatchException
from mail.utils import chunks
from odl_video import logging

log = logging.getLogger(__name__)


class MailgunClient:
    """
    Provides functions for communicating with the Mailgun REST API.
    """

    _basic_auth_credentials = ("api", settings.MAILGUN_KEY)

    @staticmethod
    def default_params():
        """
        Default params for Mailgun request. This a method instead of an attribute to allow for the
        overriding of settings values.

        Returns:
            dict: A dict of default parameters for the Mailgun API
        """
        return {"from": settings.EMAIL_SUPPORT}

    @classmethod
    def _mailgun_request(
        cls, request_func, endpoint, params, sender_name=None, raise_for_status=True
    ):
        """
        Sends a request to the Mailgun API

        Args:
            request_func (function): requests library HTTP function (get/post/etc.)
            endpoint (str): Mailgun endpoint (eg: 'messages', 'events')
            params (dict): Dict of params to add to the request as 'data'
            raise_for_status (bool): If true, check the status and raise for non-2xx statuses
        Returns:
            requests.Response: HTTP response
        """
        mailgun_url = "{}/{}".format(settings.MAILGUN_URL, endpoint)
        email_params = cls.default_params()
        email_params.update(params)
        # Update 'from' address if sender_name was specified
        if sender_name is not None:
            email_params["from"] = "{sender_name} <{email}>".format(
                sender_name=sender_name, email=email_params["from"]
            )
        response = request_func(
            mailgun_url, auth=cls._basic_auth_credentials, data=email_params
        )
        if response.status_code == status.HTTP_401_UNAUTHORIZED:
            message = "Mailgun API keys not properly configured."
            log.error(message)
            raise ImproperlyConfigured(message)
        if raise_for_status:
            response.raise_for_status()
        return response

    @classmethod
    def send_batch(
        cls,
        subject,
        html_body,
        text_body,
        recipients,
        sender_address=None,
        sender_name=None,
        chunk_size=settings.MAILGUN_BATCH_CHUNK_SIZE,
        raise_for_status=True,
    ):
        """
        Sends a text email to a list of recipients (one email per recipient) via batch.

        Args:
            subject (str): email subject
            html_body (str): email html body
            text_body (str): email text body
            recipients (iterable of (recipient, context)):
                A list where each tuple is:
                    (recipient, context)
                Where the recipient is an email address and context is a dict of variables for templating
            sender_address (str): Sender email address
            sender_name (str): Sender name
            chunk_size (int): The maximum amount of emails to be sent at the same time
            raise_for_status (bool): If true, raise for non 2xx statuses

        Returns:
            list:
                List of responses which are HTTP responses from Mailgun.

        Raises:
            SendBatchException:
               If there is at least one exception, this exception is raised with all other exceptions in a list
               along with recipients we failed to send to.
        """
        # Convert null contexts to empty dicts
        recipients = ((email, context or {}) for email, context in recipients)

        if settings.MAILGUN_RECIPIENT_OVERRIDE is not None:
            # This is used for debugging only
            recipients = [(settings.MAILGUN_RECIPIENT_OVERRIDE, {})]

        responses = []
        exception_pairs = []

        for chunk in chunks(recipients, chunk_size=chunk_size):
            chunk_dict = {email: context for email, context in chunk}
            emails = list(chunk_dict.keys())

            params = {
                "to": emails,
                "subject": subject,
                "html": html_body,
                "text": text_body,
                "recipient-variables": json.dumps(chunk_dict),
            }
            if sender_address:
                params["from"] = sender_address

            try:
                response = cls._mailgun_request(
                    requests.post,
                    "messages",
                    params,
                    sender_name=sender_name,
                    raise_for_status=raise_for_status,
                )

                responses.append(response)
            except ImproperlyConfigured:
                raise
            except Exception as exception:
                exception_pairs.append((emails, exception))

        if exception_pairs:
            raise SendBatchException(exception_pairs)

        return responses

    @classmethod
    def send_individual_email(
        cls,
        subject,
        html_body,
        text_body,
        recipient,
        recipient_variables=None,
        sender_address=None,
        sender_name=None,
        raise_for_status=True,
    ):
        """
        Sends a text email to a single recipient.

        Args:
            subject (str): email subject
            html_body (str): email text body
            text_body (str): email html body
            recipient (str): email recipient
            recipient_variables (dict): A dict of template variables to use (may be None for empty)
            sender_address (str): Sender email address
            sender_name (str): Sender name
            raise_for_status (bool): If true and a non-zero response was received,

        Returns:
            requests.Response: response from Mailgun
        """
        # Since .send_batch() returns a list, we need to return the first in the list
        responses = cls.send_batch(
            subject,
            html_body,
            text_body,
            [(recipient, recipient_variables)],
            sender_address=sender_address,
            sender_name=sender_name,
            raise_for_status=raise_for_status,
        )
        return responses[0]


def render_email_templates(template_name, context):
    """
    Renders the email templates for the email

    Args:
        template_name (str): name of the template, this should match a directory in mail/templates
        context (dict): context data for the email

    Returns:
        (str, str, str): tuple of the templates for subject, text_body, html_body
    """
    subject_text = render_to_string(
        "{}/subject.txt".format(template_name), context
    ).rstrip()

    context.update({"subject": subject_text})
    html_text = render_to_string("{}/body.html".format(template_name), context)

    # pynliner internally uses bs4, which we can now modify the inlined version into a plaintext version
    # this avoids parsing the body twice in bs4
    soup = BeautifulSoup(html_text, "html5lib")
    for link in soup.find_all("a"):
        link.replace_with("{} ({})".format(link.string, link.attrs["href"]))

    # clear any surviving style and title tags, so their contents don't get printed
    for style in soup.find_all(["style", "title"]):
        style.clear()  # clear contents, just removing the tag isn't enough

    fallback_text = soup.get_text().strip()
    # truncate more than 3 consecutive newlines
    fallback_text = re.sub(r"\n\s*\n", "\n\n\n", fallback_text)
    # ltrim the left side of all lines
    fallback_text = re.sub(
        r"^([ ]+)([\s\\X])", r"\2", fallback_text, flags=re.MULTILINE
    )

    return subject_text, fallback_text, html_text


def context_for_video(video):
    """
    Returns an email context for the given video

    Args:
        video (Video): video this email is about

    Returns:
        dict: the context for this user
    """

    context = {
        "video_url": urljoin(
            settings.ODL_VIDEO_BASE_URL,
            reverse("video-detail", kwargs={"video_key": video.hexkey}),
        ),
        "video_title": video.title,
        "collection_title": video.collection.title,
        "collection_url": urljoin(
            settings.ODL_VIDEO_BASE_URL,
            reverse(
                "collection-react-view",
                kwargs={"collection_key": video.collection.hexkey},
            ),
        ),
        "support_email": settings.EMAIL_SUPPORT,
        "static_url": urljoin(settings.ODL_VIDEO_BASE_URL, settings.STATIC_URL),
    }
    return context
