"""Regressions for M086, the improvement mechanism made mutable.

The load-bearing claims are that M0 is the mechanism M047 actually froze, that its constructive image
for the holdout is empty rather than merely unlucky, that the meta-search is a search and not a
lookup, and that nothing evaluator-side is reachable from the mechanism.
"""
from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from metamorphosis.m047_runtime_sandbox import run_body_in_sandbox
from metamorphosis.m047_search_diagnosis import diagnose_limiting_module
from metamorphosis.m047_search_templates import _candidate_sources
from metamorphosis.m047_software_body import SoftwareCase
from metamorphosis.m086_evolvable_mechanism import (
    ARMS,
    META_PRIMITIVES,
    SCHEMA_MULTI,
    SCHEMA_SINGLE,
    Mechanism,
    MechanismError,
    apply_meta_primitive,
    build_mechanism,
    candidate_meta_transformations,
    diagnose,
    generate,
    m0_mechanism,
)
from metamorphosis.m086_meta_lineage import (
    DEVELOPMENT_PUBLIC,
    HOLDOUT_HIDDEN,
    HOLDOUT_PUBLIC,
    enumerate_m0_image_on_holdout,
    evaluate,
    starting_body,
)

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "experiments/M086"


def _executions(cases):
    return run_body_in_sandbox(starting_body(), cases, timeout_seconds=60.0).cases


# -- M0 is the mechanism M047 froze --------------------------------------------------------------

@pytest.mark.parametrize("cases", [DEVELOPMENT_PUBLIC, HOLDOUT_PUBLIC])
def test_m0_diagnoses_exactly_as_m047_does(cases) -> None:
    executed = _executions(cases)
    old = diagnose_limiting_module(executed)
    new = diagnose(m0_mechanism(), executed)
    assert ((old.module,) if old.module else ()) == new.modules
    assert old.sufficient == new.sufficient


def test_m0_generates_exactly_what_m047_generates() -> None:
    body = starting_body()
    executed = _executions((SoftwareCase("t", "plus 4 5", 9, "t"),))
    old = diagnose_limiting_module(executed)
    new = diagnose(m0_mechanism(), executed)
    old_sets = sorted(tuple(sorted(r.items())) for _, r in _candidate_sources(body, old))
    new_sets = sorted(tuple(sorted(r.items())) for _, r in generate(m0_mechanism(), body, new))
    assert old_sets == new_sets
    assert old_sets, "the probe must actually produce candidates or it proves nothing"


def test_the_frozen_line_this_experiment_attacks_is_still_there() -> None:
    """If M047 ever stops meaning 'exactly one module', M086's premise is gone."""

    source = (ROOT / "metamorphosis/m047_search_diagnostic_model.py").read_text(encoding="utf-8")
    assert "return self.module is not None" in source


# -- the limitation is structural, not budgetary --------------------------------------------------

def test_both_limitations_present_two_stages_at_once() -> None:
    for cases in (DEVELOPMENT_PUBLIC, HOLDOUT_PUBLIC):
        stages = {execution.error_stage for execution in _executions(cases) if not execution.ok}
        assert stages == {"interpretation", "execution"}, stages


def test_m0_can_emit_nothing_at_all_for_the_holdout() -> None:
    image = enumerate_m0_image_on_holdout()
    assert image["diagnosed"] is False
    assert image["candidate_count"] == 0
    assert image["candidate_labels"] == []


def test_widening_the_schema_is_what_unlocks_it() -> None:
    executed = _executions(HOLDOUT_PUBLIC)
    widened = build_mechanism(m0_mechanism(), ("widen_hypothesis",))
    hypothesis = diagnose(widened, executed)
    assert hypothesis.sufficient
    assert set(hypothesis.modules) == {"interpretation", "selection"}
    assert generate(widened, starting_body(), hypothesis)


# -- the meta-search is a search ------------------------------------------------------------------

