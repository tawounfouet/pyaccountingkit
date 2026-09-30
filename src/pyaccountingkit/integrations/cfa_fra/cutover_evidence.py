"""Attestable live-consumer cutover evidence for CFA FRA LOT-26."""

from __future__ import annotations

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

    @property
    def green(self) -> bool:
        """Return whether this evidence is an attested passing proof."""
        return self.status is CutoverEvidenceStatus.PASS


@dataclass(frozen=True, slots=True)
class LiveCutoverEvidence:
    """External evidence required by MIG-13 in addition to canonical CI."""

    legacy_identities: ExternalCutoverEvidence
    regulatory_authority: ExternalCutoverEvidence

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
