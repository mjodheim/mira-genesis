"""The world-arrangement arm: does the claim's recorded domain match the measured one?

`experiments/M095/DESIGN_AUDIT.md` defect 7 found that M095's central relation was measured in
one arrangement of the authored world and read as a property of the mechanism. It was a property
of the mechanism *and* of the arrangement, and only sweeping the arrangement showed that.

A document stating a domain is an assertion; this arm makes it a measurement, so that a change to
the selection rule cannot silently move the boundary while the prose goes on describing where it
used to be.

**This arm can fail in both directions**, which is the point — and the second direction is the one
that fired. The recorded domain used to exclude worlds where the enabling repair is outranked by
the repair it enables. Then the lineage learned to descend to the obstacle its own failed search
names, those worlds started demonstrating the relation, and the arm reported `refuted` rather than
quietly absorbing a happier answer. A claim that is too narrow is a finding, not a bonus.

What the arm now predicts is that the relation holds wherever an enabling repair exists to be
found. The two `inner == 0` points are its negative witnesses: an inner class that is never
rendered directly presents no demand of its own, so there is nothing to descend to.

Nothing here reads or writes anything under `experiments/`.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from metamorphosis import m095_chain as chain
from metamorphosis import m095_world as world

ARM_SCHEMA = "m095-arrangement-arm-v1"


def declared() -> tuple[int, int]:
    """The declared world, read when asked rather than captured at import.

    This was a module-level tuple, which froze the constants the moment the module loaded
    and made the sweep silently ignore any change to them -- the same inertness the
    `build()` parameters were fixed for one defect earlier.
    """

    return (world.READING_CALLERS, world.SAMPLE_CALLERS)


def arrangements() -> tuple[tuple[int, int], ...]:
    """The points to sweep, derived rather than chosen.

    Two demands can compare in exactly three ways. For each, take the **minimal** arrangement
    realising it with both classes still present — one caller is the smallest a class can have
    and still be called — and one **larger** arrangement, so a result cannot turn on smallness.
    The declared world serves as its own regime's larger witness.

    Two further points give the inner class **no callers at all**. That is where the claim
    genuinely fails now, and a sweep without a witness of it would have nothing that must come
    out negative. Both are included because the outer demand should not matter once the inner
    demand is absent.

    No number here is picked for being big enough or convenient; each is the smallest value
    satisfying a stated constraint.
    """

    inner, outer = declared()
    return (
        (2, 1),           # inner>outer, minimal
        (inner, outer),   # inner>outer, the declared world
        (1, 1),           # inner==outer, minimal
        (2, 2),           # inner==outer, larger
        (1, 2),           # inner<outer, minimal
        (1, 3),           # inner<outer, larger
        (0, 1),           # the inner class presents no demand of its own
        (0, 3),           # the same, with the outer demand larger
    )


def domain_predicts(inner_call_sites: int, outer_call_sites: int) -> bool:
    """What the recorded domain says should happen at this arrangement.

    Stated as a rule over the arrangement rather than as a list of expected answers, so the arm
    compares a prediction against a measurement instead of a measurement against itself.

    **The rule used to be `inner_call_sites >= outer_call_sites`,** because where the enabling
    repair carried less demand than the repair it enabled, the greedy rule never reached it
    and the chain stalled — `DESIGN_AUDIT.md` defect 7, recorded as a boundary the milestone
    had to carry. It no longer does: the lineage reads the obstacle its own failed search
    names and descends to it. The claim holds in every arrangement, so the rule is that it
    holds wherever there is an enabling repair to find.

    The boundary that remains is not about rank but about **existence**: if the inner class is
    never rendered directly it presents no demand of its own, so there is no insufficiency to
    descend to and nothing the lineage can do. That is a smaller and more natural limitation
    than the ordering one, and the sweep carries witnesses of it so the arm still has points
    that must come out negative.
    """

    del outer_call_sites
    return inner_call_sites >= 1


@dataclass
class Point:
    """One arrangement, run."""

    inner_call_sites: int
    outer_call_sites: int
    regime: str = ""
    predicted: bool = False
    demonstrated: bool = False
    selected_first: str = ""
    control_reached: bool = False
    #: Whether this point repaired anything at all. A sweep in which nothing was ever
    #: repaired has measured the instrument, not the domain.
    any_repair_reached: bool = False
    error: str = ""

    @property
    def agrees(self) -> bool:
        return not self.error and self.predicted == self.demonstrated

    def to_dict(self) -> dict[str, object]:
        return {
            "inner_call_sites": self.inner_call_sites,
            "outer_call_sites": self.outer_call_sites,
            "regime": self.regime,
            "domain_predicts_enabling": self.predicted,
            "enabling_demonstrated": self.demonstrated,
            "agrees_with_the_recorded_domain": self.agrees,
            "first_selection": self.selected_first,
            "control_reached_b_from_s0": self.control_reached,
            "any_repair_reached": self.any_repair_reached,
            "error": self.error,
        }


@dataclass
class Arrangement:
    """The arm: every point, and whether the recorded domain survived them."""

    points: list[Point] = field(default_factory=list)

    @property
    def outcome(self) -> str:
        """`satisfied` / `refuted` / `unrunnable`, the vocabulary M094's qualification uses.

        `unrunnable` exists so that an instrument failure cannot be read as a refutation of the
        claim — the distinction amendment A1 was written to preserve.
        """

        if not self.points:
            return "unrunnable"
        if not any(point.any_repair_reached for point in self.points):
            # Nothing was repaired in any arrangement. Every point reports no enabling,
            # which looks exactly like a refuted domain and is in fact a dead instrument.
            # Killing the execution probe made this arm say `refuted` -- a claim about the
            # mechanism -- when the honest answer is that it could not measure.
            return "unrunnable"
        # A refutation among the points that DID run is still a refutation. Testing the
        # error first let one broken point bury a three-point disagreement as
        # "unrunnable" -- A1 used as a silencer rather than as a distinction.
        if self.disagreements:
            return "refuted"
        if any(point.error for point in self.points):
            return "unrunnable"
        return "satisfied"

    @property
    def disagreements(self) -> list[Point]:
        return [point for point in self.points if not point.error and not point.agrees]

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": ARM_SCHEMA,
            "question": (
                "does the domain recorded for the enabling claim match the domain measured by "
                "running the chain in every way the two demands can compare?"
            ),
            "rule": "the enabling relation is claimed wherever the inner class presents a demand of its own",
            "points": [point.to_dict() for point in self.points],
            "regimes_covered": sorted({point.regime for point in self.points if point.regime}),
            "disagreements": [point.to_dict() for point in self.disagreements],
            "outcome": self.outcome,
        }


def run(make_root: Callable[[str], Path]) -> Arrangement:
    """Run the chain once per arrangement.

    `make_root` supplies a fresh empty directory for a given name, so a canonical run can preserve
    each world as evidence while a rehearsal can use temporary directories. The arm does not
    decide where its evidence lives.
    """

    arm = Arrangement()
    for inner, outer in arrangements():
        point = Point(
            inner_call_sites=inner,
            outer_call_sites=outer,
            predicted=domain_predicts(inner, outer),
        )
        try:
            built = chain.run(
                make_root(f"arrangement-{inner}-{outer}"),
                make_root(f"arrangement-{inner}-{outer}-counterfactual"),
                reading_callers=inner,
                sample_callers=outer,
            )
        except Exception as error:  # noqa: BLE001 - an instrument failure, not a refutation
            point.error = f"{type(error).__name__}: {error}"
            arm.points.append(point)
            continue

        # What was BUILT, not what was asked for. A build that silently ignored the counts
        # would otherwise be recorded as the arrangement it was supposed to be, and read
        # as a refutation of the domain rather than as a broken instrument.
        measured = (built.facts.get("inner_call_sites"), built.facts.get("outer_call_sites"))
        if measured != (inner, outer):
            point.error = (
                f"asked for {inner}/{outer} call sites and the world reports "
                f"{measured[0]}/{measured[1]}"
            )
            arm.points.append(point)
            continue
        point.regime = str(built.facts.get("ordering_regime", ""))
        point.demonstrated = built.enabling_demonstrated
        point.selected_first = built.selected_first
        point.control_reached = bool(built.control and built.control.reached)
        point.any_repair_reached = any(
            item.reached for item in (*built.first_step, *built.second_step)
        )
        arm.points.append(point)
    return arm


# ── the random-target arm ─────────────────────────────────────────────


@dataclass
class Rival:
    """One target the diagnosis did not select, repaired instead of the one it did."""

    target: str
    repaired: bool = False
    adopted_method: str = ""
    b_reached: bool = False
    b_examined: int = 0
    b_blocked_by: tuple[str, ...] = ()
    notes: str = ""
    error: str = ""

    @property
    def outcome(self) -> str:
        """A rival that could not be repaired exercised nothing, and says so."""

        if self.error:
            return "unrunnable"
        if not self.repaired:
            return "unrunnable"
        return "refuted" if self.b_reached else "satisfied"

    def to_dict(self) -> dict[str, object]:
        return {
            "target": self.target,
            "was_repaired": self.repaired,
            "adopted_method": self.adopted_method,
            "b_reached_afterwards": self.b_reached,
            "b_examined": self.b_examined,
            "b_blocked_by": list(self.b_blocked_by),
            "notes": self.notes,
            "outcome": self.outcome,
            "error": self.error,
        }


@dataclass
class RandomTarget:
    """Does repairing something the diagnosis did *not* choose also unlock B?

    If it does, the diagnosis is doing no work and the enabling is a property of the world.
    Every eligible rival is run rather than one being drawn, on amendment A4's logic: a draw
    would need a salt, a salt would need to be derived from something, and exhausting a set of
    two removes the question entirely. What is reported is a census, and it says so.
    """

    rivals: list[Rival] = field(default_factory=list)
    eligible_considered: int = 0
    inner_classes: tuple[str, ...] = ()
    rivals_touching_the_inner_class: int = 0

    @property
    def outcome(self) -> str:
        if not self.rivals:
            return "unrunnable"
        if any(rival.outcome == "refuted" for rival in self.rivals):
            return "refuted"
        if not self.rivals_touching_the_inner_class:
            # No rival can write into the class the nested requirement needs a renderer
            # on, so `b_reached` was False by construction and `satisfied` was decided
            # before the arm ran. That is a control that cannot fail, and it says so.
            return "unrunnable"
        if not any(rival.outcome == "satisfied" for rival in self.rivals):
            # Every rival was unrepairable, so nothing was actually tested.
            return "unrunnable"
        return "satisfied"

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": "m095-random-target-arm-v1",
            "question": (
                "does repairing a target the diagnosis did not select also make B reachable?"
            ),
            "every_eligible_rival_was_run": len(self.rivals) == self.eligible_considered,
            "eligible_rivals": self.eligible_considered,
            "rivals_run": len(self.rivals),
            "inner_classes_the_requirement_needs": list(self.inner_classes),
            "rivals_that_could_touch_them": self.rivals_touching_the_inner_class,
            "rivals": [rival.to_dict() for rival in self.rivals],
            "outcome": self.outcome,
        }


def random_target(make_root: Callable[[str], Path]) -> RandomTarget:
    """Repair each unselected target in its own fresh world, then search for B."""

    arm = RandomTarget()
    census_root = world.build(make_root("rival-census"))
    probe = chain.measure(census_root)
    selected = {(item.target, item.capability) for item in probe.tied_selection()}
    # The nested capability is not a rival: it is the control's own target. Counting it
    # inflated the census to two and guaranteed one `unrunnable` row that tested nothing.
    eligible = [
        item for item in probe.unmet
        if (item.target, item.capability) not in selected and item.capability != chain.NESTED
    ]
    arm.eligible_considered = len(eligible)
    # A rival can only move the nested requirement by writing a renderer into the inner
    # class. If none of them targets it, `satisfied` is fixed before the arm runs.
    inner = set(chain.nested_inner_classes(census_root))
    arm.inner_classes = tuple(sorted(inner))
    arm.rivals_touching_the_inner_class = sum(1 for item in eligible if item.target in inner)

    for index, rival in enumerate(eligible):
        row = Rival(target=f"{rival.target}/{rival.capability}")
        try:
            root = world.build(make_root(f"rival-{index}"))
            target = next(
                (item for item in chain.measure(root).unmet
                 if item.target == rival.target and item.capability == rival.capability),
                None,
            )
            if target is None:
                row.error = "the rival is not unmet in its own world"
                arm.rivals.append(row)
                continue

            attempt = chain.search(root, target, label=f"rival {row.target}")
            row.repaired = attempt.reached
            if not attempt.reached:
                arm.rivals.append(row)
                continue
            row.adopted_method = (attempt.adopted_method or "").split("(")[0].strip()
            chain.adopt(root, attempt)

            after = next(
                (item for item in chain.measure(root).unmet if item.capability == chain.NESTED),
                None,
            )
            if after is None:
                # B settled by a target the diagnosis rejected is the single most
                # decisive refutation this arm can observe. It was filed as an
                # instrument error with b_reached recorded as False -- A1 inverted.
                row.b_reached = True
                row.notes = "the rival repair met the nested requirement outright"
                arm.rivals.append(row)
                continue
            follow = chain.search(root, after, label="B after a rival repair")
            row.b_reached = follow.reached
            row.b_examined = follow.examined
            row.b_blocked_by = follow.nested_unreachable
        except Exception as error:  # noqa: BLE001 - instrument failure, not a refutation
            row.error = f"{type(error).__name__}: {error}"
        arm.rivals.append(row)
    return arm


# ── the more-budget arm ───────────────────────────────────────────────


@dataclass
class Rung:
    bound: int
    examined: int
    survivors: int
    reached: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "bound": self.bound, "examined": self.examined,
            "survivors": self.survivors, "reached": self.reached,
        }


@dataclass
class MoreBudget:
    """Is B unreachable from S0, or merely deeper than the bound the chain used?

    The ceiling is not a larger number chosen for being large. Every operation in the set refuses
    to apply twice, so no composition can be longer than the set, and sweeping to `len(set)` is
    exhaustive by construction rather than by assertion.
    """

    ceiling: int = 0
    chain_bound: int = 0
    rungs: list[Rung] = field(default_factory=list)
    #: The same sweep at S1, where B IS reachable. Without it, every way of killing the
    #: searcher -- a dead operation, an unoffered operation, an execution probe that can
    #: construct no case -- produces exactly the empty result the arm reads as success.
    liveness: list[Rung] = field(default_factory=list)
    nested_offered: tuple[str, ...] = ()
    error: str = ""

    @property
    def saturates_at(self) -> int | None:
        """The first bound past which nothing new is examined."""

        for rung in self.rungs:
            if all(later.examined == rung.examined for later in self.rungs
                   if later.bound >= rung.bound):
                return rung.bound
        return None

    @property
    def outcome(self) -> str:
        if self.error or not self.rungs:
            return "unrunnable"
        if any(rung.reached for rung in self.rungs):
            return "refuted"
        if not self.nested_offered:
            # The operation whose absence the sweep is attributing the failure to was
            # never in the set. Nothing was tested.
            return "unrunnable"
        if not any(rung.reached for rung in self.liveness):
            # The searcher found nothing at S1 either, where B is reachable. A dead
            # searcher produces the same empty sweep as a genuinely unreachable target,
            # and without this the arm cannot tell them apart.
            return "unrunnable"
        saturation = self.saturates_at
        if saturation is None or saturation >= self.ceiling:
            # The sweep never closed, so "unreachable" might still mean "not searched far enough".
            return "unrunnable"
        return "satisfied"

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": "m095-more-budget-arm-v1",
            "question": "is B unreachable from S0, or only deeper than the bound the chain used?",
            "ceiling": self.ceiling,
            "why_that_ceiling": (
                "no operation applies twice, so no composition can exceed the size of the "
                "offered set; sweeping to it is exhaustive by construction"
            ),
            "chain_bound": self.chain_bound,
            "saturates_at_bound": self.saturates_at,
            "nested_operations_offered": list(self.nested_offered),
            "rungs": [rung.to_dict() for rung in self.rungs],
            "liveness_rungs_at_s1": [rung.to_dict() for rung in self.liveness],
            "the_searcher_was_shown_alive": any(r.reached for r in self.liveness),
            "outcome": self.outcome,
            "error": self.error,
        }


def more_budget(make_root: Callable[[str], Path]) -> MoreBudget:
    """Search S0 for B at every bound from 1 up to the size of the offered operation set."""

    arm = MoreBudget()
    try:
        root = world.build(make_root("more-budget"))
        target = next(
            (item for item in chain.measure(root).unmet if item.capability == chain.NESTED), None
        )
        if target is None:
            arm.error = "the world presents no nested requirement"
            return arm

        full = chain.search(root, target, label="B from S0, chain bound")
        arm.ceiling = full.operations_offered
        arm.chain_bound = full.bound
        arm.nested_offered = full.nested_offered
        if arm.ceiling < 1:
            arm.error = "the search was offered no operations"
            return arm

        for bound in range(1, arm.ceiling + 1):
            attempt = chain.search(root, target, label=f"B from S0, bound {bound}",
                                   max_length=bound)
            arm.rungs.append(Rung(bound=bound, examined=attempt.examined,
                                  survivors=attempt.survivors, reached=attempt.reached))

        # The positive control. Reach S1 by the ordinary route, then sweep the same way.
        live = world.build(make_root("more-budget-liveness"))
        for enabler in chain.measure(live).tied_selection():
            found = chain.search(live, enabler, label=f"enabler {enabler.capability}")
            if found.reached:
                chain.adopt(live, found)
        after = next(
            (item for item in chain.measure(live).unmet if item.capability == chain.NESTED),
            None,
        )
        if after is not None:
            for bound in range(1, arm.ceiling + 1):
                probe = chain.search(live, after, label=f"B at S1, bound {bound}",
                                     max_length=bound)
                arm.liveness.append(Rung(bound=bound, examined=probe.examined,
                                         survivors=probe.survivors, reached=probe.reached))
                if probe.reached:
                    break
    except Exception as error:  # noqa: BLE001 - instrument failure, not a refutation
        arm.error = f"{type(error).__name__}: {error}"
    return arm
