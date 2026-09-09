from django.db.models import Count, Q

from .models import Account, ChartOfAccounts, Journal, JournalEntry, JournalLine


def charts_for_organization(*, organization):
    return (
        ChartOfAccounts.objects.filter(organization=organization)
        .annotate(account_count=Count("accounts"))
        .order_by("-is_default", "code")
    )


def accounts_for_organization(
    *,
    organization,
    query="",
    chart_id=None,
    account_type=None,
    active=None,
):
    qs = (
        Account.objects.filter(organization=organization)
        .select_related("chart", "parent")
        .order_by("code")
    )

    if query:
        qs = qs.filter(Q(code__icontains=query) | Q(name__icontains=query))
    if chart_id:
        qs = qs.filter(chart_id=chart_id)
    if account_type:
        qs = qs.filter(account_type=account_type)
    if active in {"1", "0"}:
        qs = qs.filter(is_active=(active == "1"))

    return qs


def journals_for_organization(*, organization, query="", journal_type=None, active=None):
    qs = Journal.objects.filter(organization=organization).order_by("code")
    if query:
        qs = qs.filter(Q(code__icontains=query) | Q(name__icontains=query))
    if journal_type:
        qs = qs.filter(journal_type=journal_type)
    if active in {"1", "0"}:
        qs = qs.filter(is_active=(active == "1"))
    return qs


def journal_entries_for_organization(
    *,
    organization,
    query="",
    journal_id=None,
    status=None,
):
    qs = (
        JournalEntry.objects.filter(organization=organization)
        .select_related(
            "journal",
            "period",
            "period__fiscal_year",
            "created_by",
            "posted_by",
        )
        .prefetch_related("lines__account")
        .order_by("-posting_date", "-created_at")
    )

    if query:
        qs = qs.filter(
            Q(entry_number__icontains=query)
            | Q(description__icontains=query)
            | Q(reference__icontains=query)
        )
    if journal_id:
        qs = qs.filter(journal_id=journal_id)
    if status:
        qs = qs.filter(status=status)

    return qs


def posted_lines(*, organization):
    return (
        JournalLine.objects.filter(
            entry__organization=organization,
            entry__status__in=[
                JournalEntry.Status.POSTED,
                JournalEntry.Status.REVERSED,
            ],
        )
        .select_related("entry", "entry__journal", "account")
        .order_by("entry__posting_date", "entry__entry_number", "line_number")
    )
