"""urls for ui"""
from django.conf.urls import url, include
from rest_framework import routers
from ui import views

router = routers.DefaultRouter()
router.register(r'videos', views.VideoViewSet)

urlpatterns = [
    url(r'^$', views.Index.as_view(), name='index'),
    url(r'^register/$', views.register, name='register'),
    url(r'^login/$', views.ui_login, name='login'),
    url(r'^upload/$', views.Upload.as_view(), name='upload'),
    url(r'^videos/$', views.VideoList.as_view(), name='video-list'),
    url(r'^videos/(?P<pk>\d+)/$', views.VideoDetail.as_view(), name='video-detail'),
    url(r'^videos/(?P<pk>\d+)/uswitch/$', views.VideoUswitch.as_view(), name='video-uswitch'),
    url(r'^videos/\d+/uswitch/mosaic.html$', views.MosaicView.as_view(), name='video-mosaic'),
    url(r'^transcode/', include('dj_elastictranscoder.urls')),
    url(r'^api/v0/upload_videos/$', views.UploadVideosFromDropbox.as_view(), name='upload-videos'),
    url(r'^api/v0/', include(router.urls, namespace='video-api')),
]
