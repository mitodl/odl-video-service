"""Sentry setup and configuration"""

import sentry_sdk
from celery.exceptions import WorkerLostError
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

from cloudsync.exceptions import TranscodeTargetDoesNotExist

# these errors should be ignored by sentry
IGNORED_ERRORS = (WorkerLostError, SystemExit, TranscodeTargetDoesNotExist)


def before_send(event, hint):
    """
    Filter or transform events before they're sent to Sentry
    Args:
        event (dict): event object
        hints (dict): event hints, see https://docs.sentry.io/platforms/python/#hints
    Returns:
        dict or None: returns the modified event or None to filter out the event
    """
    if "exc_info" in hint:
        _, exc_value, _ = hint["exc_info"]
        if isinstance(exc_value, IGNORED_ERRORS):
            # so we don't want to report expected shutdown errors to sentry
            return None
    return event


def init_sentry(*, dsn, environment, version, log_level):
    """
    Initializes sentry
    Args:
        dsn (str): the sentry DSN key
        environment (str): the application environment
        version (str): the version of the application
        log_level (str): the sentry log level
    """  # noqa: D401
    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        release=version,
        before_send=before_send,
        integrations=[
            DjangoIntegration(),
            CeleryIntegration(),
            LoggingIntegration(level=log_level),
        ],
    )
