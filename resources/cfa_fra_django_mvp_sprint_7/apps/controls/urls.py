from django.urls import path
from .views import ControlDashboardView

app_name = "controls"

urlpatterns = [
    path("", ControlDashboardView.as_view(), name="index"),
]
