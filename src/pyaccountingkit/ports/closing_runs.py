"""Persistence port for immutable closing-run evidence."""

from __future__ import annotations

from typing import Protocol

from pyaccountingkit.domain.closing.closing_run import ClosingRun


class ClosingRunRepositoryProtocol(Protocol):
    """Append-only persistence contract for sealed closing runs."""

    def append(self, run: ClosingRun) -> None:
        """Persist one sealed closing run, idempotently for identical evidence."""
        ...

    def get(self, run_id: str) -> ClosingRun | None:
        """Return a previously persisted closing run when present."""
        ...


__all__ = ["ClosingRunRepositoryProtocol"]
