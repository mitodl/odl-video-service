from django.conf.urls import url
from ui import views

urlpatterns = [
    url(r'^$', views.index),
    url(r'^stream$', views.stream),
]
