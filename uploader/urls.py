from django.urls import path
from . import views

urlpatterns = [
    path("upload/", views.upload_health_data, name="upload_health_data"),
    path("emotion_input/", views.upload_emotion_json, name="upload_emotion_json"),
    path("data/", views.display_data, name="display_data"),
    path("data-emotion/", views.display_emotion_data, name="display_emotion_data"),
]
