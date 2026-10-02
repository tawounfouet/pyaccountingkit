#!/usr/bin/env python3
"""Prepare and verify immutable PyAccountingKit release bundles."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROJECT_NAME = "pyaccountingkit"
VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+(?:(?:a|b|rc)\d+)?$")
SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
DISTRIBUTION_SUFFIXES = (".whl", ".tar.gz")


class ReleasePreparationError(RuntimeError):
    """Raised when release preparation or verification fails."""


def project_version(root: Path = ROOT) -> str:
    """Read the canonical package version from pyproject.toml."""
    data = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    project = data["project"]
    if project.get("name") != PROJECT_NAME:
        raise ReleasePreparationError(
            f"unexpected project name: {project.get('name')!r} != {PROJECT_NAME!r}"
        )
    version = str(project["version"])
    if VERSION_PATTERN.fullmatch(version) is None:
        raise ReleasePreparationError(f"unsupported release version: {version}")
    return version


def expected_tag(version: str) -> str:
    """Return the only accepted tag for a package version."""
    return f"v{version}"


def is_prerelease(version: str) -> bool:
    """Return whether a supported PEP 440 version is a prerelease."""
    return re.search(r"(?:a|b|rc)\d+$", version) is not None


def validate_tag(tag: str, version: str) -> None:
    """Require exact tag-to-version equality."""
    expected = expected_tag(version)
    if tag != expected:
        raise ReleasePreparationError(f"tag/version mismatch: {tag!r} != {expected!r}")


def validate_sha(sha: str) -> None:
    """Require a full lowercase Git commit SHA."""
    if SHA_PATTERN.fullmatch(sha) is None:
        raise ReleasePreparationError(f"invalid release commit SHA: {sha!r}")


def ensure_commit_on_main(sha: str, root: Path = ROOT) -> None:
    """Require the tagged commit to be reachable from origin/main."""
    completed = subprocess.run(
        ["git", "merge-base", "--is-ancestor", sha, "origin/main"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or "tagged commit is not reachable from origin/main"
        raise ReleasePreparationError(detail)


def preflight(
    *,
    tag: str,
    sha: str,
    root: Path = ROOT,
    require_main_ancestry: bool = True,
) -> tuple[str, bool]:
    """Validate immutable release identity before any build or publication."""
    version = project_version(root)
    validate_tag(tag, version)
    validate_sha(sha)
    if require_main_ancestry:
        ensure_commit_on_main(sha, root)
    return version, is_prerelease(version)


def sha256_file(path: Path) -> str:
    """Return the lowercase SHA-256 digest of a file."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _distribution_files(dist_dir: Path, version: str) -> list[Path]:
    wheel = sorted(dist_dir.glob(f"{PROJECT_NAME}-{version}-*.whl"))
    sdist = sorted(dist_dir.glob(f"{PROJECT_NAME}-{version}.tar.gz"))
    if len(wheel) != 1 or len(sdist) != 1:
        raise ReleasePreparationError(
            "release bundle requires exactly one wheel and one sdist "
            f"for {version}; found wheel={len(wheel)}, sdist={len(sdist)}"
        )
    return [wheel[0], sdist[0]]


def _manifest_payload(
    *,
    version: str,
    tag: str,
    sha: str,
    artifacts: list[Path],
) -> dict[str, Any]:
    return {
        "schema_version": "1",
        "project": PROJECT_NAME,
        "version": version,
        "tag": tag,
        "commit_sha": sha,
        "release_type": "prerelease" if is_prerelease(version) else "stable",
        "qualification": {
            "required_command": "python scripts/qualify_release.py --release-candidate",
            "workflow_gate": "preflight",
            "fail_closed": True,
        },
        "artifacts": [
            {
                "filename": path.name,
                "sha256": sha256_file(path),
                "size": path.stat().st_size,
            }
            for path in sorted(artifacts, key=lambda item: item.name)
        ],
        "provenance": {
            "repository": os.environ.get("GITHUB_REPOSITORY", ""),
            "workflow": os.environ.get("GITHUB_WORKFLOW", ""),
            "run_id": os.environ.get("GITHUB_RUN_ID", ""),
            "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT", ""),
        },
    }


def build_bundle(*, bundle_dir: Path, tag: str, sha: str, root: Path = ROOT) -> dict[str, Any]:
    """Build one qualified wheel/sdist pair and seal its release metadata."""
    version = project_version(root)
    validate_tag(tag, version)
    validate_sha(sha)

    if bundle_dir.exists():
        shutil.rmtree(bundle_dir)
    dist_dir = bundle_dir / "dist"
    metadata_dir = bundle_dir / "metadata"
    dist_dir.mkdir(parents=True)
    metadata_dir.mkdir(parents=True)

    subprocess.run(
        [
            sys.executable,
            str(root / "scripts" / "verify_package.py"),
            "--dist-dir",
            str(dist_dir),
        ],
        cwd=root,
        check=True,
    )
    artifacts = _distribution_files(dist_dir, version)
    manifest = _manifest_payload(version=version, tag=tag, sha=sha, artifacts=artifacts)

    manifest_path = metadata_dir / "RELEASE_QUALIFICATION_MANIFEST.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    checksum_lines = [
        f"{item['sha256']}  {item['filename']}" for item in manifest["artifacts"]
    ]
    (metadata_dir / "SHA256SUMS").write_text(
        "\n".join(checksum_lines) + "\n",
        encoding="utf-8",
    )
    return manifest


