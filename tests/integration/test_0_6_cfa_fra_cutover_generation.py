"""Integration tests for the CFA FRA cutover artifact generation CLI."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from pyaccountingkit.integrations.cfa_fra import (
    LegacyIdentityMigrationArtifact,
    RegulatoryAuthorityCutoverArtifact,
    parse_cutover_artifact,
)

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "generate_cfa_fra_cutover_artifact.py"
FIXTURES = ROOT / "tests" / "fixtures" / "cfa_fra_cutover_generation"


def _command(
    key: str,
    source: Path,
    *,
    artifact_root: Path,
    artifact: str,
    write: bool = False,
    overwrite: bool = False,
) -> list[str]:
    command = [
        sys.executable,
        str(SCRIPT),
        key,
        "--source",
        str(source),
        "--artifact",
        artifact,
        "--artifact-root",
        str(artifact_root),
    ]
    if write:
        command.append("--write")
    if overwrite:
        command.append("--overwrite")
    return command


def test_identity_generator_cli_is_dry_run_by_default(tmp_path) -> None:
    result = subprocess.run(
        _command(
            "legacy_identities",
            FIXTURES / "identity-source.json",
            artifact_root=tmp_path,
            artifact="identities.json",
        ),
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Dry-run only" in result.stdout
    assert not (tmp_path / "identities.json").exists()
    payload = json.loads(result.stdout.split("\nDry-run only:", maxsplit=1)[0])
    assert payload["summary"]["unresolved_records"] == 0
    assert [item["legacy_id"] for item in payload["mappings"]] == [
        "legacy-1",
        "legacy-2",
    ]


def test_identity_generator_cli_materializes_valid_artifact(tmp_path) -> None:
    result = subprocess.run(
        _command(
            "legacy_identities",
            FIXTURES / "identity-source.json",
            artifact_root=tmp_path,
            artifact="identities.json",
            write=True,
        ),
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    parsed = parse_cutover_artifact(
        "legacy_identities",
        tmp_path / "identities.json",
    )
    assert isinstance(parsed, LegacyIdentityMigrationArtifact)
    assert len(parsed.links) == 2


def test_regulatory_generator_cli_materializes_valid_artifact(tmp_path) -> None:
    result = subprocess.run(
        _command(
            "regulatory_authority",
            FIXTURES / "regulatory-source.json",
            artifact_root=tmp_path,
            artifact="authority.json",
            write=True,
        ),
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    parsed = parse_cutover_artifact(
        "regulatory_authority",
        tmp_path / "authority.json",
    )
    assert isinstance(parsed, RegulatoryAuthorityCutoverArtifact)
    assert parsed.provider_name == "PyAccountingKit"


def test_generator_cli_refuses_overwrite_without_explicit_flag(tmp_path) -> None:
    target = tmp_path / "identities.json"
    first = subprocess.run(
        _command(
            "legacy_identities",
            FIXTURES / "identity-source.json",
            artifact_root=tmp_path,
            artifact=target.name,
            write=True,
        ),
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert first.returncode == 0, first.stdout + first.stderr

    second = subprocess.run(
        _command(
            "legacy_identities",
            FIXTURES / "identity-source.json",
            artifact_root=tmp_path,
            artifact=target.name,
            write=True,
        ),
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert second.returncode != 0
    assert "use --overwrite explicitly" in second.stderr
