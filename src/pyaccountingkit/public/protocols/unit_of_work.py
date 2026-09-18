"""Public transaction extension contracts for adapter authors."""

from __future__ import annotations

from typing import Protocol

from pyaccountingkit.ports.unit_of_work import UnitOfWorkProtocol


class UnitOfWorkFactoryProtocol(Protocol):
    """Supply a fresh transaction scope for each application operation."""

    def open(self) -> UnitOfWorkProtocol:
        """Open a new framework-neutral unit of work."""
        ...


__all__ = ["UnitOfWorkFactoryProtocol", "UnitOfWorkProtocol"]