def verify_bundle(*, bundle_dir: Path, tag: str, sha: str, root: Path = ROOT) -> dict[str, Any]:
    """Recompute release integrity before each publication boundary."""
    version = project_version(root)
    validate_tag(tag, version)
    validate_sha(sha)

    dist_dir = bundle_dir / "dist"
    metadata_dir = bundle_dir / "metadata"
    manifest_path = metadata_dir / "RELEASE_QUALIFICATION_MANIFEST.json"
    checksum_path = metadata_dir / "SHA256SUMS"
    if not manifest_path.is_file() or not checksum_path.is_file():
        raise ReleasePreparationError("release bundle metadata is incomplete")

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ReleasePreparationError(f"invalid release manifest JSON: {exc}") from exc
    if not isinstance(manifest, dict):
        raise ReleasePreparationError("release manifest must be a JSON object")

    expected_identity = {
        "schema_version": "1",
        "project": PROJECT_NAME,
        "version": version,
        "tag": tag,
        "commit_sha": sha,
        "release_type": "prerelease" if is_prerelease(version) else "stable",
    }
    for key, expected in expected_identity.items():
        if manifest.get(key) != expected:
            raise ReleasePreparationError(
                f"release manifest identity mismatch for {key}: "
                f"{manifest.get(key)!r} != {expected!r}"
            )

    artifacts = _distribution_files(dist_dir, version)
    raw_artifacts = manifest.get("artifacts")
    if not isinstance(raw_artifacts, list) or len(raw_artifacts) != 2:
        raise ReleasePreparationError("release manifest must describe exactly two distributions")

    expected_entries = []
    for path in sorted(artifacts, key=lambda item: item.name):
        expected_entries.append(
            {
                "filename": path.name,
                "sha256": sha256_file(path),
                "size": path.stat().st_size,
            }
        )
    if raw_artifacts != expected_entries:
        raise ReleasePreparationError("release artifact digest/size manifest does not match bundle")

    expected_checksums = "\n".join(
        f"{item['sha256']}  {item['filename']}" for item in expected_entries
    ) + "\n"
    if checksum_path.read_text(encoding="utf-8") != expected_checksums:
        raise ReleasePreparationError("SHA256SUMS does not match release artifacts")
    return manifest


def _write_github_output(path: Path, *, version: str, prerelease: bool) -> None:
    with path.open("a", encoding="utf-8") as stream:
        stream.write(f"version={version}\n")
        stream.write(f"prerelease={'true' if prerelease else 'false'}\n")


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    preflight_parser = subparsers.add_parser("preflight")
    preflight_parser.add_argument("--tag", required=True)
    preflight_parser.add_argument("--sha", required=True)
    preflight_parser.add_argument("--github-output", type=Path)

    build_parser = subparsers.add_parser("build")
    build_parser.add_argument("--bundle-dir", type=Path, required=True)
    build_parser.add_argument("--tag", required=True)
    build_parser.add_argument("--sha", required=True)

    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("--bundle-dir", type=Path, required=True)
    verify_parser.add_argument("--tag", required=True)
    verify_parser.add_argument("--sha", required=True)

    args = parser.parse_args()

    try:
        if args.command == "preflight":
            version, prerelease = preflight(tag=args.tag, sha=args.sha)
            if args.github_output is not None:
                _write_github_output(
                    args.github_output,
                    version=version,
                    prerelease=prerelease,
                )
            print("Release preflight: PASS")
            print(f"Version: {version}")
            print(f"Tag: {args.tag}")
            print(f"Commit: {args.sha}")
            print(f"Prerelease: {str(prerelease).lower()}")
        elif args.command == "build":
            manifest = build_bundle(
                bundle_dir=args.bundle_dir.resolve(),
                tag=args.tag,
                sha=args.sha,
            )
            print("Release bundle build: PASS")
            print(f"Version: {manifest['version']}")
            print(f"Artifacts: {len(manifest['artifacts'])}")
        else:
            manifest = verify_bundle(
                bundle_dir=args.bundle_dir.resolve(),
                tag=args.tag,
                sha=args.sha,
            )
            print("Release bundle verification: PASS")
            print(f"Version: {manifest['version']}")
    except (ReleasePreparationError, subprocess.CalledProcessError, OSError) as exc:
        print(f"Release preparation: FAIL: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
