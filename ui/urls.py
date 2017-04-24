from django.conf.urls import url, include
from rest_framework import routers
from ui import views

router = routers.DefaultRouter()
router.register(r'videos', views.VideoViewSet)

urlpatterns = [
    url(r'^$', views.index),
    url(r'^upload$', views.upload),
    url(r'^view$', views.view),
    url(r'^stream$', views.stream),
    url(r'^signed_url$', views.generate_signed_url),
    url(r'^api/', include(router.urls)),
]
