from django.contrib import admin
from django.urls import include, path
from . import views

urlpatterns = [
    path("", views.display_home, name="display_home"),
    path("uploader/", include("uploader.urls")),
    path("admin/", admin.site.urls),
]
