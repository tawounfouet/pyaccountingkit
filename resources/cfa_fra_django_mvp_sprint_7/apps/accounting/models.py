from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from apps.common.models import TimeStampedUUIDModel


class ChartOfAccounts(TimeStampedUUIDModel):
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="charts_of_accounts",
    )
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=255)
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "code"],
                name="uniq_chart_org_code",
            )
        ]

    def __str__(self):
        return f"{self.code} — {self.name}"


class Account(TimeStampedUUIDModel):
    class AccountType(models.TextChoices):
        ASSET = "ASSET", "Actif"
        LIABILITY = "LIABILITY", "Passif"
        EQUITY = "EQUITY", "Capitaux propres"
        REVENUE = "REVENUE", "Produit"
        EXPENSE = "EXPENSE", "Charge"
        OTHER = "OTHER", "Autre"

    class NormalBalance(models.TextChoices):
        DEBIT = "DEBIT", "Débit"
        CREDIT = "CREDIT", "Crédit"

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="accounts",
    )
    chart = models.ForeignKey(
        ChartOfAccounts,
        on_delete=models.CASCADE,
        related_name="accounts",
    )
    code = models.CharField(max_length=32)
    name = models.CharField(max_length=255)
    account_type = models.CharField(
        max_length=20,
        choices=AccountType.choices,
        default=AccountType.OTHER,
    )
    normal_balance = models.CharField(
        max_length=10,
        choices=NormalBalance.choices,
        default=NormalBalance.DEBIT,
    )
    current_noncurrent = models.CharField(max_length=30, blank=True)
    parent = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="children",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]
        indexes = [
            models.Index(fields=["organization", "code"], name="acct_org_code_idx"),
            models.Index(fields=["organization", "account_type"], name="acct_org_type_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "chart", "code"],
                name="uniq_account_org_chart_code",
            )
        ]

    def clean(self):
        super().clean()
        errors = {}

        if self.chart_id and self.organization_id:
            if self.chart.organization_id != self.organization_id:
                errors["chart"] = "Le plan comptable doit appartenir à la même organisation."

        if self.parent_id:
            if self.parent_id == self.id:
                errors["parent"] = "Un compte ne peut pas être son propre parent."
            elif self.organization_id and self.parent.organization_id != self.organization_id:
                errors["parent"] = "Le compte parent doit appartenir à la même organisation."
            elif self.chart_id and self.parent.chart_id != self.chart_id:
                errors["parent"] = "Le compte parent doit appartenir au même plan comptable."

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.code} — {self.name}"


class Journal(TimeStampedUUIDModel):
    class JournalType(models.TextChoices):
        PURCHASE = "PURCHASE", "Achats"
        SALES = "SALES", "Ventes"
        BANK = "BANK", "Banque"
        CASH = "CASH", "Caisse"
        PAYROLL = "PAYROLL", "Paie"
        TAX = "TAX", "Fiscal"
        GENERAL = "GENERAL", "Opérations diverses"
        OPENING = "OPENING", "À-nouveaux"

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="journals",
    )
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=255)
    journal_type = models.CharField(
        max_length=20,
        choices=JournalType.choices,
        default=JournalType.GENERAL,
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "code"],
                name="uniq_journal_org_code",
            )
        ]

    def __str__(self):
        return f"{self.code} — {self.name}"


class Counterparty(TimeStampedUUIDModel):
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="counterparties",
    )
    code = models.CharField(max_length=100)
    name = models.CharField(max_length=255)
    kind = models.CharField(max_length=50, blank=True)
    tax_identifier = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "code"],
                name="uniq_counterparty_org_code",
            )
        ]

    def __str__(self):
        return f"{self.code} — {self.name}"


class CostCenter(TimeStampedUUIDModel):
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="cost_centers",
    )
    code = models.CharField(max_length=100)
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "code"],
                name="uniq_cost_center_org_code",
            )
        ]

    def __str__(self):
        return f"{self.code} — {self.name}"


