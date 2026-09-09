from django.urls import path

from .views import (
    AccountCreateView,
    AccountListView,
    AccountUpdateView,
    ChartCreateView,
    ChartDetailView,
    ChartListView,
    EntryCreateView,
    EntryDetailView,
    EntryLineFormView,
    EntryLineRemoveView,
    EntryListView,
    EntryPostView,
    EntryReverseView,
    EntryTotalsView,
    EntryUpdateView,
    EntryValidateView,
    JournalCreateView,
    JournalListView,
    JournalUpdateView,
)

app_name = "accounting"

urlpatterns = [
    path("charts/", ChartListView.as_view(), name="charts"),
    path("charts/new/", ChartCreateView.as_view(), name="chart-create"),
    path("charts/<uuid:pk>/", ChartDetailView.as_view(), name="chart-detail"),

    path("accounts/", AccountListView.as_view(), name="accounts"),
    path("accounts/new/", AccountCreateView.as_view(), name="account-create"),
    path("accounts/<uuid:pk>/edit/", AccountUpdateView.as_view(), name="account-update"),

    path("journals/", JournalListView.as_view(), name="journals"),
    path("journals/new/", JournalCreateView.as_view(), name="journal-create"),
    path("journals/<uuid:pk>/edit/", JournalUpdateView.as_view(), name="journal-update"),

    path("entries/", EntryListView.as_view(), name="entries"),
    path("entries/new/", EntryCreateView.as_view(), name="entry-create"),
    path("entries/line-form/", EntryLineFormView.as_view(), name="entry-line-form"),
    path(
        "entries/line-form/<int:index>/remove/",
        EntryLineRemoveView.as_view(),
        name="entry-line-remove",
    ),
    path("entries/totals/", EntryTotalsView.as_view(), name="entry-totals"),
    path("entries/<uuid:pk>/", EntryDetailView.as_view(), name="entry-detail"),
    path("entries/<uuid:pk>/edit/", EntryUpdateView.as_view(), name="entry-update"),
    path("entries/<uuid:pk>/validate/", EntryValidateView.as_view(), name="entry-validate"),
    path("entries/<uuid:pk>/post/", EntryPostView.as_view(), name="entry-post"),
    path("entries/<uuid:pk>/reverse/", EntryReverseView.as_view(), name="entry-reverse"),
]
