"""Views for ui app"""
import json

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
    get_list_or_404)
from django.utils.decorators import method_decorator
from django.views.decorators.clickjacking import xframe_options_exempt
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
from cloudsync.tasks import upload_youtube_caption
from techtv2ovs.models import TechTVVideo
from ui.serializers import VideoSerializer
from ui.templatetags.render_bundle import public_path
from ui import (
    api,
    serializers,
    permissions as ui_permissions
)
from ui.models import (
    Collection,
    Video,
    VideoSubtitle,
)


def default_js_settings(request):
    """Default JS settings for views"""
    return {
        "gaTrackingID": settings.GA_TRACKING_ID,
        "public_path": public_path(request),
        "cloudfront_base_url": settings.VIDEO_CLOUDFRONT_BASE_URL,
        "user": request.user.username if request.user.is_authenticated else None,
        "email": request.user.email if request.user.is_authenticated else None,
        "support_email_address": settings.EMAIL_SUPPORT,
        "ga_dimension_camera": settings.GA_DIMENSION_CAMERA,
        "FEATURES": {
            "ENABLE_VIDEO_PERMISSIONS": settings.ENABLE_VIDEO_PERMISSIONS
        }
    }


def index(request):  # pylint: disable=unused-argument
    """Index"""
    return redirect('collection-react-view')


@method_decorator(login_required, name='dispatch')
class CollectionReactView(TemplateView):
    """List of collections"""
    template_name = "ui/collections.html"

    def get_context_data(self, collection_key=None, **kwargs):  # pylint: disable=arguments-differ
        context = super().get_context_data(**kwargs)
        if collection_key:
            get_object_or_404(Collection, key=collection_key)
        context["js_settings_json"] = json.dumps({
            **default_js_settings(self.request),
            'editable': ui_permissions.is_staff_or_superuser(self.request.user),
            'dropbox_key': settings.DROPBOX_KEY
        })
        return context


class VideoDetail(TemplateView):
    """
    Details of a video
    """
    template_name = "ui/video_detail.html"

    def get_context_data(self, video_key, **kwargs):  # pylint: disable=arguments-differ
        context = super().get_context_data(**kwargs)
        video = get_object_or_404(Video, key=video_key)
        if not ui_permissions.has_video_view_permission(video, self.request):
            raise PermissionDenied
        context["js_settings_json"] = json.dumps({
            **default_js_settings(self.request),
            'videoKey': video.key.hex,
            'editable': ui_permissions.has_admin_permission(video.collection, self.request),
            'dropbox_key': settings.DROPBOX_KEY
        })
        return context


@method_decorator(xframe_options_exempt, name='dispatch')
class VideoEmbed(TemplateView):
    """Display embedded video"""
    template_name = 'ui/video_embed.html'

    def get_context_data(self, video_key, **kwargs):  # pylint: disable=arguments-differ
        context = super().get_context_data(**kwargs)
        video = get_object_or_404(Video, key=video_key)
        if not ui_permissions.has_video_view_permission(video, self.request):
            raise PermissionDenied
        context['video'] = video
        context["js_settings_json"] = json.dumps({
            **default_js_settings(self.request),
            'video': VideoSerializer(video).data,
        })
        return context


class TechTVDetail(VideoDetail):
    """
    Video detail page for a TechTV-based URL
    """
    def get_context_data(self, video_key, **kwargs):
        # There might be more than one imported TechTV video with this id
        ttv_videos = get_list_or_404(TechTVVideo.objects.filter(ttv_id=video_key))
        video = ttv_videos[0].video
        return super().get_context_data(video.hexkey, **kwargs)


class TechTVPrivateDetail(VideoDetail):
    """
    Video detail page for a TechTV-based private URL
    """
    def get_context_data(self, video_key, **kwargs):
        # There might be more than one imported TechTV video with this private token
        ttv_videos = get_list_or_404(TechTVVideo.objects.filter(private_token=video_key))
        video = ttv_videos[0].video
        return super().get_context_data(video.hexkey, **kwargs)


class TechTVEmbed(VideoEmbed):
    """
    Video embed page for a TechTV-based URL
    """
    def get_context_data(self, video_key, **kwargs):
        # There might be more than one imported TechTV video with this id
        ttv_videos = get_list_or_404(TechTVVideo.objects.filter(ttv_id=video_key))
        video = ttv_videos[0].video
        return super().get_context_data(video.hexkey, **kwargs)


@method_decorator(login_required, name='dispatch')
class HelpPageView(TemplateView):
    """View for the help page"""
    template_name = "ui/help.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        has_admin = Collection.objects.all_admin(self.request.user).exists()
        is_staff_or_superuser = ui_permissions.is_staff_or_superuser(self.request.user)
        context["js_settings_json"] = json.dumps({
            **default_js_settings(self.request),
            'is_admin': has_admin or is_staff_or_superuser
        })
        return context


@method_decorator(login_required, name='dispatch')
class TermsOfServicePageView(TemplateView):
    """View for the help page"""
    template_name = "ui/terms.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        has_admin = Collection.objects.all_admin(self.request.user).exists()
        is_staff_or_superuser = ui_permissions.is_staff_or_superuser(self.request.user)
        context["js_settings_json"] = json.dumps({
            **default_js_settings(self.request),
            'is_admin': has_admin or is_staff_or_superuser
        })
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

        # Upload to YouTube if necessary
        if settings.ENABLE_VIDEO_PERMISSIONS:
            youtube_id = subtitle.video.youtube_id
            if youtube_id:
                upload_youtube_caption.delay(subtitle.id)

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
        ui_permissions.HasVideoPermissions,
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
        ui_permissions.HasVideoSubtitlePermissions,
    )


def _handle_error_view(request, status_code):
    """
    Handles a 403, 404 or 500 response
    """
    return render(request, "error.html", status=status_code, context={
        "js_settings_json": json.dumps({
            **default_js_settings(request),
            "status_code": status_code,
        }),
    })


def permission_denied_403_view(request, *args, **kwargs):  # pylint: disable=unused-argument
    """
    Handles a 403 response
    """
    return _handle_error_view(request, status.HTTP_403_FORBIDDEN)


def page_not_found_404_view(request, *args, **kwargs):  # pylint: disable=unused-argument
    """
    Handles a 404 response
    """
    return _handle_error_view(request, status.HTTP_404_NOT_FOUND)


def error_500_view(request, *args, **kwargs):  # pylint: disable=unused-argument
    """
    Handles a 500 response
    """
    return _handle_error_view(request, status.HTTP_500_INTERNAL_SERVER_ERROR)
