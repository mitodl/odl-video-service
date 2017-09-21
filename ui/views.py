"""Views for ui app"""
import json

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.views import login as login_view
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.utils.decorators import method_decorator
from django.urls import reverse
from django.views.generic import TemplateView
from rest_framework import (
    authentication,
    permissions,
    status,
    viewsets,
    mixins,
)
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from cloudsync import api as cloudapi
from ui.serializers import VideoSerializer
from ui.templatetags.render_bundle import public_path
from ui import (
    api,
    serializers,
    forms,
    permissions as ui_permissions
)
from ui.models import (
    Collection,
    Video,
    VideoSubtitle)


def default_js_settings(request):
    """Default JS settings for views"""
    return {
        "gaTrackingID": settings.GA_TRACKING_ID,
        "public_path": public_path(request),
        "cloudfront_base_url": settings.VIDEO_CLOUDFRONT_BASE_URL,
        "user": (request.user.email or request.user.username) if request.user.is_authenticated else "Not logged in",
        "support_email_address": settings.EMAIL_SUPPORT,
    }


class Index(TemplateView):
    """Index"""
    template_name = "ui/index.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated():
            return HttpResponseRedirect(reverse('collection-react-view'))
        return super(Index, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["login_form"] = AuthenticationForm()
        context["register_form"] = forms.UserCreationForm()
        context["js_settings_json"] = json.dumps(default_js_settings(self.request))
        return context


@method_decorator(login_required, name='dispatch')
class CollectionReactView(TemplateView):
    """List of collections"""
    template_name = "ui/collections.html"

    def get_context_data(self, **kwargs):  # pylint: disable=arguments-differ
        context = super().get_context_data(**kwargs)
        context["js_settings_json"] = json.dumps({
            **default_js_settings(self.request),
            'editable': ui_permissions.is_staff_or_superuser(self.request.user),
            'dropbox_key': settings.DROPBOX_KEY
        })
        return context


@method_decorator(login_required, name='dispatch')
class VideoDetail(TemplateView):
    """
    Details of a video
    """
    template_name = "ui/video_detail.html"

    def get_context_data(self, video_key, **kwargs):  # pylint: disable=arguments-differ
        context = super().get_context_data(**kwargs)
        video = get_object_or_404(Video, key=video_key)
        if not ui_permissions.has_view_permission(video.collection, self.request):
            raise PermissionDenied
        context["js_settings_json"] = json.dumps({
            **default_js_settings(self.request),
            'videoKey': video.key.hex,
            'editable': ui_permissions.has_admin_permission(video.collection, self.request)
        })
        return context


@method_decorator(login_required, name='dispatch')
class VideoEmbed(TemplateView):
    """Display embedded video"""
    template_name = 'ui/video_embed.html'

    def get_context_data(self, video_key, **kwargs):  # pylint: disable=arguments-differ
        context = super().get_context_data(**kwargs)
        video = get_object_or_404(Video, key=video_key)
        if not ui_permissions.has_view_permission(video.collection, self.request):
            raise PermissionDenied
        context['video'] = video
        context["js_settings_json"] = json.dumps({
            **default_js_settings(self.request),
            'video': VideoSerializer(video).data,
        })
        context['uswitchPlayerURL'] = settings.USWITCH_URL
        return context


@method_decorator(login_required, name='dispatch')
class MosaicView(TemplateView):
    """Display USwitch cameras in separate window"""
    template_name = "ui/mosaic.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['uswitchPlayerURL'] = settings.USWITCH_URL
        return context


class ModelDetailViewset(
        mixins.RetrieveModelMixin,
        mixins.UpdateModelMixin,
        mixins.DestroyModelMixin,
        viewsets.GenericViewSet
):
    """
    A viewset that provides default retrieve()`, `update()`,
    `partial_update()`, `destroy()` actions.
    """
    pass


class UploadVideosFromDropbox(APIView):
    """
    Class based view for uploading videos from dropbox to S3.
    """
    authentication_classes = (
        authentication.SessionAuthentication,
    )
    permission_classes = (
        permissions.IsAuthenticated,
        ui_permissions.CanUploadToCollection,
    )

    def post(self, request):
        """
        Creates entries for each submitted file in dropbox in the specific model and submits async tasks
        for uploading the file to S3
        """
        serializer = serializers.DropboxUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        response_data = api.process_dropbox_data(serializer.validated_data)
        return Response(
            data=response_data,
            status=status.HTTP_202_ACCEPTED
        )


class UploadVideoSubtitle(APIView):
    """
    Class based view for uploading videos from dropbox to S3.
    """
    authentication_classes = (
        authentication.SessionAuthentication,
    )
    permission_classes = (
        permissions.IsAuthenticated,
        ui_permissions.CanUploadToCollection,
    )
    parser_classes = (MultiPartParser,)

    def post(self, request):
        """
        Upload the videoSubtitle to S3, create a VideoSubtitle object
        """
        file_obj = request.data['file']
        upload_data = {
            'video': request.data['video'],
            'language': request.data['language'],
            'filename': request.data['filename']
        }
        serializer = serializers.VideoSubtitleUploadSerializer(data=upload_data)
        serializer.is_valid(raise_exception=True)

        subtitle = cloudapi.upload_subtitle_to_s3(serializer.validated_data, file_obj)
        return Response(
            data=serializers.VideoSubtitleSerializer(subtitle).data,
            status=status.HTTP_202_ACCEPTED
        )


class CollectionViewSet(viewsets.ModelViewSet):
    """
    Implements all the REST views for the Collection Model.
    """
    lookup_field = 'key'
    authentication_classes = (
        authentication.SessionAuthentication,
    )
    permission_classes = (
        permissions.IsAuthenticated,
        ui_permissions.HasCollectionPermissions
    )

    def get_queryset(self):
        """
        Custom get_queryset to filter collections.
        """
        if self.kwargs.get('key') is not None:
            return Collection.objects.all()
        return Collection.objects.all_viewable(self.request.user)

    def get_serializer_class(self):
        """
        Custom get_serializer_class to handle the different serializer class
        for the list method
        """
        # the collection key is not None in the detail view
        if self.kwargs.get('key') is not None:
            return serializers.CollectionSerializer
        return serializers.CollectionListSerializer


class VideoViewSet(ModelDetailViewset):
    """
    Implements all the REST views for the Video Model.
    This viewset does not implement the `create`: Video objects need
    to be created via other ways
    """
    lookup_field = 'key'
    queryset = Video.objects.all()
    serializer_class = serializers.VideoSerializer
    authentication_classes = (
        authentication.SessionAuthentication,
    )
    permission_classes = (
        permissions.IsAuthenticated,
        ui_permissions.HasVideoPermissions
    )


class VideoSubtitleViewSet(ModelDetailViewset):
    """
    Implements all the REST views for the VideoSubtitle Model.
    This viewset does not implement `create`: VideoSubtitle objects need
    to be created via other ways
    """
    lookup_field = 'id'
    queryset = VideoSubtitle.objects.all()
    serializer_class = serializers.VideoSubtitleSerializer
    authentication_classes = (
        authentication.SessionAuthentication,
    )
    permission_classes = (
        permissions.IsAuthenticated,
        ui_permissions.HasVideoSubtitlePermissions
    )


def register(request):
    """register"""
    if request.method == "POST":
        form = forms.UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Account created.")
            return HttpResponseRedirect(settings.LOGIN_REDIRECT_URL)
    else:
        form = forms.UserCreationForm
    context = {
        "form": form,
    }
    context["js_settings_json"] = json.dumps(default_js_settings(request))
    return render(request, "registration/register.html", context)


def ui_login(request, *args, **kwargs):
    """login"""
    extra_context = {
        "js_settings_json": json.dumps(default_js_settings(request))
    }
    return login_view(request, *args, extra_context=extra_context, **kwargs)
