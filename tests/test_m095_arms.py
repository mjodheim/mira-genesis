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


def test_the_outer_class_is_always_called_and_the_inner_one_sometimes_is_not() -> None:
    """The outer class must be called, or there is no requirement to be about at all.

    The inner class deliberately reaches zero in two points: that is the arrangement where the
    claim fails, and a sweep without it would have nothing that must come out negative.
    """

    points = arms.arrangements()
    assert all(outer >= 1 for _inner, outer in points)
    assert any(inner == 0 for inner, _outer in points)
    assert any(inner >= 1 for inner, _outer in points)


# ── the measurement ───────────────────────────────────────────────────


def test_the_measured_domain_matches_the_recorded_one(swept: arms.Arrangement) -> None:
    assert swept.outcome == "satisfied", [p.to_dict() for p in swept.disagreements]


def test_the_enabling_relation_holds_in_every_supported_regime(swept: arms.Arrangement) -> None:
    supported = [p for p in swept.points if p.inner_call_sites >= p.outer_call_sites]
    assert supported
    assert all(point.demonstrated for point in supported), (
        f"{[p.to_dict() for p in supported if not p.demonstrated]} should have demonstrated it"
    )


def test_the_ordering_no_longer_excludes_anything(swept: arms.Arrangement) -> None:
    """This asserted the opposite, and the assertion was correct when it was written.

    Where the enabling repair carried less demand than the repair it enabled, the greedy rule
    never reached it and the milestone recorded a boundary it had to carry. The lineage now reads
    the obstacle its own failed search names and descends to it, so rank excludes nothing.
    """

    outranked = [
        p for p in swept.points
        if p.inner_call_sites < p.outer_call_sites and p.inner_call_sites >= 1
    ]
    assert outranked, "the sweep no longer contains the arrangement this is about"
    assert all(point.demonstrated for point in outranked)


def test_a_world_with_no_enabler_to_find_is_still_excluded(swept: arms.Arrangement) -> None:
    """The boundary that remains, pinned as a negative so it cannot quietly move.

    It is about existence rather than rank: if the inner class is never rendered directly it
    presents no demand of its own, so there is no insufficiency to descend to. Reading the
    obstacle does not help when the remedy is not something the diagnosis can see.
    """

    absent = [p for p in swept.points if p.inner_call_sites == 0]
    assert absent, "the sweep has no point that must come out negative"
    assert not any(point.demonstrated for point in absent)
    assert all(point.predicted is False for point in absent)


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
        # These stand for runs that repaired something; the liveness gate is about a
        # sweep in which nothing was ever repaired, which is a separate test.
        any_repair_reached=True,
    )


def test_a_supported_world_that_stops_working_refutes_the_arm() -> None:
    """The claim would be too broad."""

    arm = arms.Arrangement(points=[_point(3, 2, False), _point(0, 1, False)])
    assert arm.outcome == "refuted"
    assert [p.inner_call_sites for p in arm.disagreements] == [3]


def test_an_excluded_world_that_starts_working_also_refutes_the_arm() -> None:
    """The claim would be too narrow — which is a finding, not a bonus.

    This is the direction an arm is most likely to be written to ignore. A boundary that moves
    outward while the prose still describes the old one is the same defect as one that moves in.
    """

    arm = arms.Arrangement(points=[_point(3, 2, True), _point(0, 1, True)])
    assert arm.outcome == "refuted"
    assert [p.inner_call_sites for p in arm.disagreements] == [0]


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


def test_this_world_contains_no_rival_that_could_test_the_claim(
    rivals: arms.RandomTarget,
) -> None:
    """The honest verdict, and it is not `satisfied`.

    B becomes reachable only when the INNER class supplies a renderer. Every repair is inserted
    into its own target's class, and the sole eligible rival targets the outer one. So
    `b_reached` was False by construction: the arm's pass was decided before it ran, which is a
    control that cannot fail.

    It used to report `satisfied` and the milestone's documents repeated that. What it can
    honestly say is that this world contains no rival capable of unlocking B. Making the arm
    informative needs a second insufficiency on the inner class -- a different world, not a
    different check.
    """

    assert rivals.outcome == "unrunnable"
    assert rivals.inner_classes == ("Reading",)
    assert rivals.rivals_touching_the_inner_class == 0
    assert not any(rival.b_reached for rival in rivals.rivals)


