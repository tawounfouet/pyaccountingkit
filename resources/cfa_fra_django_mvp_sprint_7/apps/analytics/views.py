from django.views.generic import TemplateView

from apps.accounting.models import JournalEntry
from apps.imports.models import FECImport
from apps.organizations.mixins import ActiveOrganizationMixin
from apps.referentials.models import StatementAccountMapping


class DashboardView(ActiveOrganizationMixin, TemplateView):
    template_name = "analytics/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        organization = self.organization
        entries = organization.journal_entries.all()
        fec_imports = organization.fec_imports.all()

        context["core_counts"] = {
            "charts": organization.charts_of_accounts.count(),
            "accounts": organization.accounts.count(),
            "journals": organization.journals.count(),
            "entries": entries.count(),
        }
        context["workflow_counts"] = {
            "draft": entries.filter(status=JournalEntry.Status.DRAFT).count(),
            "validated": entries.filter(status=JournalEntry.Status.VALIDATED).count(),
            "posted": entries.filter(status=JournalEntry.Status.POSTED).count(),
            "reversed": entries.filter(status=JournalEntry.Status.REVERSED).count(),
        }
        context["fec_counts"] = {
            "total": fec_imports.count(),
            "mapping": fec_imports.filter(status=FECImport.Status.MAPPING).count(),
            "ready": fec_imports.filter(status=FECImport.Status.READY).count(),
            "imported": fec_imports.filter(status=FECImport.Status.IMPORTED).count(),
            "failed": fec_imports.filter(status=FECImport.Status.FAILED).count(),
        }
        statement_mapped = (
            StatementAccountMapping.objects.filter(
                account__organization=organization,
            )
            .values("account_id")
            .distinct()
            .count()
        )
        context["statement_counts"] = {
            "mapped_accounts": statement_mapped,
            "total_accounts": organization.accounts.count(),
        }
        context["audit_count"] = organization.audit_events.count()
        return context
