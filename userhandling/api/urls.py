from django.urls import path

from . import views


urlpatterns = [
    path("token/", views.auth_token_api, name="auth_token"),
]
