"""Release 0.6 consumer-conversion integration qualification for LOT-26."""

from __future__ import annotations

import json
import subprocess
import sys
import tomllib
from pathlib import Path

from pyaccountingkit import AccountingApplication, CommandContext
from pyaccountingkit.integrations.cfa_fra import (
    CFAFRACompatibilityAdapter,
    DualRunObservation,
    MigrationRouting,
    MutationBackend,
    ReadBackend,
)

ROOT = Path(__file__).resolve().parents[2]


class _Entries:
    def __init__(self) -> None:
        self.posts = 0

    def post(self, **parameters: object) -> dict[str, object]:
        self.posts += 1
        return {"backend": "pyaccountingkit", "entry_id": parameters["entry_id"]}


class _Ledger:
    def __init__(self) -> None:
        self.reads = 0

    def trial_balance(self, **parameters: object) -> dict[str, object]:
        self.reads += 1
        return {"period_id": parameters["period_id"], "total": "100.00"}


class _Legacy:
    def __init__(self) -> None:
        self.posts = 0
        self.reads = 0

    def post_entry(self, **parameters: object) -> dict[str, object]:
        self.posts += 1
        return {"backend": "legacy", "entry_id": parameters["entry_id"]}

    def trial_balance(self, **parameters: object) -> dict[str, object]:
        self.reads += 1
        return {"period_id": parameters["period_id"], "total": "100.00"}


def _context(_user: object) -> CommandContext:
    return CommandContext(actor="cfa-consumer", correlation_id="lot-26-e2e")


def test_release_0_6_consumer_cutover_is_single_writer_with_shadow_read() -> None:
    entries = _Entries()
    ledger = _Ledger()
    legacy = _Legacy()
    observations: list[DualRunObservation] = []
    adapter = CFAFRACompatibilityAdapter(
        AccountingApplication(entries=entries, ledger=ledger),
        legacy_service=legacy,
        routing=MigrationRouting(
            mutation_routes={"post_entry": MutationBackend.PYACCOUNTINGKIT},
            read_routes={"trial_balance": ReadBackend.LEGACY},
            dual_run_reads=frozenset({"trial_balance"}),
        ),
        context_factory=_context,
        comparator=lambda legacy_result, target_result: legacy_result == target_result,
        observation_sink=observations.append,
    )

    posted = adapter.post_entry(entry_id="legacy-entry-42", user=object())
    balance = adapter.trial_balance(period_id="2026-12", user=object())

    assert posted == {"backend": "pyaccountingkit", "entry_id": "legacy-entry-42"}
    assert entries.posts == 1
    assert legacy.posts == 0

    assert balance == {"period_id": "2026-12", "total": "100.00"}
    assert legacy.reads == 1
    assert ledger.reads == 1
    assert observations == [
        DualRunObservation(
            operation="trial_balance",
            primary_backend=ReadBackend.LEGACY,
            matched=True,
        )
    ]


def test_release_0_6_metadata_and_legacy_runtime_boundary_are_coherent() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    version = str(pyproject["project"]["version"])
    assert version in {
        "0.6.0b1",
        "0.6.0b2",
        "0.6.0b3",
        "0.6.0b4",
        "0.6.0b5",
        "0.6.0b6",
        "0.6.0b7",
        "0.6.0b8",
        "0.6.0b9",
        "0.6.0b10",
        "0.6.0b11",
        "0.6.0b12",
        "0.6.0rc1",
        "0.6.0",
    }

    public_manifest = json.loads((ROOT / "PUBLIC_API_MANIFEST.json").read_text(encoding="utf-8"))
    adapter_manifest = json.loads(
        (ROOT / "ADAPTER_CONTRACT_MANIFEST.json").read_text(encoding="utf-8")
    )
    assert public_manifest["version"] == version
    assert adapter_manifest["version"] == version
    assert adapter_manifest["adapter_contracts"]["contract"]["current_version"] == "1"

    script = (
        "import sys; "
        "from pyaccountingkit.integrations.cfa_fra import CFAFRACompatibilityAdapter; "
        "assert CFAFRACompatibilityAdapter; "
        "loaded={name.split('.',1)[0] for name in sys.modules}; "
        "assert 'django' not in loaded; "
        "assert 'sqlalchemy' not in loaded"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
