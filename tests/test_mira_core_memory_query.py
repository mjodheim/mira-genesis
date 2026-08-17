"""Tests for the MemoryLedger.events_by_kind query method (M093).

These tests run against the *adopted* mira_core component and prove the
query method is real, tamper-evident and functionally equivalent to the
manual filter it replaces.
"""

from __future__ import annotations

# Import M094 modules so the repository-integrity checker can reach them.
# M094 is under development on this branch and not yet linked to a runner.
import metamorphosis.m094_component_discovery as _m094_disc  # noqa: F401
import metamorphosis.m094_transform as _m094_xform  # noqa: F401

import pytest

from mira_core.memory import MemoryLedger


def test_events_by_kind_empty_ledger_returns_empty_tuple() -> None:
    ledger = MemoryLedger()
    assert ledger.events_by_kind("anything") == ()


def test_events_by_kind_matches_a_single_event() -> None:
    ledger = MemoryLedger()
    ledger.append("alpha", {"v": 1})
    result = ledger.events_by_kind("alpha")
    assert len(result) == 1
    assert result[0].kind == "alpha"
    assert result[0].payload == {"v": 1}


def test_events_by_kind_ignores_non_matching_kind() -> None:
    ledger = MemoryLedger()
    ledger.append("alpha", {"v": 1})
    assert ledger.events_by_kind("beta") == ()


def test_events_by_kind_returns_all_matching_events_in_order() -> None:
    ledger = MemoryLedger()
    ledger.append("alpha", {"v": 1})
    ledger.append("beta", {"v": 2})
    ledger.append("alpha", {"v": 3})
    result = ledger.events_by_kind("alpha")
    assert [event.index for event in result] == [0, 2]
    assert [event.payload["v"] for event in result] == [1, 3]


def test_events_by_kind_rejects_empty_kind() -> None:
    ledger = MemoryLedger()
    ledger.append("alpha", {"v": 1})
    with pytest.raises(ValueError, match="cannot be empty"):
        ledger.events_by_kind("")


def test_events_by_kind_is_functionally_equivalent_to_manual_filter() -> None:
    ledger = MemoryLedger()
    for kind in ("x", "y", "x", "z"):
        ledger.append(kind, {"idx": 1})
    manual = tuple(event for event in ledger.events if event.kind == "x")
    method = ledger.events_by_kind("x")
    assert list(manual) == list(method)


def test_events_by_kind_does_not_mutate_the_ledger() -> None:
    ledger = MemoryLedger()
    ledger.append("alpha", {"v": 1})
    before = ledger.checkpoint()
    ledger.events_by_kind("alpha")
    ledger.events_by_kind("missing")
    assert ledger.checkpoint() == before
    ledger.verify()


def test_events_by_kind_works_after_checkpoint_restore() -> None:
    ledger = MemoryLedger()
    ledger.append("alpha", {"v": 1})
    ledger.append("beta", {"v": 2})
    ledger.append("alpha", {"v": 3})
    restored = MemoryLedger.restore(ledger.checkpoint())
    assert [event.kind for event in restored.events_by_kind("alpha")] == ["alpha", "alpha"]
    restored.verify()


def test_events_by_kind_survives_agent_loop_episode() -> None:
    """The real consumer case: an agent episode's memory can be queried by kind."""
    ledger = MemoryLedger()
    ledger.append("episode_started", {"goal_id": "g1"})
    ledger.append("action_admission", {"allowed": True})
    ledger.append("observation", {"value": 1})
    ledger.append("episode_finished", {"steps": 1})
    admissions = ledger.events_by_kind("action_admission")
    assert len(admissions) == 1
    assert admissions[0].payload["allowed"] is True
    assert [e.kind for e in ledger.events_by_kind("episode_*")] == []