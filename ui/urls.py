from django.conf.urls import url
from ui import views

urlpatterns = [
    url(r'^$', views.index),
    url(r'^upload$', views.upload),
    url(r'^view$', views.view),
    url(r'^stream$', views.stream),
    url(r'^signed_url$', views.generate_signed_url),
]
