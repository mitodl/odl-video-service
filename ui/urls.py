"""urls for ui"""

from django.conf import settings
from django.contrib.auth.views import LogoutView
from django.urls import include, path, re_path
from rest_framework import routers

from ui import views

router = routers.DefaultRouter()
router.register(r"videos", views.VideoViewSet, basename="video")
router.register(r"collections", views.CollectionViewSet, basename="collection")
router.register(r"subtitles", views.VideoSubtitleViewSet, basename="subtitle")

urlpatterns = [
    path("", views.index, name="index"),
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(next_page=settings.LOGIN_URL), name="logout"),
    re_path(
        r"^collections/(?P<collection_key>[0-9a-f]{32})?/?$",
        views.CollectionReactView.as_view(),
        name="collection-react-view",
    ),
    re_path(
        r"^collections/[0-9A-Za-z\-_\:]+/videos/(?P<video_key>\d+)(-.+)?/?$",
        views.TechTVDetail.as_view(),
        name="techtv-collection-detail",
    ),
    re_path(r"^help/", views.HelpPageView.as_view(), name="help-react-view"),
    re_path(
        r"^terms/", views.TermsOfServicePageView.as_view(), name="terms-react-view"
    ),
    re_path(
        r"^videos/(?P<video_key>[0-9a-f]{32})/$",
        views.VideoDetail.as_view(),
        name="video-detail",
    ),
    re_path(
        r"^videos/(?P<video_key>[0-9a-f]{32})/embed/$",
        views.VideoEmbed.as_view(),
        name="video-embed",
    ),
    re_path(
        r"^videos/(?P<video_key>[0-9a-f]{32})/download",
        views.VideoDownload.as_view(),
        name="video-download",
    ),
    re_path(
        r"^videos/(?P<video_key>\d+)(-.+)?/?$",
        views.TechTVDetail.as_view(),
        name="techtv-detail",
    ),
    re_path(
        r"^videos/(?P<video_key>.+)/private/?$",
        views.TechTVPrivateDetail.as_view(),
        name="techtv-private",
    ),
    re_path(
        r"^videos/(?P<video_key>\d+)(-.+)?/download",
        views.TechTVDownload.as_view(),
        name="techtv-download",
    ),
    re_path(
        r"^embeds/(?P<video_key>\d+)(-.+)?/?$",
        views.TechTVEmbed.as_view(),
        name="techtv-embed",
    ),
    path(
        "api/v0/upload_videos/",
        views.UploadVideosFromDropbox.as_view(),
        name="upload-videos",
    ),
    path(
        "api/v0/upload_subtitles/",
        views.UploadVideoSubtitle.as_view(),
        name="upload-subtitles",
    ),
    path("api/v0/", include((router.urls, "models-api"))),
    re_path(
        r"^api/v0/moira/user/(?P<username_or_email>[-\w]+$|.*@.*)$",
        views.MoiraListsForUser.as_view(),
        name="member-lists",
    ),
    re_path(
        r"^api/v0/moira/list/(?P<list_name>[-_\.\w]+)$",
        views.UsersForMoiraList.as_view(),
        name="list-members",
    ),
]
