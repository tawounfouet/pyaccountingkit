from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("reporting", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="reportsnapshot",
            name="report_type",
            field=models.CharField(
                choices=[
                    ("JOURNAL", "Journal"),
                    ("GENERAL_LEDGER", "Grand livre"),
                    ("TRIAL_BALANCE", "Balance"),
                    ("INCOME_STATEMENT", "Compte de résultat"),
                    ("BALANCE_SHEET", "Bilan"),
                    ("CASH_FLOW", "Flux de trésorerie"),
                    ("REGULATORY_PACKAGE", "Package réglementaire"),
                ],
                max_length=30,
            ),
        ),
    ]
