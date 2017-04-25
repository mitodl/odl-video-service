from django.conf.urls import url, include
from rest_framework import routers
from ui import views

router = routers.DefaultRouter()
router.register(r'videos', views.VideoViewSet)

urlpatterns = [
    url(r'^$', views.Index.as_view(), name='index'),
    url(r'^register/$', views.register, name='register'),
    url(r'^upload/$', views.Upload.as_view(), name='upload'),
    url(r'^videos/$', views.VideoList.as_view(), name='video-list'),
    url(r'^videos/(?P<pk>\d+)$', views.VideoDetail.as_view(), name='video-detail'),
    url(r'^stream/$', views.stream),
    url(r'^api/', include(router.urls, namespace='api')),
]
