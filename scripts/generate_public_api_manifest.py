#!/usr/bin/env python3
"""Generate PUBLIC_API_MANIFEST.json deterministically from public source exports."""

from __future__ import annotations

from manifest_generation import parse_check_flag, project_version, write_or_check

import pyaccountingkit
import pyaccountingkit.public
import pyaccountingkit.public.protocols
from pyaccountingkit.public.protocols import ADAPTER_CONTRACT_VERSION

_FILENAME = "PUBLIC_API_MANIFEST.json"


def build_payload() -> dict[str, object]:
    root_exports = sorted(pyaccountingkit.__all__)
    public_exports = sorted(pyaccountingkit.public.__all__)
    extension_exports = sorted(pyaccountingkit.public.protocols.__all__)
    return {
        "version": project_version(),
        "public_api": {
            "stability": "pre-1.0-alpha",
            "stable_exports": [name for name in root_exports if name != "__version__"],
            "root_exports": root_exports,
            "public_package_exports": public_exports,
            "extension_exports": extension_exports,
            "adapter_contract_version": str(ADAPTER_CONTRACT_VERSION),
            "note": (
                "LOT-22 / 0.5.0a2 formalizes the adapter-author extension API separately "
                "from the LOT-21 user facade. Public and extension symbol inventories are "
                "generated deterministically from explicit __all__ declarations; adapter "
                "contract v1 is published without freezing the full pre-1.0 Python API."
            ),
        },
    }


def main() -> int:
    check = parse_check_flag(__doc__ or "")
    return write_or_check(filename=_FILENAME, payload=build_payload(), check=check)


if __name__ == "__main__":
    raise SystemExit(main())
