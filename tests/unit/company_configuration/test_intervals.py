from datetime import UTC, date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from pyaccountingkit.company_configuration.domain.shared.effective_interval import (
    EffectiveInterval,
    KnowledgeInterval,
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
        EffectiveInterval(date(2026, 1, 1)).contains(datetime.now(UTC))


def test_knowledge_interval_requires_timezone_and_is_half_open():
    beginning = datetime(2026, 10, 29, tzinfo=UTC)
    end = beginning + timedelta(seconds=10)
    i = KnowledgeInterval(beginning, end)
    assert i.contains(beginning)
    assert not i.contains(end)
    with pytest.raises(InvalidInterval):
        KnowledgeInterval(datetime(2026, 10, 29))
    with pytest.raises(InvalidInterval):
        i.contains(datetime(2026, 10, 29))


def test_knowledge_equal_instants_across_offsets():
    start = datetime(2026, 10, 29, tzinfo=UTC)
    same = datetime(2026, 10, 29, 1, tzinfo=timezone(timedelta(hours=1)))
    assert KnowledgeInterval(start).contains(same)


def test_knowledge_invalid_end_rejected():
    time = datetime(2026, 10, 29, tzinfo=UTC)
    with pytest.raises(InvalidInterval):
        KnowledgeInterval(time, time)


def test_knowledge_interval_uses_absolute_order_across_repeated_dst_hour():
    """The later local 02:10 is after the earlier 02:50 on the UTC timeline."""
    paris = ZoneInfo("Europe/Paris")
    first_fold = datetime(2026, 10, 25, 2, 50, tzinfo=paris, fold=0)
    second_fold = datetime(2026, 10, 25, 2, 10, tzinfo=paris, fold=1)
    interval = KnowledgeInterval(first_fold, second_fold)

    assert interval.contains(first_fold)
    assert interval.contains(datetime(2026, 10, 25, 2, 0, tzinfo=paris, fold=1))
    assert interval.contains(datetime(2026, 10, 25, 1, 0, tzinfo=UTC))
    assert not interval.contains(second_fold)
    assert not interval.contains(datetime(2026, 10, 25, 2, 40, tzinfo=paris, fold=1))

    with pytest.raises(InvalidInterval):
        KnowledgeInterval(second_fold, first_fold)


def test_knowledge_overlap_is_symmetric_and_half_open_across_dst_fold():
    paris = ZoneInfo("Europe/Paris")
    first_fold = datetime(2026, 10, 25, 2, 50, tzinfo=paris, fold=0)
    second_fold_start = datetime(2026, 10, 25, 2, 0, tzinfo=paris, fold=1)
    second_fold_end = datetime(2026, 10, 25, 2, 10, tzinfo=paris, fold=1)
    first = KnowledgeInterval(first_fold, second_fold_end)
    overlapping = KnowledgeInterval(
        second_fold_start, datetime(2026, 10, 25, 2, 20, tzinfo=paris, fold=1)
    )
    touching = KnowledgeInterval(
        second_fold_end, datetime(2026, 10, 25, 2, 20, tzinfo=paris, fold=1)
    )

    assert first.overlaps(overlapping)
    assert overlapping.overlaps(first)
    assert not first.overlaps(touching)
    assert not touching.overlaps(first)
