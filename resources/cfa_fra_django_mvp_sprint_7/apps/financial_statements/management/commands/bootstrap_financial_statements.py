from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from apps.financial_statements.services import (
    auto_map_accounts,
    ensure_financial_statement_configuration,
)
from apps.organizations.models import Organization


class Command(BaseCommand):
    help = "Initialise le moteur d'états financiers et peut auto-mapper les comptes."

    def add_arguments(self, parser):
        parser.add_argument("organization", help="UUID ou nom exact de l'organisation")
        parser.add_argument("--username", help="Utilisateur d'audit")
        parser.add_argument(
            "--auto-map",
            action="store_true",
            help="Crée les mappings automatiques comptes -> rubriques.",
        )

    def handle(self, *args, **options):
        value = options["organization"]

        try:
            organization = Organization.objects.get(pk=value)
        except (Organization.DoesNotExist, ValueError):
            try:
                organization = Organization.objects.get(name=value)
            except Organization.DoesNotExist as exc:
                raise CommandError(f"Organisation introuvable : {value}") from exc

        user = None
        if options.get("username"):
            User = get_user_model()
            try:
                user = User.objects.get(username=options["username"])
            except User.DoesNotExist as exc:
                raise CommandError(
                    f"Utilisateur introuvable : {options['username']}"
                ) from exc

        configuration = ensure_financial_statement_configuration(
            organization=organization,
            user=user,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Configuration prête : "
                f"{configuration.framework_version.framework.code} "
                f"{configuration.framework_version.version}."
            )
        )

        if options["auto_map"]:
            result = auto_map_accounts(
                organization=organization,
                user=user,
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"Auto-mapping : {result['created']} mapping(s) créé(s)."
                )
            )
