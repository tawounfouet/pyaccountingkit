"""Deterministic bootstrap of the standalone CFA FRA live-consumer repository."""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass
from pathlib import Path

from pyaccountingkit.integrations.cfa_fra.golden import (
    ORACLE_MANIFEST_VERSION,
    ORACLE_TREE_SHA,
)

CONSUMER_BOOTSTRAP_SCHEMA = "cfa_fra_live_consumer_bootstrap/v1"
DEFAULT_FRAMEWORK_REQUIREMENT = "pyaccountingkit>=0.6.0b25,<0.7"
_LOGIN_REDIRECT_FROM = 'LOGIN_REDIRECT_URL = "dashboard"'
_LOGIN_REDIRECT_TO = 'LOGIN_REDIRECT_URL = "analytics:dashboard"'


class ConsumerBootstrapError(RuntimeError):
    """Raised when a standalone consumer cannot be bootstrapped safely."""


@dataclass(frozen=True, slots=True)
class ConsumerBootstrapPlan:
    """Reviewed, deterministic transformation from frozen oracle to consumer seed."""

    source_tree_sha: str
    source_manifest_version: str
    source_project_version: str
    framework_requirement: str
    source_file_count: int
    patches: tuple[str, ...]

    @property
    def bootstrap_sha256(self) -> str:
        body = {
            "schema": CONSUMER_BOOTSTRAP_SCHEMA,
            "source_tree_sha": self.source_tree_sha,
            "source_manifest_version": self.source_manifest_version,
            "source_project_version": self.source_project_version,
            "framework_requirement": self.framework_requirement,
            "source_file_count": self.source_file_count,
            "patches": list(self.patches),
        }
        return hashlib.sha256(
            json.dumps(
                body,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8")
        ).hexdigest()


@dataclass(frozen=True, slots=True)
class ConsumerBootstrapResult:
    """Materialized standalone consumer seed."""

    destination: Path
    plan: ConsumerBootstrapPlan
    manifest_path: Path


def _load_json(path: Path) -> dict[str, object]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConsumerBootstrapError(f"invalid bootstrap source manifest: {path}") from exc
    if not isinstance(raw, dict):
        raise ConsumerBootstrapError("bootstrap source manifest must be a JSON object")
    return raw


def _count_files(root: Path) -> int:
    return sum(1 for path in root.rglob("*") if path.is_file())


def plan_live_consumer_bootstrap(
    source_root: Path,
    *,
    source_tree_sha: str,
    framework_requirement: str = DEFAULT_FRAMEWORK_REQUIREMENT,
) -> ConsumerBootstrapPlan:
    """Validate the frozen source and return the exact standalone bootstrap plan."""
    source = source_root.resolve()
    if not source.is_dir():
        raise ConsumerBootstrapError(f"bootstrap source does not exist: {source}")
    if source_tree_sha != ORACLE_TREE_SHA:
        raise ConsumerBootstrapError(
            "bootstrap source tree SHA does not match frozen CFA FRA oracle"
        )

    manifest = _load_json(source / "MANIFEST.json")
    if manifest.get("project") != "cfa_fra_django_mvp_sprint_7":
        raise ConsumerBootstrapError("bootstrap source project identity is not CFA FRA Sprint 7")
    manifest_version = manifest.get("version")
    if manifest_version != ORACLE_MANIFEST_VERSION:
        raise ConsumerBootstrapError(
            "bootstrap source manifest version does not match frozen CFA FRA oracle"
        )

    pyproject = (source / "pyproject.toml").read_text(encoding="utf-8")
    project_version_marker = 'version = "'
    start = pyproject.find(project_version_marker)
    if start < 0:
        raise ConsumerBootstrapError("bootstrap source pyproject.toml has no project version")
    start += len(project_version_marker)
    end = pyproject.find('"', start)
    if end < 0:
        raise ConsumerBootstrapError("bootstrap source pyproject.toml project version is invalid")
    project_version = pyproject[start:end]

    settings = (source / "config" / "settings" / "base.py").read_text(encoding="utf-8")
    if _LOGIN_REDIRECT_FROM not in settings:
        raise ConsumerBootstrapError(
            "bootstrap source no longer contains the qualified Sprint-7 login redirect defect"
        )
    if framework_requirement in pyproject:
        raise ConsumerBootstrapError("bootstrap source already depends on target PyAccountingKit")

    return ConsumerBootstrapPlan(
        source_tree_sha=source_tree_sha,
        source_manifest_version=str(manifest_version),
        source_project_version=project_version,
        framework_requirement=framework_requirement,
        source_file_count=_count_files(source),
        patches=(
            "add_pyaccountingkit_dependency",
            "fix_login_redirect_namespace",
            "add_consumer_bootstrap_manifest",
        ),
    )


def _assert_safe_destination(source: Path, destination: Path) -> None:
    if destination == source:
        raise ConsumerBootstrapError("bootstrap destination may not equal frozen oracle source")
    if source in destination.parents:
        raise ConsumerBootstrapError("bootstrap destination may not be inside frozen oracle source")
    if destination in source.parents:
        raise ConsumerBootstrapError("bootstrap destination may not contain frozen oracle source")


def _patch_pyproject(path: Path, requirement: str) -> None:
    text = path.read_text(encoding="utf-8")
    marker = '    "reportlab>=4.2,<5",\n]'
    if marker not in text:
        raise ConsumerBootstrapError("consumer pyproject dependency list no longer matches oracle")
    path.write_text(
        text.replace(marker, f'    "reportlab>=4.2,<5",\n    "{requirement}",\n]'),
        encoding="utf-8",
    )


def _patch_login_redirect(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if _LOGIN_REDIRECT_FROM not in text:
        raise ConsumerBootstrapError("consumer login redirect no longer matches oracle")
    path.write_text(text.replace(_LOGIN_REDIRECT_FROM, _LOGIN_REDIRECT_TO), encoding="utf-8")


def consumer_bootstrap_manifest(plan: ConsumerBootstrapPlan) -> dict[str, object]:
    """Return the deterministic provenance manifest written into the standalone consumer."""
    return {
        "schema": CONSUMER_BOOTSTRAP_SCHEMA,
        "kind": "standalone_consumer_seed",
        "consumer": "CFA FRA Django MVP Sprint 7",
        "source": {
            "oracle_tree_sha": plan.source_tree_sha,
            "oracle_manifest_version": plan.source_manifest_version,
            "oracle_project_version": plan.source_project_version,
        },
        "framework_requirement": plan.framework_requirement,
        "patches": list(plan.patches),
        "bootstrap_sha256": plan.bootstrap_sha256,
        "cutover_state": "NOT_STARTED",
        "binding_state": "UNBOUND_UNTIL_PUBLISHED",
    }


def apply_live_consumer_bootstrap(
    source_root: Path,
    destination: Path,
    plan: ConsumerBootstrapPlan,
    *,
    overwrite: bool = False,
) -> ConsumerBootstrapResult:
    """Copy the immutable oracle and apply only the reviewed standalone-seed patches."""
    source = source_root.resolve()
    target = destination.resolve()
    _assert_safe_destination(source, target)

    current_plan = plan_live_consumer_bootstrap(
        source,
        source_tree_sha=plan.source_tree_sha,
        framework_requirement=plan.framework_requirement,
    )
    if current_plan != plan:
        raise ConsumerBootstrapError("reviewed consumer bootstrap plan is stale")

    if target.exists():
        if not overwrite:
            raise ConsumerBootstrapError("bootstrap destination already exists")
        shutil.rmtree(target)

    shutil.copytree(source, target)
    _patch_pyproject(target / "pyproject.toml", plan.framework_requirement)
    _patch_login_redirect(target / "config" / "settings" / "base.py")

    manifest_path = target / "PYACCOUNTINGKIT_CONSUMER_BOOTSTRAP.json"
    manifest_path.write_text(
        json.dumps(consumer_bootstrap_manifest(plan), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return ConsumerBootstrapResult(
        destination=target,
        plan=plan,
        manifest_path=manifest_path,
    )


__all__ = [
    "CONSUMER_BOOTSTRAP_SCHEMA",
    "DEFAULT_FRAMEWORK_REQUIREMENT",
    "ConsumerBootstrapError",
    "ConsumerBootstrapPlan",
    "ConsumerBootstrapResult",
    "apply_live_consumer_bootstrap",
    "consumer_bootstrap_manifest",
    "plan_live_consumer_bootstrap",
]
