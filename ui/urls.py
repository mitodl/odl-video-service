"""urls for ui"""
from django.conf.urls import url, include
from rest_framework import routers
from ui import views

router = routers.DefaultRouter()
router.register(r'videos', views.VideoViewSet, base_name='video')
router.register(r'collections', views.CollectionViewSet, base_name='collection')

urlpatterns = [
    url(r'^$', views.Index.as_view(), name='index'),
    url(r'^register/$', views.register, name='register'),
    url(r'^login/$', views.ui_login, name='login'),

    url(r'^collections/', views.CollectionReactView.as_view(), name='collection-react-view'),
    url(r'^collection_form/$', views.CollectionFormView.as_view(), name='collection-form-view'),
    url(r'^collection_upload/(?P<collection_key>[0-9a-f]+)$', views.Upload.as_view(), name='upload'),

    url(r'^videos/(?P<video_key>[0-9a-f]+)/$', views.VideoDetail.as_view(), name='video-detail'),
    url(r'^videos/(?P<video_key>[0-9a-f]+)/embed/$', views.VideoEmbed.as_view(), name='video-embed'),
    url(r'^videos/(?P<video_key>[0-9a-f]+)/embed/mosaic.html$', views.MosaicView.as_view(), name='video-mosaic'),
    url(r'^transcode/', include('dj_elastictranscoder.urls')),
    url(r'^api/v0/upload_videos/$', views.UploadVideosFromDropbox.as_view(), name='upload-videos'),
    url(r'^api/v0/', include(router.urls, namespace='models-api')),
]
