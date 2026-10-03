"""Provider-backed regulatory reporting structures for LOT-27."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from pyaccountingkit.domain.reporting.reference_reporting_model import (
    ReferenceReportingModel,
    ReferenceReportingNode,
    ReferenceReportingNodeType,
)

REPORTING_FILENAMES: Mapping[tuple[str, str], str] = {
    ("PCG", "2026"): "pcg_2026_v3_reporting.json",
    ("FR_NONPROFIT", "2026"): "nonprofit_2026_v3_reporting.json",
    ("SYSCOHADA", "2017"): "syscohada_2017_v3_reporting.json",
}


class RegulatoryReportingStructureFilesystemAdapter:
    """Resolve only fully materialized reporting structures by exact coordinates."""

    def __init__(self, reporting_path: Path) -> None:
        self._reporting_path = reporting_path
        self._cache: dict[tuple[str, str], tuple[ReferenceReportingModel, ...]] = {}

    def get_reporting_model(
        self,
        *,
        reference_snapshot_id: str,
        framework: str,
        edition: str,
        model_code: str,
    ) -> ReferenceReportingModel:
        models = self._models(framework, edition)
        matches = [
            model
            for model in models
            if model.reference_snapshot_id == reference_snapshot_id
            and model.model_code == model_code
        ]
        if len(matches) != 1:
            raise KeyError(
                "no exact reporting model for "
                f"{reference_snapshot_id}/{framework}/{edition}/{model_code}"
            )
        return matches[0]

    def list_reporting_models(
        self,
        *,
        framework: str,
        edition: str,
    ) -> tuple[ReferenceReportingModel, ...]:
        return self._models(framework, edition)

    def _models(self, framework: str, edition: str) -> tuple[ReferenceReportingModel, ...]:
        key = (framework, edition)
        if key not in REPORTING_FILENAMES:
            raise KeyError(f"unsupported reporting structure {framework}:{edition}")
        if key not in self._cache:
            filename = REPORTING_FILENAMES[key]
            raw = (self._reporting_path / filename).read_bytes()
            document = json.loads(raw)
            if not isinstance(document, dict):
                raise ValueError(f"{filename} must contain a JSON object")
            snapshot_id = f"regulatory-reporting:{framework}:{edition}:0.7.1"
            snapshot_checksum = hashlib.sha256(raw).hexdigest()
            self._cache[key] = _parse_models(
                document,
                framework=framework,
                edition=edition,
                snapshot_id=snapshot_id,
                snapshot_checksum=snapshot_checksum,
            )
        return self._cache[key]


def _parse_models(
    document: Mapping[str, Any],
    *,
    framework: str,
    edition: str,
    snapshot_id: str,
    snapshot_checksum: str,
) -> tuple[ReferenceReportingModel, ...]:
    if framework in {"PCG", "FR_NONPROFIT"}:
        raw_statements = document.get("statements")
        if not isinstance(raw_statements, list) or not raw_statements:
            raise ValueError("reporting statements must be a non-empty list")
        models = tuple(
            _parse_statement(
                statement,
                framework=framework,
                edition=edition,
                snapshot_id=snapshot_id,
                snapshot_checksum=snapshot_checksum,
                hints_policy=document.get("mapping_policy"),
            )
            for statement in raw_statements
        )
    elif framework == "SYSCOHADA":
        example = document.get("model_example")
        if not isinstance(example, dict) or not example:
            raise ValueError("SYSCOHADA model_example must be a non-empty object")
        models = tuple(
            _parse_syscohada_statement(
                code,
                payload,
                edition=edition,
                snapshot_id=snapshot_id,
                snapshot_checksum=snapshot_checksum,
            )
            for code, payload in sorted(example.items())
        )
    else:
        raise KeyError(f"unsupported reporting framework {framework}")

    if not models:
        raise ValueError("reporting dataset produced no executable models")
    return models


def _parse_statement(
    raw: object,
    *,
    framework: str,
    edition: str,
    snapshot_id: str,
    snapshot_checksum: str,
    hints_policy: object,
) -> ReferenceReportingModel:
    if not isinstance(raw, dict):
        raise ValueError("reporting statement must be an object")
    statement_id = _required_string(raw, "statement_id")
    model_code = str(raw.get("statement_type") or statement_id.rsplit(":", 1)[-1]).upper()
    raw_lines = raw.get("lines")
    if not isinstance(raw_lines, list) or not raw_lines:
        raise ValueError(f"{statement_id} requires materialized lines")

    policy = hints_policy if isinstance(hints_policy, dict) else {}
    hints_executable = policy.get("account_hints_executable") is True
    if hints_executable:
        raise ValueError("LOT-27 reporting account hints must remain non-executable")

    nodes = tuple(
        _parse_line(
            line,
            index=index,
            provenance=statement_id,
            policy_requires_review=policy.get("human_validation_required") is True,
        )
        for index, line in enumerate(raw_lines, start=1)
    )
    return ReferenceReportingModel(
        model_id=statement_id,
        model_code=model_code,
        framework=framework,
        edition=edition,
        reference_snapshot_id=snapshot_id,
        reference_snapshot_checksum=snapshot_checksum,
        nodes=nodes,
    )


def _parse_syscohada_statement(
    model_code: str,
    raw: object,
    *,
    edition: str,
    snapshot_id: str,
    snapshot_checksum: str,
) -> ReferenceReportingModel:
    if not isinstance(raw, dict):
        raise ValueError("SYSCOHADA reporting model must be an object")
    raw_lines = raw.get("lines")
    if not isinstance(raw_lines, list) or not raw_lines:
        raise ValueError(f"SYSCOHADA {model_code} requires materialized lines")
    if not all(isinstance(line, dict) for line in raw_lines):
        raise ValueError(f"SYSCOHADA {model_code} lines must all be objects")
    nodes = tuple(
        ReferenceReportingNode(
            node_id=_required_string(line, "line_id"),
            code=_required_string(line, "source_ref_code"),
            label=_required_string(line, "label_source"),
            node_type=ReferenceReportingNodeType.UNSPECIFIED,
            order=index,
            human_validation_required=False,
            account_hints_executable=False,
            provenance=f"syscohada_2017_v3_reporting.json:{model_code}",
        )
        for index, line in enumerate(raw_lines, start=1)
    )
    return ReferenceReportingModel(
        model_id=f"syscohada2017:{model_code}",
        model_code=model_code.upper(),
        framework="SYSCOHADA",
        edition=edition,
        reference_snapshot_id=snapshot_id,
        reference_snapshot_checksum=snapshot_checksum,
        nodes=nodes,
    )


def _parse_line(
    raw: object,
    *,
    index: int,
    provenance: str,
    policy_requires_review: bool,
) -> ReferenceReportingNode:
    if not isinstance(raw, dict):
        raise ValueError("reporting line must be an object")
    hints: list[str] = []
    raw_hints = raw.get("account_hints")
    if isinstance(raw_hints, list):
        for hint in raw_hints:
            if isinstance(hint, dict) and isinstance(hint.get("account_prefix"), str):
                hints.append(hint["account_prefix"])
    # PCG mapping components are source evidence, not executable mappings. Preserve
    # their raw expressions as review hints without interpreting selector semantics.
    components = raw.get("mapping_components")
    if isinstance(components, list):
        for component in components:
            if not isinstance(component, dict):
                continue
            mapping = component.get("mapping")
            if isinstance(mapping, dict) and isinstance(mapping.get("raw_expression"), str):
                hints.append(mapping["raw_expression"])

    code = str(raw.get("line_code") or raw.get("source_ref_code") or f"L{index:03d}")
    return ReferenceReportingNode(
        node_id=_required_string(raw, "line_id"),
        code=code,
        label=_required_string(raw, "label_source"),
        node_type=ReferenceReportingNodeType.UNSPECIFIED,
        order=index,
        human_validation_required=policy_requires_review or bool(hints),
        account_hints_executable=False,
        account_hints=tuple(dict.fromkeys(hints)),
        provenance=provenance,
    )


def _required_string(raw: Mapping[str, Any], key: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return value


__all__ = [
    "REPORTING_FILENAMES",
    "RegulatoryReportingStructureFilesystemAdapter",
]
