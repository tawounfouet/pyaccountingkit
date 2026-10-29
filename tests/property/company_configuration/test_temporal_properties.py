"""Hypothesis properties for half-open, non-ambiguous temporal primitives."""

from datetime import UTC, date, datetime, timedelta

from hypothesis import given, settings, strategies as st

from pyaccountingkit.company_configuration.domain.shared.effective_interval import (
    EffectiveInterval,
    KnowledgeInterval,
)


@given(st.integers(min_value=1, max_value=100000))
@settings(max_examples=150)
def test_effective_boundary_is_exclusive(days):
    start = date(2000, 1, 1)
    end = start + timedelta(days=days)
    interval = EffectiveInterval(start, end)
    assert interval.contains(start)
    assert interval.contains(end - timedelta(days=1))
    assert not interval.contains(end)


@given(st.integers(min_value=1, max_value=100000), st.integers(min_value=1, max_value=100000))
@settings(max_examples=150)
def test_touching_periods_never_overlap(first_span, second_span):
    start = date(2000, 1, 1)
    middle = start + timedelta(days=first_span)
    last = middle + timedelta(days=second_span)
    a, b = EffectiveInterval(start, middle), EffectiveInterval(middle, last)
    assert not a.overlaps(b)
    assert not b.overlaps(a)


@given(st.integers(min_value=1, max_value=100000))
@settings(max_examples=150)
def test_knowledge_boundary_and_timezone(days):
    start = datetime(2000, 1, 1, tzinfo=UTC)
    end = start + timedelta(days=days)
    interval = KnowledgeInterval(start, end)
    assert interval.contains(start)
    assert not interval.contains(end)
    assert interval.overlaps(KnowledgeInterval(start, end))


@given(st.integers(min_value=1, max_value=100000))
@settings(max_examples=150)
def test_overlap_is_symmetric(days):
    start = date(2000, 1, 1)
    middle = start + timedelta(days=days)
    a = EffectiveInterval(start, middle)
    b = EffectiveInterval(start + timedelta(days=1), None)
    assert a.overlaps(b) == b.overlaps(a)
