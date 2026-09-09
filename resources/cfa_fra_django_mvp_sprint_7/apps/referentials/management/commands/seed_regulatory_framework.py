import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from ._seed_framework import seed_framework


class Command(BaseCommand):
    help = (
        "Charge un référentiel réglementaire complet "
        "(comptes + définitions/lignes d'états) depuis JSON."
    )

    def add_arguments(self, parser):
        parser.add_argument("path")
        parser.add_argument("--framework-code")
        parser.add_argument("--framework-name")
        parser.add_argument("--version")

    def handle(self, *args, **options):
        path = Path(options["path"])
        if not path.exists():
            raise CommandError(f"Fichier introuvable : {path}")

        payload = json.loads(path.read_text(encoding="utf-8"))
        framework_meta = (
            payload.get("framework", {})
            if isinstance(payload, dict)
            else {}
        )

        code = (
            options.get("framework_code")
            or framework_meta.get("code")
        )
        name = (
            options.get("framework_name")
            or framework_meta.get("name")
        )
        version = (
            options.get("version")
            or framework_meta.get("version")
        )

        if not code or not name or not version:
            raise CommandError(
                "code, name et version doivent être fournis "
                "dans le JSON ou via les options."
            )

        result = seed_framework(
            path=str(path),
            framework_code=code,
            framework_name=name,
            version_name=version,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"{result['framework']} {result['version']} : "
                f"{result['accounts']} compte(s), "
                f"{result['statements']} état(s), "
                f"{result['statement_lines']} ligne(s)."
            )
        )
