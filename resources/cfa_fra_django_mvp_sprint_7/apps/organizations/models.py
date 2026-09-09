from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.common.models import TimeStampedUUIDModel

class Organization(TimeStampedUUIDModel):
    name = models.CharField(max_length=255)
    legal_name = models.CharField(max_length=255, blank=True)
    registration_number = models.CharField(max_length=100, blank=True)
    base_currency = models.CharField(max_length=3, default="XAF")
    country_code = models.CharField(max_length=2, default="CM")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

class OrganizationMembership(TimeStampedUUIDModel):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Administrateur"
        ACCOUNTANT = "ACCOUNTANT", "Comptable"
        REVIEWER = "REVIEWER", "Reviewer"
        AUDITOR = "AUDITOR", "Auditeur"
        READ_ONLY = "READ_ONLY", "Lecture seule"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="memberships"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="organization_memberships"
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.READ_ONLY)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "user"],
                name="uniq_membership_org_user",
            )
        ]

class FiscalYear(TimeStampedUUIDModel):
    class Status(models.TextChoices):
        OPEN = "OPEN", "Ouvert"
        CLOSING = "CLOSING", "En clôture"
        CLOSED = "CLOSED", "Clôturé"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="fiscal_years"
    )
    name = models.CharField(max_length=50)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)

    class Meta:
        ordering = ["-start_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "name"],
                name="uniq_fiscal_year_org_name",
            ),
            models.CheckConstraint(
                condition=Q(end_date__gte=models.F("start_date")),
                name="fiscal_year_end_gte_start",
            ),
        ]

    def __str__(self):
        return f"{self.organization} — {self.name}"

class AccountingPeriod(TimeStampedUUIDModel):
    class Status(models.TextChoices):
        OPEN = "OPEN", "Ouverte"
        CLOSING = "CLOSING", "En clôture"
        CLOSED = "CLOSED", "Clôturée"

    fiscal_year = models.ForeignKey(
        FiscalYear, on_delete=models.CASCADE, related_name="periods"
    )
    period_number = models.PositiveSmallIntegerField()
    name = models.CharField(max_length=50)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)

    class Meta:
        ordering = ["fiscal_year", "period_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["fiscal_year", "period_number"],
                name="uniq_period_fiscal_year_number",
            ),
            models.CheckConstraint(
                condition=Q(end_date__gte=models.F("start_date")),
                name="accounting_period_end_gte_start",
            ),
        ]

class AccountingSettings(TimeStampedUUIDModel):
    organization = models.OneToOneField(
        Organization, on_delete=models.CASCADE, related_name="accounting_settings"
    )
    default_framework_code = models.CharField(max_length=50, default="SYSCOHADA")
    default_chart_code = models.CharField(max_length=50, blank=True)
    require_review_before_posting = models.BooleanField(default=True)
    allow_negative_accounts = models.BooleanField(default=True)
    decimal_places = models.PositiveSmallIntegerField(default=2)
