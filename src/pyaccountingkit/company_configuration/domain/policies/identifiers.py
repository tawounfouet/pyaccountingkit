"""L07-01 local typed candidate IDs; no shared/public identity migration."""

from dataclasses import dataclass

from ..shared.identifiers import _UUIDIdentifier


@dataclass(frozen=True, slots=True)
class PolicyCandidateId(_UUIDIdentifier):
    """Opaque identity for a not-yet-published policy draft."""


@dataclass(frozen=True, slots=True)
class RulesetCandidateId(_UUIDIdentifier):
    """Opaque identity for a not-yet-published ruleset draft."""


@dataclass(frozen=True, slots=True)
class PolicyAssignmentCandidateId(_UUIDIdentifier):
    """Opaque identity for an unapproved book policy assignment."""
