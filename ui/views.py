"""Views for ui app"""
import json

from celery import chain
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.http import JsonResponse, HttpResponseRedirect
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView, ListView, DetailView
from rest_framework import viewsets, status
from rest_framework.decorators import detail_route
from rest_framework.response import Response

from cloudsync.tasks import stream_to_s3, transcode_from_s3
from ui.api import refresh_status
from ui.util import get_dropbox_credentials
from ui.models import Video, VideoFile
from ui.forms import VideoForm, UserCreationForm
from ui.serializers import VideoSerializer, DropboxFileSerializer
from ui.permissions import (
    admin_required, IsAdminOrHasMoiraPermissions
)


class Index(TemplateView):
    """Index"""
    template_name = "ui/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["login_form"] = AuthenticationForm()
        context["register_form"] = UserCreationForm()
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
        return context


@method_decorator(login_required, name='dispatch')
class VideoList(ListView):
    """VideoList"""
    model = Video


@method_decorator(login_required, name='dispatch')
class VideoDetail(DetailView):
    """VideoDetail"""
    model = Video

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        video = context["object"]
        refresh_status(video)
        context['form'] = VideoForm(instance=video)
        return context


@require_POST
@login_required
@admin_required
def stream(request):
    """stream"""
    data = json.loads(request.body.decode('utf-8'))
    serializer = DropboxFileSerializer(data=data, many=True)
    serializer.is_valid(raise_exception=True)
    dropbox_files = serializer.validated_data
    response = {}
    for dropbox_file in dropbox_files:
        video = Video.objects.create(
            source_url=dropbox_file["link"],
            creator=request.user,
            title=dropbox_file["name"]
        )
        try:
            VideoFile.objects.create(
                s3_object_key=video.s3_key(),
                video_id=video.id,
                bucket_name=settings.VIDEO_S3_BUCKET
            )
        except Exception as e:
            # Delete the video object if videofile object can't be created, no point in keeping it around
            video.delete()
            raise e
        # Kick off chained async celery tasks to transfer file to S3, then start a transcode job
        task_result = chain(stream_to_s3.s(dropbox_file["link"], video.s3_key()), transcode_from_s3.si(video.id))()
        response[video.id] = {
            "key": video.s3_key(),
            "task": task_result.id,
        }

    return JsonResponse(response)


@method_decorator(login_required, name='dispatch')
class VideoViewSet(viewsets.ModelViewSet):
    """VideoViewSet"""
    queryset = Video.objects.all()
    serializer_class = VideoSerializer
    permission_classes = [IsAdminOrHasMoiraPermissions]

    def destroy(self, request, *args, **kwargs):  # pylint:disable=unused-argument
        """Destroy the video via REST API"""
        video = self.get_object()
        self.perform_destroy(video)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @detail_route(permission_classes=(IsAdminOrHasMoiraPermissions,), url_path=r'signed_url/(?P<encoding>\w+)')
    def signed_url(self, request, pk=None, encoding=None):  # pylint:disable=unused-argument
        """
        REST API route for getting a signed URL
        """
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
    return render(request, "registration/register.html", context)
