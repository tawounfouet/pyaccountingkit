import uuid

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("organizations", "0001_initial"),
        ("referentials", "0002_sprint6_statement_account_mapping"),
    ]

    operations = [
        migrations.CreateModel(
            name="FinancialStatementConfiguration",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("comparative_enabled", models.BooleanField(default=True)),
                ("cash_account_prefixes", models.JSONField(blank=True, default=list)),
                ("infer_cash_flow_categories", models.BooleanField(default=True)),
                ("is_active", models.BooleanField(default=True)),
                (
                    "framework_version",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="entity_financial_statement_configurations",
                        to="referentials.frameworkversion",
                    ),
                ),
                (
                    "organization",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="financial_statement_configuration",
                        to="organizations.organization",
                    ),
                ),
            ],
            options={"ordering": ["organization__name"]},
        ),
    ]
