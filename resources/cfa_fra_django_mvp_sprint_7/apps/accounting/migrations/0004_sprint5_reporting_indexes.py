from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounting", "0003_sprint3_workflow"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="journalentry",
            index=models.Index(
                fields=[
                    "organization",
                    "status",
                    "entry_type",
                    "posting_date",
                ],
                name="entry_report_scope_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="journalline",
            index=models.Index(
                fields=["entry", "account", "line_number"],
                name="line_entry_account_idx",
            ),
        ),
    ]