class JournalEntry(TimeStampedUUIDModel):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Brouillon"
        VALIDATED = "VALIDATED", "Validée"
        POSTED = "POSTED", "Postée"
        REVERSED = "REVERSED", "Extournée"

    class EntryType(models.TextChoices):
        OPENING = "OPENING", "À-nouveaux"
        NORMAL = "NORMAL", "Normale"
        ADJUSTING = "ADJUSTING", "Ajustement"
        CLOSING = "CLOSING", "Clôture"
        REVERSAL = "REVERSAL", "Extourne"

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="journal_entries",
    )
    journal = models.ForeignKey(
        Journal,
        on_delete=models.PROTECT,
        related_name="entries",
    )
    period = models.ForeignKey(
        "organizations.AccountingPeriod",
        on_delete=models.PROTECT,
        related_name="journal_entries",
    )
    entry_number = models.CharField(max_length=150)
    posting_date = models.DateField()
    description = models.TextField()
    reference = models.CharField(max_length=255, blank=True)
    entry_type = models.CharField(
        max_length=20,
        choices=EntryType.choices,
        default=EntryType.NORMAL,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    source = models.CharField(max_length=50, default="MANUAL")
    source_reference = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_journal_entries",
    )
    validated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="validated_journal_entries",
    )
    validated_at = models.DateTimeField(null=True, blank=True)
    posted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="posted_journal_entries",
    )
    posted_at = models.DateTimeField(null=True, blank=True)
    reversal_of = models.OneToOneField(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="reversal_entry",
    )

    class Meta:
        ordering = ["-posting_date", "-created_at"]
        indexes = [
            models.Index(fields=["organization", "posting_date"], name="entry_org_date_idx"),
            models.Index(
                fields=["organization", "status", "posting_date"],
                name="entry_org_status_date_idx",
            ),
            models.Index(
                fields=["organization", "status", "entry_type", "posting_date"],
                name="entry_report_scope_idx",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "journal", "entry_number", "posting_date"],
                name="uniq_entry_org_journal_number_date",
            )
        ]

    def clean(self):
        super().clean()
        errors = {}

        if self.journal_id and self.organization_id:
            if self.journal.organization_id != self.organization_id:
                errors["journal"] = "Le journal doit appartenir à la même organisation."

        if self.period_id and self.organization_id:
            if self.period.fiscal_year.organization_id != self.organization_id:
                errors["period"] = "La période doit appartenir à la même organisation."

        if self.period_id and self.posting_date:
            if not (self.period.start_date <= self.posting_date <= self.period.end_date):
                errors["posting_date"] = "La date doit appartenir à la période comptable sélectionnée."

        if errors:
            raise ValidationError(errors)

    @property
    def total_debit(self):
        return sum((line.debit for line in self.lines.all()), Decimal("0"))

    @property
    def total_credit(self):
        return sum((line.credit for line in self.lines.all()), Decimal("0"))

    @property
    def difference(self):
        return self.total_debit - self.total_credit

    @property
    def is_balanced(self):
        return self.difference == Decimal("0")

    def __str__(self):
        return f"{self.entry_number} — {self.description[:60]}"


class JournalLine(TimeStampedUUIDModel):
    class CashFlowTag(models.TextChoices):
        OPERATING = "OPERATING", "Exploitation"
        INVESTING = "INVESTING", "Investissement"
        FINANCING = "FINANCING", "Financement"
        TRANSFER = "TRANSFER", "Transfert"
        OPENING = "OPENING", "Ouverture"
        NONE = "", "Non classé"

    entry = models.ForeignKey(
        JournalEntry,
        on_delete=models.CASCADE,
        related_name="lines",
    )
    line_number = models.PositiveIntegerField()
    account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name="journal_lines",
    )
    description = models.CharField(max_length=500, blank=True)
    debit = models.DecimalField(max_digits=24, decimal_places=4, default=Decimal("0"))
    credit = models.DecimalField(max_digits=24, decimal_places=4, default=Decimal("0"))
    counterparty = models.ForeignKey(
        Counterparty,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="journal_lines",
    )
    cost_center = models.ForeignKey(
        CostCenter,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="journal_lines",
    )
    cash_flow_tag = models.CharField(
        max_length=20,
        choices=CashFlowTag.choices,
        blank=True,
    )
    source_line_number = models.PositiveIntegerField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["entry", "line_number"]
        indexes = [
            models.Index(fields=["account", "entry"], name="line_account_entry_idx"),
            models.Index(
                fields=["entry", "account", "line_number"],
                name="line_entry_account_idx",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["entry", "line_number"],
                name="uniq_entry_line_number",
            ),
            models.CheckConstraint(
                condition=Q(debit__gte=0) & Q(credit__gte=0),
                name="journal_line_nonnegative_amounts",
            ),
            models.CheckConstraint(
                condition=~(Q(debit__gt=0) & Q(credit__gt=0)),
                name="journal_line_not_both_debit_credit",
            ),
            models.CheckConstraint(
                condition=Q(debit__gt=0) | Q(credit__gt=0),
                name="journal_line_one_side_positive",
            ),
        ]

    def clean(self):
        super().clean()
        errors = {}

        if self.account_id and self.entry_id:
            if self.account.organization_id != self.entry.organization_id:
                errors["account"] = "Le compte et l'écriture doivent appartenir à la même organisation."

        if self.counterparty_id and self.entry_id:
            if self.counterparty.organization_id != self.entry.organization_id:
                errors["counterparty"] = "Le tiers doit appartenir à la même organisation."

        if self.cost_center_id and self.entry_id:
            if self.cost_center.organization_id != self.entry.organization_id:
                errors["cost_center"] = "Le centre de coûts doit appartenir à la même organisation."

        if self.debit and self.credit:
            errors["debit"] = "Une ligne ne peut pas porter simultanément un débit et un crédit."
            errors["credit"] = "Une ligne ne peut pas porter simultanément un débit et un crédit."

        if not self.debit and not self.credit:
            errors["debit"] = "Une ligne doit comporter un montant au débit ou au crédit."

        if errors:
            raise ValidationError(errors)

    @property
    def signed_amount(self):
        return self.debit - self.credit

    def __str__(self):
        return f"{self.entry.entry_number} / {self.line_number} / {self.account.code}"
