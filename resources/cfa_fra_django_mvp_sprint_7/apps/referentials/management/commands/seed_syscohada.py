from django.core.management.base import BaseCommand
from ._seed_framework import seed_framework

class Command(BaseCommand):
    help = "Charge un référentiel SYSCOHADA depuis un fichier JSON."

    def add_arguments(self, parser):
        parser.add_argument("path")

    def handle(self, *args, **options):
        result = seed_framework(
            path=options["path"],
            framework_code="SYSCOHADA",
            framework_name="SYSCOHADA",
            version_name="2017",
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"{result['accounts']} comptes, "
                f"{result['statements']} états et "
                f"{result['statement_lines']} lignes SYSCOHADA chargés."
            )
        )
