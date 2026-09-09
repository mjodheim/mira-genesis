"""One-shot branch repair for Genesis causal-novelty metrology.

This file is intentionally deleted by the branch workflow after the focused suite passes.
It modifies DEVELOPMENT apparatus only; it never edits frozen experimental sources or results.
"""
from __future__ import annotations

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if text.count(old) != 1:
        raise SystemExit(f"{label} anchor changed")
    return text.replace(old, new, 1)


def repair_loop() -> None:
    path = ROOT / "genesis" / "loop.py"
    text = path.read_text(encoding="utf-8")

    text = replace_once(
        text,
        "same budget and requires a loss of reach. `causal_chain` then counts the consecutive acquisitions\n"
        "whose dependency was actually established, so a claim about recursive improvement reads a number that\n"
        "can be small.",
        "same budget and requires a loss in work the current generation newly solved over its parent.\n"
        "Losing only retained work is not evidence that the new work needed the earlier acquisition.\n"
        "`causal_chain` then counts the consecutive acquisitions whose dependency was actually established, so a\n"
        "claim about recursive improvement reads a number that can be small.",
        "loop docstring",
    )

    call = re.compile(
        r'(?m)^(?P<i>\s*)with_acquisition=candidate\["outcomes"\],\n'
        r'(?P=i)without_acquisition=run\["outcomes"\],'
    )
    text, count = call.subn(
        lambda match: (
            f'{match.group("i")}parent_outcomes=parent["outcomes"],\n'
            f'{match.group("i")}with_acquisition=candidate["outcomes"],\n'
            f'{match.group("i")}without_acquisition=run["outcomes"],'
        ),
        text,
        count=1,
    )
    if count != 1:
        raise SystemExit("causal call anchor changed")

    needle = '                "solved_without_acquisition": outcome["solved_without_acquisition"],\n'
    text = replace_once(
        text,
        needle,
        needle
        + '                "newly_solved_with_acquisition": outcome["newly_solved_with_acquisition"],\n'
        + '                "newly_solved_lost_without_acquisition": outcome[\n'
        + '                    "newly_solved_lost_without_acquisition"\n'
        + '                ],\n'
        + '                "retained_solved_lost_without_acquisition": outcome[\n'
        + '                    "retained_solved_lost_without_acquisition"\n'
        + '                ],\n',
        "causal record",
    )

    marker = (
        "# ---------------------------------------------------------------------------------------------\n"
        "# Causal dependency between generations\n"
        "# ---------------------------------------------------------------------------------------------\n"
        "def ablation_supports_causal_dependency("
    )
    position = text.find(marker)
    if position < 0 or text.find(marker, position + 1) >= 0:
        raise SystemExit("causal function marker changed")
    prefix = text[:position]
    replacement = '''# ---------------------------------------------------------------------------------------------
# Causal dependency between generations
# ---------------------------------------------------------------------------------------------
def ablation_supports_causal_dependency(
    *,
    parent_outcomes: Sequence[Mapping[str, Any]],
    with_acquisition: Sequence[Mapping[str, Any]],
    without_acquisition: Sequence[Mapping[str, Any]],
    equal_budget: bool,
) -> dict[str, Any]:
    """Test whether the *new work* of a later generation needed an earlier acquisition.

    A raw loss in total solved tasks is insufficient. The earlier acquisition is retained work, so
    ablating it can trivially break tasks the parent already solved while leaving every task newly
    solved by the later generation intact. That demonstrates retention dependence, not causal
    dependence of the new improvement.

    The comparison identifies the tasks the candidate newly solves relative to its parent and
    requires the equal-budget ablation to lose at least one of those tasks. Losses confined to work
    the parent already solved are recorded separately and establish nothing about this generation's
    novelty.
    """
    if not equal_budget:
        return {
            "supported": False,
            "reason": "the ablated arm did not run at the same budget, so the comparison is void",
        }

    def by_task(rows: Sequence[Mapping[str, Any]], label: str) -> dict[str, str]:
        mapped: dict[str, str] = {}
        for row in rows:
            task_id = row.get("task_id")
            if not isinstance(task_id, str) or not task_id:
                raise TrustRootError("%s causal outcome carries no task id" % label)
            if task_id in mapped:
                raise TrustRootError("%s causal outcome repeats task %r" % (label, task_id))
            mapped[task_id] = str(row.get("outcome") or "")
        return mapped

    parent = by_task(parent_outcomes, "parent")
    intact = by_task(with_acquisition, "candidate")
    ablated = by_task(without_acquisition, "ablated candidate")
    if set(parent) != set(intact) or set(parent) != set(ablated):
        raise TrustRootError("causal parent, candidate and ablation did not face the same tasks")

    parent_solved = {task for task, outcome in parent.items() if outcome == "solved"}
    intact_solved = {task for task, outcome in intact.items() if outcome == "solved"}
    ablated_solved = {task for task, outcome in ablated.items() if outcome == "solved"}

    newly_solved = intact_solved - parent_solved
    lost_newly_solved = newly_solved - ablated_solved
    retained_solved = parent_solved & intact_solved
    lost_retained_solved = retained_solved - ablated_solved
    all_lost = intact_solved - ablated_solved

    supported = bool(lost_newly_solved)
    if supported:
        reason = ""
    elif not newly_solved:
        reason = (
            "the later generation solved no task its parent did not already solve, so there is no "
            "new work whose dependency could be established"
        )
    elif all_lost:
        reason = (
            "removing the earlier acquisition only broke retained work; every task newly solved by "
            "the later generation remained solved"
        )
    else:
        reason = (
            "removing the earlier acquisition cost nothing on the later generation's newly solved "
            "work, so the new improvement did not need it"
        )

    return {
        "supported": supported,
        "solved_with_acquisition": len(intact_solved),
        "solved_without_acquisition": len(ablated_solved),
        "newly_solved_with_acquisition": sorted(newly_solved),
        "newly_solved_lost_without_acquisition": sorted(lost_newly_solved),
        "retained_solved_lost_without_acquisition": sorted(lost_retained_solved),
        "reason": reason,
        "equal_budget": True,
    }
'''
    path.write_text(prefix + replacement, encoding="utf-8")


