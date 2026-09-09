from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import ListView, TemplateView

from apps.organizations.mixins import ActiveOrganizationMixin
from apps.organizations.permissions import REVIEW_ROLES, WRITE_ROLES

from .forms import (
    AccountImportMappingForm,
    FECUploadForm,
    JournalImportMappingForm,
)
from .models import FECImport, ImportMapping, JournalImportMapping
from .services import (
    auto_create_unmapped_references,
    create_fec_import,
    execute_fec_import,
    parse_fec_import,
    update_account_mapping,
    update_journal_mapping,
)


def request_audit_metadata(request):
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
    source_ip = forwarded_for.split(",")[0].strip() if forwarded_for else request.META.get("REMOTE_ADDR")
    return {
        "path": request.path,
        "method": request.method,
        "htmx": bool(getattr(request, "htmx", False)),
        "source_ip": source_ip,
    }


def validation_error_message(exc):
    if hasattr(exc, "messages"):
        return " ".join(exc.messages)
    return str(exc)


class WriteImportMixin(ActiveOrganizationMixin):
    allowed_roles = WRITE_ROLES


class ReviewImportMixin(ActiveOrganizationMixin):
    allowed_roles = REVIEW_ROLES


class FECImportObjectMixin:
    def get_import_batch(self):
        return get_object_or_404(
            FECImport.objects.select_related(
                "organization",
                "fiscal_year",
                "uploaded_by",
                "imported_by",
            ),
            pk=self.kwargs["pk"],
            organization=self.organization,
        )


class FECImportListView(ActiveOrganizationMixin, ListView):
    model = FECImport
    template_name = "imports/list.html"
    context_object_name = "imports"
    paginate_by = 25

    def get_queryset(self):
        return (
            FECImport.objects.filter(organization=self.organization)
            .select_related(
                "fiscal_year",
                "uploaded_by",
                "imported_by",
            )
            .order_by("-created_at")
        )


class FECUploadView(WriteImportMixin, View):
    template_name = "imports/upload.html"

    def get(self, request):
        return render(
            request,
            self.template_name,
            {"form": FECUploadForm(organization=self.organization)},
        )

    def post(self, request):
        form = FECUploadForm(
            request.POST,
            request.FILES,
            organization=self.organization,
        )

        if form.is_valid():
            try:
                import_batch = create_fec_import(
                    organization=self.organization,
                    fiscal_year=form.cleaned_data["fiscal_year"],
                    uploaded_file=form.cleaned_data["file"],
                    user=request.user,
                    audit_metadata=request_audit_metadata(request),
                )
                import_batch = parse_fec_import(
                    import_batch=import_batch,
                    user=request.user,
                    audit_metadata=request_audit_metadata(request),
                )
            except ValidationError as exc:
                form.add_error(None, validation_error_message(exc))
            else:
                messages.success(
                    request,
                    (
                        f"FEC {import_batch.original_filename} chargé et analysé : "
                        f"{import_batch.summary.get('line_count', 0)} lignes."
                    ),
                )
                return redirect("imports:fec-detail", pk=import_batch.pk)

        return render(
            request,
            self.template_name,
            {"form": form},
            status=400,
        )


class FECImportDetailView(ActiveOrganizationMixin, FECImportObjectMixin, TemplateView):
    template_name = "imports/detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        import_batch = self.get_import_batch()

        context["import_batch"] = import_batch
        context["raw_lines"] = import_batch.raw_lines.all()[:100]
        context["errors"] = (
            import_batch.errors.select_related("raw_line")
            .order_by("severity", "created_at")[:100]
        )
        context["error_count"] = import_batch.errors.count()
        context["account_mapping_count"] = import_batch.mappings.count()
        context["journal_mapping_count"] = import_batch.journal_mappings.count()
        context["can_review"] = self.membership.role in REVIEW_ROLES
        return context


class FECParseView(WriteImportMixin, FECImportObjectMixin, View):
    def post(self, request, pk):
        import_batch = self.get_import_batch()
        try:
            parse_fec_import(
                import_batch=import_batch,
                user=request.user,
                audit_metadata=request_audit_metadata(request),
            )
        except ValidationError as exc:
            messages.error(request, validation_error_message(exc))
        else:
            messages.success(request, "Le FEC a été reparsé et les contrôles ont été recalculés.")

        return redirect("imports:fec-detail", pk=import_batch.pk)


class FECMappingView(WriteImportMixin, FECImportObjectMixin, TemplateView):
    template_name = "imports/mappings.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        import_batch = self.get_import_batch()

        account_rows = []
        for mapping in import_batch.mappings.select_related(
            "account",
            "account__chart",
        ).all():
            account_rows.append(
                {
                    "mapping": mapping,
                    "form": AccountImportMappingForm(
                        instance=mapping,
                        organization=self.organization,
                        prefix=f"account-{mapping.pk}",
                    ),
                }
            )

        journal_rows = []
        for mapping in import_batch.journal_mappings.select_related("journal").all():
            journal_rows.append(
                {
                    "mapping": mapping,
                    "form": JournalImportMappingForm(
                        instance=mapping,
                        organization=self.organization,
                        prefix=f"journal-{mapping.pk}",
                    ),
                }
            )

        context.update(
            {
                "import_batch": import_batch,
                "account_rows": account_rows,
                "journal_rows": journal_rows,
            }
        )
        return context


