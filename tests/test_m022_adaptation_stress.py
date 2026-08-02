from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace

import pytest

from metamorphosis.m012b_dfa import DFA
from metamorphosis.m017_lab import Episode
from metamorphosis.m019_engine import Case
import metamorphosis.m022_adaptation_stress as m022
from metamorphosis.m022_adaptation_stress import (
    StagedCase,
    audit_summary,
    build_repeated_motif_sequence,
    compare_adaptive_to_frozen,
)


class _Library:
    def __init__(self) -> None:
        self.macros: list[str] = []


class _LearningOrganism:
    """A tiny deterministic positive control for the paired evaluator itself."""

    def __init__(self, *, learns: bool) -> None:
        self.learns = learns
        self.exposures = 0
        self.search_budget = 0
        self.library = _Library()

    def solve(self, base, oracle):
        del base, oracle
        nodes = 100 if self.exposures == 0 or not self.learns else 10
        if self.learns:
            self.exposures += 1
            if self.exposures == 2 and not self.library.macros:
                self.library.macros.append("learned")
        return SimpleNamespace(status="success", search_nodes=nodes, solution=object())


def _cases(rounds: int = 4) -> tuple[StagedCase, ...]:
    case = Case(base=None, make_oracle=lambda: None, verify=lambda solution: solution is not None)
    return tuple(StagedCase(case, motif_index=0, round_index=index) for index in range(rounds))


def test_adaptive_copy_can_improve_while_frozen_copy_stays_at_baseline():
    organism = _LearningOrganism(learns=True)
    original = deepcopy(organism)

    audit = compare_adaptive_to_frozen(
        organism,
        _cases(),
        late_round_start=2,
        search_budget=1_000,
    )
    summary = audit_summary(audit)

    assert audit.adaptive_solved == audit.frozen_solved == 4
    assert audit.common_late_pairs == 2
    assert audit.adaptive_late_nodes == 20
    assert audit.frozen_late_nodes == 200
    assert audit.late_cost_ratio_per_mille == 10_000
    assert summary["macros_after_sequence"] == 1
    assert organism.exposures == original.exposures == 0
    assert organism.library.macros == original.library.macros == []


def test_non_learning_control_has_exactly_one_to_one_cost():
    audit = compare_adaptive_to_frozen(
        _LearningOrganism(learns=False),
        _cases(),
        late_round_start=2,
    )

    assert audit.adaptive_solved == audit.frozen_solved == 4
    assert audit.late_cost_ratio_per_mille == 1_000
    assert audit_summary(audit)["median_late_pair_ratio_per_mille"] == 1_000


def test_false_success_is_fatal():
    bad_case = Case(base=None, make_oracle=lambda: None, verify=lambda solution: False)

    with pytest.raises(AssertionError, match="false success"):
        compare_adaptive_to_frozen(
            _LearningOrganism(learns=False),
            (StagedCase(bad_case, motif_index=0, round_index=0),),
        )


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"motif_count": 0}, "motif_count"),
        ({"repetitions": 2}, "repetitions"),
        (
            {"motif_count": 3, "repetitions": 4, "candidate_episodes": 11},
            "candidate_episodes",
        ),
    ],
)
def test_sequence_builder_rejects_invalid_shapes(kwargs, message):
    with pytest.raises(ValueError, match=message):
        build_repeated_motif_sequence(0, **kwargs)


def test_sequence_builder_deduplicates_source_bodies(monkeypatch):
    first = DFA((0, 1), ((0, 1), (1, 0)), (False, True))
    second = DFA((0, 1), ((1, 0), (1, 1)), (False, True))
    third = DFA((0, 1), ((0, 0), (0, 1)), (True, False))
    episodes = (
        Episode(0, first, first, (), 0, False),
        Episode(1, first, first, (), 0, False),
        Episode(2, second, second, (), 0, False),
        Episode(3, third, third, (), 0, False),
    )

    monkeypatch.setattr(m022, "make_environment", lambda *args, **kwargs: object())
    monkeypatch.setattr(m022, "generate_episodes", lambda *args, **kwargs: episodes)

    staged = build_repeated_motif_sequence(
        0,
        motif_count=1,
        repetitions=3,
        candidate_episodes=3,
    )

    assert len(staged) == 3
    assert len({row.case.base for row in staged}) == 3
