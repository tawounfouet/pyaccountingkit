from django.db.models import Q
from django.views.generic import ListView

from apps.organizations.mixins import ActiveOrganizationMixin

from .models import AuditEvent


class AuditListView(ActiveOrganizationMixin, ListView):
    model = AuditEvent
    template_name = "audit/list.html"
    context_object_name = "events"
    paginate_by = 50

    def get_queryset(self):
        qs = (
            AuditEvent.objects.filter(organization=self.organization)
            .select_related("actor")
            .order_by("-created_at")
        )

        query = self.request.GET.get("q", "").strip()
        action = self.request.GET.get("action", "").strip()

        if query:
            qs = qs.filter(
                Q(entity_id__icontains=query)
                | Q(entity_type__icontains=query)
                | Q(action__icontains=query)
            )
        if action:
            qs = qs.filter(action=action)

        return qs

    def get_template_names(self):
        if getattr(self.request, "htmx", False):
            return ["audit/_table.html"]
        return [self.template_name]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["actions"] = (
            AuditEvent.objects.filter(organization=self.organization)
            .order_by("action")
            .values_list("action", flat=True)
            .distinct()
        )
        return context
