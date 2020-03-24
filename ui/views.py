"""Views for ui app"""
import json

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.views import redirect_to_login
from django.contrib.auth.views import LoginView as DjangoLoginView
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import HttpResponse, Http404
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
    get_list_or_404)
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.generic import TemplateView
from raven.contrib.django.raven_compat.models import client as sentry
from rest_framework import (
    authentication,
    permissions,
    status,
    viewsets,
    mixins,
)
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from cloudsync import api as cloudapi
from cloudsync.tasks import upload_youtube_caption
from techtv2ovs.models import TechTVVideo
from ui.constants import EDX_ADMIN_GROUP
from ui.pagination import CollectionSetPagination, VideoSetPagination
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

from ui.utils import get_video_analytics, generate_mock_video_analytics_data, query_moira_lists, list_members


def default_js_settings(request):
    """Default JS settings for views"""
    return {
        "gaTrackingID": settings.GA_TRACKING_ID,
        "environment": settings.ENVIRONMENT,
        "sentry_dsn": sentry.get_public_dsn(),
        "release_version": settings.VERSION,
        "public_path": public_path(request),
        "cloudfront_base_url": settings.VIDEO_CLOUDFRONT_BASE_URL,
        "user": request.user.username if request.user.is_authenticated else None,
        "email": request.user.email if request.user.is_authenticated else None,
        "is_app_admin": (
            (request.user.is_superuser or request.user.is_staff)
            if request.user.is_authenticated
            else False
        ),
        "support_email_address": settings.EMAIL_SUPPORT,
        "ga_dimension_camera": settings.GA_DIMENSION_CAMERA,
        "FEATURES": {
            "ENABLE_VIDEO_PERMISSIONS": settings.ENABLE_VIDEO_PERMISSIONS
        }
    }


def conditional_response(view, video=None, **kwargs):
    """
    Redirect to login page if user is anonymous and video is private.
    Raise a permission denied error if user is logged in but doesn't have permission.
    Otherwise, return standard template response.

    Args:
        view(TemplateView): a video-specific View object (ViewDetail, ViewEmbed, etc).
        video(ui.models.Video): a video to display with the view

    Returns:
        TemplateResponse: the template response to render
    """
    if not ui_permissions.has_video_view_permission(video, view.request):
        if view.request.user.is_authenticated:
            raise PermissionDenied
        else:
            return redirect_to_login(view.request.path)
    context = view.get_context_data(video, **kwargs)
    return view.render_to_response(context)


def index(request):  # pylint: disable=unused-argument
    """Index"""
    return redirect('collection-react-view')


@method_decorator(xframe_options_exempt, name='dispatch')
class CollectionReactView(TemplateView):
    """List of collections"""
    template_name = "ui/collections.html"

    def get_context_data(self, **kwargs):  # pylint: disable=arguments-differ
        context = super().get_context_data(**kwargs)
        context["js_settings_json"] = json.dumps({
            **default_js_settings(self.request),
            'is_edx_course_admin': (
                self.request.user.is_authenticated and
                self.request.user.groups.filter(name=EDX_ADMIN_GROUP).exists()
            ),
            'dropbox_key': settings.DROPBOX_KEY
        })
        return context

    def get(self, request, *args, **kwargs):
        collection_key = kwargs['collection_key']
        if collection_key:
            get_object_or_404(Collection, key=collection_key)
            return super().get(request, *args, **kwargs)

        if not request.user.is_authenticated:
            return redirect_to_login(self.request.path)
        return super().get(request, *args, **kwargs)


class VideoDetail(TemplateView):
    """
    Details of a video
    """
    template_name = "ui/video_detail.html"

    def get(self, request, *args, **kwargs):
        video = get_object_or_404(Video, key=kwargs['video_key'])
        self.get_context_data(video, **kwargs)
        return conditional_response(self, video, *args, **kwargs)

    def get_context_data(self, video, **kwargs):  # pylint: disable=arguments-differ
        context = super().get_context_data(**kwargs)
        context["js_settings_json"] = json.dumps({
            **default_js_settings(self.request),
            'videoKey': video.key.hex,
            'is_video_admin': ui_permissions.has_admin_permission(video.collection, self.request),
            'dropbox_key': settings.DROPBOX_KEY
        })
        return context


@method_decorator(xframe_options_exempt, name='dispatch')
class VideoEmbed(TemplateView):
    """Display embedded video"""
    template_name = 'ui/video_embed.html'

    def get(self, request, *args, **kwargs):
        video = get_object_or_404(Video, key=kwargs['video_key'])
        return conditional_response(self, video, *args, **kwargs)

    def get_context_data(self, video, **kwargs):  # pylint: disable=arguments-differ
        context = super().get_context_data(**kwargs)
        context['video'] = video
        context["js_settings_json"] = json.dumps({
            **default_js_settings(self.request),
            'video': VideoSerializer(video).data,
        })
        return context


