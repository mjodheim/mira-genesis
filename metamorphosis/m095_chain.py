"""The M095 chain: two repairs the lineage chose, the second reachable only after the first.

    S0 --(A)--> S1 --(B)--> S2      and, from S0, B is unreachable.

Everything mechanical is M094's: the same diagnosis, the same breadth-first composition search,
the same execution-based acceptance. M095 adds one operation (`m095_reach.IncludeRenderedField`)
and one capability shape (`m095_reach.RenderNestedValueObject`), and claims one thing M094 did
not: **the second repair is reachable only because the first was adopted.**

Three properties carry that, and each is measured rather than asserted:

* **the second target is not supplied.** After A is adopted the diagnosis is re-run against the
  changed code and picks B itself. Nothing between the two repairs is human.
* **B is unreachable from S0.** `control_from_s0` targets B directly, with the identical
  operation set and the identical bound, and exhausts it. Nothing is found — not "nothing was
  chosen", nothing exists to choose. It runs *before* the chain, so it cannot be informed by it.
* **A is what changed that.** `counterfactual` rebuilds S0 from scratch and searches for B
  again. It fails again, so the enabling is A and not elapsed time, budget, or the order things
  were tried in.

The operation set offered is identical in both states. What differs is that one of its members
can apply, which is read from the code. See `m095_reach`.
"""

from __future__ import annotations

import ast
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

from metamorphosis import m094_composition as composition
from metamorphosis import m094_execution as execution
from metamorphosis import m095_reach as reach
from metamorphosis import m095_world as world
from metamorphosis.m094_diagnosis import (
    CAPABILITY_SHAPES,
    Diagnosis,
    Insufficiency,
    clear_caches,
    decode_rendering,
    diagnose,
)
from metamorphosis.m094_synthesis import (
    _declared_field_names,
    _exposed_collection_names,
    _find_class_node,
)

CHAIN_SCHEMA = "m095-chain-v1"

#: M094's shapes plus the one that can see a nested rendering. Passed explicitly rather than
#: added to `CAPABILITY_SHAPES`, because M094's result depends on measuring with that tuple.
SHAPES = tuple(CAPABILITY_SHAPES) + (reach.RenderNestedValueObject(),)

NESTED = "render_nested_value_object_as_mapping"


class ChainError(RuntimeError):
    """A chain step was asked for something the state cannot give."""


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    ).hexdigest()


def measure(root: Path) -> Diagnosis:
    """The diagnosis over the world, with the nested shape available."""

    return diagnose(root, (world.COMPONENT,), SHAPES)


# ── one search, identical in every state ─────────────────────────────


@dataclass
class Attempt:
    """One search: what was offered, what it examined, and what it reached."""

    label: str
    class_name: str
    capability: str
    requirement: str
    examined: int = 0
    survivors: int = 0
    adopted_method: str | None = None
    adopted_source: str | None = None
    nested_offered: tuple[str, ...] = ()
    nested_unreachable: tuple[str, ...] = ()
    executed: int = 0
    confirmed: int = 0
    #: How many operations the search was offered, and the longest chain it would grow.
    operations_offered: int = 0
    bound: int = 0
    notes: dict[str, object] = field(default_factory=dict)

    @property
    def reached(self) -> bool:
        return self.adopted_source is not None

    def to_dict(self) -> dict[str, object]:
        return {
            "label": self.label,
            "class": self.class_name,
            "capability": self.capability,
            "requirement": [list(item) for item in decode_rendering(self.requirement)],
            "examined": self.examined,
            "survivors": self.survivors,
            "executed": self.executed,
            "confirmed_by_execution": self.confirmed,
            "operations_offered": self.operations_offered,
            "bound": self.bound,
            "reached": self.reached,
            "adopted_method": self.adopted_method,
            "nested_operations_offered": list(self.nested_offered),
            "nested_operations_unreachable": list(self.nested_unreachable),
            "notes": dict(self.notes),
        }


def _nested_operations(root: Path, tree: ast.AST, node: ast.ClassDef, requirement: str):
    """The nested-rendering operations this requirement calls for, in this state.

    The inner class name comes from the field's annotation and the inner requirement from what
    the call sites wrote about the inner object — both recovered, neither declared.
    """

    annotations = {
        item.target.id: ast.unparse(item.annotation)
        for item in node.body
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)
    }
    considered = measure(root).considered
    nested: list[reach.NestedRendering] = []
    for key, source_field, _wrapper in decode_rendering(requirement):
        inner_name = annotations.get(source_field, "").strip()
        if not inner_name or _find_class_node(tree, inner_name) is None:
            continue
        inner_requirement = next(
            (item.detail for item in considered
             if item.target == inner_name
             and item.capability == "render_value_object_as_mapping"),
            "",
        )
        if not inner_requirement:
            continue
        nested.append(reach.NestedRendering(
            key=key, field=source_field,
            inner_class_name=inner_name, inner_requirement=inner_requirement,
        ))
    inner_classes = {
        item.inner_class_name: _find_class_node(tree, item.inner_class_name)
        for item in nested
    }
    return reach.operations_for_nested(tuple(nested), inner_classes)


