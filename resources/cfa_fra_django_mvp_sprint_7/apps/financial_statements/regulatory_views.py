from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import ListView, TemplateView

from apps.exports.services import create_regulatory_export
from apps.organizations.mixins import ActiveOrganizationMixin
from apps.organizations.permissions import WRITE_ROLES
from apps.referentials.models import StatementDefinition, StatementLine

from .forms import (
    RegulatoryExportForm,
    RegulatoryMappingForm,
    RegulatoryPeriodForm,
    RegulatoryProfileForm,
)
from .models import (
    RegulatoryStatementLineMapping,
    RegulatoryStatementProfile,
)
from .regulatory import (
    auto_map_regulatory_profile,
    build_regulatory_package,
    create_regulatory_profile,
    profile_metrics,
    update_regulatory_mapping,
)
from .services import ensure_financial_statement_configuration


def _audit_metadata(request):
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
    source_ip = (
        forwarded_for.split(",")[0].strip()
        if forwarded_for
        else request.META.get("REMOTE_ADDR")
    )
    return {
        "path": request.path,
        "method": request.method,
        "source_ip": source_ip,
        "htmx": bool(getattr(request, "htmx", False)),
    }


def _bound_period_form(request, organization):
    if request.GET:
        return RegulatoryPeriodForm(
            request.GET,
            organization=organization,
        )

    probe = RegulatoryPeriodForm(organization=organization)
    data = {}
    for key, value in probe.initial.items():
        if hasattr(value, "pk"):
            data[key] = str(value.pk)
        elif hasattr(value, "isoformat"):
            data[key] = value.isoformat()
        else:
            data[key] = value
    return RegulatoryPeriodForm(
        data,
        organization=organization,
    )


class WriteRegulatoryMixin(ActiveOrganizationMixin):
    allowed_roles = WRITE_ROLES


class RegulatoryProfileObjectMixin:
    def get_profile(self):
        return get_object_or_404(
            RegulatoryStatementProfile.objects.select_related(
                "organization",
                "source_version",
                "source_version__framework",
                "target_version",
                "target_version__framework",
            ),
            pk=self.kwargs["pk"],
            organization=self.organization,
        )


