from django.core.exceptions import PermissionDenied

from .models import OrganizationMembership

WRITE_ROLES = {
    OrganizationMembership.Role.ADMIN,
    OrganizationMembership.Role.ACCOUNTANT,
    OrganizationMembership.Role.REVIEWER,
}

REVIEW_ROLES = {
    OrganizationMembership.Role.ADMIN,
    OrganizationMembership.Role.REVIEWER,
}

def get_membership_or_403(*, user, organization):
    try:
        return OrganizationMembership.objects.get(
            user=user,
            organization=organization,
            is_active=True,
            organization__is_active=True,
        )
    except OrganizationMembership.DoesNotExist as exc:
        raise PermissionDenied("Vous n'avez pas accès à cette organisation.") from exc

def require_role(*, membership, allowed_roles):
    if membership.role not in allowed_roles:
        raise PermissionDenied("Vous ne disposez pas du rôle requis.")