def test_the_search_space_is_ordered_without_knowing_the_answer() -> None:
    space = candidate_meta_transformations()
    singles = [item for item in space if len(item) == 1]
    pairs = [item for item in space if len(item) == 2]
    assert len(singles) == len(META_PRIMITIVES)
    assert space[:len(singles)] == tuple(singles), "singles must be tried before pairs"
    assert singles == sorted(singles), "the order is alphabetical, not a ranking"
    assert pairs and all(first < second for first, second in pairs)


def test_no_rule_maps_an_evidence_pattern_to_the_primitive_that_works() -> None:
    """The trap: a frozen generator that already says 'when compound, widen'."""

    for module in ("m086_evolvable_mechanism.py", "m086_meta_lineage.py"):
        source = (ROOT / "metamorphosis" / module).read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if not isinstance(node, ast.If):
                continue
            rendered = ast.unparse(node)
            mentions_evidence = any(
                marker in rendered for marker in ("stages", "unknown_tokens", "missing_operations")
            )
            names_a_primitive = any(primitive in rendered for primitive in META_PRIMITIVES)
            assert not (mentions_evidence and names_a_primitive), (
                f"{module} branches from evidence straight to a named meta-primitive"
            )


def test_every_primitive_is_individually_reachable_and_distinct() -> None:
    base = m0_mechanism()
    digests = {base.digest()}
    for primitive in META_PRIMITIVES:
        changed = apply_meta_primitive(base, primitive)
        assert changed.digest() not in digests, f"{primitive} changed nothing"
        assert changed.provenance == (primitive,)
        digests.add(changed.digest())
    with pytest.raises(MechanismError):
        apply_meta_primitive(base, "invent_something")


def test_widening_alone_does_not_compose_and_composing_alone_does_not_widen() -> None:
    base = m0_mechanism()
    assert apply_meta_primitive(base, "widen_hypothesis").schema == SCHEMA_MULTI
    assert apply_meta_primitive(base, "widen_hypothesis").composes is False
    assert apply_meta_primitive(base, "compose_expansions").schema == SCHEMA_SINGLE
    assert apply_meta_primitive(base, "compose_expansions").composes is True


def test_composition_alone_cannot_help_because_nothing_is_diagnosed() -> None:
    """Which is why the search has to run rather than being reasoned about in advance."""

    composed = build_mechanism(m0_mechanism(), ("compose_expansions",))
    hypothesis = diagnose(composed, _executions(HOLDOUT_PUBLIC))
    assert hypothesis.sufficient is False
    assert generate(composed, starting_body(), hypothesis) == ()


# -- the evaluator is not part of the mutable body -------------------------------------------------

def test_the_mechanism_module_cannot_see_the_evaluator_or_the_holdout() -> None:
    source = (ROOT / "metamorphosis/m086_evolvable_mechanism.py").read_text(encoding="utf-8")
    for marker in ("HOLDOUT_HIDDEN", "HOLDOUT_PUBLIC", "solves(", "run_body_in_sandbox"):
        assert marker not in source
    imported = {
        node.module for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.ImportFrom) and node.module
    }
    assert "metamorphosis.m086_meta_lineage" not in imported


def test_no_meta_primitive_can_reach_the_evaluator() -> None:
    """A primitive that could edit the test would make every later result meaningless."""

    mechanism = build_mechanism(m0_mechanism(), tuple(META_PRIMITIVES))
    rendered = json.dumps(mechanism.to_dict())
    for marker in ("holdout", "hidden", "evaluate", "solves"):
        assert marker not in rendered.lower()


def test_hidden_cases_are_disjoint_from_everything_the_mechanism_sees() -> None:
    visible = {case.request for case in DEVELOPMENT_PUBLIC} | {
        case.request for case in HOLDOUT_PUBLIC
    }
    hidden = {case.request for case in HOLDOUT_HIDDEN}
    assert visible.isdisjoint(hidden)


# -- the frozen threshold --------------------------------------------------------------------------

def _preserved() -> dict:
    path = BASE / "RESULT.json"
    if not path.exists():
        pytest.skip("the M086 result has not been preserved yet")
    return json.loads(path.read_text(encoding="utf-8"))


