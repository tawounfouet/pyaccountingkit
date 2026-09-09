import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    initial = True
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("organizations", "0001_initial"),
        ("accounting", "0001_initial"),
    ]
    operations = [
        migrations.CreateModel(
            name="FECImport",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("original_filename", models.CharField(max_length=255)),
                ("original_file", models.FileField(upload_to="fec/%Y/%m/")),
                ("sha256", models.CharField(db_index=True, max_length=64)),
                ("encoding", models.CharField(default="utf-8", max_length=50)),
                ("status", models.CharField(choices=[("UPLOADED", "Uploadé"), ("PARSED", "Analysé"), ("VALIDATED", "Validé"), ("IMPORTING", "Import en cours"), ("IMPORTED", "Importé"), ("FAILED", "Échec")], default="UPLOADED", max_length=20)),
                ("imported_at", models.DateTimeField(blank=True, null=True)),
                ("summary", models.JSONField(blank=True, default=dict)),
                ("fiscal_year", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="fec_imports", to="organizations.fiscalyear")),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="fec_imports", to="organizations.organization")),
                ("uploaded_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="fec_imports", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="FECRawLine",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("line_number", models.PositiveIntegerField()),
                ("journal_code", models.CharField(max_length=50)),
                ("journal_label", models.CharField(blank=True, max_length=255)),
                ("entry_number", models.CharField(max_length=255)),
                ("entry_date", models.DateField()),
                ("account_number", models.CharField(max_length=50)),
                ("account_label", models.CharField(max_length=255)),
                ("auxiliary_number", models.CharField(blank=True, max_length=255)),
                ("auxiliary_label", models.CharField(blank=True, max_length=255)),
                ("piece_reference", models.CharField(blank=True, max_length=255)),
                ("piece_date", models.DateField(blank=True, null=True)),
                ("entry_label", models.TextField(blank=True)),
                ("debit", models.DecimalField(decimal_places=4, default=0, max_digits=24)),
                ("credit", models.DecimalField(decimal_places=4, default=0, max_digits=24)),
                ("letter", models.CharField(blank=True, max_length=100)),
                ("letter_date", models.DateField(blank=True, null=True)),
                ("validation_date", models.DateField(blank=True, null=True)),
                ("currency_amount", models.DecimalField(decimal_places=4, default=0, max_digits=24)),
                ("currency_code", models.CharField(blank=True, max_length=10)),
                ("raw_data", models.JSONField(default=dict)),
                ("import_batch", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="raw_lines", to="imports.fecimport")),
            ],
            options={"ordering": ["import_batch", "line_number"]},
        ),
        migrations.CreateModel(
            name="ImportError",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("code", models.CharField(max_length=100)),
                ("severity", models.CharField(choices=[("INFO", "Information"), ("WARNING", "Avertissement"), ("ERROR", "Erreur"), ("BLOCKING", "Bloquant")], max_length=20)),
                ("message", models.TextField()),
                ("details", models.JSONField(blank=True, default=dict)),
                ("is_resolved", models.BooleanField(default=False)),
                ("import_batch", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="errors", to="imports.fecimport")),
                ("raw_line", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="errors", to="imports.fecrawline")),
            ],
        ),
        migrations.CreateModel(
            name="ImportMapping",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("source_account_number", models.CharField(max_length=50)),
                ("created_automatically", models.BooleanField(default=False)),
                ("account", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="import_mappings", to="accounting.account")),
                ("import_batch", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="mappings", to="imports.fecimport")),
            ],
        ),
        migrations.AddConstraint(model_name="fecimport", constraint=models.UniqueConstraint(fields=("organization", "fiscal_year", "sha256"), name="uniq_fec_import_org_year_hash")),
        migrations.AddConstraint(model_name="fecrawline", constraint=models.UniqueConstraint(fields=("import_batch", "line_number"), name="uniq_fec_raw_import_line")),
        migrations.AddConstraint(model_name="importmapping", constraint=models.UniqueConstraint(fields=("import_batch", "source_account_number"), name="uniq_import_source_account")),
    ]
