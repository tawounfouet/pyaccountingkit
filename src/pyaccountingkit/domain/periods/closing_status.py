"""Closing status lifecycle of an accounting period.

The canonical transition is ``OPEN -> REVIEW -> CLOSING -> CLOSED``; a period
may also be ``LOCKED`` at any point to block posting without closing it.
"""

from __future__ import annotations

from enum import StrEnum


class ClosingStatus(StrEnum):
    OPEN = "OPEN"
    REVIEW = "REVIEW"
    LOCKED = "LOCKED"
    CLOSING = "CLOSING"
    CLOSED = "CLOSED"

    def is_closed(self) -> bool:
        return self is ClosingStatus.CLOSED

    def is_open_for_posting(self) -> bool:
        return self is ClosingStatus.OPEN

    def can_transition_to(self, target: ClosingStatus) -> bool:
        transitions: dict[ClosingStatus, frozenset[ClosingStatus]] = {
            ClosingStatus.OPEN: frozenset(
                {ClosingStatus.REVIEW, ClosingStatus.LOCKED, ClosingStatus.CLOSING}
            ),
            ClosingStatus.REVIEW: frozenset({ClosingStatus.OPEN, ClosingStatus.CLOSING}),
            ClosingStatus.LOCKED: frozenset({ClosingStatus.OPEN}),
            ClosingStatus.CLOSING: frozenset({ClosingStatus.CLOSED}),
            ClosingStatus.CLOSED: frozenset(),
        }
        return target in transitions[self]


__all__ = ["ClosingStatus"]
