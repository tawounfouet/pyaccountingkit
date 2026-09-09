import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("referentials", "0001_initial"),
        ("accounting", "0004_sprint5_reporting_indexes"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="StatementAccountMapping",
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
                ("balance_multiplier", models.SmallIntegerField(default=1)),
                (
                    "mapping_type",
                    models.CharField(
                        choices=[
                            ("MANUAL", "Manuel"),
                            ("RULE", "Règle"),
                            ("SUGGESTED", "Suggestion"),
                        ],
                        default="MANUAL",
                        max_length=20,
                    ),
                ),
                (
                    "confidence",
                    models.DecimalField(
                        blank=True,
                        decimal_places=4,
                        max_digits=5,
                        null=True,
                    ),
                ),
                ("validated_at", models.DateTimeField(blank=True, null=True)),
                ("notes", models.TextField(blank=True)),
                (
                    "account",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="statement_mappings",
                        to="accounting.account",
                    ),
                ),
                (
                    "statement_line",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="entity_account_mappings",
                        to="referentials.statementline",
                    ),
                ),
                (
                    "validated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="validated_statement_account_mappings",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": [
                    "account__code",
                    "statement_line__definition__statement_type",
                ],
            },
        ),
        migrations.AddConstraint(
            model_name="statementaccountmapping",
            constraint=models.UniqueConstraint(
                fields=("account", "statement_line"),
                name="uniq_account_statement_line_mapping",
            ),
        ),
    ]
