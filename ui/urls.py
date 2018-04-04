"""urls for ui"""
from django.conf import settings
from django.conf.urls import url, include
from django.contrib.auth.views import logout as django_logout_view
from rest_framework import routers
from ui import views

router = routers.DefaultRouter()
router.register(r'videos', views.VideoViewSet, base_name='video')
router.register(r'collections', views.CollectionViewSet, base_name='collection')
router.register(r'subtitles', views.VideoSubtitleViewSet, base_name='subtitle')

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^logout/$', django_logout_view, {'next_page': settings.LOGIN_URL}),

    url(r'^collections/(?P<collection_key>[0-9a-f]{32})?/?$', views.CollectionReactView.as_view(),
        name='collection-react-view'),

    url(r'^help/', views.HelpPageView.as_view(), name='help-react-view'),
    url(r'^terms/', views.TermsOfServicePageView.as_view(), name='terms-react-view'),

    url(r'^videos/(?P<video_key>[0-9a-f]{32})/$', views.VideoDetail.as_view(), name='video-detail'),
    url(r'^videos/(?P<video_key>[0-9a-f]{32})/embed/$', views.VideoEmbed.as_view(), name='video-embed'),

    url(r'^videos/(?P<video_key>\d+)(-.+)?/?$', views.TechTVDetail.as_view(), name='techtv-detail'),
    url(r'^videos/(?P<video_key>.+)/private/?$', views.TechTVPrivateDetail.as_view(), name='techtv-private'),
    url(r'^embeds/(?P<video_key>\d+)(-.+)?/?$', views.TechTVEmbed.as_view(), name='techtv-embed'),

    url(r'^transcode/', include('dj_elastictranscoder.urls')),
    url(r'^api/v0/upload_videos/$', views.UploadVideosFromDropbox.as_view(), name='upload-videos'),
    url(r'^api/v0/upload_subtitles/$', views.UploadVideoSubtitle.as_view(),
        name='upload-subtitles'),
    url(r'^api/v0/', include((router.urls, 'models-api'))),
]
