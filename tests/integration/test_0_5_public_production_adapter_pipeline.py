"""Release 0.5 cross-lot qualification for public and Production adapter contracts."""

from __future__ import annotations

import json
import subprocess
import sys
import tomllib
from pathlib import Path

from pyaccountingkit import AccountingApplication, CommandContext, Money
from pyaccountingkit.public.protocols import (
    ADAPTER_CONTRACT_VERSION,
    runtime_capabilities,
)

ROOT = Path(__file__).resolve().parents[2]


def test_release_0_5_public_and_production_adapter_contract_is_coherent() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    adapter_manifest = json.loads(
        (ROOT / "ADAPTER_CONTRACT_MANIFEST.json").read_text(encoding="utf-8")
    )
    api_manifest = json.loads(
        (ROOT / "PUBLIC_API_MANIFEST.json").read_text(encoding="utf-8")
    )

    assert pyproject["project"]["version"] == "0.5.0rc1"
    assert set(pyproject["project"]["optional-dependencies"]) >= {
        "django",
        "sqlalchemy",
        "dev",
    }

    contracts = adapter_manifest["adapter_contracts"]
    assert contracts["contract"]["current_version"] == "1"
    assert contracts["contract"]["production_adapters"] == [
        "django_postgresql",
        "sqlalchemy_postgresql",
    ]
    assert contracts["django_postgresql"]["qualification"].endswith(
        "production-qualified"
    )
    assert contracts["sqlalchemy_postgresql"]["qualification"].endswith(
        "production-qualified"
    )
    assert contracts["django_postgresql"]["public_api_orm_leakage"] is False
    assert contracts["sqlalchemy_postgresql"]["public_api_orm_leakage"] is False

    assert api_manifest["public_api"]["adapter_contract_version"] == "1"
    assert "AccountingApplication" in api_manifest["public_api"]["root_exports"]
    assert str(ADAPTER_CONTRACT_VERSION) == "1"
    assert runtime_capabilities().adapter_contract_version == ADAPTER_CONTRACT_VERSION

    assert AccountingApplication
    assert CommandContext
    assert Money


def test_release_0_5_core_import_remains_orm_neutral() -> None:
    script = (
        "import sys; import pyaccountingkit; "
        "loaded={name.split('.',1)[0] for name in sys.modules}; "
        "assert 'django' not in loaded, sorted(name for name in sys.modules if name.startswith('django')); "
        "assert 'sqlalchemy' not in loaded, "
        "sorted(name for name in sys.modules if name.startswith('sqlalchemy'))"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
