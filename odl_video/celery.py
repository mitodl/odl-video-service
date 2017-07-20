"""
Celery configuration
"""

import logging
import os

from celery import Celery
from raven import Client
from raven.contrib.celery import register_logger_signal, register_signal

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'odl_video.settings')

from django.conf import settings  # noqa pylint: disable=wrong-import-position

log = logging.getLogger(__name__)

client = Client(**settings.RAVEN_CONFIG)

register_logger_signal(client, loglevel=settings.SENTRY_LOG_LEVEL)

# The register_signal function can also take an optional argument
# `ignore_expected` which causes exception classes specified in Task.throws
# to be ignored
register_signal(client, ignore_expected=True)

app = Celery('odl_video')

# Using a string here means the worker don't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)  # pragma: no cover


@app.task(bind=True)
def debug_task(self):
    """
    Task for debugging purposes
    """
    print('Request: {0!r}'.format(self.request))
