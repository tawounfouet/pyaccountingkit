from django.core.management.base import BaseCommand, CommandError

from apps.accounting.services import bootstrap_accounting_core
from apps.organizations.models import Organization


class Command(BaseCommand):
    help = "Initialise le plan comptable d'entité et les journaux standard d'une organisation."

    def add_arguments(self, parser):
        parser.add_argument("organization", help="UUID ou nom exact de l'organisation")

    def handle(self, *args, **options):
        value = options["organization"]

        try:
            organization = Organization.objects.get(pk=value)
        except (Organization.DoesNotExist, ValueError):
            try:
                organization = Organization.objects.get(name=value)
            except Organization.DoesNotExist as exc:
                raise CommandError(f"Organisation introuvable: {value}") from exc

        chart, journals = bootstrap_accounting_core(organization=organization)
        self.stdout.write(
            self.style.SUCCESS(
                f"Accounting Core initialisé: plan={chart.code}, journaux={len(journals)}."
            )
        )
