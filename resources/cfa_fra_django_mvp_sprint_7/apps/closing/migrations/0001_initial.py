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
            name="ClosingRun",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("status", models.CharField(choices=[("DRAFT", "Brouillon"), ("VALIDATED", "Validée"), ("POSTED", "Postée"), ("FAILED", "Échec")], default="DRAFT", max_length=20)),
                ("posted_at", models.DateTimeField(blank=True, null=True)),
                ("notes", models.TextField(blank=True)),
                ("fiscal_year", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="closing_runs", to="organizations.fiscalyear")),
                ("initiated_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="closing_runs", to=settings.AUTH_USER_MODEL)),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="closing_runs", to="organizations.organization")),
            ],
        ),
        migrations.CreateModel(
            name="ClosingEntryLink",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("role", models.CharField(max_length=50)),
                ("closing_run", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="entry_links", to="closing.closingrun")),
                ("entry", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="closing_links", to="accounting.journalentry")),
            ],
        ),
    ]
