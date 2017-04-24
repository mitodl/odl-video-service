import os
import json
from datetime import datetime, timedelta
from django.conf import settings
from django.views.decorators.http import require_POST
from django.shortcuts import render
from django.views.generic import TemplateView, ListView, DetailView
from django.http import JsonResponse, HttpResponseRedirect
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils.decorators import method_decorator
from rest_framework import viewsets
from rest_framework import status
from rest_framework.response import Response
from cloudsync.tasks import stream_to_s3
from ui.util import cloudfront_signed_url
from ui.models import Video
from ui.forms import VideoForm
from ui.serializers import (
    VideoSerializer, DropboxFileSerializer, CloudFrontSignedURLSerializer
)


class Index(TemplateView):
    template_name = "ui/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["login_form"] = AuthenticationForm()
        context["register_form"] = UserCreationForm()
        return context


@method_decorator(login_required, name='dispatch')
@method_decorator(user_passes_test(lambda u: u.is_staff), name='dispatch')
class Upload(TemplateView):
    template_name = "ui/upload.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        dropbox_key = os.environ.get("DROPBOX_APP_KEY")
        if not dropbox_key:
            raise RuntimeError("Missing required env var: DROPBOX_APP_KEY")
        context["dropbox_key"] = dropbox_key
        return context


@method_decorator(login_required, name='dispatch')
class VideoList(ListView):
    model = Video


@method_decorator(login_required, name='dispatch')
class VideoDetail(DetailView):
    model = Video

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        video = context["object"]
        context['form'] = VideoForm(instance=video)
        context['cloudfront_signed_url'] = cloudfront_signed_url(
            key=video.s3_object_key,
            expires_at=datetime.utcnow() + timedelta(hours=2),
        )
        return context


@require_POST
@login_required
def stream(request):
    data = json.loads(request.body.decode('utf-8'))
    serializer = DropboxFileSerializer(data=data, many=True)
    serializer.is_valid(raise_exception=True)
    videos = serializer.save()

    response = {
        video.id: {
            "key": video.s3_object_key,
            "task": stream_to_s3.delay(video.source_url).id,
        }
        for video in videos
    }
    return JsonResponse(response)


@require_POST
@login_required
def generate_signed_url(request):
    data = json.loads(request.body.decode('utf-8'))
    serializer = CloudFrontSignedURLSerializer(data=data)
    serializer.is_valid(raise_exception=True)
    key = serializer.validated_data["key"]
    expires_at = serializer.calculated_expiration()
    signed_url = cloudfront_signed_url(key=key, expires_at=expires_at)
    return JsonResponse({
        "url": signed_url,
        "expires_at": expires_at.isoformat(),
    })


class VideoViewSet(viewsets.ModelViewSet):
    queryset = Video.objects.all()
    serializer_class = VideoSerializer

    def destroy(self, request, *args, **kwargs):
        video = self.get_object()
        if request.GET.get("s3"):
            video.s3_object.delete()
        self.perform_destroy(video)
        return Response(status=status.HTTP_204_NO_CONTENT)


def register(request):
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

