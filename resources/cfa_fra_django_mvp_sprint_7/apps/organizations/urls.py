from django.urls import path

from .views import (
    FiscalYearCreateView,
    OrganizationCreateView,
    OrganizationDetailView,
    OrganizationListView,
    SwitchOrganizationView,
)

app_name = "organizations"

urlpatterns = [
    path("", OrganizationListView.as_view(), name="list"),
    path("new/", OrganizationCreateView.as_view(), name="create"),
    path("switch/", SwitchOrganizationView.as_view(), name="switch"),
    path("<uuid:pk>/", OrganizationDetailView.as_view(), name="detail"),
    path(
        "<uuid:organization_id>/fiscal-years/new/",
        FiscalYearCreateView.as_view(),
        name="fiscal-year-create",
    ),
]
