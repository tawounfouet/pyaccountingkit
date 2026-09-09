import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Organization",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=255)),
                ("legal_name", models.CharField(blank=True, max_length=255)),
                ("registration_number", models.CharField(blank=True, max_length=100)),
                ("base_currency", models.CharField(default="XAF", max_length=3)),
                ("country_code", models.CharField(default="CM", max_length=2)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="AccountingSettings",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("default_framework_code", models.CharField(default="SYSCOHADA", max_length=50)),
                ("default_chart_code", models.CharField(blank=True, max_length=50)),
                ("require_review_before_posting", models.BooleanField(default=True)),
                ("allow_negative_accounts", models.BooleanField(default=True)),
                ("decimal_places", models.PositiveSmallIntegerField(default=2)),
                ("organization", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="accounting_settings", to="organizations.organization")),
            ],
        ),
        migrations.CreateModel(
            name="FiscalYear",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=50)),
                ("start_date", models.DateField()),
                ("end_date", models.DateField()),
                ("status", models.CharField(choices=[("OPEN", "Ouvert"), ("CLOSING", "En clôture"), ("CLOSED", "Clôturé")], default="OPEN", max_length=20)),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="fiscal_years", to="organizations.organization")),
            ],
            options={"ordering": ["-start_date"]},
        ),
        migrations.CreateModel(
            name="OrganizationMembership",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("role", models.CharField(choices=[("ADMIN", "Administrateur"), ("ACCOUNTANT", "Comptable"), ("REVIEWER", "Reviewer"), ("AUDITOR", "Auditeur"), ("READ_ONLY", "Lecture seule")], default="READ_ONLY", max_length=20)),
                ("is_active", models.BooleanField(default=True)),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="memberships", to="organizations.organization")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="organization_memberships", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="AccountingPeriod",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("period_number", models.PositiveSmallIntegerField()),
                ("name", models.CharField(max_length=50)),
                ("start_date", models.DateField()),
                ("end_date", models.DateField()),
                ("status", models.CharField(choices=[("OPEN", "Ouverte"), ("CLOSING", "En clôture"), ("CLOSED", "Clôturée")], default="OPEN", max_length=20)),
                ("fiscal_year", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="periods", to="organizations.fiscalyear")),
            ],
            options={"ordering": ["fiscal_year", "period_number"]},
        ),
        migrations.AddConstraint(
            model_name="fiscalyear",
            constraint=models.UniqueConstraint(fields=("organization", "name"), name="uniq_fiscal_year_org_name"),
        ),
        migrations.AddConstraint(
            model_name="fiscalyear",
            constraint=models.CheckConstraint(condition=models.Q(("end_date__gte", models.F("start_date"))), name="fiscal_year_end_gte_start"),
        ),
        migrations.AddConstraint(
            model_name="organizationmembership",
            constraint=models.UniqueConstraint(fields=("organization", "user"), name="uniq_membership_org_user"),
        ),
        migrations.AddConstraint(
            model_name="accountingperiod",
            constraint=models.UniqueConstraint(fields=("fiscal_year", "period_number"), name="uniq_period_fiscal_year_number"),
        ),
        migrations.AddConstraint(
            model_name="accountingperiod",
            constraint=models.CheckConstraint(condition=models.Q(("end_date__gte", models.F("start_date"))), name="accounting_period_end_gte_start"),
        ),
    ]
