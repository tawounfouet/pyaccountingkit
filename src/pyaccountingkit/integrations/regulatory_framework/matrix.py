"""Deterministic regulatory compatibility matrix rendering (LOT-27)."""

from __future__ import annotations

from collections.abc import Iterable

from pyaccountingkit.integrations.regulatory_framework.baseline import (
    PROVIDER_ID,
    PROVIDER_VERSION,
)
from pyaccountingkit.integrations.regulatory_framework.qualification import (
    RegulatoryFrameworkIntegrationProfile,
)


def regulatory_compatibility_matrix_payload(
    framework_version: str,
    profiles: Iterable[RegulatoryFrameworkIntegrationProfile],
) -> dict[str, object]:
    """Render capability-scoped profiles without synthesizing unsupported capabilities."""
    ordered = sorted(profiles, key=lambda profile: profile.standard_ref)
    if len({profile.standard_ref for profile in ordered}) != len(ordered):
        raise ValueError("regulatory compatibility matrix requires unique standard_ref values")
    for profile in ordered:
        if profile.tested_framework_version != framework_version:
            raise ValueError(
                f"profile {profile.standard_ref} targets "
                f"{profile.tested_framework_version}, expected {framework_version}"
            )

    return {
        "version": framework_version,
        "qualification_model": "capability-scoped/v1",
        "regulatory_source": {
            "provider_id": PROVIDER_ID,
            "provider_version": PROVIDER_VERSION,
        },
        "regulatory_frameworks": [profile.to_payload() for profile in ordered],
    }


__all__ = ["regulatory_compatibility_matrix_payload"]