def test_the_controls_own_target_is_not_counted_as_a_rival(
    rivals: arms.RandomTarget,
) -> None:
    """The nested capability IS B. Counting it inflated the census from one to two.

    It could only ever report `unrunnable`, because B is unreachable at S0 -- which is what the
    control already establishes. An arm padded with a re-run of the control looks like it
    exhausted a set of two.
    """

    assert rivals.eligible_considered == 1
    assert len(rivals.rivals) == 1
    assert all(chain.NESTED not in rival.target for rival in rivals.rivals)
    assert rivals.to_dict()["every_eligible_rival_was_run"] is True


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


# ── the tie must not decide, in any order ─────────────────────────────


def test_the_domain_survives_permuting_every_tie(tmp_path, monkeypatch) -> None:
    """Amendment A4's premise, taken seriously: tied members are indistinguishable.

    If they are indistinguishable by the measure, then the order they arrive in is not
    information, and permuting it must change nothing. It did. Two of the four supported
    arrangements flipped to `no` under reversal -- A4's defect a third time, relocated into the S0
    loop, in a milestone whose two documents both declared it settled.

    What made it invisible is worth keeping: under reversal the mechanism WORKED. The nested
    repair was reached, in the first round, after its enabler. The record only read the second
    round, so a successful run reported nothing.
    """

    from metamorphosis.m094_diagnosis import Diagnosis

    original = Diagnosis.tied_selection

    def sweep(name: str) -> arms.Arrangement:
        base = tmp_path / name
        base.mkdir(parents=True, exist_ok=True)

        def make_root(leaf: str) -> Path:
            root = base / leaf
            root.mkdir(parents=True, exist_ok=True)
            return root

        return arms.run(make_root)

    forward = sweep("forward")
    monkeypatch.setattr(
        Diagnosis, "tied_selection", lambda self: list(reversed(original(self)))
    )
    reversed_ = sweep("reversed")

    assert forward.outcome == "satisfied"
    assert reversed_.outcome == "satisfied", (
        "the domain depends on the order tied capabilities arrive in: "
        f"{[p.to_dict() for p in reversed_.disagreements]}"
    )
    assert [(p.inner_call_sites, p.outer_call_sites, p.demonstrated) for p in forward.points] == [
        (p.inner_call_sites, p.outer_call_sites, p.demonstrated) for p in reversed_.points
    ]


# ── the arms must notice a dead mechanism ─────────────────────────────


def test_a_refutation_outranks_an_instrument_error(tmp_path) -> None:
    """One broken point must not bury a disagreement as `unrunnable`.

    Error was tested before refutation, so a three-point refutation plus one exception reported
    `unrunnable` -- amendment A1 used as a silencer rather than as a distinction. A1 says an
    instrument failure is not evidence ABOUT THE MECHANISM; it does not say the points that ran
    stop counting.
    """

    broken = _point(2, 1, False)
    broken.error = "ChainError: boom"
    arm = arms.Arrangement(points=[broken, _point(3, 2, False)])
    assert arm.outcome == "refuted"


def test_a_rival_that_settles_b_refutes_rather_than_erroring() -> None:
    """A1 inverted: the strongest possible refutation was filed as an instrument failure.

    `b_reached_afterwards` was recorded as False in exactly the case where a rival had reached B
    outright -- the opposite of what happened.
    """

    settled = arms.Rival(target="X/y", repaired=True, b_reached=True,
                         notes="the rival repair met the nested requirement outright")
    assert settled.outcome == "refuted"
    arm = arms.RandomTarget(rivals=[settled], eligible_considered=1,
                            inner_classes=("Reading",), rivals_touching_the_inner_class=1)
    assert arm.outcome == "refuted"


def test_the_budget_arm_shows_its_searcher_alive_before_reading_an_empty_sweep(
    budget: arms.MoreBudget,
) -> None:
    """An empty sweep is what a dead searcher produces, and what an unreachable target produces.

    Without a rung that must come back positive, the arm cannot tell them apart -- and reported
    `satisfied` under three independent deaths of the mechanism.
    """

    assert budget.nested_offered, "the operation the sweep blames was never offered"
    assert any(rung.reached for rung in budget.liveness), (
        "no bound reached B at S1, where it is reachable: the searcher is dead"
    )
    assert budget.outcome == "satisfied"


def test_a_dead_searcher_makes_the_budget_arm_unrunnable_not_satisfied(monkeypatch, tmp_path) -> None:
    """The three kills, each of which used to read as a pass."""

    from metamorphosis import m094_execution as execution
    from metamorphosis import m095_reach as reach

    def sweep(name: str) -> arms.MoreBudget:
        base = tmp_path / name
        base.mkdir(parents=True, exist_ok=True)

        def make_root(leaf: str) -> Path:
            root = base / leaf
            root.mkdir(parents=True, exist_ok=True)
            return root

        return arms.more_budget(make_root)

    monkeypatch.setattr(reach.IncludeRenderedField, "apply", lambda self, draft: None)
    assert sweep("no-apply").outcome == "unrunnable"
    monkeypatch.undo()

    monkeypatch.setattr(reach, "operations_for_nested", lambda nested, classes: ())
    assert sweep("not-offered").outcome == "unrunnable"
    monkeypatch.undo()

    monkeypatch.setattr(execution, "constructible_cases", lambda *a, **k: [])
    assert sweep("no-cases").outcome == "unrunnable"


