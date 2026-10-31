"""L05-04 process-local immutable mapping catalog fixture; read-only R&D."""

from ..domain.chart_of_accounts.mapping import (
    InvalidMappingCandidate,
    MappingSetVersionCandidate,
)
from ..domain.shared.accounting_scope import ConfigurationScope


class MemoryMappingSetCandidates:
    def __init__(self, sets: tuple[MappingSetVersionCandidate, ...]) -> None:
        if not isinstance(sets, tuple) or any(
            not isinstance(value, MappingSetVersionCandidate) for value in sets
        ):
            raise InvalidMappingCandidate("Immutable mapping-set catalog required")
        self._sets = sets

    def list_for_scope(
        self, scope: ConfigurationScope
    ) -> tuple[MappingSetVersionCandidate, ...]:
        if not isinstance(scope, ConfigurationScope) or scope.book_id is not None:
            raise InvalidMappingCandidate("Entity-level read scope required")
        return tuple(value for value in self._sets if value.scope == scope)
