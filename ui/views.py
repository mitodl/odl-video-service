"""Views for ui app"""
import json

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.views import login as login_view
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
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
from rest_framework.response import Response
from rest_framework.views import APIView

from ui import (
    api,
    serializers,
    forms,
)
from ui.encodings import EncodingNames
from ui.templatetags.render_bundle import public_path
from ui.models import (
    Collection,
    Video,
    VideoFile,
)
from ui.permissions import IsCollectionOwner, CanUploadToCollection


def default_js_settings(request):
    """Default JS settings for views"""
    return json.dumps({
        "gaTrackingID": settings.GA_TRACKING_ID,
        "public_path": public_path(request),
    })


class Index(TemplateView):
    """Index"""
    template_name = "ui/index.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated():
            return HttpResponseRedirect(reverse('collection-list'))
        return super(Index, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["login_form"] = AuthenticationForm()
        context["register_form"] = forms.UserCreationForm()
        context["js_settings_json"] = json.dumps(default_js_settings(self.request))
        return context


@method_decorator(login_required, name='dispatch')
class CollectionList(TemplateView):
    """List of collections"""
    template_name = "ui/collection_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['collection_list'] = Collection.for_owner(self.request.user)
        context['form'] = forms.CollectionForm(initial={'owner': self.request.user.id})
        context["js_settings_json"] = json.dumps(default_js_settings(self.request))
        return context


@method_decorator(login_required, name='dispatch')
class CollectionDetail(TemplateView):
    """Details of a collection"""
    template_name = "ui/collection_detail.html"

    def get_context_data(self, collection_key, **kwargs):  # pylint: disable=arguments-differ
        context = super().get_context_data(**kwargs)

        collection = get_object_or_404(Collection, key=collection_key)
        video_list = Video.objects.filter(collection=collection)

        default_settings = json.loads(default_js_settings(self.request))
        context["collection"] = collection
        context["video_list"] = video_list
        context["js_settings_json"] = json.dumps(default_settings)
        return context


@method_decorator(login_required, name='dispatch')
class Upload(TemplateView):
    """Upload"""
    template_name = "ui/upload.html"

    def get_context_data(self, collection_key, **kwargs):  # pylint: disable=arguments-differ
        context = super().get_context_data(**kwargs)

        collection = get_object_or_404(Collection, key=collection_key)
        context["collection"] = collection
        context["dropbox_key"] = settings.DROPBOX_KEY
        context["js_settings_json"] = json.dumps(default_js_settings(self.request))
        return context


@method_decorator(login_required, name='dispatch')
class VideoDetail(TemplateView):
    """
    Details of a video
    """
    template_name = "ui/video_detail.html"

    def get_context_data(self, video_key, **kwargs):  # pylint: disable=arguments-differ
        context = super().get_context_data(**kwargs)
        default_settings = json.loads(default_js_settings(self.request))
        video = get_object_or_404(Video, key=video_key)
        context['video'] = video
        context['form'] = forms.VideoForm(instance=video)
        try:
            videofile = video.videofile_set.get(encoding=EncodingNames.HLS)
            default_settings['videofile'] = videofile.cloudfront_url
        except VideoFile.DoesNotExist:
            videofile = None
            default_settings['videofile'] = None

        context['videofile'] = videofile
        context["js_settings_json"] = json.dumps(default_settings)
        return context


@method_decorator(login_required, name='dispatch')
class VideoUswitch(TemplateView):
    """Display video using USwitch"""
    model = Video
    template_name = 'ui/video_uswitch.html'

    def get_context_data(self, video_key, **kwargs):  # pylint: disable=arguments-differ
        context = super().get_context_data(**kwargs)
        default_settings = json.loads(default_js_settings(self.request))
        video = get_object_or_404(Video, key=video_key)
        videofile = video.videofile_set.get(encoding=EncodingNames.HLS)
        default_settings['videofile'] = {
            "src": videofile.cloudfront_url,
            "title": video.title,
            "description": video.description,
        }
        context['uswitchPlayerURL'] = settings.USWITCH_URL
        default_settings["uswitchPlayerURL"] = settings.USWITCH_URL
        context['videofile'] = videofile
        context["js_settings_json"] = json.dumps(default_settings)
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
        CanUploadToCollection,
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
        IsCollectionOwner,
    )

    def get_queryset(self):
        """
        Custom get_queryset to filter only the collections for the current owner.
        NOTE: The Collection.for_owner needs to change when we introduce support for Moira Lists
        """
        if self.request.user.is_superuser:
            return Collection.objects.all()
        return Collection.for_owner(self.request.user)

    def get_serializer_class(self):
        """
        Custom get_serializer_class to handle the different serializer class
        for the list method
        """
        # the collection key is not None in the detail view
        if self.kwargs.get('key') is not None:
            return serializers.CollectionSerializer
        return serializers.CollectionListSerializer

    def create(self, request, *args, **kwargs):
        """
        Customized create object method to check that the user can only create
        collections for herself.
        """
        owner_id = request.data.get('owner')
        if not request.user.is_superuser and (owner_id is None or int(owner_id) != request.user.id):
            return Response(
                {
                    'error': 'You do not have permissions to perform this action'
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().create(request, *args, **kwargs)


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
    context["js_settings_json"] = default_js_settings(request)
    return render(request, "registration/register.html", context)


def ui_login(request, *args, **kwargs):
    """login"""
    extra_context = {
        "js_settings_json": default_js_settings(request)
    }
    return login_view(request, *args, extra_context=extra_context, **kwargs)
