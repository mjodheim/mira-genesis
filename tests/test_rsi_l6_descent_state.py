from __future__ import annotations
import importlib.util
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
P=ROOT/"experiment"/"rsi_l6_l8"/"descent_state.py"
spec=importlib.util.spec_from_file_location("rsi_l6_descent_state_test",P)
assert spec is not None and spec.loader is not None
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

def h(ch): return ch*64

def transition(a,b,sa,sb,good=True):
    return {
        "from_generation":a,"to_generation":b,
        "producer_generation":a,"produced_generation":b,
        "from_generation_sha256":sa,"to_generation_sha256":sb,
        "evaluator_commitment_sha256":h("c"),
        "holdout_commitment_sha256":h("d"),
        "mechanism_commitment_sha256":h("e"),
        "selection_record_sha256":h("f"),
        "successor_selected_without_human_ranking":True,
        "candidate_frozen_before_fresh_holdout":True,
        "evaluator_frozen_before_candidate":True,
        "negative_evidence_retained":True,
        "acquired_mechanism_id":a+"-mechanism",
        "budgets":{"predecessor":10,"successor":10,"ablation":10},
        "predecessor_holdout_utility":[1,100],
        "successor_holdout_utility":[1,110] if good else [1,90],
        "ablated_holdout_utility":[1,80],
    }

def test_positive_chain_advances_without_human_generation_choice():
    s=m.init_state(generation_id="G2",generation_sha256=h("a"),protocol_commitment_sha256=h("b"))
    m.record_transition(s,transition("G2","G3",h("a"),h("3")))
    assert m.next_request(s)["from_generation"]=="G3"
    m.record_transition(s,transition("G3","G4",h("3"),h("4")))
    m.record_transition(s,transition("G4","G5",h("4"),h("5")))
    assert m.readiness(s,3)["chain_complete"] is True

def test_negative_transition_is_retained_and_stops_descent():
    s=m.init_state(generation_id="G2",generation_sha256=h("a"),protocol_commitment_sha256=h("b"))
    m.record_transition(s,transition("G2","G3",h("a"),h("3"),good=False))
    assert len(s["transitions"])==1
    assert s["transitions"][0]["causal_transition_positive"] is False
    assert s["stopped"] is True
    assert m.next_request(s)["can_open_next_transition"] is False

def test_cannot_skip_current_parent_generation():
    s=m.init_state(generation_id="G2",generation_sha256=h("a"),protocol_commitment_sha256=h("b"))
    try:
        m.record_transition(s,transition("G3","G4",h("3"),h("4")))
    except ValueError as e:
        assert "current generation" in str(e)
    else:
        raise AssertionError("generation skip was accepted")

def test_parent_digest_is_binding():
    s=m.init_state(generation_id="G2",generation_sha256=h("a"),protocol_commitment_sha256=h("b"))
    try:
        m.record_transition(s,transition("G2","G3",h("9"),h("3")))
    except ValueError as e:
        assert "parent digest" in str(e)
    else:
        raise AssertionError("wrong parent digest was accepted")
