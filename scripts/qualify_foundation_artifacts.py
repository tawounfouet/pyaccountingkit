"""FND-C06: qualify source, sdist and wheel as the SAME standalone Foundation.

Standard-library only. Fail closed if one numbered migration is absent, edited,
duplicated, or differs between source, sdist and wheel. No package publication,
schema changes or production IAM attestations are performed by this script.
"""

from __future__ import annotations

import hashlib
import sys
import tarfile
import zipfile
from pathlib import Path

MIGRATIONS = Path(
    "src/pyaccountingkit/company_configuration/infrastructure/postgres/migrations"
)
WHEEL_MIGRATIONS = (
    "pyaccountingkit/company_configuration/infrastructure/postgres/migrations"
)
EXPECTED_VERSION = "0.0.0"
EXPECTED_MIGRATION_NUMBERS = tuple(range(1, 18))
REQUIRED_MODULES = (
    "pyaccountingkit/__init__.py",
    "pyaccountingkit/company_configuration/__init__.py",
    "pyaccountingkit/company_configuration/domain/shared/effective_interval.py",
    "pyaccountingkit/company_configuration/application/service.py",
    "pyaccountingkit/company_configuration/infrastructure/postgres/migrate.py",
    "pyaccountingkit/company_configuration/infrastructure/postgres/dispatch.py",
    "pyaccountingkit/company_configuration/infrastructure/postgres/inbox.py",
    "pyaccountingkit/company_configuration/infrastructure/postgres/"
    "migrations/__init__.py",
)


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _check_migration_inventory(contents: dict[str, bytes], label: str) -> None:
    migrations = sorted(contents)
    numbers = [int(name[:4]) for name in migrations]
    if (
        len(migrations) != len(EXPECTED_MIGRATION_NUMBERS)
        or tuple(numbers) != EXPECTED_MIGRATION_NUMBERS
        or len(set(numbers)) != len(migrations)
    ):
        raise RuntimeError(f"{label}: missing, duplicate or unexpected SQL migrations")


def qualify(root: Path, dist: Path) -> None:
    """Require exact source/SDist/wheel migration parity and package metadata."""
    source_directory = root / MIGRATIONS
    source = {
        file.name: file.read_bytes()
        for file in source_directory.glob("*.sql")
        if file.is_file()
    }
    _check_migration_inventory(source, "source")

    wheels = sorted(dist.glob("pyaccountingkit-*.whl"))
    sdists = sorted(dist.glob("pyaccountingkit-*.tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1:
        raise RuntimeError("Exactly one wheel and one sdist are required")
    wheel, sdist = wheels[0], sdists[0]

    with zipfile.ZipFile(wheel) as package:
        members = set(package.namelist())
        for module in REQUIRED_MODULES:
            if module not in members:
                raise RuntimeError(f"Wheel is missing Python module: {module}")
        wheel_sql = {
            Path(name).name: package.read(name)
            for name in members
            if name.startswith(WHEEL_MIGRATIONS + "/") and name.endswith(".sql")
        }
        metadata_files = [name for name in members if name.endswith(".dist-info/METADATA")]
        if len(metadata_files) != 1:
            raise RuntimeError("Exactly one package metadata file required")
        metadata = package.read(metadata_files[0]).decode("utf-8")
        if (
            "Name: pyaccountingkit\n" not in metadata
            or f"Version: {EXPECTED_VERSION}\n" not in metadata
        ):
            raise RuntimeError("Distribution identity/version mismatch")
    _check_migration_inventory(wheel_sql, "wheel")

    with tarfile.open(sdist, "r:gz") as archive:
        members = [item for item in archive.getmembers() if item.isfile()]
        src_sql = {}
        for item in members:
            if (
                "/src/" + WHEEL_MIGRATIONS + "/" in item.name
                and item.name.endswith(".sql")
            ):
                stream = archive.extractfile(item)
                if stream is None:
                    raise RuntimeError(f"Unable to read sdist SQL file: {item.name}")
                filename = Path(item.name).name
                if filename in src_sql:
                    raise RuntimeError("Duplicate migration in sdist")
                src_sql[filename] = stream.read()
        paths = {item.name.split("/", 1)[1] for item in members if "/" in item.name}
        for module in REQUIRED_MODULES:
            if "src/" + module not in paths:
                raise RuntimeError(f"sdist is missing Python module: {module}")
    _check_migration_inventory(src_sql, "sdist")
    for name, original in sorted(source.items()):
        if wheel_sql.get(name) != original or src_sql.get(name) != original:
            raise RuntimeError(f"Migration content differs across artifacts: {name}")
    print(
        f"PASS FND-C06: {len(source)} exact SHA256 SQL migrations in "
        f"source/wheel/sdist; {len(REQUIRED_MODULES)} import-critical modules; "
        f"version={EXPECTED_VERSION} (placeholder, NOT published)"
    )
    for name in sorted(source):
        print(f"{name}: {_digest(source[name])}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("Usage: qualify_foundation_artifacts.py <repo-root> <dist-dir>")
    qualify(Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve())
