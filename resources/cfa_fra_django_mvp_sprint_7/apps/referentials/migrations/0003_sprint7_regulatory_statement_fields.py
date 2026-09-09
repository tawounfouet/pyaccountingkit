from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("referentials", "0002_sprint6_statement_account_mapping"),
    ]

    operations = [
        migrations.AddField(
            model_name="statementline",
            name="is_required",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="statementline",
            name="standard_reference",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="statementline",
            name="metadata",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
