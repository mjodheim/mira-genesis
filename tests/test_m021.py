from __future__ import annotations

from types import SimpleNamespace

import pytest

from metamorphosis.m019_engine import Case
from metamorphosis.m021_measures import (
    MEASURES,
    rank_by_minimal_criterion,
    rank_by_novelty,
    rank_by_objective,
    rank_by_quality_diversity,
)
from scripts.run_m021_measure_comparison import audit_organism, selection_rng


def _individual(
    lineage: str,
    *,
    energy: int,
    solved: int = 0,
    macros: tuple[str, ...] = (),
    forget_kind: str = "none",
):
    return SimpleNamespace(
        lineage=lineage,
        ledger=SimpleNamespace(energy=energy, solved=solved),
        genome=SimpleNamespace(forget_kind=forget_kind),
        organism=SimpleNamespace(
            library=SimpleNamespace(
                macros=[SimpleNamespace(name=name) for name in macros]
            )
        ),
    )


def test_objective_ranks_energy_then_lineage():
    population = [
        _individual("b", energy=10),
        _individual("a", energy=10),
        _individual("c", energy=30),
    ]

    assert [i.lineage for i in rank_by_objective(population)] == ["c", "a", "b"]


def test_novelty_rewards_a_behaviour_not_already_represented():
    population = [
        _individual("a", energy=10, macros=("x",)),
        _individual("b", energy=10, macros=("x",)),
        _individual("c", energy=10, macros=("y", "z")),
    ]

    assert rank_by_novelty(population)[0].lineage == "c"


def test_quality_diversity_places_one_elite_per_niche_before_second_best():
    population = [
        _individual("a", energy=100, macros=("m1",), forget_kind="none"),
        _individual("b", energy=90, macros=("m2",), forget_kind="none"),
        _individual(
            "c",
            energy=80,
            macros=("m1", "m2", "m3", "m4"),
            forget_kind="budget",
        ),
        _individual(
            "d",
            energy=70,
            macros=("m5", "m6", "m7", "m8"),
            forget_kind="budget",
        ),
    ]

    assert [i.lineage for i in rank_by_quality_diversity(population)] == [
        "a",
        "c",
        "b",
        "d",
    ]


def test_minimal_criterion_never_places_a_rejected_individual_before_viable_ones():
    population = [
        _individual("rejected", energy=1_000, solved=0, macros=("rare",)),
        _individual("viable-a", energy=1, solved=1, macros=("x",)),
        _individual("viable-b", energy=1, solved=1, macros=("y",)),
    ]

    ranked = rank_by_minimal_criterion(population)

    assert {i.lineage for i in ranked[:2]} == {"viable-a", "viable-b"}
    assert ranked[-1].lineage == "rejected"


@pytest.mark.parametrize("ranker", MEASURES.values(), ids=MEASURES.keys())
def test_every_ranker_returns_a_permutation(ranker):
    population = [
        _individual("a", energy=30, solved=1, macros=("x",)),
        _individual("b", energy=20, solved=0, macros=("y",)),
        _individual("c", energy=10, solved=1, macros=("z",)),
    ]

    ranked = ranker(population)

    assert len(ranked) == len(population)
    assert {id(i) for i in ranked} == {id(i) for i in population}


def test_all_measures_receive_the_same_exogenous_random_stream_for_a_seed():
    first = selection_rng(12)
    second = selection_rng(12)

    assert [first.randrange(10_000) for _ in range(20)] == [
        second.randrange(10_000) for _ in range(20)
    ]


class _LearningAuditOrganism:
    def __init__(self) -> None:
        self.search_budget = 0
        self.learned = 0

    def solve(self, base, oracle):
        del base, oracle
        solved = self.learned > 0
        self.learned += 1
        return SimpleNamespace(
            status="success" if solved else "abstained",
            solution=object() if solved else None,
            search_nodes=10,
        )


def test_held_out_audit_is_non_mutating_and_distinguishes_adaptation_from_transfer():
    organism = _LearningAuditOrganism()
    cases = [
        Case(base=None, make_oracle=lambda: None, verify=lambda solution: solution is not None),
        Case(base=None, make_oracle=lambda: None, verify=lambda solution: solution is not None),
    ]

    adaptive_solved, _ = audit_organism(organism, cases, adaptive=True)
    frozen_solved, _ = audit_organism(organism, cases, adaptive=False)

    assert adaptive_solved == 1
    assert frozen_solved == 0
    assert organism.learned == 0, "the audit must never mutate the selected organism"
