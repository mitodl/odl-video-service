"""
Views for cloudsync app
"""

from urllib.parse import urljoin

from celery.result import AsyncResult
from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse
from google_auth_oauthlib.flow import InstalledAppFlow
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView


class CeleryTaskStatus(APIView):
    """
    Class based view for checking status of celery tasks.
    """

    def get(self, request, task_id):  # noqa: ARG002
        """
        Returns the status of a task
        """
        result = AsyncResult(task_id)
        if isinstance(result.info, Exception):
            return Response(
                {
                    "status": result.state,
                    "exception": result.info.__class__.__name__,
                    "args": result.info.args,
                }
            )
        return Response(
            {
                "status": result.state,
                "info": result.info,
            }
        )


class YoutubeTokensView(GenericAPIView):
    """Admin-only endpoint for generating new Youtube OAuth tokens"""

    permission_classes = (IsAdminUser,)

    def get(self, request, *args, **kwargs):  # noqa: ARG002
        """Return Youtube credential info"""
        token_url = urljoin(settings.ODL_VIDEO_BASE_URL, reverse("yt_tokens"))
        oauth_config = {
            "installed": {
                "client_id": settings.YT_CLIENT_ID,
                "client_secret": settings.YT_CLIENT_SECRET,
                "project_id": settings.YT_PROJECT_ID,
                "redirect_uris": [token_url],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://accounts.google.com/o/oauth2/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            }
        }
        flow = InstalledAppFlow.from_client_config(
            oauth_config,
            [
                "https://www.googleapis.com/auth/youtube",
                "https://www.googleapis.com/auth/youtube.force-ssl",
                "https://www.googleapis.com/auth/youtube.upload",
            ],
        )

        if not request.query_params.get("code"):
            authorization_url, _ = flow.authorization_url(
                access_type="offline", prompt="consent", include_granted_scopes="true"
            )
            return redirect(f"{authorization_url}&redirect_uri={token_url}")
        else:
            flow.redirect_uri = token_url
            flow.fetch_token(authorization_response=request.build_absolute_uri())
            credentials = flow.credentials
            output = {
                "YT_ACCESS_TOKEN": credentials.token,
                "YT_REFRESH_TOKEN": credentials.refresh_token,
            }
            return Response(output)
