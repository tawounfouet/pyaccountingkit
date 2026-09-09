from django.urls import path

from .regulatory_views import (
    RegulatoryAutoMapView,
    RegulatoryExportView,
    RegulatoryMappingUpdateView,
    RegulatoryMappingView,
    RegulatoryProfileCreateView,
    RegulatoryProfileDetailView,
    RegulatoryProfileListView,
)

from .views import (
    BalanceSheetView,
    CashFlowStatementView,
    FinancialRatiosView,
    FinancialStatementConfigurationView,
    FinancialStatementsHomeView,
    IncomeStatementView,
    StatementAutoMapView,
    StatementLineDetailView,
    StatementMappingUpdateView,
    StatementMappingView,
)

app_name = "financial_statements"

urlpatterns = [

    path("regulatory/", RegulatoryProfileListView.as_view(), name="regulatory-list"),
    path("regulatory/new/", RegulatoryProfileCreateView.as_view(), name="regulatory-create"),
    path(
        "regulatory/<uuid:pk>/",
        RegulatoryProfileDetailView.as_view(),
        name="regulatory-detail",
    ),
    path(
        "regulatory/<uuid:pk>/mappings/",
        RegulatoryMappingView.as_view(),
        name="regulatory-mappings",
    ),
    path(
        "regulatory/<uuid:pk>/mappings/auto/",
        RegulatoryAutoMapView.as_view(),
        name="regulatory-auto-map",
    ),
    path(
        "regulatory/<uuid:pk>/mappings/<uuid:source_line_id>/",
        RegulatoryMappingUpdateView.as_view(),
        name="regulatory-mapping-update",
    ),
    path(
        "regulatory/<uuid:pk>/export/",
        RegulatoryExportView.as_view(),
        name="regulatory-export",
    ),
    path("", FinancialStatementsHomeView.as_view(), name="index"),
    path("configuration/", FinancialStatementConfigurationView.as_view(), name="configuration"),
    path("mappings/", StatementMappingView.as_view(), name="mappings"),
    path("mappings/auto/", StatementAutoMapView.as_view(), name="auto-map"),
    path(
        "mappings/accounts/<uuid:account_id>/",
        StatementMappingUpdateView.as_view(),
        name="mapping-update",
    ),
    path("income-statement/", IncomeStatementView.as_view(), name="income-statement"),
    path("balance-sheet/", BalanceSheetView.as_view(), name="balance-sheet"),
    path("cash-flow/", CashFlowStatementView.as_view(), name="cash-flow"),
    path("ratios/", FinancialRatiosView.as_view(), name="ratios"),
    path(
        "lines/<uuid:line_id>/",
        StatementLineDetailView.as_view(),
        name="line-detail",
    ),
]
