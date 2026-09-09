from .models import OrganizationMembership

def organization_context(request):
    if not request.user.is_authenticated:
        return {
            "active_organization": None,
            "available_organizations": [],
            "active_membership": None,
        }

    memberships = list(
        OrganizationMembership.objects.filter(
            user=request.user,
            is_active=True,
            organization__is_active=True,
        )
        .select_related("organization")
        .order_by("organization__name")
    )

    active_id = request.session.get("active_organization_id")
    active_membership = next(
        (membership for membership in memberships if str(membership.organization_id) == str(active_id)),
        None,
    )

    if active_membership is None and memberships:
        active_membership = memberships[0]
        request.session["active_organization_id"] = str(active_membership.organization_id)

    return {
        "active_organization": active_membership.organization if active_membership else None,
        "available_organizations": [m.organization for m in memberships],
        "active_membership": active_membership,
    }
