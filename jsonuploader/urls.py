from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("uploader/", include("uploader.urls")),
    path("admin/", admin.site.urls),
]
