"""M095's chain, and the control that gives it meaning.

The claim is not "two repairs happened". It is that the second was **unreachable** before the
first and reachable after it, with the same operation set and the same bound, and that the
lineage chose the second itself.

Four facts carry that, and each has a test that fails if it stops holding:

1. from S0, B is unreachable — the search exhausts and finds nothing;
2. the diagnosis picks A first, and picks B afterwards, on its own;
3. from S1, B is reachable, and the repair it builds calls the method A created;
4. in a world where A never happened, B is unreachable again.

Fact 4 is what separates "B became reachable" from "B was always reachable and we got round to
it". Without it the chain would show a sequence and prove nothing about enabling.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from metamorphosis import m095_chain as chain  # noqa: E402
from metamorphosis import m095_world as world  # noqa: E402
from metamorphosis.m095_world import (  # noqa: E402,F401
    COMPONENT,
    READING_CALLERS,
    SAMPLE_CALLERS,
    WorldFacts,
    build,
)
from metamorphosis.m095_chain import (  # noqa: E402,F401
    NESTED,
    SHAPES,
    Attempt,
    Chain,
    ChainError,
    control_from_s0,
    measure,
    run,
    search,
)


@pytest.fixture(scope="module")
def executed(tmp_path_factory) -> Chain:
    """One chain run, shared: it is deterministic and takes a few seconds."""

    root = tmp_path_factory.mktemp("m095-chain")
    counterfactual = tmp_path_factory.mktemp("m095-counterfactual")
    return chain.run(root, counterfactual)


# ── the world presents the two demands, and ranks them by measurement ─


def test_the_world_presents_a_plain_and_a_nested_demand(tmp_path: Path) -> None:
    world.build(tmp_path)
    unmet = {(i.target, i.capability): i for i in measure(tmp_path).unmet}

    assert ("Reading", "render_value_object_as_mapping") in unmet
    assert ("Sample", NESTED) in unmet
    # Reading outranks Sample by demand, so the order is measured and not arranged by fiat.
    assert unmet[("Reading", "render_value_object_as_mapping")].demand == 3
    assert unmet[("Sample", NESTED)].demand == 2


def test_nothing_renders_itself_at_s0(tmp_path: Path) -> None:
    world.build(tmp_path)
    tree = ast.parse((tmp_path / world.COMPONENT).read_text(encoding="utf-8"))
    methods = [
        node.name for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and not node.name.startswith("_")
    ]
    assert methods == [], f"S0 already supplies {methods}"


# ── 1. B is unreachable from S0 ───────────────────────────────────────


def test_b_is_unreachable_from_s0(executed: Chain) -> None:
    control = executed.control
    assert control is not None
    assert control.reached is False
    assert control.survivors == 0
    assert control.examined > 0, "an unreachable target must still have been searched for"


def test_the_control_names_the_operation_the_state_cannot_use(executed: Chain) -> None:
    """Unreachable for a stated reason, not merely unfound."""

    assert executed.control.nested_unreachable == ("include=reading<-render(reading)",)
    assert executed.control.nested_offered == ("include=reading<-render(reading)",)


# ── 2. the lineage chooses both targets ───────────────────────────────


def test_the_diagnosis_selects_the_first_target(executed: Chain) -> None:
    assert executed.selected_first == "Reading/render_value_object_as_mapping"


def test_the_diagnosis_selects_the_second_target_itself(executed: Chain) -> None:
    """Nothing between the two repairs is human. This is the sequential-autonomy claim.

    The selection is now every capability the measure ranks equal first, not the one whose name
    sorts earliest, so it names both.
    """

    assert NESTED in executed.selected_second
    assert "render_value_object_as_mapping" in executed.selected_second


# ── 3. B is reachable from S1, through what A built ───────────────────


def test_both_repairs_are_reached(executed: Chain) -> None:
    assert executed.step_a is not None and executed.step_a.reached
    assert executed.step_b is not None and executed.step_b.reached


def test_the_second_repair_calls_the_method_the_first_created(executed: Chain) -> None:
    """The dependency is visible in the code, not only in the timing."""

    assert "self.reading.as_mapping()" in executed.step_b.adopted_method
    assert "as_mapping" in executed.step_a.adopted_method


def test_the_search_space_grows_once_the_operation_applies(executed: Chain) -> None:
    """A quantitative signature of the reach change, not just a boolean.

    At S0 the nested operation prunes every branch it touches, so those compositions are never
    grown. At S1 it applies and they are.
    """

    assert executed.step_b.examined > executed.control.examined


def test_the_nested_operation_is_reachable_at_s1(executed: Chain) -> None:
    assert executed.step_b.nested_unreachable == ()
    assert executed.step_b.nested_offered == ("include=reading<-render(reading)",)


# ── 4. without A, B is unreachable again ──────────────────────────────


def test_without_a_the_second_repair_is_out_of_reach(executed: Chain) -> None:
    """The counterfactual. Without it the chain shows a sequence and proves no enabling."""

    counterfactual = executed.counterfactual
    assert counterfactual is not None
    assert counterfactual.reached is False
    assert counterfactual.survivors == 0
    assert counterfactual.nested_unreachable == ("include=reading<-render(reading)",)


def test_the_counterfactual_searched_as_hard_as_the_enabled_run(executed: Chain) -> None:
    """It must fail for want of reach, not for want of trying."""

    assert executed.counterfactual.examined == executed.control.examined
    assert executed.counterfactual.examined > 0


# ── and the whole claim ───────────────────────────────────────────────


def test_the_enabling_relation_is_demonstrated(executed: Chain) -> None:
    assert executed.enabling_demonstrated is True


def test_the_record_states_what_was_and_was_not_supplied(executed: Chain) -> None:
    record = executed.to_dict()
    assert record["second_target_was_not_supplied"] is True
    assert record["world"]["authored"] is True, "the world is authored and must say so"
    assert record["enabling_demonstrated"] is True


def test_a_world_with_nothing_nested_has_no_control_to_run(tmp_path: Path) -> None:
    """The control must be impossible to run vacuously."""

    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / world.COMPONENT).write_text(
        "from dataclasses import dataclass\n\n\n"
        "@dataclass(frozen=True)\nclass Reading:\n    reading_id: str\n",
        encoding="utf-8",
    )
    (tmp_path / "caller.py").write_text(
        "from pkg.values import Reading\n\n\n"
        'def one(r: Reading) -> dict:\n    return {"reading_id": r.reading_id}\n',
        encoding="utf-8",
    )
    with pytest.raises(ChainError):
        control_from_s0(tmp_path)


def test_the_world_is_what_it_says_it_is(tmp_path: Path) -> None:
    """The disclosed facts must match the world actually written."""

    build(tmp_path)
    facts = WorldFacts()
    assert facts.inner_call_sites == READING_CALLERS == len(
        list(tmp_path.glob("reading_caller_*.py"))
    )
    assert facts.outer_call_sites == SAMPLE_CALLERS == len(
        list(tmp_path.glob("sample_caller_*.py"))
    )
    assert (tmp_path / COMPONENT).exists()
    assert facts.to_dict()["authored"] is True


# ── separating "A enabled B" from "the operation enabled B" ───────────


def test_at_s1_without_the_operation_b_is_still_out_of_reach(executed: Chain) -> None:
    """The arm the A-removing counterfactual cannot supply.

    A is adopted and the state is S1; only the nested operation is withheld. If B were reachable
    here, A would never have been what enabled it and the chain would be refuted. It is not.
    """

    withheld = executed.without_operation
    assert withheld is not None
    assert withheld.reached is False
    assert withheld.survivors == 0
    assert withheld.notes.get("nested_operations_withheld") is True
    assert withheld.nested_offered == ()


def test_neither_a_nor_the_operation_suffices_alone(executed: Chain) -> None:
    """The claim is conjunctive, and saying so is more honest than saying "A enabled B".

    A without the operation reaches nothing; the operation without A reaches nothing; together
    they reach B. A is necessary and the operation is the vehicle.
    """

    record = executed.to_dict()
    assert record["a_is_necessary"] is True
    assert record["the_operation_is_the_vehicle_not_the_cause"] is True
    # And the conjunction is what succeeds.
    assert executed.step_b.reached is True


def test_withholding_the_operation_does_not_shrink_the_rest_of_the_search(
    executed: Chain,
) -> None:
    """It must fail for want of the operation, not for having searched less."""

    assert executed.without_operation.examined == executed.control.examined


# ── what the design audit found, kept as tests ────────────────────────


def test_the_search_confirms_its_survivors_by_execution(executed: Chain) -> None:
    """Amendment A2's rule, which this search had quietly dropped.

    The audit found M095 accepting candidates on the structural predicate alone while its own
    docstring claimed otherwise — the exact defect A2 fixed for M094, reintroduced one
    milestone later. A repair that reads correctly and raises when run must not be adopted.
    """

    assert executed.step_a.executed > 0 and executed.step_a.confirmed > 0
    assert executed.step_b.executed > 0 and executed.step_b.confirmed > 0
    assert executed.step_b.confirmed <= executed.step_b.survivors


def test_the_nested_requirement_records_what_the_call_sites_wrote(tmp_path: Path) -> None:
    """Not merely that something was nested — which inner keys, bound to which fields.

    With an empty wrapper the probe expected the inner *object* where the call site had
    written a *mapping*, and refused every correct candidate. The chain still reported an
    enabling relation, because the structural predicate alone was deciding.
    """

    from metamorphosis.m094_diagnosis import decode_rendering
    from metamorphosis.m095_reach import decode_nested

    build(tmp_path)
    target = next(i for i in measure(tmp_path).unmet if i.capability == NESTED)
    (key, field, wrapper), = decode_rendering(target.detail)
    assert (key, field) == ("reading", "reading")
    assert decode_nested(wrapper) == (("reading_id", "reading_id"), ("unit", "unit"))


def test_a_nested_case_is_built_as_an_object_not_a_string(tmp_path: Path) -> None:
    """A field annotated as a value object must be constructed, not filled with text.

    Filled with text, every method reaching into it raises, every candidate is refused, and
    the entry reads as a refutation of the mechanism rather than of the generator.
    """

    from metamorphosis.m094_execution import NESTED_MARKER, constructible_cases
    from metamorphosis.m094_diagnosis import decode_rendering

    build(tmp_path)
    target = next(i for i in measure(tmp_path).unmet if i.capability == NESTED)
    cases = constructible_cases(
        tmp_path, COMPONENT, "Sample", decode_rendering(target.detail),
    )
    assert cases
    for case in cases:
        assert isinstance(case["reading"], dict)
        assert case["reading"][NESTED_MARKER] == "Reading"


def test_the_capability_tie_is_real_and_no_longer_decides_anything(
    executed: Chain,
) -> None:
    """A4's rule, at the capability level.

    At S1 two capabilities on `Sample` tie at demand 2, and the ordering between them is still
    alphabetical on the capability name — `render_nested_…` sorts before `render_value_…`. That
    used to decide which one was repaired, so had the tie fallen the other way the lineage
    would have repaired the plain renderer and no enabling would have been demonstrated.

    The tie is unchanged and the ordering is unchanged. What changed is that both are repaired,
    so nothing rests on which name sorts first. The first half of this test keeps the tie
    honest; the second keeps the remedy honest.
    """

    import tempfile

    root = Path(tempfile.mkdtemp(prefix="m095-tie-"))
    build(root)
    chain.adopt(root, chain.search(root, measure(root).unmet[0], label="A"))
    unmet = measure(root).unmet

    assert len(unmet) >= 2
    assert unmet[0].demand == unmet[1].demand, "the tie this test exists for has gone"
    assert [i.capability for i in unmet[:2]] == sorted(i.capability for i in unmet[:2])

    # And every one of them is repaired, so the ordering decides nothing.
    assert len(executed.second_step) == 2
    assert executed.every_tied_capability_repaired is True


def test_two_repairs_on_one_class_do_not_collide_on_a_name(executed: Chain) -> None:
    """The obstacle that made A4's remedy hard here.

    Both repairs land on `Sample`, and the method-name candidates are a short shared list. A
    second method of the same name shadows the first, which would silently undo the earlier
    repair. A name the class already defines is therefore not available.
    """

    names = [
        item.adopted_method.split("(")[0].removeprefix("def ").strip()
        for item in executed.second_step
    ]
    assert len(names) == len(set(names)), f"two repairs share a name: {names}"


def test_nothing_is_left_unmet_after_the_chain(executed: Chain, tmp_path: Path) -> None:
    """The strongest statement available: the lineage repaired everything it measured.

    Re-run rather than trusted, because a chain that stopped early and a chain that finished
    look the same from the outside.
    """

    import tempfile

    root = Path(tempfile.mkdtemp(prefix="m095-done-"))
    counterfactual = Path(tempfile.mkdtemp(prefix="m095-done-cf-"))
    chain.run(root, counterfactual)
    assert [i.target for i in measure(root).unmet] == []
