from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounting", "0001_initial"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="chartofaccounts",
            options={"ordering": ["code"]},
        ),
        migrations.AlterModelOptions(
            name="account",
            options={"ordering": ["code"]},
        ),
        migrations.AlterModelOptions(
            name="counterparty",
            options={"ordering": ["code"]},
        ),
        migrations.AlterModelOptions(
            name="costcenter",
            options={"ordering": ["code"]},
        ),
        migrations.AlterModelOptions(
            name="journalentry",
            options={"ordering": ["-posting_date", "-created_at"]},
        ),
        migrations.AddIndex(
            model_name="account",
            index=models.Index(
                fields=["organization", "code"],
                name="acct_org_code_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="account",
            index=models.Index(
                fields=["organization", "account_type"],
                name="acct_org_type_idx",
            ),
        ),
        migrations.RemoveIndex(
            model_name="journalentry",
            name="accounting__organiz_f37663_idx",
        ),
        migrations.RemoveIndex(
            model_name="journalentry",
            name="accounting__organiz_863e07_idx",
        ),
        migrations.AddIndex(
            model_name="journalentry",
            index=models.Index(
                fields=["organization", "posting_date"],
                name="entry_org_date_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="journalentry",
            index=models.Index(
                fields=["organization", "status", "posting_date"],
                name="entry_org_status_date_idx",
            ),
        ),
        migrations.RemoveIndex(
            model_name="journalline",
            name="accounting__account_96ccbb_idx",
        ),
        migrations.AddIndex(
            model_name="journalline",
            index=models.Index(
                fields=["account", "entry"],
                name="line_account_entry_idx",
            ),
        ),
    ]
