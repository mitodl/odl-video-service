"""
URLs for cloudsync app
"""

from django.conf.urls import url
from cloudsync import views

urlpatterns = [
    url(
        r"^api/v0/tasks/(?P<task_id>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})$",
        views.CeleryTaskStatus.as_view(),
        name="celery-task-status",
    ),
]