def search(root: Path, target: Insufficiency, *, label: str,
           max_length: int | None = None, withhold_nested: bool = False) -> Attempt:
    """Assemble a repair for one insufficiency, in whatever state the tree is in.

    The same function serves the control, both chain steps and both counterfactuals. Nothing in
    it consults which of those it is being used for.

    `withhold_nested` removes the nested-rendering operations from the set while leaving the
    state alone. It answers the question the A-removing counterfactual cannot: is the enabling
    A's, or is it merely the operation's? Run at S1, where A *has* been adopted, a failure says
    the operation is the vehicle through which A's repair is reachable — and a success would say
    A was never needed, which would refute the whole chain.
    """

    attempt = Attempt(label=label, class_name=target.target,
                      capability=target.capability, requirement=target.detail)

    source = (root / world.COMPONENT).read_text(encoding="utf-8")
    tree = ast.parse(source)
    node = _find_class_node(tree, target.target)
    if node is None:
        attempt.notes["stopped"] = f"class {target.target} is absent"
        return attempt

    shape = next(s for s in SHAPES if s.name == target.capability)
    nested_ops = ()
    if target.capability == NESTED and not withhold_nested:
        nested_ops = _nested_operations(root, tree, node, target.detail)
        attempt.nested_offered = tuple(op.describe() for op in nested_ops)
        attempt.nested_unreachable = reach.unreachable_operations(nested_ops)
    elif withhold_nested:
        # Recorded, because an arm that quietly offered less than it claimed would look
        # exactly like an arm that failed for the reason it was built to test.
        attempt.notes["nested_operations_withheld"] = True

    taken = frozenset(
        item.name for item in node.body
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not item.name.startswith("_")
    )
    operations = tuple(composition.operations_for(
        "render_value_object_as_mapping",
        _declared_field_names(node), target.detail,
        sorted(_exposed_collection_names(node)),
        taken,
    )) + tuple(nested_ops)

    def accepts(modified: str) -> bool:
        try:
            candidate = ast.parse(modified)
        except SyntaxError:
            return False
        found = _find_class_node(candidate, target.target)
        return found is not None and shape.is_supplied_by(found, target.target, target.detail)

    def confirms(ordered: list[tuple[str, str]]) -> list[tuple[str, str]]:
        """Run the survivors. M094's amendment A2, which this search had quietly dropped.

        The structural predicate says a candidate *reads* correctly. A2 established that it
        must also *behave* correctly, on values the class accepts, in a fresh interpreter that
        is never told which method should work -- and an audit of this module found it had
        gone back to reading. A repair that satisfies the shape and raises when executed is
        exactly what M094's qualification refuted.
        """

        cases = execution.constructible_cases(
            root, world.COMPONENT, target.target, decode_rendering(target.detail),
        )
        if not cases:
            return []
        window = ordered[: execution.MAX_CONFIRMATIONS]
        records = execution.probe_variants(
            root, world.COMPONENT,
            [(str(index), modified) for index, (_method, modified) in enumerate(window)],
            target.target, decode_rendering(target.detail), cases,
        )
        by_id = {record["id"]: record for record in records}
        return [
            pair for index, pair in enumerate(window)
            if execution.agrees(by_id.get(str(index), {}))
        ]

    bound = max_length or composition.MAX_COMPOSITION_LENGTH
    # Recorded from the set the search is about to use, never rebuilt: an arm that
    # certified a ceiling for a set the search never saw would certify nothing.
    attempt.operations_offered = len(operations)
    attempt.bound = bound
    survivors: list[tuple[str, str]] = []
    for chain in composition._compositions(operations, bound):
        draft = composition.MethodDraft()
        applied = True
        for operation in chain:
            grown = operation.apply(draft)
            if grown is None:
                applied = False
                break
            draft = grown
        attempt.examined += 1
        if not applied:
            continue
        function = composition.render(draft)
        if function is None:
            continue
        method = composition.unparse(function)
        modified = composition.insert_into_class(source, target.target, method)
        if modified is None or not accepts(modified):
            continue
        survivors.append((method, modified))

    attempt.survivors = len(survivors)
    if not survivors:
        attempt.notes["stopped"] = "no composition reached the requirement"
        return attempt

    # Content address orders them, as M094's search does; execution decides among them.
    ordered = sorted(survivors, key=lambda pair: _digest({"m": pair[0]}))
    confirmed = confirms(ordered)
    attempt.executed = min(len(ordered), execution.MAX_CONFIRMATIONS)
    attempt.confirmed = len(confirmed)
    if not confirmed:
        attempt.notes["stopped"] = "no survivor reproduced the requirement when executed"
        return attempt
    method, modified = confirmed[0]
    attempt.adopted_method = method
    attempt.adopted_source = modified
    return attempt


