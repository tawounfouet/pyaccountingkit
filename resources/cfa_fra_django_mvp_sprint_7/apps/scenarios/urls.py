from django.urls import path
from .views import ScenarioListView

app_name = "scenarios"

urlpatterns = [
    path("", ScenarioListView.as_view(), name="list"),
]
