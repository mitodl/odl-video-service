"""Views for ui app"""
import json

from celery import chain
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.views import login as login_view
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.http import HttpResponseRedirect
from django.db import transaction
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView, ListView, DetailView
from rest_framework import (
    authentication,
    permissions,
    status,
    viewsets,
)
from rest_framework.decorators import detail_route
from rest_framework.response import Response
from rest_framework.views import APIView

from cloudsync.tasks import stream_to_s3, transcode_from_s3
from ui.api import refresh_status
from ui.encodings import EncodingNames
from ui.templatetags.render_bundle import public_path
from ui.util import get_dropbox_credentials
from ui.models import Video, VideoFile
from ui.forms import VideoForm, UserCreationForm
from ui.serializers import VideoSerializer, DropboxFileSerializer
from ui.permissions import (
    admin_required, IsAdminOrHasMoiraPermissions
)


def default_js_settings(request):
    """Default JS settings for views"""
    return json.dumps({
        "gaTrackingID": settings.GA_TRACKING_ID,
        "public_path": public_path(request),
    })


class Index(TemplateView):
    """Index"""
    template_name = "ui/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["login_form"] = AuthenticationForm()
        context["register_form"] = UserCreationForm()
        context["js_settings_json"] = json.dumps(default_js_settings(self.request))
        return context


@method_decorator(login_required, name='dispatch')
@method_decorator(admin_required, name='dispatch')
class Upload(TemplateView):
    """Upload"""
    template_name = "ui/upload.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        key, _ = get_dropbox_credentials()
        context["dropbox_key"] = key
        context["js_settings_json"] = json.dumps(default_js_settings(self.request))
        return context


@method_decorator(login_required, name='dispatch')
class VideoList(ListView):
    """VideoList"""
    model = Video

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["js_settings_json"] = json.dumps(default_js_settings(self.request))
        return context


@method_decorator(login_required, name='dispatch')
class VideoDetail(DetailView):
    """VideoDetail"""
    model = Video

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        video = context["object"]
        refresh_status(video)
        context['form'] = VideoForm(instance=video)
        context['videofile'] = context['object'].videofile_set.filter(encoding=EncodingNames.HLS)
        context["js_settings_json"] = json.dumps(default_js_settings(self.request))
        return context


class UploadVideosFromDropbox(APIView):
    """
    Class based view for uploading videos from dropbox to S3.
    """
    authentication_classes = (
        authentication.SessionAuthentication,
    )
    permission_classes = (
        permissions.IsAuthenticated,
    )

    def post(self, request):
        """
        Creates entries for each submitted file in dropbox in the specific model and submits async tasks
        for uploading the file to S3
        """
        serializer = DropboxFileSerializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        dropbox_files = serializer.validated_data
        response_data = {}
        for dropbox_file in dropbox_files:
            with transaction.atomic():
                video = Video.objects.create(
                    source_url=dropbox_file["link"],
                    creator=request.user,
                    title=dropbox_file["name"]
                )
                VideoFile.objects.create(
                    s3_object_key=video.s3_key(),
                    video_id=video.id,
                    bucket_name=settings.VIDEO_S3_BUCKET
                )
            # Kick off chained async celery tasks to transfer file to S3, then start a transcode job
            task_result = chain(
                stream_to_s3.s(dropbox_file["link"], video.s3_key()),
                transcode_from_s3.si(video.id)
            )()

            response_data[video.id] = {
                "key": video.s3_key(),
                "task": task_result.id,
            }

        return Response(data=response_data)


@method_decorator(login_required, name='dispatch')
class VideoViewSet(viewsets.ModelViewSet):
    """
    Implements all the REST views for the Video Model.
    """
    queryset = Video.objects.all()
    serializer_class = VideoSerializer
    permission_classes = (
        IsAdminOrHasMoiraPermissions,
    )

    def destroy(self, request, *args, **kwargs):  # pylint:disable=unused-argument
        """Destroy the video via REST API"""
        video = self.get_object()
        self.perform_destroy(video)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @detail_route(
        permission_classes=(
            IsAdminOrHasMoiraPermissions,
        ),
        url_path=r'signed_url/(?P<encoding>\w+)'
    )
    def signed_url(self, request, pk, encoding):  # pylint: disable=unused-argument
        """signed_url"""
        video = self.get_object()
        self.check_object_permissions(self.request, video)
        video_file = video.videofile_set.get(encoding=encoding)
        signed_url = video_file.cloudfront_signed_url
        return Response({
            "url": signed_url
        })


def register(request):
    """register"""
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Account created.")
            return HttpResponseRedirect(settings.LOGIN_REDIRECT_URL)
    else:
        form = UserCreationForm
    context = {
        "form": form,
    }
    context["js_settings_json"] = default_js_settings(request)
    return render(request, "registration/register.html", context)


def ui_login(request, *args, **kwargs):
    """login"""
    extra_context = {
        "js_settings_json": default_js_settings(request)
    }
    return login_view(request, *args, extra_context=extra_context, **kwargs)
