from django.urls import path
from .views import ClosingView

app_name = "closing"

urlpatterns = [
    path("", ClosingView.as_view(), name="index"),
]