def repair_development_fixtures() -> None:
    path = ROOT / "genesis" / "development_bodies.py"
    text = path.read_text(encoding="utf-8")

    text = replace_once(
        text,
        '''        required = self.routed.get(key)
        if required is not None:
            if required not in self.capabilities:
                raise RuntimeError("this body reaches for %r, which it no longer has" % required)
            return answer_to(task)
''',
        '''        required = self.routed.get(key)
        if required is not None:
            requirements = (required,) if isinstance(required, str) else tuple(required)
            missing = [name for name in requirements if name not in self.capabilities]
            if missing:
                raise RuntimeError("this body reaches for %r, which it no longer has" % missing[0])
            return answer_to(task)
''',
        "RecordBody routing",
    )

    text = replace_once(
        text,
        '''# Each later generation *routes* its earlier gains through the components that produced them, so an
# ablation removes something rather than merely relabelling the verdict.
''',
        '''# Each later generation keeps its earlier routed gains, and its *new* task requires both the
# immediately preceding acquisition and the acquisition introduced in the current generation. This
# matters: losing only an old routed task after ablation is retention dependence, not evidence that
# the current generation's new work needed its predecessor.
''',
        "fixture chain explanation",
    )

    text = replace_once(
        text,
        '#: generation 2 adds t4 through its own acquisition.\nROUTED_AFTER_MIGRATION = {**ROUTED_TASKS, "t4": SECOND_ACQUISITION}\n',
        '#: generation 2 adds t4 through its own acquisition and the predecessor it claims to need.\n'
        'ROUTED_AFTER_MIGRATION = {\n'
        '    **ROUTED_TASKS, "t4": (ACQUIRED_COMPONENT, SECOND_ACQUISITION)\n'
        '}\n',
        "generation 2 routing",
    )
    text = replace_once(
        text,
        '#: generation 3 adds t5 through its own acquisition, and keeps needing generation 2\'s.\n'
        'ROUTED_THIRD_GENERATION = {**ROUTED_AFTER_MIGRATION, "t5": THIRD_ACQUISITION}\n',
        '#: generation 3 adds t5 through its own acquisition and generation 2\'s acquisition.\n'
        'ROUTED_THIRD_GENERATION = {\n'
        '    **ROUTED_AFTER_MIGRATION, "t5": (SECOND_ACQUISITION, THIRD_ACQUISITION)\n'
        '}\n',
        "generation 3 routing",
    )
    text = replace_once(
        text,
        '''#: generation 4 adds t6 and t7 through its own, and still needs everything before it.
ROUTED_FOURTH_GENERATION = {
    **ROUTED_THIRD_GENERATION,
    "t6": FOURTH_ACQUISITION,
    "t7": FOURTH_ACQUISITION,
}
''',
        '''#: generation 4 adds t6 and t7 through its own acquisition and generation 3's acquisition.
ROUTED_FOURTH_GENERATION = {
    **ROUTED_THIRD_GENERATION,
    "t6": (THIRD_ACQUISITION, FOURTH_ACQUISITION),
    "t7": (THIRD_ACQUISITION, FOURTH_ACQUISITION),
}
''',
        "generation 4 routing",
    )
    path.write_text(text, encoding="utf-8")