# ── the chain, the control, the counterfactual ───────────────────────


def _nested_is_reachable(root: Path) -> bool:
    """Can the nested-rendering operation apply in the state as it stands?

    This is the flip the milestone is about, asked of the tree rather than of the history. It is
    what identifies A: the repair after which this turns true. Reading it from the state is what
    keeps the chain from assuming the ordering it exists to test.
    """

    diagnosis = measure(root)
    target = next(
        (item for item in diagnosis.considered if item.capability == NESTED), None
    )
    if target is None:
        return False
    tree = ast.parse((root / world.COMPONENT).read_text(encoding="utf-8"))
    node = _find_class_node(tree, target.target)
    if node is None:
        return False
    operations = _nested_operations(root, tree, node, target.detail)
    return bool(operations) and not reach.unreachable_operations(operations)


def control_from_s0(root: Path) -> Attempt:
    """Target B directly from S0 and exhaust the operation set.

    Run before the chain, so nothing about it can be informed by what the chain found.
    """

    target = next(
        (item for item in measure(root).unmet if item.capability == NESTED), None
    )
    if target is None:
        raise ChainError("the world presents no nested requirement to be unreachable")
    return search(root, target, label="B from S0")


def adopt(root: Path, attempt: Attempt) -> None:
    """Write a reached repair into the world, and forget what was measured before it."""

    if attempt.adopted_source is None:
        raise ChainError(f"{attempt.label} reached nothing to adopt")
    (root / world.COMPONENT).write_text(attempt.adopted_source, encoding="utf-8")
    clear_caches()


@dataclass
class Chain:
    """The whole run: the control, the two steps, and the counterfactual."""

    control: Attempt | None = None
    step_a: Attempt | None = None
    step_b: Attempt | None = None
    counterfactual: Attempt | None = None
    #: S1 with the nested operation withheld. Separates "A enabled B" from "the operation did".
    without_operation: Attempt | None = None
    #: Every repair attempted at S0 — one per capability the measure ranked equal first, the same
    #: rule amendment A4 imposes at S1. `step_a` is whichever of them made the nested operation
    #: applicable, identified by measuring the flip rather than by its position in this list.
    first_step: list[Attempt] = field(default_factory=list)
    #: Every repair made at S1 — one per capability the measure ranked equal first. `step_b` is
    #: the nested one, kept named because it is the one the enabling claim is about.
    second_step: list[Attempt] = field(default_factory=list)
    selected_first: str = ""
    selected_second: str = ""
    #: What was actually on disk, counted rather than assumed.
    facts: dict[str, object] = field(default_factory=dict)
    #: How `step_a` was identified — by the operation flipping, or by falling back to
    #: the first repair that reached. Recorded because a record that merely asserts the
    #: good case cannot be checked, and the fallback is the case worth seeing.
    step_a_identified_by: str = "nothing_reached"

    @property
    def every_tied_capability_repaired(self) -> bool:
        """Nothing at S1 was left to a name-based tie-break."""

        return bool(self.second_step) and all(item.reached for item in self.second_step)

    @property
    def enabling_demonstrated(self) -> bool:
        """B unreachable from S0, reachable from S1, and unreachable again without A."""

        return bool(
            self.control is not None and not self.control.reached
            and self.step_a is not None and self.step_a.reached
            and self.step_b is not None and self.step_b.reached
            and self.counterfactual is not None and not self.counterfactual.reached
        )

    @property
    def s0_tie_was_not_broken_by_name(self) -> bool:
        """Every capability the measure ranked equal first at S0 was attempted, not just one.

        Amendment A4's rule was applied at S1 and not at S0, where `run` took the head of a
        sorted list. In the declared world nothing ties at S0 so the ordering decided nothing,
        but in a world where the two classes draw equal demand it decided the milestone. The
        rule is now the same in both states.
        """

        return bool(self.first_step)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": CHAIN_SCHEMA,
            "world": dict(self.facts),
            "control_b_from_s0": self.control.to_dict() if self.control else None,
            "step_a": self.step_a.to_dict() if self.step_a else None,
            "step_b": self.step_b.to_dict() if self.step_b else None,
            "counterfactual_b_without_a": (
                self.counterfactual.to_dict() if self.counterfactual else None
            ),
            "counterfactual_b_at_s1_without_the_operation": (
                self.without_operation.to_dict() if self.without_operation else None
            ),
            "a_is_necessary": (
                self.counterfactual is not None and not self.counterfactual.reached
            ),
            "the_operation_is_the_vehicle_not_the_cause": (
                self.without_operation is not None and not self.without_operation.reached
                and self.counterfactual is not None and not self.counterfactual.reached
            ),
            "first_target_selected_by_the_diagnosis": self.selected_first,
            "second_target_selected_by_the_diagnosis": self.selected_second,
            "first_step_repairs": [item.to_dict() for item in self.first_step],
            "second_step_repairs": [item.to_dict() for item in self.second_step],
            "every_tied_capability_was_repaired": self.every_tied_capability_repaired,
            "the_s0_tie_was_not_broken_by_a_name": self.s0_tie_was_not_broken_by_name,
            "second_target_came_from": self.selected_second,
            "step_a_identified_by": self.step_a_identified_by,
            "enabling_demonstrated": self.enabling_demonstrated,
        }


