"""Attestable live-consumer cutover evidence for CFA FRA LOT-26."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
import re

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class CutoverEvidenceStatus(StrEnum):
    """Status of one externally produced live-cutover proof."""

    PASS = "PASS"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True, slots=True)
class ExternalCutoverEvidence:
    """One evidence record produced outside the bundled frozen oracle.

    PASS records are attestations: they require provenance metadata and a SHA-256
    digest for the referenced artifact. BLOCKED records are explicit gaps and
    therefore require a human-readable reason instead of fabricated proof.
    """

    status: CutoverEvidenceStatus
    source: str
    reason: str | None = None
    artifact: str | None = None
    sha256: str | None = None
    observed_at: str | None = None
    producer: str | None = None

    def __post_init__(self) -> None:
        if not self.source.strip():
            raise ValueError("cutover evidence source must not be empty")

        if self.status is CutoverEvidenceStatus.BLOCKED:
            if self.reason is None or not self.reason.strip():
                raise ValueError("blocked cutover evidence requires a reason")
            return

        if self.reason is not None:
            raise ValueError("passing cutover evidence must not carry a blocker reason")
        for name, value in (
            ("artifact", self.artifact),
            ("sha256", self.sha256),
            ("observed_at", self.observed_at),
            ("producer", self.producer),
        ):
            if value is None or not value.strip():
                raise ValueError(f"passing cutover evidence requires {name}")

        assert self.sha256 is not None
        if _SHA256_RE.fullmatch(self.sha256) is None:
            raise ValueError("cutover evidence sha256 must be 64 lowercase hex characters")

        assert self.observed_at is not None
        if not self.observed_at.endswith("Z"):
            raise ValueError("cutover evidence observed_at must be an explicit UTC timestamp")
        try:
            datetime.fromisoformat(self.observed_at.removesuffix("Z") + "+00:00")
        except ValueError as exc:
            raise ValueError("cutover evidence observed_at must be ISO-8601") from exc

    @classmethod
    def from_mapping(cls, payload: Mapping[str, object]) -> ExternalCutoverEvidence:
        """Parse one JSON-compatible evidence record through the same invariants."""
        raw_status = payload.get("status")
        raw_source = payload.get("source")
        if not isinstance(raw_status, str):
            raise ValueError("cutover evidence status must be a string")
        if not isinstance(raw_source, str):
            raise ValueError("cutover evidence source must be a string")

        values: dict[str, str | None] = {}
        for key in ("reason", "artifact", "sha256", "observed_at", "producer"):
            raw = payload.get(key)
            if raw is not None and not isinstance(raw, str):
                raise ValueError(f"cutover evidence {key} must be a string")
            values[key] = raw

        return cls(
            status=CutoverEvidenceStatus(raw_status),
            source=raw_source,
            reason=values["reason"],
            artifact=values["artifact"],
            sha256=values["sha256"],
            observed_at=values["observed_at"],
            producer=values["producer"],
        )

    @property
    def green(self) -> bool:
        """Return whether this evidence is an attested passing proof."""
        return self.status is CutoverEvidenceStatus.PASS


@dataclass(frozen=True, slots=True)
class LiveCutoverEvidence:
    """External evidence required by MIG-13 in addition to canonical CI."""

    legacy_identities: ExternalCutoverEvidence
    regulatory_authority: ExternalCutoverEvidence

    @classmethod
    def from_mapping(cls, payload: Mapping[str, object]) -> LiveCutoverEvidence:
        """Parse the required external evidence set from a manifest mapping."""
        raw_identities = payload.get("legacy_identities")
        raw_authority = payload.get("regulatory_authority")
        if not isinstance(raw_identities, dict):
            raise ValueError("legacy_identities cutover evidence is missing")
        if not isinstance(raw_authority, dict):
            raise ValueError("regulatory_authority cutover evidence is missing")
        return cls(
            legacy_identities=ExternalCutoverEvidence.from_mapping(raw_identities),
            regulatory_authority=ExternalCutoverEvidence.from_mapping(raw_authority),
        )

    @property
    def identities_traceable(self) -> bool:
        return self.legacy_identities.green

    @property
    def regulatory_authority_replaced(self) -> bool:
        return self.regulatory_authority.green


__all__ = [
    "CutoverEvidenceStatus",
    "ExternalCutoverEvidence",
    "LiveCutoverEvidence",
]
