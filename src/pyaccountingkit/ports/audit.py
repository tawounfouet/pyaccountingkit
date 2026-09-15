"""Audit port — records immutable events of business mutations."""

from __future__ import annotations

from typing import Protocol

from pyaccountingkit.domain.audit.events import AuditEvent


class AuditLogSinkProtocol(Protocol):
    """Persists an AuditEvent for later reconstruction and control."""

    def record(self, event: AuditEvent) -> None:
        """Append an event to the audit log."""
        ...


__all__ = ["AuditLogSinkProtocol"]