def test_preserved_result_is_single_attempt() -> None:
    preserved = _preserved()
    assert preserved["attempt"] == 1
    assert preserved["retried"] is False
    assert preserved["external_model_called"] is False


def test_preserved_verdict_recomputes() -> None:
    preserved = _preserved()
    verdict = evaluate(preserved["arms"], preserved["m0_constructive_image_on_holdout"])
    assert verdict.positive == (preserved["verdict"] == "positive")
    assert list(verdict.reasons) == preserved["failed_conditions"]


def test_only_the_evolvable_arm_solves_the_holdout() -> None:
    preserved = _preserved()
    assert preserved["arms"]["evolvable_meta"]["holdout_hidden_solved"] is True
    for arm in ("fixed_meta", "meta_acquisition_ablated", "task_only_mutable"):
        assert preserved["arms"][arm]["holdout_hidden_solved"] is False, arm


def test_the_ablated_arm_did_acquire_and_then_lost_it() -> None:
    """Otherwise it would be a second fixed_meta rather than a control on the acquisition."""

    ablated = _preserved()["arms"]["meta_acquisition_ablated"]
    assert ablated["meta_transformations_adopted"] == 1
    assert ablated["development_solved"] is True
    assert ablated["mechanism_at_holdout_digest"] == ablated["mechanism_start_digest"]
    assert ablated["mechanism_after_development_digest"] != ablated["mechanism_start_digest"]


def test_the_search_rejected_alternatives() -> None:
    evolvable = _preserved()["arms"]["evolvable_meta"]
    assert evolvable["rejected_primitives"], "a search that rejects nothing is a lookup"
    assert list(evolvable["adopted_primitives"]) not in [
        list(item) for item in evolvable["rejected_primitives"]
    ]


@pytest.mark.parametrize("arm", ARMS)
def test_every_arm_is_recorded(arm: str) -> None:
    assert arm in _preserved()["arms"]


def test_evaluation_rejects_a_control_that_solves_the_holdout() -> None:
    preserved = _preserved()
    degraded = json.loads(json.dumps(preserved["arms"]))
    degraded["fixed_meta"]["holdout_hidden_solved"] = True
    verdict = evaluate(degraded, preserved["m0_constructive_image_on_holdout"])
    assert verdict.positive is False
    assert any("P3" in reason for reason in verdict.reasons)


def test_evaluation_rejects_a_nonempty_starting_image() -> None:
    preserved = _preserved()
    verdict = evaluate(preserved["arms"], {"candidate_count": 3, "candidate_labels": ["x"]})
    assert verdict.positive is False
    assert any("not structural" in reason for reason in verdict.reasons)


def test_evaluation_rejects_a_patch_the_starting_mechanism_could_have_made() -> None:
    preserved = _preserved()
    label = preserved["arms"]["evolvable_meta"]["holdout_adopted_label"]
    verdict = evaluate(
        preserved["arms"], {"candidate_count": 0, "candidate_labels": [label]},
    )
    assert verdict.positive is False
    assert any("constructive image" in reason for reason in verdict.reasons)


def test_claim_boundary_stays_bounded() -> None:
    protocol = json.loads((BASE / "PROTOCOL.json").read_text(encoding="utf-8"))
    boundary = protocol["claim_boundary"]
    for key in (
        "agi_evidence", "open_ended_evolution", "arbitrary_self_improvement",
        "general_autonomy", "closes_generality_gate_g4", "closes_generality_gate_g6",
        "closes_generality_gate_g7", "advances_any_generality_gate", "replaces_m085",
        "touches_m085_fail_closed_boundary", "is_an_independent_reproduction",
    ):
        assert boundary[key] is False, key


def test_the_amendments_were_recorded_before_materialization() -> None:
    protocol = json.loads((BASE / "PROTOCOL.json").read_text(encoding="utf-8"))
    amendments = protocol["amendments"]
    assert amendments
    for amendment in amendments:
        assert amendment["applied_before_bank_materialization"] is True
    assert any(a.get("thresholds_relaxed") is False for a in amendments)
