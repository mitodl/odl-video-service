"""odl_video URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.shortcuts import redirect
from django.urls import include, path, re_path

urlpatterns = [
    path(
        "admin/logout/",
        lambda request: redirect("/logout/", permanent=False),
        name="admin_logout",
    ),
    re_path(r"^admin/", admin.site.urls),
    path("", include("ui.urls")),
    path("", include("cloudsync.urls")),
    path("auth/", include("social_django.urls", namespace="social")),
    path("hijack/", include("hijack.urls", namespace="hijack")),
    path("api/", include("mitol.transcoding.urls")),
]

handler403 = "ui.views.permission_denied_403_view"
handler404 = "ui.views.page_not_found_404_view"
handler500 = "ui.views.error_500_view"