class RegulatoryProfileListView(ActiveOrganizationMixin, ListView):
    model = RegulatoryStatementProfile
    template_name = "financial_statements/regulatory/list.html"
    context_object_name = "profiles"

    def get_queryset(self):
        return (
            RegulatoryStatementProfile.objects.filter(
                organization=self.organization,
            )
            .select_related(
                "source_version",
                "source_version__framework",
                "target_version",
                "target_version__framework",
            )
            .order_by("name")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        for profile in context["profiles"]:
            profile.sprint7_metrics = profile_metrics(profile)
        return context


class RegulatoryProfileCreateView(WriteRegulatoryMixin, View):
    template_name = "financial_statements/regulatory/create.html"

    def get(self, request):
        configuration = ensure_financial_statement_configuration(
            organization=self.organization,
            user=request.user,
        )
        return render(
            request,
            self.template_name,
            {
                "form": RegulatoryProfileForm(
                    source_version=configuration.framework_version,
                )
            },
        )

    def post(self, request):
        configuration = ensure_financial_statement_configuration(
            organization=self.organization,
            user=request.user,
        )
        form = RegulatoryProfileForm(
            request.POST,
            source_version=configuration.framework_version,
        )

        if form.is_valid():
            try:
                profile = create_regulatory_profile(
                    organization=self.organization,
                    target_version=form.cleaned_data["target_version"],
                    user=request.user,
                    name=form.cleaned_data.get("name") or None,
                )
            except ValidationError as exc:
                form.add_error(None, exc)
            else:
                messages.success(
                    request,
                    f"Profil réglementaire {profile.name} prêt à être mappé.",
                )
                return redirect(
                    "financial_statements:regulatory-mappings",
                    pk=profile.pk,
                )

        return render(
            request,
            self.template_name,
            {"form": form},
            status=400,
        )


class RegulatoryProfileDetailView(
    ActiveOrganizationMixin,
    RegulatoryProfileObjectMixin,
    View,
):
    template_name = "financial_statements/regulatory/detail.html"

    def get(self, request, pk):
        profile = self.get_profile()
        form = _bound_period_form(request, self.organization)
        package = None

        if form.is_valid():
            package = build_regulatory_package(
                profile=profile,
                fiscal_year=form.cleaned_data["fiscal_year"],
                end_date=form.cleaned_data["end_date"],
            )

        export_form = RegulatoryExportForm(
            initial={
                "fiscal_year": (
                    form.cleaned_data.get("fiscal_year")
                    if form.is_valid()
                    else None
                ),
                "end_date": (
                    form.cleaned_data.get("end_date")
                    if form.is_valid()
                    else None
                ),
                "export_format": "XLSX",
            },
            organization=self.organization,
        )

        return render(
            request,
            self.template_name,
            {
                "profile": profile,
                "form": form,
                "package": package,
                "metrics": profile_metrics(profile),
                "export_form": export_form,
            },
        )


class RegulatoryMappingView(
    WriteRegulatoryMixin,
    RegulatoryProfileObjectMixin,
    TemplateView,
):
    template_name = "financial_statements/regulatory/mappings.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.get_profile()

        mapping_by_source = {
            mapping.source_line_id: mapping
            for mapping in profile.line_mappings.select_related(
                "source_line",
                "source_line__definition",
                "target_line",
                "target_line__definition",
            )
        }

        rows = []
        source_lines = (
            StatementLine.objects.filter(
                definition__version=profile.source_version,
                definition__statement_type__in=[
                    StatementDefinition.StatementType.INCOME_STATEMENT,
                    StatementDefinition.StatementType.BALANCE_SHEET,
                    StatementDefinition.StatementType.CASH_FLOW,
                ],
                is_total=False,
            )
            .select_related("definition")
            .order_by(
                "definition__statement_type",
                "order",
                "code",
            )
        )

        for source_line in source_lines:
            mapping = mapping_by_source.get(source_line.id)
            rows.append(
                {
                    "source_line": source_line,
                    "mapping": mapping,
                    "form": RegulatoryMappingForm(
                        target_version=profile.target_version,
                        statement_type=source_line.definition.statement_type,
                        initial_mapping=mapping,
                        prefix=f"reg-{source_line.pk}",
                    ),
                }
            )

        context["profile"] = profile
        context["rows"] = rows
        context["metrics"] = profile_metrics(profile)
        return context


class RegulatoryMappingUpdateView(
    WriteRegulatoryMixin,
    RegulatoryProfileObjectMixin,
    View,
):
    def post(self, request, pk, source_line_id):
        profile = self.get_profile()
        source_line = get_object_or_404(
            StatementLine.objects.select_related("definition"),
            pk=source_line_id,
            definition__version=profile.source_version,
            is_total=False,
        )
        existing = (
            profile.line_mappings.filter(
                source_line=source_line,
            )
            .select_related("target_line")
            .first()
        )

        form = RegulatoryMappingForm(
            request.POST,
            target_version=profile.target_version,
            statement_type=source_line.definition.statement_type,
            initial_mapping=existing,
            prefix=f"reg-{source_line.pk}",
        )

        if form.is_valid():
            try:
                mapping = update_regulatory_mapping(
                    profile=profile,
                    source_line=source_line,
                    target_line=form.cleaned_data["target_line"],
                    multiplier=form.cleaned_data["multiplier"],
                    user=request.user,
                )
            except ValidationError as exc:
                form.add_error(None, exc)
                mapping = existing
        else:
            mapping = existing

        if getattr(request, "htmx", False):
            refreshed = (
                profile.line_mappings.filter(
                    source_line=source_line,
                )
                .select_related(
                    "target_line",
                    "target_line__definition",
                )
                .first()
            )
            return render(
                request,
                "financial_statements/regulatory/_mapping_row.html",
                {
                    "profile": profile,
                    "source_line": source_line,
                    "mapping": refreshed,
                    "form": RegulatoryMappingForm(
                        target_version=profile.target_version,
                        statement_type=source_line.definition.statement_type,
                        initial_mapping=refreshed,
                        prefix=f"reg-{source_line.pk}",
                    ),
                },
                status=200 if not form.errors else 400,
            )

        if form.errors:
            messages.error(
                request,
                "Le mapping réglementaire n'a pas pu être mis à jour.",
            )
        else:
            messages.success(
                request,
                f"Mapping {source_line.code} mis à jour.",
            )
        return redirect(
            "financial_statements:regulatory-mappings",
            pk=profile.pk,
        )


class RegulatoryAutoMapView(
    WriteRegulatoryMixin,
    RegulatoryProfileObjectMixin,
    View,
):
    def post(self, request, pk):
        profile = self.get_profile()
        result = auto_map_regulatory_profile(
            profile=profile,
            user=request.user,
        )
        messages.success(
            request,
            (
                f"Auto-mapping : {result['created']} correspondance(s), "
                f"{result['unresolved']} ligne(s) non résolue(s)."
            ),
        )
        return redirect(
            "financial_statements:regulatory-mappings",
            pk=profile.pk,
        )


class RegulatoryExportView(
    WriteRegulatoryMixin,
    RegulatoryProfileObjectMixin,
    View,
):
    def post(self, request, pk):
        profile = self.get_profile()
        form = RegulatoryExportForm(
            request.POST,
            organization=self.organization,
        )

        if form.is_valid():
            try:
                job = create_regulatory_export(
                    profile=profile,
                    fiscal_year=form.cleaned_data["fiscal_year"],
                    end_date=form.cleaned_data["end_date"],
                    export_format=form.cleaned_data["export_format"],
                    user=request.user,
                    audit_metadata=_audit_metadata(request),
                )
            except ValidationError as exc:
                messages.error(
                    request,
                    " ".join(exc.messages),
                )
            except Exception as exc:
                messages.error(
                    request,
                    f"Export impossible : {exc}",
                )
            else:
                messages.success(
                    request,
                    f"Export {job.get_format_display()} généré.",
                )
                return redirect("exports:detail", pk=job.pk)

        return redirect(
            "financial_statements:regulatory-detail",
            pk=profile.pk,
        )
