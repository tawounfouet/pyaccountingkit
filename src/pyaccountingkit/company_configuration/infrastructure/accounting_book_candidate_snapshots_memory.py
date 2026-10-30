"""Immutable in-process L04-06 version fixture, NOT a publication store."""

from ..domain.accounting_books import (
    BookConfigurationCandidateVersion,
    InvalidBookCandidateVersion,
)
from ..domain.shared.accounting_scope import ConfigurationScope


class MemoryBookCandidateVersions:
    """Explicitly supplied snapshots; no save, publish, event or SQL operation."""

    def __init__(self, versions: tuple[BookConfigurationCandidateVersion, ...]) -> None:
        if not isinstance(versions, tuple) or any(
            not isinstance(version, BookConfigurationCandidateVersion)
            for version in versions
        ):
            raise InvalidBookCandidateVersion("Typed immutable version tuple required")
        self._versions = versions

    def list_for_book(
        self, scope: ConfigurationScope
    ) -> tuple[BookConfigurationCandidateVersion, ...]:
        if not isinstance(scope, ConfigurationScope) or scope.book_id is None:
            raise InvalidBookCandidateVersion("Book-level scope required")
        return tuple(version for version in self._versions if version.scope == scope)
