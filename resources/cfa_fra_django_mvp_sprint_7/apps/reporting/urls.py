from django.urls import path
from .views import GeneralLedgerView, JournalReportView, TrialBalanceView

app_name = "reporting"

urlpatterns = [
    path("journal/", JournalReportView.as_view(), name="journal"),
    path("general-ledger/", GeneralLedgerView.as_view(), name="general-ledger"),
    path("trial-balance/", TrialBalanceView.as_view(), name="trial-balance"),
]