def test_a_dead_instrument_is_unrunnable_not_a_refuted_domain(monkeypatch, tmp_path) -> None:
    """Every point reporting no enabling looks the same whether the domain is wrong or the
    instrument is dead. Killing the execution probe made this arm say `refuted` -- a claim about
    the mechanism -- when the honest answer is that it could not measure at all.
    """

    from metamorphosis import m094_execution as execution

    def sweep(name: str) -> arms.Arrangement:
        base = tmp_path / name
        base.mkdir(parents=True, exist_ok=True)

        def make_root(leaf: str) -> Path:
            root = base / leaf
            root.mkdir(parents=True, exist_ok=True)
            return root

        return arms.run(make_root)

    monkeypatch.setattr(execution, "constructible_cases", lambda *a, **k: [])
    arm = sweep("dead")
    assert arm.outcome == "unrunnable"
    assert not any(point.any_repair_reached for point in arm.points)


def test_a_sweep_that_repaired_something_can_still_refute(swept: arms.Arrangement) -> None:
    """The liveness gate must not swallow real disagreements."""

    assert any(point.any_repair_reached for point in swept.points)
    assert arms.Arrangement(points=[_point(3, 2, False)]).outcome == "refuted"


def test_the_declared_point_is_read_when_asked_not_captured_at_import(monkeypatch) -> None:
    """A module-level tuple froze the constants at import and made the sweep ignore them."""

    monkeypatch.setattr(world, "READING_CALLERS", 7)
    assert arms.declared() == (7, world.SAMPLE_CALLERS)
    assert (7, world.SAMPLE_CALLERS) in arms.arrangements()


def test_a_probe_that_never_ran_is_not_recorded_as_candidates_that_failed(
    tmp_path, monkeypatch
) -> None:
    """Amendment A1's fifth regression in this milestone.

    `executed` was set from the survivor count whatever happened, so a probe that could
    construct no case -- and therefore ran nothing at all -- was recorded as N candidates that
    ran and disagreed. That reads as a refutation of the repair, which is precisely the
    confusion A1 exists to prevent.
    """

    from metamorphosis import m094_execution as execution

    world.build(tmp_path)
    target = next(
        item for item in chain.measure(tmp_path).unmet if item.capability != chain.NESTED
    )

    alive = chain.search(tmp_path, target, label="intact")
    assert alive.executed > 0 and alive.confirmed > 0

    monkeypatch.setattr(execution, "constructible_cases", lambda *a, **k: [])
    dead = chain.search(tmp_path, target, label="dead probe")
    assert dead.executed == 0, "a probe that ran nothing reported candidates as executed"
    assert dead.confirmed == 0
    assert "instrument_could_not_run" in dead.notes
    assert "could not run" in str(dead.notes["stopped"])


def test_the_sweep_separates_a_ranking_that_needed_help_from_one_that_did_not(
    swept: arms.Arrangement,
) -> None:
    """Six arrangements demonstrate the relation. Two of them had to be told.

    Before the descent, A was selected by demand and *happened* to enable B — the diagnosis's own
    ranking produced the enabling order without being told, and that coincidence was the
    interesting part. Where the enabler is outranked the descent selects A *because* it enables B,
    which measures the same relation but says something weaker about the ranking.

    Reporting both as `demonstrated` conflates two results, so the record carries the second count
    as well.
    """

    record = swept.to_dict()
    demonstrated = [p for p in swept.points if p.demonstrated]
    unaided = [p for p in demonstrated if not p.descended]

    assert record["demonstrated"] == len(demonstrated)
    assert record["demonstrated_without_descending"] == len(unaided)
    assert unaided, "no arrangement reached the enabling order on rank alone"
    assert len(unaided) < len(demonstrated), (
        "no arrangement needed the descent, so this sweep cannot tell the two apart and the "
        "distinction is untested"
    )

    # The ones that needed help are exactly the ones where the enabler is outranked.
    assert {(p.inner_call_sites, p.outer_call_sites) for p in demonstrated if p.descended} == {
        (p.inner_call_sites, p.outer_call_sites)
        for p in demonstrated
        if p.inner_call_sites < p.outer_call_sites
    }
