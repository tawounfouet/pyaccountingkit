#!/usr/bin/env python3
"""Generate PUBLIC_API_MANIFEST.json deterministically from public source exports."""

from __future__ import annotations

from manifest_generation import parse_check_flag, project_version, write_or_check

import pyaccountingkit
import pyaccountingkit.public
import pyaccountingkit.public.protocols
from pyaccountingkit.public.protocols import ADAPTER_CONTRACT_VERSION

_FILENAME = "PUBLIC_API_MANIFEST.json"


def _stability(version: str) -> str:
    if "rc" in version:
        return "pre-1.0-release-candidate"
    if "a" in version or "b" in version:
        return "pre-1.0-prerelease"
    return "pre-1.0-stable-release"


def build_payload() -> dict[str, object]:
    version = project_version()
    root_exports = sorted(pyaccountingkit.__all__)
    public_exports = sorted(pyaccountingkit.public.__all__)
    extension_exports = sorted(pyaccountingkit.public.protocols.__all__)
    return {
        "version": version,
        "public_api": {
            "stability": _stability(version),
            "stable_exports": [name for name in root_exports if name != "__version__"],
            "root_exports": root_exports,
            "public_package_exports": public_exports,
            "extension_exports": extension_exports,
            "adapter_contract_version": str(ADAPTER_CONTRACT_VERSION),
            "note": (
                "The 0.5 line exposes the framework-neutral LOT-21 user facade and the "
                "separate LOT-22 adapter-author extension API on adapter contract v1. "
                "Django/PostgreSQL and SQLAlchemy/PostgreSQL are Production-qualified "
                "without freezing the full pre-1.0 Python API."
            ),
        },
    }


def main() -> int:
    check = parse_check_flag(__doc__ or "")
    return write_or_check(filename=_FILENAME, payload=build_payload(), check=check)


if __name__ == "__main__":
    raise SystemExit(main())
