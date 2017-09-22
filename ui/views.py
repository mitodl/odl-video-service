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

import logging
from functools import wraps
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.shortcuts import resolve_url
from django.utils.decorators import available_attrs
from django.contrib.auth.decorators import urlparse
from urllib.parse import quote

log = logging.getLogger(__name__)
TEST_LOG_PREFIX = '*** 231 TEST ***'


def ovstest_user_passes_test(test_func, login_url=None, redirect_field_name=REDIRECT_FIELD_NAME):
    """
    Decorator for views that checks that the user passes the given test,
    redirecting to the log-in page if necessary. The test should be a callable
    that takes the user object and returns True if the user passes.
    """

    def decorator(view_func):
        @wraps(view_func, assigned=available_attrs(view_func))
        def _wrapped_view(request, *args, **kwargs):
            log.warning(
                '%s user (%s) passes test? [%s]' % (
                    TEST_LOG_PREFIX, request.user.username, test_func(request.user)
                )
            )
            if test_func(request.user):
                log.warning(
                    '%s login successful. URL: %s. Request meta:' %
                    (TEST_LOG_PREFIX, request.get_full_path())
                )
                for key, value in request.META.items():
                    log.warning('%s [%s]: %s' % (TEST_LOG_PREFIX, key, value))
                return view_func(request, *args, **kwargs)
            path = request.build_absolute_uri()
            resolved_login_url = resolve_url(login_url or settings.LOGIN_URL)
            # If the login url is the same scheme and net location then just
            # use the path as the "next" url.
            login_scheme, login_netloc = urlparse(resolved_login_url)[:2]
            current_scheme, current_netloc = urlparse(path)[:2]
            if ((not login_scheme or login_scheme == current_scheme) and
                    (not login_netloc or login_netloc == current_netloc)):
                path = request.get_full_path()
            from django.contrib.auth.views import redirect_to_login
            log.warning(
                '%s login_scheme: [%s], login_netloc: [%s], current_scheme: [%s], current_netloc: [%s]' % (
                    TEST_LOG_PREFIX, login_scheme, login_netloc, current_scheme, current_netloc
                )
            )
            log.warning(
                '%s redirecting to path [%s]; LOGIN_URL [%s]; resolved_login_url [%s]; redirect_field_name [%s]' % (
                    TEST_LOG_PREFIX, path, settings.LOGIN_URL, resolved_login_url, redirect_field_name
                )
            )
            return redirect_to_login(
                path, resolved_login_url, redirect_field_name)
        return _wrapped_view
    return decorator


def ovstest_login_required(func=None, redirect_field_name=REDIRECT_FIELD_NAME, login_url=None):
    """
    Decorator for views that checks that the user is logged in, redirecting
    to the log-in page if necessary.
    """
    actual_decorator = ovstest_user_passes_test(
        lambda u: u.is_authenticated,
        login_url=login_url,
        redirect_field_name=redirect_field_name
    )
    if func:
        return actual_decorator(func)
    return actual_decorator


def ovs_login_required(cls):
    return method_decorator(
        ovstest_login_required,
        name='dispatch'
    )(cls)


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


@ovs_login_required
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


@ovs_login_required
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


@ovs_login_required
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


@ovs_login_required
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