class VideoDownload(View):
    """
    Download a public video
    """
    def download(self, video):
        """
        Return the response as a file download

        Args:
            video(Video): the video to download

        Returns:
            HttpResponseRedirect: redirect to the cloudfront URL for the video download
        """
        video_file = video.download
        if not video_file:
            raise Http404()
        return redirect(video_file.cloudfront_url)

    def get(self, request, *args, **kwargs):  # pylint:disable=unused-argument
        """
        Respond to a GET request.

        Returns:
            HttpResponseRedirect: redirect to the cloudfront URL for the video download
        """
        video = get_object_or_404(Video, key=kwargs['video_key'], is_public=True)
        return self.download(video)


class TechTVDetail(VideoDetail):
    """
    Video detail page for a TechTV-based URL
    """
    def get(self, request, *args, **kwargs):
        ttv_videos = get_list_or_404(TechTVVideo.objects.filter(ttv_id=kwargs['video_key']))
        return conditional_response(self, ttv_videos[0].video, *args, **kwargs)


class TechTVPrivateDetail(VideoDetail):
    """
    Video detail page for a TechTV-based private URL
    """
    def get(self, request, *args, **kwargs):
        ttv_videos = get_list_or_404(TechTVVideo.objects.filter(private_token=kwargs['video_key']))
        return conditional_response(self, ttv_videos[0].video, *args, **kwargs)


@method_decorator(xframe_options_exempt, name='dispatch')
class TechTVEmbed(VideoEmbed):
    """
    Video embed page for a TechTV-based URL
    """
    def get(self, request, *args, **kwargs):
        ttv_videos = get_list_or_404(TechTVVideo.objects.filter(ttv_id=kwargs['video_key']))
        return conditional_response(self, ttv_videos[0].video, *args, **kwargs)


class TechTVDownload(VideoDownload):
    """
    Public video download for a TechTV-based URL
    """
    def get(self, request, *args, **kwargs):  # pylint:disable=unused-argument
        ttv_videos = get_list_or_404(
            Video.objects.filter(techtvvideo__ttv_id=kwargs['video_key']).filter(is_public=True)
        )
        video = ttv_videos[0]
        return self.download(video)


class HelpPageView(TemplateView):
    """View for the help page"""
    template_name = "ui/help.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        js_settings = default_js_settings(self.request)
        context["js_settings_json"] = json.dumps(js_settings)
        return context


class TermsOfServicePageView(TemplateView):
    """View for the help page"""
    template_name = "ui/terms.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        js_settings = default_js_settings(self.request)
        context["js_settings_json"] = json.dumps(js_settings)
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
        ui_permissions.HasCollectionPermissions,
    )

    pagination_class = CollectionSetPagination
    filter_backends = (OrderingFilter,)
    ordering_fields = ('created_at', 'title')

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


class VideoViewSet(mixins.ListModelMixin, ModelDetailViewset):
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
    pagination_class = VideoSetPagination
    filter_backends = (OrderingFilter,)
    ordering_fields = ('created_at', 'title', )
    ordering = ('-created_at',)

    def get_queryset(self):
        return Video.objects.all_viewable(self.request.user)

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        collection_key = self.request.query_params.get('collection')
        if collection_key:
            queryset = queryset.filter(collection__key=collection_key)
        return queryset

    @action(detail=True)
    def analytics(self, request, key=None):
        """get video analytics data"""
        # pylint: disable=unused-argument
        if 'throw' in request.GET:
            return HttpResponse(status=500)
        if 'mock' in request.GET:
            # This is not for unit testing.
            # Instead it is for integration testing w/ front-end code.
            # (test the full analytics system, but w/out querying google analytics)
            data = generate_mock_video_analytics_data(**{
                param: request.GET[param]
                for param in ['n', 'seed']
                if param in request.GET
            })
        else:
            video = self.get_object()
            data = get_video_analytics(video)
        return Response({'data': data})


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


@method_decorator(xframe_options_exempt, name='dispatch')
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


class LoginView(DjangoLoginView):
    """Login"""
    def get_context_data(self, **kwargs):  # pylint: disable=arguments-differ
        context = super().get_context_data(**kwargs)
        context["js_settings_json"] = json.dumps({
            **default_js_settings(self.request),
        })
        return context

    def get(self, request, *args, **kwargs):
        """ This is the Touchstone `login` page, so redirect if `next` is a URL parameter """
        if request.user.is_authenticated:
            next_redirect = request.GET.get('next')
            if next_redirect:
                return redirect(next_redirect)
            else:
                return redirect('/')
        return super().get(request, *args, **kwargs)


class MoiraListsForUser(APIView):
    """
    View for getting moira lists against given user.
    """
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAdminUser,)

    def get(self, request, username_or_email):
        """Get and return the list names"""

        email = username_or_email
        if '@' not in email:
            email = "{username}@mit.edu".format(username=username_or_email)

        try:
            user = User.objects.get(Q(username=username_or_email) | Q(email=email))
        except User.DoesNotExist:
            return Response(status.HTTP_404_NOT_FOUND)

        user_lists = query_moira_lists(user)
        return Response(data={'user_lists': user_lists})


class UsersForMoiraList(APIView):
    """
    View for getting users against give list name.
    """
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAdminUser,)

    def get(self, request, list_name):
        """Get and return the users"""
        return Response(data={'users': list_members(list_name)})
