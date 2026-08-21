"""The world-arrangement arm, and whether it can actually fail.

An arm that reports `satisfied` whatever the mechanism does is decoration. These tests spend most
of their effort on the failure directions: a world in a supported regime that stops working, a
world in the excluded regime that starts working, and an instrument failure that must not be
mistaken for either.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from metamorphosis import m095_arms as arms  # noqa: E402
from metamorphosis import m095_chain as chain  # noqa: E402
from metamorphosis import m095_world as world  # noqa: E402


@pytest.fixture(scope="module")
def swept(tmp_path_factory) -> arms.Arrangement:
    """One sweep, shared. It runs the whole chain six times."""

    base = tmp_path_factory.mktemp("m095-arrangements")

    def make_root(name: str) -> Path:
        root = base / name
        root.mkdir(parents=True, exist_ok=True)
        return root

    return arms.run(make_root)


# ── the points are derived, not chosen ────────────────────────────────


def test_every_way_the_two_demands_can_compare_has_a_witness() -> None:
    """Three regimes, none omitted. An arm that skipped one would measure a partial domain."""

    regimes = {
        "inner>outer" if inner > outer else ("inner==outer" if inner == outer else "inner<outer")
        for inner, outer in arms.arrangements()
    }
    assert regimes == {"inner>outer", "inner==outer", "inner<outer"}


def test_each_regime_has_a_minimal_and_a_larger_witness() -> None:
    """So a result cannot turn on the arrangement being small."""

    by_regime: dict[str, list[tuple[int, int]]] = {}
    for inner, outer in arms.arrangements():
        regime = ("inner>outer" if inner > outer
                  else "inner==outer" if inner == outer else "inner<outer")
        by_regime.setdefault(regime, []).append((inner, outer))
    for regime, points in by_regime.items():
        assert len(points) >= 2, f"{regime} has only {points}"
        assert len({sum(point) for point in points}) > 1, f"{regime} witnesses are the same size"


def test_the_declared_world_is_one_of_the_points() -> None:
    """The arm must include the arrangement the milestone actually reports."""

    assert (world.READING_CALLERS, world.SAMPLE_CALLERS) in arms.arrangements()


def test_no_point_carries_a_caller_count_below_one() -> None:
    """A class with no call sites presents no demand, so the comparison would be vacuous."""

    assert all(inner >= 1 and outer >= 1 for inner, outer in arms.arrangements())


# ── the measurement ───────────────────────────────────────────────────


def test_the_measured_domain_matches_the_recorded_one(swept: arms.Arrangement) -> None:
    assert swept.outcome == "satisfied", [p.to_dict() for p in swept.disagreements]


def test_the_enabling_relation_holds_in_every_supported_regime(swept: arms.Arrangement) -> None:
    supported = [p for p in swept.points if p.inner_call_sites >= p.outer_call_sites]
    assert supported
    assert all(point.demonstrated for point in supported), (
        f"{[p.to_dict() for p in supported if not p.demonstrated]} should have demonstrated it"
    )


def test_the_excluded_regime_really_is_excluded(swept: arms.Arrangement) -> None:
    """Pinned as a negative. If this starts passing, the recorded domain is too narrow."""

    excluded = [p for p in swept.points if p.inner_call_sites < p.outer_call_sites]
    assert excluded
    assert not any(point.demonstrated for point in excluded)


def test_the_control_never_reaches_b_from_s0_in_any_arrangement(swept: arms.Arrangement) -> None:
    """If B were reachable from S0 anywhere, the whole chain would be measuring nothing."""

    assert not any(point.control_reached for point in swept.points)


# ── it can fail, in both directions ───────────────────────────────────


def _point(inner: int, outer: int, demonstrated: bool) -> arms.Point:
    return arms.Point(
        inner_call_sites=inner,
        outer_call_sites=outer,
        predicted=arms.domain_predicts(inner, outer),
        demonstrated=demonstrated,
        regime="measured",
    )


def test_a_supported_world_that_stops_working_refutes_the_arm() -> None:
    """The claim would be too broad."""

    arm = arms.Arrangement(points=[_point(3, 2, False), _point(1, 2, False)])
    assert arm.outcome == "refuted"
    assert [p.inner_call_sites for p in arm.disagreements] == [3]


def test_an_excluded_world_that_starts_working_also_refutes_the_arm() -> None:
    """The claim would be too narrow — which is a finding, not a bonus.

    This is the direction an arm is most likely to be written to ignore. A boundary that moves
    outward while the prose still describes the old one is the same defect as one that moves in.
    """

    arm = arms.Arrangement(points=[_point(3, 2, True), _point(1, 2, True)])
    assert arm.outcome == "refuted"
    assert [p.inner_call_sites for p in arm.disagreements] == [1]


def test_a_point_that_could_not_run_is_unrunnable_not_refuted() -> None:
    """Amendment A1's distinction: an instrument failure is not evidence about the mechanism."""

    broken = _point(3, 2, False)
    broken.error = "ChainError: the world presents no nested requirement"
    arm = arms.Arrangement(points=[broken, _point(1, 1, True)])
    assert arm.outcome == "unrunnable"


def test_an_empty_sweep_is_unrunnable_not_satisfied() -> None:
    """`all()` over nothing is True, which is how a vacuous arm reports success."""

    assert arms.Arrangement().outcome == "unrunnable"


# ── the arm stays out of the experiment record ────────────────────────


