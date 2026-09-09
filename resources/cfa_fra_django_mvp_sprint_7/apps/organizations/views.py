from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DetailView, ListView

from .forms import FiscalYearForm, OrganizationForm
from .models import AccountingPeriod, FiscalYear, Organization, OrganizationMembership
from .permissions import WRITE_ROLES, get_membership_or_403, require_role
from .services import ensure_accounting_settings, generate_monthly_periods
from apps.accounting.services import bootstrap_accounting_core

class OrganizationListView(LoginRequiredMixin, ListView):
    model = Organization
    template_name = "organizations/list.html"
    context_object_name = "organizations"

    def get_queryset(self):
        return (
            Organization.objects.filter(
                memberships__user=self.request.user,
                memberships__is_active=True,
                is_active=True,
            )
            .distinct()
            .order_by("name")
        )

class OrganizationCreateView(LoginRequiredMixin, CreateView):
    model = Organization
    form_class = OrganizationForm
    template_name = "organizations/form.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        OrganizationMembership.objects.create(
            organization=self.object,
            user=self.request.user,
            role=OrganizationMembership.Role.ADMIN,
        )
        ensure_accounting_settings(organization=self.object)
        bootstrap_accounting_core(organization=self.object)
        self.request.session["active_organization_id"] = str(self.object.id)
        messages.success(self.request, "Organisation créée avec succès.")
        return response

    def get_success_url(self):
        return reverse_lazy("organizations:detail", kwargs={"pk": self.object.pk})

class OrganizationDetailView(LoginRequiredMixin, DetailView):
    model = Organization
    template_name = "organizations/detail.html"
    context_object_name = "organization"

    def get_queryset(self):
        return (
            Organization.objects.filter(
                memberships__user=self.request.user,
                memberships__is_active=True,
            )
            .prefetch_related("fiscal_years__periods")
        )

class FiscalYearCreateView(LoginRequiredMixin, CreateView):
    model = FiscalYear
    form_class = FiscalYearForm
    template_name = "organizations/fiscal_year_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.organization = get_object_or_404(Organization, pk=kwargs["organization_id"])
        membership = get_membership_or_403(user=request.user, organization=self.organization)
        require_role(membership=membership, allowed_roles=WRITE_ROLES)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.organization = self.organization
        response = super().form_valid(form)
        generate_monthly_periods(fiscal_year=self.object)
        messages.success(
            self.request,
            f"Exercice {self.object.name} créé avec ses périodes mensuelles.",
        )
        return response

    def get_success_url(self):
        return reverse_lazy("organizations:detail", kwargs={"pk": self.organization.pk})

class SwitchOrganizationView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        organization_id = request.POST.get("organization_id")
        if not organization_id:
            return HttpResponseBadRequest("Organisation manquante.")

        organization = get_object_or_404(Organization, pk=organization_id, is_active=True)
        get_membership_or_403(user=request.user, organization=organization)

        request.session["active_organization_id"] = str(organization.id)

        if getattr(request, "htmx", False):
            response = redirect(request.headers.get("HX-Current-URL", "/"))
            response["HX-Refresh"] = "true"
            return response

        return redirect("analytics:dashboard")
