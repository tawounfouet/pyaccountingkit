from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError

from apps.imports.services import (
    auto_create_unmapped_references,
    create_fec_import,
    execute_fec_import,
    parse_fec_import,
)
from apps.organizations.models import FiscalYear, Organization


class Command(BaseCommand):
    help = (
        "Charge un FEC, le parse, prépare les mappings et peut exécuter "
        "l'import transactionnel."
    )

    def add_arguments(self, parser):
        parser.add_argument("path")
        parser.add_argument("--organization", required=True)
        parser.add_argument("--fiscal-year", required=True)
        parser.add_argument("--username", required=True)
        parser.add_argument(
            "--auto-map",
            action="store_true",
            help="Crée automatiquement les comptes et journaux manquants.",
        )
        parser.add_argument(
            "--execute",
            action="store_true",
            help="Exécute l'import après parsing/mapping.",
        )

    def handle(self, *args, **options):
        file_path = Path(options["path"])
        if not file_path.exists():
            raise CommandError(f"Fichier introuvable : {file_path}")

        try:
            organization = Organization.objects.get(pk=options["organization"])
        except (Organization.DoesNotExist, ValueError):
            try:
                organization = Organization.objects.get(name=options["organization"])
            except Organization.DoesNotExist as exc:
                raise CommandError(
                    f"Organisation introuvable : {options['organization']}"
                ) from exc

        try:
            fiscal_year = FiscalYear.objects.get(
                organization=organization,
                name=options["fiscal_year"],
            )
        except FiscalYear.DoesNotExist as exc:
            raise CommandError(
                f"Exercice {options['fiscal_year']} introuvable pour {organization}."
            ) from exc

        User = get_user_model()
        try:
            user = User.objects.get(username=options["username"])
        except User.DoesNotExist as exc:
            raise CommandError(
                f"Utilisateur introuvable : {options['username']}"
            ) from exc

        with file_path.open("rb") as handle:
            uploaded = File(handle, name=file_path.name)
            import_batch = create_fec_import(
                organization=organization,
                fiscal_year=fiscal_year,
                uploaded_file=uploaded,
                user=user,
                audit_metadata={"source": "management_command"},
            )

        import_batch = parse_fec_import(
            import_batch=import_batch,
            user=user,
            audit_metadata={"source": "management_command"},
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Parsing terminé : statut={import_batch.status}, "
                f"lignes={import_batch.summary.get('line_count', 0)}."
            )
        )

        if options["auto_map"]:
            import_batch = auto_create_unmapped_references(
                import_batch=import_batch,
                user=user,
                audit_metadata={"source": "management_command"},
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"Auto-mapping terminé : statut={import_batch.status}."
                )
            )

        if options["execute"]:
            import_batch = execute_fec_import(
                import_batch=import_batch,
                user=user,
                audit_metadata={"source": "management_command"},
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"Import terminé : "
                    f"{import_batch.summary.get('imported_entry_count', 0)} écritures / "
                    f"{import_batch.summary.get('imported_line_count', 0)} lignes."
                )
            )
