from django.urls import path
from .views import csrf_token_view
from .views import TestConnection

urlpatterns = [
    path("test-connection/", TestConnection.as_view(), name="test_connection"),
    path("csrftoken/", csrf_token_view, name="csrftoken"),
]
