from datetime import date, datetime, timedelta, timezone

import pytest

from pyaccountingkit.company_configuration.domain.shared.effective_interval import (
    EffectiveInterval, KnowledgeInterval,
)
from pyaccountingkit.company_configuration.domain.shared.errors import InvalidInterval


def test_effective_interval_is_half_open():
    i = EffectiveInterval(date(2026, 1, 1), date(2027, 1, 1))
    assert i.contains(date(2026, 1, 1))
    assert i.contains(date(2026, 12, 31))
    assert not i.contains(date(2027, 1, 1))


def test_touching_intervals_do_not_overlap():
    a = EffectiveInterval(date(2026, 1, 1), date(2027, 1, 1))
    b = EffectiveInterval(date(2027, 1, 1), date(2028, 1, 1))
    assert not a.overlaps(b)
    assert not b.overlaps(a)


def test_open_ended_intervals_overlap():
    a = EffectiveInterval(date(2026, 1, 1))
    b = EffectiveInterval(date(2027, 1, 1))
    assert a.overlaps(b) and b.overlaps(a)


@pytest.mark.parametrize("start,end", [(date(2027, 1, 1), date(2027, 1, 1)),
                                          (date(2028, 1, 1), date(2027, 1, 1)),
                                          (datetime(2026, 1, 1), None)])
def test_invalid_effective_interval_rejected(start, end):
    with pytest.raises(InvalidInterval):
        EffectiveInterval(start, end)


def test_business_date_rejects_datetime():
    with pytest.raises(InvalidInterval):
        EffectiveInterval(date(2026, 1, 1)).contains(datetime.now(timezone.utc))


def test_knowledge_interval_requires_timezone_and_is_half_open():
    beginning = datetime(2026, 10, 29, tzinfo=timezone.utc)
    end = beginning + timedelta(seconds=10)
    i = KnowledgeInterval(beginning, end)
    assert i.contains(beginning)
    assert not i.contains(end)
    with pytest.raises(InvalidInterval):
        KnowledgeInterval(datetime(2026, 10, 29))
    with pytest.raises(InvalidInterval):
        i.contains(datetime(2026, 10, 29))


def test_knowledge_equal_instants_across_offsets():
    start = datetime(2026, 10, 29, tzinfo=timezone.utc)
    same = datetime(2026, 10, 29, 1, tzinfo=timezone(timedelta(hours=1)))
    assert KnowledgeInterval(start).contains(same)


def test_knowledge_invalid_end_rejected():
    time = datetime(2026, 10, 29, tzinfo=timezone.utc)
    with pytest.raises(InvalidInterval):
        KnowledgeInterval(time, time)
