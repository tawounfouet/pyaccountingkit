from datetime import date

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.organizations.models import FiscalYear, Organization, OrganizationMembership
from apps.organizations.services import ensure_accounting_settings, generate_monthly_periods
from apps.accounting.models import Account
from apps.accounting.services import bootstrap_accounting_core
from apps.financial_statements.services import auto_map_accounts

class Command(BaseCommand):
    help = "Crée un utilisateur admin, une organisation de démonstration et l'exercice 2025."

    def add_arguments(self, parser):
        parser.add_argument("--username", default="admin")
        parser.add_argument("--email", default="admin@example.com")
        parser.add_argument("--password", default="admin1234")

    @transaction.atomic
    def handle(self, *args, **options):
        User = get_user_model()

        user, created = User.objects.get_or_create(
            username=options["username"],
            defaults={
                "email": options["email"],
                "is_staff": True,
                "is_superuser": True,
            },
        )
        if created:
            user.set_password(options["password"])
            user.save()
        else:
            changed = False
            if not user.is_staff:
                user.is_staff = True
                changed = True
            if not user.is_superuser:
                user.is_superuser = True
                changed = True
            if changed:
                user.save(update_fields=["is_staff", "is_superuser"])

        organization, _ = Organization.objects.get_or_create(
            name="CFA FRA Demo",
            defaults={
                "legal_name": "CFA FRA Demo",
                "base_currency": "XAF",
                "country_code": "CM",
            },
        )

        OrganizationMembership.objects.get_or_create(
            organization=organization,
            user=user,
            defaults={"role": OrganizationMembership.Role.ADMIN},
        )

        ensure_accounting_settings(organization=organization)
        chart, _journals = bootstrap_accounting_core(organization=organization)
        Account.objects.get_or_create(
            organization=organization,
            chart=chart,
            code="57110000",
            defaults={
                "name": "Caisse",
                "account_type": Account.AccountType.ASSET,
                "normal_balance": Account.NormalBalance.DEBIT,
            },
        )
        Account.objects.get_or_create(
            organization=organization,
            chart=chart,
            code="10110000",
            defaults={
                "name": "Capital",
                "account_type": Account.AccountType.EQUITY,
                "normal_balance": Account.NormalBalance.CREDIT,
            },
        )

        auto_map_accounts(
            organization=organization,
            user=user,
        )

        fiscal_year, _ = FiscalYear.objects.get_or_create(
            organization=organization,
            name="2025",
            defaults={
                "start_date": date(2025, 1, 1),
                "end_date": date(2025, 12, 31),
            },
        )

        if not fiscal_year.periods.exists():
            generate_monthly_periods(fiscal_year=fiscal_year)

        self.stdout.write(
            self.style.SUCCESS(
                "Demo créée. Login: "
                f"{options['username']} / {options['password']} "
                "(changez ce mot de passe hors développement)."
            )
        )
