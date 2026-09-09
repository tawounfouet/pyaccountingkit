from django.urls import path
from .views import FrameworkAccountListView

app_name = "referentials"

urlpatterns = [
    path("", FrameworkAccountListView.as_view(), name="accounts"),
]
