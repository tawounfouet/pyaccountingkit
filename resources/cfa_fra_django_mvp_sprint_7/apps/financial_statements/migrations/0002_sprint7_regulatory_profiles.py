import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("financial_statements", "0001_sprint6_financial_statement_configuration"),
        ("referentials", "0003_sprint7_regulatory_statement_fields"),
        ("organizations", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="RegulatoryStatementProfile",
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
                ("name", models.CharField(max_length=255)),
                ("is_active", models.BooleanField(default=True)),
                ("is_default", models.BooleanField(default=False)),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="regulatory_statement_profiles",
                        to="organizations.organization",
                    ),
                ),
                (
                    "source_version",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="source_regulatory_profiles",
                        to="referentials.frameworkversion",
                    ),
                ),
                (
                    "target_version",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="target_regulatory_profiles",
                        to="referentials.frameworkversion",
                    ),
                ),
            ],
            options={
                "ordering": ["organization__name", "name"],
            },
        ),
        migrations.AddConstraint(
            model_name="regulatorystatementprofile",
            constraint=models.UniqueConstraint(
                fields=("organization", "target_version"),
                name="uniq_org_regulatory_target_version",
            ),
        ),
        migrations.CreateModel(
            name="RegulatoryStatementLineMapping",
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
                (
                    "multiplier",
                    models.DecimalField(
                        decimal_places=6,
                        default=1,
                        max_digits=12,
                    ),
                ),
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
                    "profile",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="line_mappings",
                        to="financial_statements.regulatorystatementprofile",
                    ),
                ),
                (
                    "source_line",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="regulatory_source_mappings",
                        to="referentials.statementline",
                    ),
                ),
                (
                    "target_line",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="regulatory_target_mappings",
                        to="referentials.statementline",
                    ),
                ),
                (
                    "validated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="validated_regulatory_statement_mappings",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": [
                    "source_line__definition__statement_type",
                    "source_line__order",
                    "source_line__code",
                ],
            },
        ),
        migrations.AddConstraint(
            model_name="regulatorystatementlinemapping",
            constraint=models.UniqueConstraint(
                fields=("profile", "source_line"),
                name="uniq_regulatory_profile_source_line",
            ),
        ),
    ]
