import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    initial = True
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("accounting", "0001_initial"),
    ]
    operations = [
        migrations.CreateModel(
            name="AccountingFramework",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("code", models.CharField(max_length=50, unique=True)),
                ("name", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                ("is_active", models.BooleanField(default=True)),
            ],
        ),
        migrations.CreateModel(
            name="FrameworkVersion",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("version", models.CharField(max_length=50)),
                ("effective_from", models.DateField(blank=True, null=True)),
                ("effective_to", models.DateField(blank=True, null=True)),
                ("source_url", models.URLField(blank=True)),
                ("is_current", models.BooleanField(default=False)),
                ("framework", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="versions", to="referentials.accountingframework")),
            ],
        ),
        migrations.CreateModel(
            name="FrameworkAccount",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("code", models.CharField(max_length=100)),
                ("name", models.CharField(max_length=500)),
                ("name_en", models.CharField(blank=True, max_length=500)),
                ("account_type", models.CharField(blank=True, max_length=50)),
                ("normal_balance", models.CharField(blank=True, max_length=20)),
                ("current_noncurrent", models.CharField(blank=True, max_length=30)),
                ("statement", models.CharField(blank=True, max_length=100)),
                ("statement_section", models.CharField(blank=True, max_length=150)),
                ("standard_reference", models.CharField(blank=True, max_length=255)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("parent", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="children", to="referentials.frameworkaccount")),
                ("version", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="accounts", to="referentials.frameworkversion")),
            ],
            options={"ordering": ["version", "code"]},
        ),
        migrations.CreateModel(
            name="StatementDefinition",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("code", models.CharField(max_length=100)),
                ("name", models.CharField(max_length=255)),
                ("statement_type", models.CharField(choices=[("BALANCE_SHEET", "Bilan"), ("INCOME_STATEMENT", "Compte de résultat"), ("CASH_FLOW", "Flux de trésorerie"), ("EQUITY_CHANGES", "Variation des capitaux propres")], max_length=50)),
                ("version", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="statement_definitions", to="referentials.frameworkversion")),
            ],
        ),
        migrations.CreateModel(
            name="StatementLine",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("code", models.CharField(max_length=100)),
                ("label", models.CharField(max_length=255)),
                ("order", models.PositiveIntegerField(default=0)),
                ("sign", models.SmallIntegerField(default=1)),
                ("is_total", models.BooleanField(default=False)),
                ("definition", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="lines", to="referentials.statementdefinition")),
                ("parent", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="children", to="referentials.statementline")),
            ],
            options={"ordering": ["definition", "order", "code"]},
        ),
        migrations.CreateModel(
            name="AccountMapping",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("mapping_type", models.CharField(choices=[("MANUAL", "Manuel"), ("RULE", "Règle"), ("SUGGESTED", "Suggestion")], default="MANUAL", max_length=20)),
                ("confidence", models.DecimalField(blank=True, decimal_places=4, max_digits=5, null=True)),
                ("validated_at", models.DateTimeField(blank=True, null=True)),
                ("notes", models.TextField(blank=True)),
                ("account", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="framework_mappings", to="accounting.account")),
                ("framework_account", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="entity_account_mappings", to="referentials.frameworkaccount")),
                ("validated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="validated_account_mappings", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddConstraint(model_name="frameworkversion", constraint=models.UniqueConstraint(fields=("framework", "version"), name="uniq_framework_version")),
        migrations.AddConstraint(model_name="frameworkaccount", constraint=models.UniqueConstraint(fields=("version", "code"), name="uniq_framework_account_code")),
        migrations.AddConstraint(model_name="statementdefinition", constraint=models.UniqueConstraint(fields=("version", "code"), name="uniq_statement_definition_code")),
        migrations.AddConstraint(model_name="statementline", constraint=models.UniqueConstraint(fields=("definition", "code"), name="uniq_statement_line_code")),
        migrations.AddConstraint(model_name="accountmapping", constraint=models.UniqueConstraint(fields=("account", "framework_account"), name="uniq_account_framework_mapping")),
    ]
