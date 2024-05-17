"""
URLs for cloudsync app
"""

from django.urls import path, re_path

from cloudsync import views

urlpatterns = [
    path(
        "api/v0/tasks/<uuid:task_id>",
        views.CeleryTaskStatus.as_view(),
        name="celery-task-status",
    ),
    re_path(
        r"api/v0/youtube-tokens/", views.YoutubeTokensView.as_view(), name="yt_tokens"
    ),
]
