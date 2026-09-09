#!/usr/bin/env python3
"""Build and verify PyAccountingKit distribution artifacts in isolation."""

from __future__ import annotations

import argparse
import subprocess
import sys
import tarfile
import tempfile
import tomllib
import venv
import zipfile
from email.parser import Parser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_IMPORT = "pyaccountingkit"


class VerificationError(RuntimeError):
    """Raised when package verification fails."""


def project_metadata() -> tuple[str, str, list[str]]:
    """Read canonical project name, version and runtime dependencies."""
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = data["project"]
    name = str(project["name"])
    version = str(project["version"])
    dependencies = [str(item) for item in project.get("dependencies", [])]
    return name, version, dependencies


def run(command: list[str]) -> None:
    """Run a subprocess from the repository root and fail on error."""
    print("+", " ".join(command))
    subprocess.run(command, cwd=ROOT, check=True)


def build_distributions(dist_dir: Path) -> None:
    """Build wheel and sdist into the requested directory."""
    dist_dir.mkdir(parents=True, exist_ok=True)
    run([sys.executable, "-m", "build", "--outdir", str(dist_dir)])


def select_artifacts(dist_dir: Path, version: str) -> tuple[Path, Path]:
    """Select exactly one wheel and one sdist for the expected version."""
    wheel_candidates = sorted(dist_dir.glob(f"pyaccountingkit-{version}-*.whl"))
    sdist_candidates = sorted(dist_dir.glob(f"pyaccountingkit-{version}.tar.gz"))
    if len(wheel_candidates) != 1:
        raise VerificationError(
            f"expected exactly one wheel for {version}, found {len(wheel_candidates)}"
        )
    if len(sdist_candidates) != 1:
        raise VerificationError(
            f"expected exactly one sdist for {version}, found {len(sdist_candidates)}"
        )
    return wheel_candidates[0], sdist_candidates[0]


def verify_wheel(wheel: Path, expected_name: str, expected_version: str) -> None:
    """Validate wheel structure and core metadata."""
    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())
        required = {
            f"{PACKAGE_IMPORT}/__init__.py",
            f"{PACKAGE_IMPORT}/py.typed",
        }
        missing = sorted(required - names)
        if missing:
            raise VerificationError(f"wheel missing required files: {missing}")

        metadata_files = [name for name in names if name.endswith(".dist-info/METADATA")]
        if len(metadata_files) != 1:
            raise VerificationError("wheel must contain exactly one METADATA file")
        metadata_text = archive.read(metadata_files[0]).decode("utf-8")
        metadata = Parser().parsestr(metadata_text)
        if metadata.get("Name") != expected_name:
            raise VerificationError(
                f"wheel Name mismatch: {metadata.get('Name')} != {expected_name}"
            )
        if metadata.get("Version") != expected_version:
            raise VerificationError(
                f"wheel Version mismatch: {metadata.get('Version')} != {expected_version}"
            )

        forbidden_prefixes = ("tests/", "docs/", "resources/", "data/")
        leaked = sorted(name for name in names if name.startswith(forbidden_prefixes))
        if leaked:
            raise VerificationError(f"wheel contains repository-only content: {leaked[:10]}")


def verify_sdist(sdist: Path, version: str) -> None:
    """Validate that the sdist contains the reproducibility-critical files."""
    prefix = f"pyaccountingkit-{version}/"
    required_suffixes = {
        "pyproject.toml",
        "README.md",
        "LICENSE",
        "src/pyaccountingkit/__init__.py",
        "src/pyaccountingkit/py.typed",
    }
    with tarfile.open(sdist, mode="r:gz") as archive:
        names = set(archive.getnames())
    missing = sorted(item for item in required_suffixes if prefix + item not in names)
    if missing:
        raise VerificationError(f"sdist missing required files: {missing}")


def verify_isolated_import(wheel: Path, expected_version: str) -> None:
    """Install the wheel into a fresh venv and verify import/version metadata."""
    with tempfile.TemporaryDirectory(prefix="pyaccountingkit-venv-") as temp_dir:
        env_dir = Path(temp_dir) / "venv"
        venv.EnvBuilder(with_pip=True, clear=True).create(env_dir)
        if sys.platform == "win32":
            python = env_dir / "Scripts" / "python.exe"
        else:
            python = env_dir / "bin" / "python"

        run([str(python), "-m", "pip", "install", "--quiet", "--no-deps", str(wheel)])
        code = (
            "import pyaccountingkit; "
            "print(pyaccountingkit.__version__); "
            "print(pyaccountingkit.__file__)"
        )
        completed = subprocess.run(
            [str(python), "-c", code],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        lines = completed.stdout.strip().splitlines()
        if not lines or lines[0] != expected_version:
            actual = lines[0] if lines else "<no output>"
            raise VerificationError(
                f"isolated import version mismatch: {actual} != {expected_version}"
            )


def verify(dist_dir: Path) -> None:
    """Run the full build and package verification sequence."""
    name, version, dependencies = project_metadata()
    if name != PACKAGE_IMPORT:
        raise VerificationError(f"unexpected project name: {name}")
    if version == "0.0.1" and dependencies:
        raise VerificationError(
            f"bootstrap 0.0.1 must have zero runtime dependencies: {dependencies}"
        )

    build_distributions(dist_dir)
    wheel, sdist = select_artifacts(dist_dir, version)
    run([sys.executable, "-m", "twine", "check", str(wheel), str(sdist)])
    verify_wheel(wheel, name, version)
    verify_sdist(sdist, version)
    verify_isolated_import(wheel, version)

    print("Package verification: PASS")
    print(f"Wheel: {wheel.name}")
    print(f"Sdist: {sdist.name}")
    print(f"Runtime dependencies: {len(dependencies)}")


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dist-dir",
        type=Path,
        help="Persist build artifacts in this directory instead of a temporary directory.",
    )
    args = parser.parse_args()

    try:
        if args.dist_dir is not None:
            verify(args.dist_dir.resolve())
        else:
            with tempfile.TemporaryDirectory(prefix="pyaccountingkit-dist-") as temp_dir:
                verify(Path(temp_dir))
    except (VerificationError, subprocess.CalledProcessError, OSError) as exc:
        print(f"Package verification: FAIL: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
