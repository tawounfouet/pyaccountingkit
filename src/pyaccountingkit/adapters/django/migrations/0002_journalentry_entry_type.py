# Generated for PyAccountingKit LOT-25 / 0.6.0a1.

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("pyaccountingkit_django", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="journalentrymodel",
            name="entry_type",
            field=models.CharField(
                db_index=True,
                default="NORMAL",
                max_length=16,
            ),
        ),
    ]