def repair_tests() -> None:
    path = ROOT / "tests" / "test_genesis_loop.py"
    tests = path.read_text(encoding="utf-8")
    start_marker = "def test_removing_an_earlier_acquisition_must_cost_something():"
    end_marker = "\n\n# -- causal dependency as a property"
    if tests.count(start_marker) != 1:
        raise SystemExit("direct causal test start anchor changed")
    start = tests.index(start_marker)
    end = tests.index(end_marker, start)
    new_tests = '''def test_removing_an_earlier_acquisition_must_cost_new_work():
    parent = [
        {"task_id": "t0", "outcome": "solved"},
        {"task_id": "t1", "outcome": "solved"},
        {"task_id": "t2", "outcome": "unsolved"},
        {"task_id": "t3", "outcome": "unsolved"},
    ]
    candidate = [{"task_id": "t%d" % i, "outcome": "solved"} for i in range(4)]
    ablated = [
        {"task_id": "t0", "outcome": "solved"},
        {"task_id": "t1", "outcome": "solved"},
        {"task_id": "t2", "outcome": "unsolved"},
        {"task_id": "t3", "outcome": "unsolved"},
    ]
    outcome = ablation_supports_causal_dependency(
        parent_outcomes=parent,
        with_acquisition=candidate,
        without_acquisition=ablated,
        equal_budget=True,
    )
    assert outcome["supported"] is True
    assert outcome["newly_solved_with_acquisition"] == ["t2", "t3"]
    assert outcome["newly_solved_lost_without_acquisition"] == ["t2", "t3"]
    assert outcome["retained_solved_lost_without_acquisition"] == []


def test_breaking_only_retained_work_does_not_establish_causal_dependency():
    """Regression: total solved may collapse while the generation's novelty survives intact."""
    parent = [
        {"task_id": "old0", "outcome": "solved"},
        {"task_id": "old1", "outcome": "solved"},
        {"task_id": "new", "outcome": "unsolved"},
    ]
    candidate = [
        {"task_id": "old0", "outcome": "solved"},
        {"task_id": "old1", "outcome": "solved"},
        {"task_id": "new", "outcome": "solved"},
    ]
    ablated = [
        {"task_id": "old0", "outcome": "unsolved"},
        {"task_id": "old1", "outcome": "unsolved"},
        {"task_id": "new", "outcome": "solved"},
    ]
    outcome = ablation_supports_causal_dependency(
        parent_outcomes=parent,
        with_acquisition=candidate,
        without_acquisition=ablated,
        equal_budget=True,
    )
    assert outcome["solved_with_acquisition"] == 3
    assert outcome["solved_without_acquisition"] == 1
    assert outcome["supported"] is False
    assert outcome["newly_solved_with_acquisition"] == ["new"]
    assert outcome["newly_solved_lost_without_acquisition"] == []
    assert outcome["retained_solved_lost_without_acquisition"] == ["old0", "old1"]
    assert "only broke retained work" in outcome["reason"]


def test_an_ablation_that_costs_nothing_refutes_the_causal_claim():
    parent = [
        {"task_id": "t0", "outcome": "solved"},
        {"task_id": "t1", "outcome": "solved"},
        {"task_id": "t2", "outcome": "unsolved"},
        {"task_id": "t3", "outcome": "unsolved"},
    ]
    rows = [{"task_id": "t%d" % i, "outcome": "solved"} for i in range(4)]
    outcome = ablation_supports_causal_dependency(
        parent_outcomes=parent,
        with_acquisition=rows,
        without_acquisition=list(rows),
        equal_budget=True,
    )
    assert outcome["supported"] is False
    assert "cost nothing" in outcome["reason"]


def test_an_unequal_budget_voids_the_comparison_rather_than_passing_it():
    outcome = ablation_supports_causal_dependency(
        parent_outcomes=[{"task_id": "t0", "outcome": "unsolved"}],
        with_acquisition=[{"task_id": "t0", "outcome": "solved"}],
        without_acquisition=[{"task_id": "t0", "outcome": "unsolved"}],
        equal_budget=False,
    )
    assert outcome["supported"] is False
    assert "same budget" in outcome["reason"]


def test_causal_ablation_refuses_different_task_sets():
    with pytest.raises(tr.TrustRootError, match="same tasks"):
        ablation_supports_causal_dependency(
            parent_outcomes=[{"task_id": "parent", "outcome": "unsolved"}],
            with_acquisition=[{"task_id": "candidate", "outcome": "solved"}],
            without_acquisition=[{"task_id": "candidate", "outcome": "unsolved"}],
            equal_budget=True,
        )
'''
    tests = tests[:start] + new_tests + tests[end:]
    tests = replace_once(
        tests,
        '    assert causal["established"] is True\n    assert causal["depends_on"] == bodies.ACQUIRED_COMPONENT\n',
        '    assert causal["established"] is True\n'
        '    assert causal["newly_solved_lost_without_acquisition"] == ["t4"]\n'
        '    assert causal["depends_on"] == bodies.ACQUIRED_COMPONENT\n',
        "positive cycle causal assertion",
    )
    path.write_text(tests, encoding="utf-8")