def run(root: Path, counterfactual_root: Path, *,
        reading_callers: int | None = None,
        sample_callers: int | None = None) -> Chain:
    """S0 -> A -> S1 -> B -> S2, with the control first and the counterfactual last.

    `root` and `counterfactual_root` are both built as S0. The second is never touched by the
    chain, so searching it for B afterwards asks the question the counterfactual exists to ask:
    without A, is B still out of reach?
    """

    chain = Chain()
    arrangement = dict(reading_callers=reading_callers, sample_callers=sample_callers)
    world.build(root, **arrangement)
    world.build(counterfactual_root, **arrangement)
    chain.facts = world.WorldFacts.of(root).to_dict()

    # The control runs first, on untouched S0.
    chain.control = control_from_s0(root)

    s0 = measure(root)
    if not s0.unmet:
        raise ChainError("S0 presents nothing to repair")

    # Amendment A4's rule, at S0 as well as at S1. This used to take `s0.unmet[0]`, the head of a
    # list sorted by demand and then by name. In the declared world nothing ties at S0, so the
    # ordering decided nothing and the defect was invisible; where the two classes draw equal
    # demand it decided whether the milestone demonstrated anything at all.
    tied_first = s0.tied_selection()
    chain.selected_first = ", ".join(f"{i.target}/{i.capability}" for i in tied_first)
    reachable_before = _nested_is_reachable(root)
    for target in tied_first:
        label = "A from S0" if len(tied_first) == 1 else f"S0 tied: {target.capability}"
        attempt = search(root, target, label=label)
        chain.first_step.append(attempt)
        if not attempt.reached:
            continue
        adopt(root, attempt)
        # A is not "the first repair". It is the repair after which the nested operation can
        # apply — read from the state, so the chain does not assume the order it is testing.
        if chain.step_a is None and not reachable_before and _nested_is_reachable(root):
            chain.step_a = attempt
            chain.step_a_identified_by = "the_nested_operation_became_applicable"
            reachable_before = True
    if chain.step_a is None:
        # Nothing flipped the operation. Keep whatever was adopted in the record, so a run that
        # demonstrates no enabling still says what it did rather than looking unfinished.
        chain.step_a = next((item for item in chain.first_step if item.reached), None)
        if chain.step_a is not None:
            chain.step_a_identified_by = "fallback_first_repair_that_reached"

    s1 = measure(root)
    tied = s1.tied_selection()
    if tied:
        chain.selected_second = ", ".join(f"{i.target}/{i.capability}" for i in tied)
        nested_target = next((i for i in tied if i.capability == NESTED), tied[0])

        # Asked at S1, before anything is adopted: with A in place but the nested operation
        # withheld, is the nested repair reachable? A "yes" would mean A was never what
        # enabled it.
        chain.without_operation = search(
            root, nested_target, label="B from S1, operation withheld", withhold_nested=True,
        )

        # Amendment A4's rule, at the capability level. Two capabilities on `Sample` tie at
        # demand 2, and taking the first would be taking the one whose name sorts earliest --
        # and had that gone the other way, no enabling would have been demonstrated. Every
        # tied insufficiency is repaired, so nothing rests on the ordering.
        for target in tied:
            label = "B from S1" if target is nested_target else f"S1 tied: {target.capability}"
            attempt = search(root, target, label=label)
            chain.second_step.append(attempt)
            if attempt.reached:
                adopt(root, attempt)
            if target is nested_target:
                chain.step_b = attempt

    # And the same question again, in a world where A never happened.
    target = next(
        (item for item in measure(counterfactual_root).unmet if item.capability == NESTED),
        None,
    )
    if target is not None:
        chain.counterfactual = search(
            counterfactual_root, target, label="B without A",
        )
    return chain
