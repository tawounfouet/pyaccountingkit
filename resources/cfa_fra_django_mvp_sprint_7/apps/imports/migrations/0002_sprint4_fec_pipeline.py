import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("imports", "0001_initial"),
        ("accounting", "0003_sprint3_workflow"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="fecimport",
            options={"ordering": ["-created_at"]},
        ),
        migrations.AlterField(
            model_name="fecimport",
            name="status",
            field=models.CharField(
                choices=[
                    ("UPLOADED", "Uploadé"),
                    ("PARSED", "Analysé"),
                    ("MAPPING", "Mapping requis"),
                    ("READY", "Prêt à importer"),
                    ("IMPORTING", "Import en cours"),
                    ("IMPORTED", "Importé"),
                    ("FAILED", "Échec"),
                ],
                default="UPLOADED",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="fecimport",
            name="imported_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="completed_fec_imports",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="fecimport",
            name="parsed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="fecrawline",
            name="journal_code",
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AlterField(
            model_name="fecrawline",
            name="entry_number",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AlterField(
            model_name="fecrawline",
            name="entry_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="fecrawline",
            name="account_number",
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AlterField(
            model_name="fecrawline",
            name="account_label",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="fecrawline",
            name="row_hash",
            field=models.CharField(blank=True, db_index=True, max_length=64),
        ),
        migrations.AddField(
            model_name="fecrawline",
            name="normalized_entry_key",
            field=models.CharField(blank=True, db_index=True, max_length=500),
        ),
        migrations.AddField(
            model_name="fecrawline",
            name="is_valid",
            field=models.BooleanField(default=True),
        ),
        migrations.AddIndex(
            model_name="fecrawline",
            index=models.Index(
                fields=["import_batch", "journal_code", "entry_number"],
                name="fecraw_batch_jrn_entry_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="fecrawline",
            index=models.Index(
                fields=["import_batch", "account_number"],
                name="fecraw_batch_account_idx",
            ),
        ),
        migrations.AlterModelOptions(
            name="importmapping",
            options={"ordering": ["source_account_number"]},
        ),
        migrations.AlterField(
            model_name="importmapping",
            name="account",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="import_mappings",
                to="accounting.account",
            ),
        ),
        migrations.AddField(
            model_name="importmapping",
            name="source_account_label",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="importmapping",
            name="occurrence_count",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.CreateModel(
            name="JournalImportMapping",
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
                ("source_journal_code", models.CharField(max_length=50)),
                ("source_journal_label", models.CharField(blank=True, max_length=255)),
                ("occurrence_count", models.PositiveIntegerField(default=0)),
                ("created_automatically", models.BooleanField(default=False)),
                (
                    "import_batch",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="journal_mappings",
                        to="imports.fecimport",
                    ),
                ),
                (
                    "journal",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="fec_import_mappings",
                        to="accounting.journal",
                    ),
                ),
            ],
            options={
                "ordering": ["source_journal_code"],
            },
        ),
        migrations.AddConstraint(
            model_name="journalimportmapping",
            constraint=models.UniqueConstraint(
                fields=("import_batch", "source_journal_code"),
                name="uniq_import_source_journal",
            ),
        ),
    ]
