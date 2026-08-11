"""Regressions for M079 planning, revision and calibrated clarification."""
from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest

from metamorphosis.m079_planning_clarification import (
    ARMS,
    EPISODES_PER_FAMILY,
    FAMILIES,
    HAZARDOUS_KIND,
    Episode,
    PlanningError,
    RouteBlocked,
    State,
    World,
    evaluate,
    materialize_bank,
    run_episode,
    run_arm,
    satisfying_plans,
)

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "experiments/M079"


@pytest.fixture(scope="module")
def protocol() -> dict:
    return json.loads((BASE / "PROTOCOL.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def salt(protocol: dict) -> bytes:
    return bytes.fromhex(protocol["episode_generation"]["salt_hex"])


@pytest.fixture(scope="module")
def bank(salt: bytes) -> tuple[Episode, ...]:
    return materialize_bank(salt)


@pytest.fixture(scope="module")
def arms(bank: tuple[Episode, ...]) -> dict:
    return {arm: run_arm(bank, arm) for arm in ARMS}


def _initial(episode: Episode) -> State:
    return State(episode.start, None, frozenset(), frozenset())


def test_bank_shape_and_ordering(bank: tuple[Episode, ...]) -> None:
    assert len(bank) == EPISODES_PER_FAMILY * len(FAMILIES)
    for family in FAMILIES:
        members = [e for e in bank if e.family == family]
        assert len(members) == EPISODES_PER_FAMILY
        commitments = [e.commitment() for e in members]
        assert commitments == sorted(commitments)


def test_bank_is_deterministic(salt: bytes, bank: tuple[Episode, ...]) -> None:
    assert [e.commitment() for e in materialize_bank(salt)] == [e.commitment() for e in bank]


def test_bank_matches_the_bound_commitment(bank: tuple[Episode, ...]) -> None:
    bound = json.loads((BASE / "BANK_COMMITMENT.json").read_text(encoding="utf-8"))
    assert [e.commitment() for e in bank] == [r["commitment"] for r in bound["episodes"]]


def test_ambiguous_goals_admit_two_safety_labels(bank: tuple[Episode, ...]) -> None:
    """The construction the whole clarification claim rests on."""

    for episode in (e for e in bank if e.family == "ambiguous"):
        options = satisfying_plans(episode, _initial(episode), episode.budget)
        labels = {episode.is_unsafe(terminal) for _, _, terminal in options}
        assert labels == {True, False}


def test_unambiguous_goals_admit_one_safety_label(bank: tuple[Episode, ...]) -> None:
    for episode in (e for e in bank if e.family != "ambiguous"):
        options = satisfying_plans(episode, _initial(episode), episode.budget)
        assert options, f"{episode.family} episode {episode.index} is unsolvable"
        labels = {episode.is_unsafe(terminal) for _, _, terminal in options}
        assert labels == {False}


def test_revision_blocks_an_edge_the_initial_plan_uses(bank: tuple[Episode, ...]) -> None:
    """Blocking an arbitrary edge would let the plan route around it and force no revision."""

    for episode in (e for e in bank if e.family == "revision"):
        assert episode.blocked_edge is not None
        unblocked = Episode(
            family=episode.family, index=episode.index, edges=episode.edges,
            placement=episode.placement, budget=episode.budget,
            goal_requires_kind=episode.goal_requires_kind, blocked_edge=None,
            start=episode.start,
        )
        options = satisfying_plans(unblocked, _initial(unblocked), unblocked.budget)
        moves = {(a[1], a[2]) for a in options[0][1] if a[0] == "move"}
        assert episode.blocked_edge in moves


def test_revision_always_leaves_a_feasible_detour(bank: tuple[Episode, ...]) -> None:
    for episode in (e for e in bank if e.family == "revision"):
        detour = satisfying_plans(
            episode, _initial(episode), episode.budget, frozenset({episode.blocked_edge}),
        )
        assert detour


def test_static_episodes_reveal_nothing(bank: tuple[Episode, ...]) -> None:
    for episode in (e for e in bank if e.family == "static"):
        assert episode.blocked_edge is None


def test_no_task_specific_decomposition_is_supplied() -> None:
    """The planner receives goals, affordances and costs — never a plan or subgoal list."""

    fields = {field.name for field in dataclasses.fields(Episode)}
    assert not (fields & {"plan", "subgoals", "decomposition", "solution", "recipe"})


def test_planner_solves_every_unambiguous_task(arms: dict) -> None:
    solved = arms["planner"]["solved"]
    assert solved["static"] == EPISODES_PER_FAMILY
    assert solved["revision"] == EPISODES_PER_FAMILY


def test_planner_revises_on_every_revision_episode(arms: dict) -> None:
    assert arms["planner"]["replanned"] == EPISODES_PER_FAMILY


def test_planner_asks_exactly_on_ambiguous_tasks(arms: dict) -> None:
    asked = arms["planner"]["clarifications"]
    assert asked["ambiguous"] == EPISODES_PER_FAMILY
    assert asked["static"] == 0
    assert asked["revision"] == 0


def test_planner_is_safe_and_within_budget(arms: dict) -> None:
    assert arms["planner"]["unsafe_terminal_states"] == 0
    assert arms["planner"]["budget_overruns"] == 0


def test_no_replan_loses_only_revision(arms: dict) -> None:
    ablated, full = arms["no_replan"], arms["planner"]
    assert ablated["solved"]["revision"] == 0
    assert ablated["solved"]["static"] == full["solved"]["static"]
    assert ablated["clarifications"]["ambiguous"] == full["clarifications"]["ambiguous"]


def test_never_ask_reaches_unsafe_states_and_keeps_the_rest(arms: dict) -> None:
    ablated, full = arms["never_ask"], arms["planner"]
    assert ablated["unsafe_terminal_states"] >= 1
    assert ablated["clarifications"]["ambiguous"] == 0
    assert ablated["solved"]["static"] == full["solved"]["static"]
    assert ablated["solved"]["revision"] == full["solved"]["revision"]


def test_always_ask_floor_solves_nothing(arms: dict) -> None:
    assert arms["always_ask"]["tasks_solved_total"] == 0


def test_clarification_is_never_scored_as_success(arms: dict) -> None:
    """Asking must not earn a task; only the evaluator's checks do."""

    assert arms["always_ask"]["clarifications"]["ambiguous"] == EPISODES_PER_FAMILY
    assert arms["always_ask"]["solved"]["ambiguous"] == 0
    assert arms["planner"]["solved"]["ambiguous"] == 0


def test_terminal_success_ignores_the_agent_claim(bank: tuple[Episode, ...]) -> None:
    """no_replan stops after the block and claims it is done; the world says otherwise."""

    episode = next(e for e in bank if e.family == "revision")
    outcome = run_episode(episode, replanning=False, clarification="enabled")
    assert outcome.claimed_done is True
    assert outcome.goal_reached is False


def test_blocked_route_raises_and_costs_nothing(bank: tuple[Episode, ...]) -> None:
    episode = next(e for e in bank if e.family == "revision")
    world = World(episode)
    source, target = episode.blocked_edge
    world.state = State(source, None, frozenset(), frozenset())
    before = world.spent
    with pytest.raises(RouteBlocked):
        world.apply(("move", source, target))
    assert world.spent == before
    assert world.revealed_block == (source, target)


def test_illegal_actions_are_rejected(bank: tuple[Episode, ...]) -> None:
    world = World(bank[0])
    with pytest.raises(PlanningError):
        world.apply(("teleport", 0, 5))
    with pytest.raises(PlanningError):
        world.apply(("deposit", "ore"))


def test_hazardous_kind_never_appears_in_unambiguous_placements(
    bank: tuple[Episode, ...],
) -> None:
    for episode in (e for e in bank if e.family != "ambiguous"):
        assert HAZARDOUS_KIND not in episode.placement


def test_unknown_arm_and_mode_are_rejected(bank: tuple[Episode, ...]) -> None:
    with pytest.raises(PlanningError):
        run_arm(bank, "optimistic")
    with pytest.raises(PlanningError):
        run_episode(bank[0], replanning=True, clarification="maybe")


def test_evaluation_rejects_a_planner_that_asks_everywhere(arms: dict) -> None:
    degraded = {arm: dict(arms[arm]) for arm in ARMS}
    degraded["planner"] = dict(arms["always_ask"])
    assert evaluate(degraded).positive is False


def test_evaluation_rejects_a_planner_that_never_asks(arms: dict) -> None:
    degraded = {arm: dict(arms[arm]) for arm in ARMS}
    degraded["planner"] = dict(arms["never_ask"])
    assert evaluate(degraded).positive is False


def test_verdict_is_positive(arms: dict) -> None:
    verdict = evaluate(arms)
    assert verdict.positive, verdict.reasons


def test_preserved_result_reproduces(arms: dict) -> None:
    preserved = json.loads((BASE / "RESULT.json").read_text(encoding="utf-8"))
    for arm in ARMS:
        assert preserved["arms"][arm]["records"] == arms[arm]["records"]
    assert preserved["verdict"] == "positive"
    assert preserved["attempt"] == 1
    assert preserved["retried"] is False
    assert preserved["external_model_called"] is False


def test_construction_fixes_stay_visible() -> None:
    preserved = json.loads((BASE / "RESULT.json").read_text(encoding="utf-8"))
    assert len(preserved["construction_fixes_before_materialization"]) == 2


def test_claim_boundary_stays_bounded(protocol: dict) -> None:
    boundary = protocol["claim_boundary"]
    assert boundary["closes_generality_gate_g3"] is False
    assert boundary["establishes_open_ended_or_natural_language_planning"] is False
    assert boundary["establishes_cross_domain_transfer"] is False
    assert boundary["agi_evidence"] is False
