from django.urls import path

from .views import (
    ExportDetailView,
    ExportDownloadView,
    ExportListView,
)

app_name = "exports"

urlpatterns = [
    path("", ExportListView.as_view(), name="list"),
    path("<uuid:pk>/", ExportDetailView.as_view(), name="detail"),
    path("<uuid:pk>/download/", ExportDownloadView.as_view(), name="download"),
]
