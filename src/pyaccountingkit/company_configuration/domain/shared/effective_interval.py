"""Distinct business dates and timezone-aware knowledge instants.

Both intervals use [start, end). EffectiveInterval uses calendar dates;
KnowledgeInterval uses timezone-aware instants (never naive datetimes).
"""

from dataclasses import dataclass
from datetime import date, datetime

from .errors import InvalidInterval


@dataclass(frozen=True, slots=True)
class EffectiveInterval:
    start: date
    end: date | None = None

    def __post_init__(self) -> None:
        if type(self.start) is not date or (self.end is not None and type(self.end) is not date):
            raise InvalidInterval("EffectiveInterval expects dates, not datetimes")
        if self.end is not None and self.end <= self.start:
            raise InvalidInterval("EffectiveInterval end must be after start")

    def contains(self, day: date) -> bool:
        if type(day) is not date:
            raise InvalidInterval("Expected a business date")
        return self.start <= day and (self.end is None or day < self.end)

    def overlaps(self, other: "EffectiveInterval") -> bool:
        if not isinstance(other, EffectiveInterval):
            raise InvalidInterval("Expected an EffectiveInterval")
        return (self.end is None or other.start < self.end) and (
            other.end is None or self.start < other.end
        )


@dataclass(frozen=True, slots=True)
class KnowledgeInterval:
    start: datetime
    end: datetime | None = None

    def __post_init__(self) -> None:
        for value in (self.start, self.end):
            if value is not None and (
                type(value) is not datetime or value.tzinfo is None
                or value.utcoffset() is None
            ):
                raise InvalidInterval("KnowledgeInterval requires timezone-aware datetimes")
        if self.end is not None and self.end <= self.start:
            raise InvalidInterval("KnowledgeInterval end must be after start")

    def contains(self, instant: datetime) -> bool:
        if (type(instant) is not datetime or instant.tzinfo is None
                or instant.utcoffset() is None):
            raise InvalidInterval("Expected a timezone-aware instant")
        return self.start <= instant and (self.end is None or instant < self.end)

    def overlaps(self, other: "KnowledgeInterval") -> bool:
        if not isinstance(other, KnowledgeInterval):
            raise InvalidInterval("Expected a KnowledgeInterval")
        return (self.end is None or other.start < self.end) and (
            other.end is None or self.start < other.end
        )