def test_the_arm_cannot_reach_the_experiment_directory() -> None:
    """It measures; it does not record. Writing a result is the runner's job and the owner's act."""

    source = (REPO_ROOT / "metamorphosis" / "m095_arms.py").read_text(encoding="utf-8")
    body = source.split('"""', 2)[-1]
    assert "experiments" not in body
    assert "QUALIFICATION" not in body


# ── the random-target arm ─────────────────────────────────────────────


@pytest.fixture(scope="module")
def rivals(tmp_path_factory) -> arms.RandomTarget:
    base = tmp_path_factory.mktemp("m095-rivals")

    def make_root(name: str) -> Path:
        root = base / name
        root.mkdir(parents=True, exist_ok=True)
        return root

    return arms.random_target(make_root)


def test_repairing_a_target_the_diagnosis_rejected_does_not_unlock_b(
    rivals: arms.RandomTarget,
) -> None:
    """If it did, the diagnosis would be doing no work and the world would be doing all of it."""

    assert rivals.outcome == "satisfied"
    assert not any(rival.b_reached for rival in rivals.rivals)


def test_the_arm_runs_every_eligible_rival_rather_than_drawing_one(
    rivals: arms.RandomTarget,
) -> None:
    """Exhausting the set removes the question of where a seed came from."""

    assert rivals.to_dict()["every_eligible_rival_was_run"] is True
    assert len(rivals.rivals) >= 2


def test_no_rival_is_a_target_the_diagnosis_selected(rivals: arms.RandomTarget) -> None:
    """An arm that repaired the selected target would be the chain, not a control."""

    root = world.build(Path(tempfile.mkdtemp(prefix="m095-selected-")))
    selected = {
        f"{item.target}/{item.capability}" for item in chain.measure(root).tied_selection()
    }
    assert selected
    assert not ({rival.target for rival in rivals.rivals} & selected)


def test_a_satisfied_rival_names_what_still_blocked_b(rivals: arms.RandomTarget) -> None:
    """Unreachable for a stated reason, not merely unfound."""

    for rival in rivals.rivals:
        if rival.outcome == "satisfied":
            assert rival.b_blocked_by, f"{rival.target} passed without naming an obstacle"
            assert rival.b_examined > 0


def test_a_rival_that_could_not_be_repaired_is_unrunnable_not_a_pass() -> None:
    """It exercised nothing. Counting it as evidence would be a control that cannot fail."""

    assert arms.Rival(target="X/y", repaired=False).outcome == "unrunnable"


def test_a_rival_that_unlocks_b_refutes_the_arm() -> None:
    arm = arms.RandomTarget(rivals=[arms.Rival(target="X/y", repaired=True, b_reached=True)])
    assert arm.outcome == "refuted"


def test_an_arm_whose_every_rival_was_unrepairable_is_unrunnable() -> None:
    """Nothing was tested, so `satisfied` would be a vacuous pass."""

    arm = arms.RandomTarget(rivals=[arms.Rival(target="X/y"), arms.Rival(target="X/z")])
    assert arm.outcome == "unrunnable"


# ── the more-budget arm ───────────────────────────────────────────────


@pytest.fixture(scope="module")
def budget(tmp_path_factory) -> arms.MoreBudget:
    base = tmp_path_factory.mktemp("m095-budget")

    def make_root(name: str) -> Path:
        root = base / name
        root.mkdir(parents=True, exist_ok=True)
        return root

    return arms.more_budget(make_root)


def test_b_is_unreachable_at_every_bound_not_merely_at_the_chains(budget: arms.MoreBudget) -> None:
    assert budget.outcome == "satisfied"
    assert not any(rung.reached for rung in budget.rungs)


def test_the_ceiling_is_the_size_of_the_offered_set_not_a_chosen_number(
    budget: arms.MoreBudget,
) -> None:
    """No operation applies twice, so the set size bounds the chain length by construction."""

    root = world.build(Path(tempfile.mkdtemp(prefix="m095-ceiling-")))
    target = next(item for item in chain.measure(root).unmet if item.capability == chain.NESTED)
    assert budget.ceiling == chain.search(root, target, label="ceiling").operations_offered
    assert [rung.bound for rung in budget.rungs] == list(range(1, budget.ceiling + 1))


def test_the_search_closed_strictly_below_the_ceiling(budget: arms.MoreBudget) -> None:
    """Saturation is what makes 'unreachable' mean unreachable rather than under-searched."""

    assert budget.saturates_at is not None
    assert budget.saturates_at < budget.ceiling


def test_the_curve_never_shrinks_as_the_bound_grows(budget: arms.MoreBudget) -> None:
    examined = [rung.examined for rung in budget.rungs]
    assert examined == sorted(examined)


def test_a_bound_that_reaches_b_refutes_the_arm() -> None:
    """Then B was only deeper than the chain's bound, and the enabling claim is about search."""

    arm = arms.MoreBudget(
        ceiling=3, chain_bound=2,
        rungs=[arms.Rung(1, 5, 0, False), arms.Rung(2, 9, 0, False), arms.Rung(3, 9, 1, True)],
    )
    assert arm.outcome == "refuted"


def test_a_sweep_that_never_closed_is_unrunnable_not_satisfied() -> None:
    """Still growing at the ceiling means the question was not answered."""

    arm = arms.MoreBudget(
        ceiling=2, chain_bound=2,
        rungs=[arms.Rung(1, 5, 0, False), arms.Rung(2, 9, 0, False)],
    )
    assert arm.outcome == "unrunnable"
