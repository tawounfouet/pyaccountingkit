"""Unit tests for the optimistic-concurrency Revision value object."""

from __future__ import annotations

import pytest

from pyaccountingkit.core.revisions import INITIAL_REVISION, Revision


def test_initial_revision_is_constant() -> None:
    assert INITIAL_REVISION == 0
    assert Revision().value == INITIAL_REVISION


def test_incremented_returns_new_revision() -> None:
    revision = Revision(3)
    assert revision.incremented() == Revision(4)
    assert revision == Revision(3)


def test_revision_rejects_negative_values() -> None:
    with pytest.raises(ValueError):
        Revision(-1)


def test_revision_int_and_str_conversions() -> None:
    assert int(Revision(7)) == 7
    assert str(Revision(7)) == "7"
    assert int(Revision()) == 0
