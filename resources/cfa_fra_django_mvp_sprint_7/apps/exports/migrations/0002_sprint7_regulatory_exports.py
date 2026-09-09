from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("exports", "0001_initial"),
        ("reporting", "0002_sprint7_regulatory_snapshot_type"),
        ("financial_statements", "0002_sprint7_regulatory_profiles"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="exportjob",
            options={"ordering": ["-created_at"]},
        ),
        migrations.AlterField(
            model_name="exportjob",
            name="format",
            field=models.CharField(
                choices=[
                    ("XLSX", "Excel"),
                    ("PDF", "PDF"),
                    ("CSV", "CSV"),
                    ("JSON", "JSON"),
                ],
                default="CSV",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="exportjob",
            name="content_sha256",
            field=models.CharField(blank=True, db_index=True, max_length=64),
        ),
        migrations.AddField(
            model_name="exportjob",
            name="mime_type",
            field=models.CharField(blank=True, max_length=150),
        ),
        migrations.AddField(
            model_name="exportjob",
            name="snapshot",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="export_jobs",
                to="reporting.reportsnapshot",
            ),
        ),
        migrations.AddField(
            model_name="exportjob",
            name="regulatory_profile",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="export_jobs",
                to="financial_statements.regulatorystatementprofile",
            ),
        ),
    ]
