"""Views for ui app"""
import json

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

from cloudsync.tasks import stream_to_s3
from ui.util import get_expiration, get_dropbox_credentials
from ui.models import Video
from ui.forms import VideoForm, UserCreationForm
from ui.serializers import VideoSerializer, DropboxFileSerializer
from ui.permissions import (
    admin_required,
    IsAdminOrReadOnly,
    IsAdminOrHasMoiraPermissions
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
        context['form'] = VideoForm(instance=context["object"])
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
        video, _ = Video.objects.get_or_create(
            s3_object_key=dropbox_file["name"],
            defaults={
                "source_url": dropbox_file["link"],
                "creator": request.user,
            }
        )
        # make sure these values are set
        video.source_url = dropbox_file["link"]
        video.creator = request.user
        video.save()
        task_result = stream_to_s3.delay(video.source_url)
        response[video.id] = {
            "key": video.s3_object_key,
            "task": task_result.id,
        }
    return JsonResponse(response)


class VideoViewSet(viewsets.ModelViewSet):
    """VideoViewSet"""
    queryset = Video.objects.all()
    serializer_class = VideoSerializer
    permission_classes = (IsAdminOrReadOnly,)

    def destroy(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        video = self.get_object()
        if request.GET.get("s3"):
            video.s3_object.delete()
        self.perform_destroy(video)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @detail_route(permission_classes=(IsAdminOrHasMoiraPermissions,))
    def signed_url(self, request, pk=None):  # pylint: disable=unused-argument
        """signed_url"""
        video = self.get_object()
        self.check_object_permissions(self.request, video)
        expires = get_expiration(request.query_params)
        signed_url = video.cloudfront_signed_url(expires=expires)
        return Response({
            "url": signed_url,
            "expires": expires,
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
