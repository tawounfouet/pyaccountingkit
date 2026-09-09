from __future__ import annotations
from pathlib import Path
import json
import shutil
from datetime import datetime, timezone

from ...io import sha256_file, dump_json
from .layout import CORE_ARTIFACTS, OPTIONAL_FILES, ANOMALY_FILES
from .validator import validate_legacy_root


def _first_existing(root: Path, candidates: tuple[str, ...]) -> Path | None:
    for rel in candidates:
        path = root / rel
        if path.exists():
            return path
    return None


def _copy_immutable(source: Path, target: Path) -> dict:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    src_hash = sha256_file(source)
    dst_hash = sha256_file(target)
    if src_hash != dst_hash:
        raise IOError(f"Byte-for-byte migration failed for {source}")
    return {
        "source_path": str(source),
        "target_path": str(target),
        "sha256": src_hash,
        "bytes": source.stat().st_size,
        "migration_mode": "byte_for_byte_copy",
    }


def migrate_legacy_repository(
    legacy_root: str | Path,
    target_root: str | Path,
    *,
    strict: bool = False,
) -> dict:
    legacy_root = Path(legacy_root)
    target_root = Path(target_root)
    before = validate_legacy_root(legacy_root, strict=False)

    report = {
        "migration_id": "pcemf-amifond-to-regacct-v0.2",
        "source_root": str(legacy_root),
        "target_root": str(target_root),
        "strict_requested": strict,
        "pre_migration_validation": before,
        "artifacts": [],
        "missing_required": [],
        "optional_missing": [],
    }

    for spec in CORE_ARTIFACTS:
        source = _first_existing(legacy_root, spec.source_candidates)
        if source is None:
            if spec.required:
                report["missing_required"].append({
                    "phase": spec.phase,
                    "candidates": list(spec.source_candidates),
                })
            else:
                report["optional_missing"].append(spec.phase)
            continue
        report["artifacts"].append({
            "phase": spec.phase,
            **_copy_immutable(source, target_root / spec.target),
        })

    # Preserve anomaly evidence byte-for-byte.
    for rel in ANOMALY_FILES:
        source = legacy_root / rel
        if source.exists():
            target = target_root / rel
            report["artifacts"].append({
                "phase": "anomaly_evidence",
                **_copy_immutable(source, target),
            })

    # Preserve RAG / approved / review artifacts into generalized locations.
    optional_targets = {
        "rag_index": "rag/indexes/syscohada-guide-v1.json",
        "crosswalk_manifest": "datasets/crosswalk/pcemf_syscohada_v5_manifest.json",
        "crosswalk_approved": "datasets/crosswalk/pcemf_syscohada_v5_approved.json",
        "crosswalk_reviews": "validation/review/pcemf_syscohada_v5_review_decisions.json",
    }
    for name, candidates in OPTIONAL_FILES.items():
        source = _first_existing(legacy_root, candidates)
        if source is None:
            report["optional_missing"].append(name)
            continue
        report["artifacts"].append({
            "phase": name,
            **_copy_immutable(source, target_root / optional_targets[name]),
        })

    # Sidecar only: build-time timestamp does not contaminate canonical datasets.
    report["generated_at_utc"] = datetime.now(timezone.utc).isoformat()
    report["status"] = "blocked_missing_required" if report["missing_required"] else "migrated"

    target_report = target_root / "validation/review/pcemf_legacy_migration_report.json"
    dump_json(target_report, report)

    if strict:
        strict_validation = validate_legacy_root(legacy_root, strict=True)
        if strict_validation["mismatches"] or report["missing_required"]:
            raise ValueError(
                "Strict PCEMF migration blocked: historical invariants or required artifacts do not match"
            )
    return report
