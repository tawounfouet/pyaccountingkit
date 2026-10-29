"""Distinct business dates and timezone-aware knowledge instants.

Both intervals use [start, end). EffectiveInterval uses calendar dates;
KnowledgeInterval uses timezone-aware instants (never naive datetimes).
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime

from .errors import InvalidInterval


def _knowledge_instant_utc(value: datetime) -> datetime:
    """Compare instants on a UTC timeline, including repeated DST local hours.

    Python compares aware datetimes sharing the same tzinfo by wall-clock time;
    `fold=0` and `fold=1` must instead be compared as distinct instants.
    """
    return value.astimezone(UTC)


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
        if self.end is not None and (
            _knowledge_instant_utc(self.end) <= _knowledge_instant_utc(self.start)
        ):
            raise InvalidInterval("KnowledgeInterval end must be after start")

    def contains(self, instant: datetime) -> bool:
        if (type(instant) is not datetime or instant.tzinfo is None
                or instant.utcoffset() is None):
            raise InvalidInterval("Expected a timezone-aware instant")
        instant_utc = _knowledge_instant_utc(instant)
        return _knowledge_instant_utc(self.start) <= instant_utc and (
            self.end is None or instant_utc < _knowledge_instant_utc(self.end)
        )

    def overlaps(self, other: "KnowledgeInterval") -> bool:
        if not isinstance(other, KnowledgeInterval):
            raise InvalidInterval("Expected a KnowledgeInterval")
        return (
            self.end is None
            or _knowledge_instant_utc(other.start) < _knowledge_instant_utc(self.end)
        ) and (
            other.end is None
            or _knowledge_instant_utc(self.start) < _knowledge_instant_utc(other.end)
        )
