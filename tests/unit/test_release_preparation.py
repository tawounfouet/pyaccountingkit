"""Tests for fail-closed release identity and bundle integrity."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "prepare_release.py"


def _load_release_module() -> ModuleType:
    name = "pyaccountingkit_prepare_release_test"
    spec = importlib.util.spec_from_file_location(name, SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _write_project(root: Path, version: str) -> None:
    (root / "pyproject.toml").write_text(
        (
            "[project]\n"
            'name = "pyaccountingkit"\n'
            f'version = "{version}"\n'
        ),
        encoding="utf-8",
    )


def _sealed_bundle(module: ModuleType, root: Path, *, version: str, tag: str, sha: str) -> Path:
    _write_project(root, version)
    bundle = root / "release-bundle"
    dist = bundle / "dist"
    metadata = bundle / "metadata"
    dist.mkdir(parents=True)
    metadata.mkdir(parents=True)

    wheel = dist / f"pyaccountingkit-{version}-py3-none-any.whl"
    sdist = dist / f"pyaccountingkit-{version}.tar.gz"
    wheel.write_bytes(b"wheel-bytes")
    sdist.write_bytes(b"sdist-bytes")
    manifest = module._manifest_payload(
        version=version,
        tag=tag,
        sha=sha,
        artifacts=[wheel, sdist],
    )
    (metadata / "RELEASE_QUALIFICATION_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    checksums = "\n".join(
        f"{item['sha256']}  {item['filename']}" for item in manifest["artifacts"]
    )
    (metadata / "SHA256SUMS").write_text(checksums + "\n", encoding="utf-8")
    return bundle


def test_preflight_accepts_exact_current_prerelease_identity(tmp_path: Path) -> None:
    """The tag must be exactly v<pyproject version> before publication can start."""
    module = _load_release_module()
    _write_project(tmp_path, "0.7.0b1")
    sha = "a" * 40

    version, prerelease = module.preflight(
        tag="v0.7.0b1",
        sha=sha,
        root=tmp_path,
        require_main_ancestry=False,
    )

    assert version == "0.7.0b1"
    assert prerelease is True


def test_preflight_rejects_tag_version_drift(tmp_path: Path) -> None:
    """A stale or future tag cannot publish a differently versioned checkout."""
    module = _load_release_module()
    _write_project(tmp_path, "0.7.0b1")

    with pytest.raises(module.ReleasePreparationError, match="tag/version mismatch"):
        module.preflight(
            tag="v0.7.0b2",
            sha="b" * 40,
            root=tmp_path,
            require_main_ancestry=False,
        )


def test_preflight_rejects_noncanonical_commit_sha(tmp_path: Path) -> None:
    """Release provenance requires a full lowercase Git SHA."""
    module = _load_release_module()
    _write_project(tmp_path, "0.7.0b1")

    with pytest.raises(module.ReleasePreparationError, match="invalid release commit SHA"):
        module.preflight(
            tag="v0.7.0b1",
            sha="short",
            root=tmp_path,
            require_main_ancestry=False,
        )


@pytest.mark.parametrize(
    ("version", "expected"),
    [
        ("0.7.0a1", True),
        ("0.7.0b1", True),
        ("0.7.0rc1", True),
        ("0.7.0", False),
    ],
)
def test_release_type_detection(version: str, expected: bool) -> None:
    """Alpha, beta and RC tags are GitHub prereleases; stable tags are not."""
    module = _load_release_module()
    assert module.is_prerelease(version) is expected


def test_bundle_verification_accepts_untampered_artifacts(tmp_path: Path) -> None:
    """A sealed bundle remains publishable when identity and digests match."""
    module = _load_release_module()
    sha = "c" * 40
    bundle = _sealed_bundle(
        module,
        tmp_path,
        version="0.7.0b1",
        tag="v0.7.0b1",
        sha=sha,
    )

    manifest = module.verify_bundle(
        bundle_dir=bundle,
        tag="v0.7.0b1",
        sha=sha,
        root=tmp_path,
    )

    assert manifest["version"] == "0.7.0b1"
    assert manifest["release_type"] == "prerelease"
    assert len(manifest["artifacts"]) == 2


def test_bundle_verification_rejects_artifact_tampering(tmp_path: Path) -> None:
    """Any byte change after sealing must fail before a publication boundary."""
    module = _load_release_module()
    sha = "d" * 40
    bundle = _sealed_bundle(
        module,
        tmp_path,
        version="0.7.0b1",
        tag="v0.7.0b1",
        sha=sha,
    )
    wheel = bundle / "dist" / "pyaccountingkit-0.7.0b1-py3-none-any.whl"
    wheel.write_bytes(b"tampered-wheel")

    with pytest.raises(module.ReleasePreparationError, match="does not match bundle"):
        module.verify_bundle(
            bundle_dir=bundle,
            tag="v0.7.0b1",
            sha=sha,
            root=tmp_path,
        )


def test_bundle_verification_rejects_checksum_file_tampering(tmp_path: Path) -> None:
    """Checksums are themselves part of the release bundle contract."""
    module = _load_release_module()
    sha = "e" * 40
    bundle = _sealed_bundle(
        module,
        tmp_path,
        version="0.7.0b1",
        tag="v0.7.0b1",
        sha=sha,
    )
    (bundle / "metadata" / "SHA256SUMS").write_text(
        "0" * 64 + "  fake.whl\n",
        encoding="utf-8",
    )

    with pytest.raises(module.ReleasePreparationError, match="SHA256SUMS"):
        module.verify_bundle(
            bundle_dir=bundle,
            tag="v0.7.0b1",
            sha=sha,
            root=tmp_path,
        )
