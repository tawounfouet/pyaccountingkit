"""FND-C06: exact-source and distributable migration integrity qualification.

A pinned, already CI-qualified implementation commit is the immutable reference
for the 14 SQL migrations. No database connection or production changes occur.
This is an artifact packaging qualification, NOT a G0/G1/G2 approval or release.
"""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import tarfile
import zipfile
from pathlib import Path

BASELINE_COMMIT = "70593b9a7ac08683f2776a18c15988d2ddbaf9a6"
MIGRATIONS = Path(
    "src/pyaccountingkit/company_configuration/infrastructure/postgres/migrations"
)
PACKAGE_PREFIX = "pyaccountingkit/company_configuration/infrastructure/postgres/migrations/"
EXPECTED_NUMBERS = tuple(range(1, 15))


class ArtifactQualificationError(RuntimeError):
    """Migrations or distributable artifacts are not the reviewed baseline."""


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def frozen_migration_digests(checkout: Path) -> dict[str, str]:
    """Compare every current migration's bytes with pinned Git commit contents."""
    folder = checkout / MIGRATIONS
    filenames = sorted(p.name for p in folder.glob("*.sql"))
    numbers = []
    for filename in filenames:
        if len(filename) < 6 or not filename[:4].isdigit() or filename[4] != "_":
            raise ArtifactQualificationError("Unexpected migration SQL filename")
        numbers.append(int(filename[:4]))
    if tuple(numbers) != EXPECTED_NUMBERS:
        raise ArtifactQualificationError("Expected exactly contiguous migrations 0001-0014")
    digests = {}
    for filename in filenames:
        relative = (MIGRATIONS / filename).as_posix()
        result = subprocess.run(
            ["git", "show", f"{BASELINE_COMMIT}:{relative}"],
            cwd=checkout, capture_output=True, check=False,
        )
        if result.returncode != 0:
            raise ArtifactQualificationError(
                f"Pinned Git migration source missing: {filename}"
            )
        current = (folder / filename).read_bytes()
        if current != result.stdout:
            raise ArtifactQualificationError(
                f"Migration drift from the reviewed source: {filename}"
            )
        digests[filename] = _digest(current)
    return digests


def verify_wheel(wheel: Path, digests: dict[str, str]) -> None:
    """Wheel must contain exactly the original SQL migration bytes."""
    with zipfile.ZipFile(wheel) as archive:
        files = archive.namelist()
        members = sorted(
            name for name in files if name.startswith(PACKAGE_PREFIX)
            and name.endswith(".sql")
        )
        expected = sorted(PACKAGE_PREFIX + name for name in digests)
        if members != expected:
            raise ArtifactQualificationError("Wheel migration inventory mismatch")
        for member in members:
            filename = member.removeprefix(PACKAGE_PREFIX)
            if _digest(archive.read(member)) != digests[filename]:
                raise ArtifactQualificationError(f"Wheel migration drift: {filename}")
        metadata = [name for name in files if name.endswith(".dist-info/METADATA")]
        if len(metadata) != 1:
            raise ArtifactQualificationError("Expected one wheel package metadata file")
        body = archive.read(metadata[0]).decode("utf-8")
        if "Name: pyaccountingkit\n" not in body or "Version: 0.0.0\n" not in body:
            raise ArtifactQualificationError("Foundation artifact is not the 0.0.0 scaffold")


def verify_sdist(sdist: Path, digests: dict[str, str]) -> None:
    """Source distribution must carry an identical checked SQL inventory."""
    with tarfile.open(sdist, "r:gz") as archive:
        members = [
            item for item in archive.getmembers()
            if item.isfile() and "/src/" in item.name
            and "/company_configuration/infrastructure/postgres/migrations/" in item.name
            and item.name.endswith(".sql")
        ]
        filenames = sorted(item.name.rsplit("/", 1)[-1] for item in members)
        if filenames != sorted(digests):
            raise ArtifactQualificationError("Sdist migration inventory mismatch")
        for item in members:
            source = archive.extractfile(item)
            if source is None:
                raise ArtifactQualificationError("Missing source distribution file")
            filename = item.name.rsplit("/", 1)[-1]
            if _digest(source.read()) != digests[filename]:
                raise ArtifactQualificationError(f"Sdist migration drift: {filename}")


def qualify(checkout: Path, dist: Path) -> dict[str, str]:
    digests = frozen_migration_digests(checkout)
    wheels = sorted(dist.glob("*.whl"))
    sdists = sorted(dist.glob("*.tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1:
        raise ArtifactQualificationError("Exactly one wheel and one sdist required")
    verify_wheel(wheels[0], digests)
    verify_sdist(sdists[0], digests)
    return digests


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkout", type=Path, default=Path.cwd())
    parser.add_argument("--dist", type=Path, default=Path("dist"))
    args = parser.parse_args()
    verified = qualify(args.checkout.resolve(), args.dist.resolve())
    for filename, digest in verified.items():
        print(f"SHA256 {digest}  {filename}")
    print("FND-C06: 14 immutable source + wheel + sdist migrations VERIFIED")
