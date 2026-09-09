from decimal import Decimal

from django.db.models import (
    Case,
    DecimalField,
    ExpressionWrapper,
    F,
    Q,
    Sum,
    Value,
    When,
    Window,
)
from django.db.models.functions import Coalesce

from apps.accounting.models import Account, JournalEntry, JournalLine

from .types import TrialBalanceVariant


POSTED_STATUSES = [
    JournalEntry.Status.POSTED,
    JournalEntry.Status.REVERSED,
]

REPORT_DECIMAL = DecimalField(max_digits=30, decimal_places=4)


def allowed_entry_types(variant: str):
    if variant == TrialBalanceVariant.BEFORE_ADJUSTMENTS:
        return [
            JournalEntry.EntryType.OPENING,
            JournalEntry.EntryType.NORMAL,
            JournalEntry.EntryType.REVERSAL,
        ]

    if variant == TrialBalanceVariant.POST_CLOSING:
        return [
            JournalEntry.EntryType.OPENING,
            JournalEntry.EntryType.NORMAL,
            JournalEntry.EntryType.ADJUSTING,
            JournalEntry.EntryType.CLOSING,
            JournalEntry.EntryType.REVERSAL,
        ]

    return [
        JournalEntry.EntryType.OPENING,
        JournalEntry.EntryType.NORMAL,
        JournalEntry.EntryType.ADJUSTING,
        JournalEntry.EntryType.REVERSAL,
    ]


def posted_line_scope(
    *,
    organization,
    fiscal_year,
    variant=TrialBalanceVariant.ADJUSTED,
    end_date=None,
):
    qs = JournalLine.objects.filter(
        entry__organization=organization,
        entry__period__fiscal_year=fiscal_year,
        entry__status__in=POSTED_STATUSES,
        entry__entry_type__in=allowed_entry_types(variant),
    )

    if end_date:
        qs = qs.filter(entry__posting_date__lte=end_date)

    return qs


def journal_lines(
    *,
    organization,
    fiscal_year,
    start_date=None,
    end_date=None,
    journal=None,
    entry_type=None,
    query="",
):
    qs = (
        JournalLine.objects.filter(
            entry__organization=organization,
            entry__period__fiscal_year=fiscal_year,
            entry__status__in=POSTED_STATUSES,
        )
        .select_related(
            "entry",
            "entry__journal",
            "entry__period",
            "entry__period__fiscal_year",
            "account",
            "counterparty",
            "cost_center",
        )
        .order_by(
            "entry__posting_date",
            "entry__journal__code",
            "entry__entry_number",
            "line_number",
        )
    )

    if start_date:
        qs = qs.filter(entry__posting_date__gte=start_date)
    if end_date:
        qs = qs.filter(entry__posting_date__lte=end_date)
    if journal:
        qs = qs.filter(entry__journal=journal)
    if entry_type:
        qs = qs.filter(entry__entry_type=entry_type)
    if query:
        qs = qs.filter(
            Q(entry__entry_number__icontains=query)
            | Q(entry__reference__icontains=query)
            | Q(entry__description__icontains=query)
            | Q(description__icontains=query)
            | Q(account__code__icontains=query)
            | Q(account__name__icontains=query)
        )

    movement = ExpressionWrapper(
        F("debit") - F("credit"),
        output_field=REPORT_DECIMAL,
    )

    return qs.annotate(
        signed_movement=movement,
    )


def journal_totals(qs):
    return qs.aggregate(
        total_debit=Coalesce(
            Sum("debit"),
            Value(Decimal("0")),
            output_field=REPORT_DECIMAL,
        ),
        total_credit=Coalesce(
            Sum("credit"),
            Value(Decimal("0")),
            output_field=REPORT_DECIMAL,
        ),
    )


