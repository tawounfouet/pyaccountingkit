# Generated for PyAccountingKit REM-03 / F11.

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("pyaccountingkit_django", "0002_journalentry_entry_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="idempotencyrecordmodel",
            name="payload_fingerprint",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
    ]
