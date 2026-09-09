from django.urls import path

from .views import (
    FECAccountMappingUpdateView,
    FECAutoMappingView,
    FECExecuteImportView,
    FECImportDetailView,
    FECImportListView,
    FECJournalMappingUpdateView,
    FECMappingView,
    FECParseView,
    FECUploadView,
)

app_name = "imports"

urlpatterns = [
    path("fec/", FECImportListView.as_view(), name="fec-list"),
    path("fec/new/", FECUploadView.as_view(), name="fec-upload"),
    path("fec/<uuid:pk>/", FECImportDetailView.as_view(), name="fec-detail"),
    path("fec/<uuid:pk>/parse/", FECParseView.as_view(), name="fec-parse"),
    path("fec/<uuid:pk>/mappings/", FECMappingView.as_view(), name="fec-mappings"),
    path(
        "fec/<uuid:pk>/mappings/auto/",
        FECAutoMappingView.as_view(),
        name="fec-auto-mapping",
    ),
    path(
        "fec/<uuid:pk>/mappings/accounts/<uuid:mapping_id>/",
        FECAccountMappingUpdateView.as_view(),
        name="fec-account-mapping-update",
    ),
    path(
        "fec/<uuid:pk>/mappings/journals/<uuid:mapping_id>/",
        FECJournalMappingUpdateView.as_view(),
        name="fec-journal-mapping-update",
    ),
    path(
        "fec/<uuid:pk>/execute/",
        FECExecuteImportView.as_view(),
        name="fec-execute",
    ),
]