def write_audit() -> None:
    path = ROOT / "docs" / "audits" / "GENESIS_CAUSAL_NOVELTY_REPAIR_2026-09-09.md"
    path.write_text(
        '''# Genesis causal novelty repair — DEVELOPMENT apparatus

**Prepared:** 9 September 2026  
**Status:** runtime metrology repair; no scientific observation; no gate movement.

## Defect

The runtime called a later acquisition causally dependent on an earlier one whenever removing the
earlier acquisition reduced the **total** number of solved tasks. Because retention is required, that
criterion could be satisfied merely by breaking work the parent already solved while leaving every
task newly solved by the current generation intact.

That is retention dependence, not evidence that the new improvement needed the earlier acquisition.

## Repair

For every accepted candidate the causal comparison now receives the parent outcomes as a third arm.
It identifies `candidate_solved - parent_solved` and establishes dependency only when the runtime-
derived, equal-budget ablation loses at least one member of that newly solved set. Losses confined to
retained parent work are recorded separately and do not establish a causal link. All three arms must
carry exactly the same task identifiers or the measurement fails closed.

## Fixture finding

The stronger criterion exposed two false-positive DEVELOPMENT fixtures. Their new tasks were routed
only through the current acquisition; removing the claimed predecessor broke older retained tasks but
left the newly gained task intact. The fixture chain now requires each newly introduced routed task to
use both the immediately preceding acquisition and the acquisition introduced in its own generation.
This makes the synthetic positive control test the property it claims rather than merely total loss.

A separate counterexample keeps the old false-positive shape permanently: candidate total solved falls
from 3 to 1 after ablation while its only newly solved task remains solved. The repaired criterion must
report no causal dependency and record the two losses as retained work.

## M108 revalidation

The real M108 bridge is re-run under the stronger rule. Its causal link is accepted only if the M108
tasks newly solved over the M107 parent are themselves lost when M107 is removed.

## Boundary

No M107–M125 frozen source, protocol, result, sealed bank, reveal state or scientific decision is
modified. This changes only the integrated Genesis DEVELOPMENT measurement and its synthetic fixtures.
''',
        encoding="utf-8",
    )


if __name__ == "__main__":
    repair_loop()
    repair_development_fixtures()
    repair_tests()
    write_audit()
