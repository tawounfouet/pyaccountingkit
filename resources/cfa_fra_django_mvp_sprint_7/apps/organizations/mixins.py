from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect

from .models import OrganizationMembership
from .permissions import require_role


class ActiveOrganizationMixin(LoginRequiredMixin):
    # Resolve and scope the active organization from the authenticated user's memberships.

    allowed_roles = None

    def dispatch(self, request, *args, **kwargs):
        memberships = (
            OrganizationMembership.objects.filter(
                user=request.user,
                is_active=True,
                organization__is_active=True,
            )
            .select_related("organization")
            .order_by("organization__name")
        )

        membership_list = list(memberships)
        if not membership_list:
            return redirect("organizations:create")

        active_id = request.session.get("active_organization_id")
        membership = next(
            (
                item
                for item in membership_list
                if str(item.organization_id) == str(active_id)
            ),
            None,
        )
        if membership is None:
            membership = membership_list[0]
            request.session["active_organization_id"] = str(membership.organization_id)

        if self.allowed_roles:
            require_role(membership=membership, allowed_roles=self.allowed_roles)

        self.organization = membership.organization
        self.membership = membership
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["organization"] = self.organization
        context["membership"] = self.membership
        return context
