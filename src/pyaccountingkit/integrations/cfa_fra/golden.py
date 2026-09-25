"""Deterministic CFA FRA golden-fixture and parity primitives.

CFA FRA is a behavioral oracle for migration evidence. This module deliberately
contains no Django import and no legacy runtime dependency.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from types import MappingProxyType
from typing import cast

ORACLE_TREE_SHA = "07d4880534d2e2239e19fd4ef4139de70b56773a"
ORACLE_MANIFEST_VERSION = "0.8.0"


class GoldenCategory(StrEnum):
    """Behavior families qualified against the CFA FRA oracle."""

    ACCOUNTING = "ACCOUNTING"
    POSTING = "POSTING"
    REVERSAL = "REVERSAL"
    FEC = "FEC"
    LEDGER = "LEDGER"
    STATEMENTS = "STATEMENTS"
    CONTROLS = "CONTROLS"
    CLOSING = "CLOSING"
    ANALYSIS = "ANALYSIS"
    REGULATORY = "REGULATORY"


class DivergenceCategory(StrEnum):
    """Approved reasons for intentionally differing from the legacy oracle."""

    BUG_FIX = "BUG_FIX"
    GENERALIZATION = "GENERALIZATION"
    REGULATORY_CORRECTION = "REGULATORY_CORRECTION"
    PORTABILITY_CHANGE = "PORTABILITY_CHANGE"
    SAFETY_HARDENING = "SAFETY_HARDENING"
    API_REDESIGN = "API_REDESIGN"


def _normalize(value: object, *, path: str) -> object:
    if isinstance(value, float):
        raise TypeError(f"binary float forbidden in golden fixture at {path}")
    if isinstance(value, Decimal):
        return format(value, "f")
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, Mapping):
        normalized: dict[str, object] = {}
        for raw_key, item in value.items():
            if not isinstance(raw_key, str):
                raise TypeError(f"golden fixture mapping key must be str at {path}")
            normalized[raw_key] = _normalize(item, path=f"{path}.{raw_key}")
        return MappingProxyType(normalized)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return tuple(
            _normalize(item, path=f"{path}[{index}]")
            for index, item in enumerate(value)
        )
    raise TypeError(
        f"unsupported golden fixture value {type(value).__name__} at {path}"
    )


def _freeze_mapping(value: Mapping[str, object], *, path: str) -> Mapping[str, object]:
    normalized = _normalize(value, path=path)
    if not isinstance(normalized, Mapping):
        raise TypeError(f"expected mapping at {path}")
    return cast(Mapping[str, object], normalized)


def _plain(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in sorted(value.items())}
    if isinstance(value, tuple):
        return [_plain(item) for item in value]
    return value


def _canonical_json(value: object) -> str:
    return json.dumps(
        _plain(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _required_str(payload: Mapping[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{key} must be a non-empty string")
    return value


def _mapping(payload: Mapping[str, object], key: str) -> Mapping[str, object]:
    value = payload.get(key)
    if not isinstance(value, Mapping):
        raise ValueError(f"{key} must be a mapping")
    return cast(Mapping[str, object], value)


@dataclass(frozen=True, slots=True)
class IntentionalDivergence:
    """Reviewed semantic mismatch allowed during CFA FRA migration."""

    divergence_id: str
    category: DivergenceCategory
    paths: tuple[str, ...]
    oracle_behavior: str
    pyaccountingkit_behavior: str
    rationale: str
    migration_impact: str
    reference: str

    def __post_init__(self) -> None:
        for field_name in (
            "divergence_id",
            "oracle_behavior",
            "pyaccountingkit_behavior",
            "rationale",
            "migration_impact",
            "reference",
        ):
            if not getattr(self, field_name).strip():
                raise ValueError(f"{field_name} must be non-empty")
        if not self.paths:
            raise ValueError("intentional divergence must declare at least one path")
        if any(not path.startswith("$") for path in self.paths):
            raise ValueError("intentional divergence paths must start with '$'")

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> IntentionalDivergence:
        raw_paths = payload.get("paths")
        if not isinstance(raw_paths, Sequence) or isinstance(
            raw_paths, (str, bytes, bytearray)
        ):
            raise ValueError("paths must be a sequence of JSON paths")
        paths = tuple(str(path) for path in raw_paths)
        return cls(
            divergence_id=_required_str(payload, "divergence_id"),
            category=DivergenceCategory(_required_str(payload, "category")),
            paths=paths,
            oracle_behavior=_required_str(payload, "oracle_behavior"),
            pyaccountingkit_behavior=_required_str(
                payload, "pyaccountingkit_behavior"
            ),
            rationale=_required_str(payload, "rationale"),
            migration_impact=_required_str(payload, "migration_impact"),
            reference=_required_str(payload, "reference"),
        )


@dataclass(frozen=True, slots=True)
class ParityMismatch:
    """One normalized semantic difference between oracle and implementation."""

    path: str
    expected: object
    actual: object
    divergence_id: str | None = None


@dataclass(frozen=True, slots=True)
class ParityResult:
    """Result of comparing one observation with a golden fixture."""

    fixture_checksum: str
    mismatches: tuple[ParityMismatch, ...]
    unregistered_mismatches: tuple[ParityMismatch, ...]
    accepted_divergence_ids: tuple[str, ...]

    @property
    def exact(self) -> bool:
        return not self.mismatches

    @property
    def qualified(self) -> bool:
        return not self.unregistered_mismatches


_MISSING = "<MISSING>"
_ABSENT = "<ABSENT>"


def _diff(
    expected: object,
    actual: object,
    *,
    path: str,
    output: list[tuple[str, object, object]],
) -> None:
    if isinstance(expected, Mapping) and isinstance(actual, Mapping):
        expected_keys = {str(key) for key in expected}
        actual_keys = {str(key) for key in actual}
        for key in sorted(expected_keys | actual_keys):
            child = f"{path}.{key}"
            if key not in expected:
                output.append((child, _ABSENT, actual[key]))
            elif key not in actual:
                output.append((child, expected[key], _MISSING))
            else:
                _diff(expected[key], actual[key], path=child, output=output)
        return

    if isinstance(expected, tuple) and isinstance(actual, tuple):
        shared = min(len(expected), len(actual))
        for index in range(shared):
            _diff(
                expected[index],
                actual[index],
                path=f"{path}[{index}]",
                output=output,
            )
        for index in range(shared, len(expected)):
            output.append((f"{path}[{index}]", expected[index], _MISSING))
        for index in range(shared, len(actual)):
            output.append((f"{path}[{index}]", _ABSENT, actual[index]))
        return

    if expected != actual:
        output.append((path, expected, actual))


@dataclass(frozen=True, slots=True)
class GoldenFixture:
    """Versioned normalized oracle observation used for exact parity checks."""

    scenario_id: str
    category: GoldenCategory
    inputs: Mapping[str, object]
    expected: Mapping[str, object]
    oracle_tree_sha: str = ORACLE_TREE_SHA
    oracle_manifest_version: str = ORACLE_MANIFEST_VERSION
    divergences: tuple[IntentionalDivergence, ...] = ()

    def __post_init__(self) -> None:
        if not self.scenario_id.strip():
            raise ValueError("scenario_id must be non-empty")
        if len(self.oracle_tree_sha) != 40:
            raise ValueError("oracle_tree_sha must be a 40-character Git SHA")
        if not self.oracle_manifest_version.strip():
            raise ValueError("oracle_manifest_version must be non-empty")
        object.__setattr__(
            self,
            "inputs",
            _freeze_mapping(self.inputs, path="$.inputs"),
        )
        object.__setattr__(
            self,
            "expected",
            _freeze_mapping(self.expected, path="$.expected"),
        )
        ids = [item.divergence_id for item in self.divergences]
        if len(ids) != len(set(ids)):
            raise ValueError("divergence IDs must be unique within a fixture")

    @property
    def checksum(self) -> str:
        payload = {
            "scenario_id": self.scenario_id,
            "category": self.category.value,
            "oracle_tree_sha": self.oracle_tree_sha,
            "oracle_manifest_version": self.oracle_manifest_version,
            "inputs": self.inputs,
            "expected": self.expected,
            "divergences": [
                {
                    "divergence_id": item.divergence_id,
                    "category": item.category.value,
                    "paths": item.paths,
                    "oracle_behavior": item.oracle_behavior,
                    "pyaccountingkit_behavior": item.pyaccountingkit_behavior,
                    "rationale": item.rationale,
                    "migration_impact": item.migration_impact,
                    "reference": item.reference,
                }
                for item in self.divergences
            ],
        }
        return hashlib.sha256(_canonical_json(payload).encode()).hexdigest()

    def compare(self, actual: Mapping[str, object]) -> ParityResult:
        normalized_actual = _freeze_mapping(actual, path="$.actual")
        raw: list[tuple[str, object, object]] = []
        _diff(self.expected, normalized_actual, path="$", output=raw)

        registered_by_path: dict[str, str] = {}
        for divergence in self.divergences:
            for path in divergence.paths:
                registered_by_path[path] = divergence.divergence_id

        mismatches = tuple(
            ParityMismatch(
                path=path,
                expected=expected,
                actual=actual_value,
                divergence_id=registered_by_path.get(path),
            )
            for path, expected, actual_value in raw
        )
        unregistered = tuple(
            mismatch for mismatch in mismatches if mismatch.divergence_id is None
        )
        accepted = tuple(
            sorted(
                {
                    mismatch.divergence_id
                    for mismatch in mismatches
                    if mismatch.divergence_id is not None
                }
            )
        )
        return ParityResult(
            fixture_checksum=self.checksum,
            mismatches=mismatches,
            unregistered_mismatches=unregistered,
            accepted_divergence_ids=cast(tuple[str, ...], accepted),
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> GoldenFixture:
        raw_divergences = payload.get("divergences", ())
        if not isinstance(raw_divergences, Sequence) or isinstance(
            raw_divergences, (str, bytes, bytearray)
        ):
            raise ValueError("divergences must be a sequence")
        divergences: list[IntentionalDivergence] = []
        for item in raw_divergences:
            if not isinstance(item, Mapping):
                raise ValueError("each divergence must be a mapping")
            divergences.append(
                IntentionalDivergence.from_dict(cast(Mapping[str, object], item))
            )
        return cls(
            scenario_id=_required_str(payload, "scenario_id"),
            category=GoldenCategory(_required_str(payload, "category")),
            inputs=_mapping(payload, "inputs"),
            expected=_mapping(payload, "expected"),
            oracle_tree_sha=_required_str(payload, "oracle_tree_sha"),
            oracle_manifest_version=_required_str(
                payload, "oracle_manifest_version"
            ),
            divergences=tuple(divergences),
        )


def load_golden_fixture(path: str | Path) -> GoldenFixture:
    """Load and validate a JSON fixture from disk."""

    raw: object = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, Mapping):
        raise ValueError("golden fixture root must be a mapping")
    return GoldenFixture.from_dict(cast(Mapping[str, object], raw))


__all__ = [
    "ORACLE_TREE_SHA",
    "ORACLE_MANIFEST_VERSION",
    "DivergenceCategory",
    "GoldenCategory",
    "GoldenFixture",
    "IntentionalDivergence",
    "ParityMismatch",
    "ParityResult",
    "load_golden_fixture",
]