class FECAccountMappingUpdateView(WriteImportMixin, FECImportObjectMixin, View):
    def post(self, request, pk, mapping_id):
        import_batch = self.get_import_batch()
        mapping = get_object_or_404(
            ImportMapping.objects.select_related("account"),
            pk=mapping_id,
            import_batch=import_batch,
        )

        form = AccountImportMappingForm(
            request.POST,
            instance=mapping,
            organization=self.organization,
            prefix=f"account-{mapping.pk}",
        )

        if form.is_valid():
            try:
                mapping = update_account_mapping(
                    mapping=mapping,
                    account=form.cleaned_data["account"],
                    user=request.user,
                    audit_metadata=request_audit_metadata(request),
                )
            except ValidationError as exc:
                form.add_error(None, validation_error_message(exc))

        if getattr(request, "htmx", False):
            mapping.refresh_from_db()
            import_batch.refresh_from_db()
            return render(
                request,
                "imports/_account_mapping_response.html",
                {
                    "import_batch": import_batch,
                    "mapping": mapping,
                    "form": AccountImportMappingForm(
                        instance=mapping,
                        organization=self.organization,
                        prefix=f"account-{mapping.pk}",
                    ),
                },
                status=200 if not form.errors else 400,
            )

        if form.errors:
            for error in form.non_field_errors():
                messages.error(request, error)
        else:
            messages.success(request, f"Mapping du compte {mapping.source_account_number} mis à jour.")
        return redirect("imports:fec-mappings", pk=import_batch.pk)


class FECJournalMappingUpdateView(WriteImportMixin, FECImportObjectMixin, View):
    def post(self, request, pk, mapping_id):
        import_batch = self.get_import_batch()
        mapping = get_object_or_404(
            JournalImportMapping.objects.select_related("journal"),
            pk=mapping_id,
            import_batch=import_batch,
        )

        form = JournalImportMappingForm(
            request.POST,
            instance=mapping,
            organization=self.organization,
            prefix=f"journal-{mapping.pk}",
        )

        if form.is_valid():
            try:
                mapping = update_journal_mapping(
                    mapping=mapping,
                    journal=form.cleaned_data["journal"],
                    user=request.user,
                    audit_metadata=request_audit_metadata(request),
                )
            except ValidationError as exc:
                form.add_error(None, validation_error_message(exc))

        if getattr(request, "htmx", False):
            mapping.refresh_from_db()
            import_batch.refresh_from_db()
            return render(
                request,
                "imports/_journal_mapping_response.html",
                {
                    "import_batch": import_batch,
                    "mapping": mapping,
                    "form": JournalImportMappingForm(
                        instance=mapping,
                        organization=self.organization,
                        prefix=f"journal-{mapping.pk}",
                    ),
                },
                status=200 if not form.errors else 400,
            )

        if form.errors:
            for error in form.non_field_errors():
                messages.error(request, error)
        else:
            messages.success(request, f"Mapping du journal {mapping.source_journal_code} mis à jour.")
        return redirect("imports:fec-mappings", pk=import_batch.pk)


class FECAutoMappingView(WriteImportMixin, FECImportObjectMixin, View):
    def post(self, request, pk):
        import_batch = self.get_import_batch()
        try:
            import_batch = auto_create_unmapped_references(
                import_batch=import_batch,
                user=request.user,
                audit_metadata=request_audit_metadata(request),
            )
        except ValidationError as exc:
            messages.error(request, validation_error_message(exc))
        else:
            messages.success(
                request,
                (
                    "Mappings complétés automatiquement. "
                    f"Statut : {import_batch.get_status_display()}."
                ),
            )
        return redirect("imports:fec-mappings", pk=import_batch.pk)


class FECExecuteImportView(ReviewImportMixin, FECImportObjectMixin, View):
    def post(self, request, pk):
        import_batch = self.get_import_batch()

        try:
            import_batch = execute_fec_import(
                import_batch=import_batch,
                user=request.user,
                audit_metadata=request_audit_metadata(request),
            )
        except ValidationError as exc:
            messages.error(request, validation_error_message(exc))
        except Exception as exc:
            messages.error(
                request,
                f"Import transactionnel annulé : {exc}",
            )
        else:
            messages.success(
                request,
                (
                    f"FEC importé : "
                    f"{import_batch.summary.get('imported_entry_count', 0)} écritures / "
                    f"{import_batch.summary.get('imported_line_count', 0)} lignes."
                ),
            )

        return redirect("imports:fec-detail", pk=import_batch.pk)