def ledger_lines(
    *,
    organization,
    fiscal_year,
    account,
    start_date=None,
    end_date=None,
    variant=TrialBalanceVariant.ADJUSTED,
    query="",
):
    scope = posted_line_scope(
        organization=organization,
        fiscal_year=fiscal_year,
        variant=variant,
        end_date=end_date,
    ).filter(account=account)

    opening_scope = scope
    if start_date:
        opening_scope = opening_scope.filter(entry__posting_date__lt=start_date)
    else:
        opening_scope = opening_scope.none()

    opening = opening_scope.aggregate(
        debit=Coalesce(
            Sum("debit"),
            Value(Decimal("0")),
            output_field=REPORT_DECIMAL,
        ),
        credit=Coalesce(
            Sum("credit"),
            Value(Decimal("0")),
            output_field=REPORT_DECIMAL,
        ),
    )
    opening_signed = opening["debit"] - opening["credit"]

    period_scope = scope
    if start_date:
        period_scope = period_scope.filter(entry__posting_date__gte=start_date)

    if query:
        period_scope = period_scope.filter(
            Q(entry__entry_number__icontains=query)
            | Q(entry__reference__icontains=query)
            | Q(entry__description__icontains=query)
            | Q(description__icontains=query)
        )

    movement_expr = ExpressionWrapper(
        F("debit") - F("credit"),
        output_field=REPORT_DECIMAL,
    )
    running_expr = Window(
        expression=Sum(
            ExpressionWrapper(
                F("debit") - F("credit"),
                output_field=REPORT_DECIMAL,
            )
        ),
        partition_by=[F("account_id")],
        order_by=[
            F("entry__posting_date").asc(),
            F("entry__created_at").asc(),
            F("entry_id").asc(),
            F("line_number").asc(),
        ],
    )

    qs = (
        period_scope.select_related(
            "entry",
            "entry__journal",
            "entry__period",
            "account",
            "counterparty",
            "cost_center",
        )
        .annotate(
            signed_movement=movement_expr,
            period_running_signed=running_expr,
        )
        .annotate(
            running_signed_balance=ExpressionWrapper(
                Value(opening_signed, output_field=REPORT_DECIMAL)
                + F("period_running_signed"),
                output_field=REPORT_DECIMAL,
            )
        )
        .order_by(
            "entry__posting_date",
            "entry__created_at",
            "entry_id",
            "line_number",
        )
    )

    period_totals = period_scope.aggregate(
        debit=Coalesce(
            Sum("debit"),
            Value(Decimal("0")),
            output_field=REPORT_DECIMAL,
        ),
        credit=Coalesce(
            Sum("credit"),
            Value(Decimal("0")),
            output_field=REPORT_DECIMAL,
        ),
    )
    closing_signed = (
        opening_signed
        + period_totals["debit"]
        - period_totals["credit"]
    )

    return {
        "queryset": qs,
        "opening_debit": opening["debit"],
        "opening_credit": opening["credit"],
        "opening_signed": opening_signed,
        "period_debit": period_totals["debit"],
        "period_credit": period_totals["credit"],
        "closing_signed": closing_signed,
    }


def trial_balance_rows(
    *,
    organization,
    fiscal_year,
    as_of_date,
    variant=TrialBalanceVariant.ADJUSTED,
    query="",
    include_zero=False,
):
    line_filter = Q(
        journal_lines__entry__organization=organization,
        journal_lines__entry__period__fiscal_year=fiscal_year,
        journal_lines__entry__status__in=POSTED_STATUSES,
        journal_lines__entry__entry_type__in=allowed_entry_types(variant),
        journal_lines__entry__posting_date__lte=as_of_date,
    )

    accounts = Account.objects.filter(
        organization=organization,
    ).select_related("chart")

    if query:
        accounts = accounts.filter(
            Q(code__icontains=query)
            | Q(name__icontains=query)
        )

    total_debit_expr = Coalesce(
        Sum(
            "journal_lines__debit",
            filter=line_filter,
        ),
        Value(Decimal("0")),
        output_field=REPORT_DECIMAL,
    )
    total_credit_expr = Coalesce(
        Sum(
            "journal_lines__credit",
            filter=line_filter,
        ),
        Value(Decimal("0")),
        output_field=REPORT_DECIMAL,
    )

    qs = (
        accounts.annotate(
            total_debit=total_debit_expr,
            total_credit=total_credit_expr,
        )
        .annotate(
            signed_balance=ExpressionWrapper(
                F("total_debit") - F("total_credit"),
                output_field=REPORT_DECIMAL,
            ),
        )
        .annotate(
            debit_balance=Case(
                When(
                    signed_balance__gt=0,
                    then=F("signed_balance"),
                ),
                default=Value(Decimal("0")),
                output_field=REPORT_DECIMAL,
            ),
            credit_balance=Case(
                When(
                    signed_balance__lt=0,
                    then=ExpressionWrapper(
                        Value(Decimal("0")) - F("signed_balance"),
                        output_field=REPORT_DECIMAL,
                    ),
                ),
                default=Value(Decimal("0")),
                output_field=REPORT_DECIMAL,
            ),
        )
        .order_by("code")
    )

    if not include_zero:
        qs = qs.exclude(signed_balance=Decimal("0"))

    return qs


def trial_balance_totals(qs):
    return qs.aggregate(
        movement_debit=Coalesce(
            Sum("total_debit"),
            Value(Decimal("0")),
            output_field=REPORT_DECIMAL,
        ),
        movement_credit=Coalesce(
            Sum("total_credit"),
            Value(Decimal("0")),
            output_field=REPORT_DECIMAL,
        ),
        balance_debit=Coalesce(
            Sum("debit_balance"),
            Value(Decimal("0")),
            output_field=REPORT_DECIMAL,
        ),
        balance_credit=Coalesce(
            Sum("credit_balance"),
            Value(Decimal("0")),
            output_field=REPORT_DECIMAL,
        ),
    )
