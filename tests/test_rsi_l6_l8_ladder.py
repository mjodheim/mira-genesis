from __future__ import annotations
import importlib.util
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
P=ROOT/"experiment"/"rsi_l6_l8"/"ladder.py"
spec=importlib.util.spec_from_file_location("rsi_l6_l8_ladder_test",P)
assert spec is not None and spec.loader is not None
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

CONFIG={
    "l6_min_causal_transitions":3,
    "l7_min_domain_families":4,
    "l7_min_independently_maintained_domains":1,
    "l8_min_bottleneck_episodes":4,
    "l8_min_distinct_selected_components":2,
}

def transition(a,b):
    return {
        "from_generation":a,"to_generation":b,
        "producer_generation":a,"produced_generation":b,
        "successor_selected_without_human_ranking":True,
        "candidate_frozen_before_fresh_holdout":True,
        "evaluator_frozen_before_candidate":True,
        "equal_budget":True,
        "negative_evidence_retained":True,
        "acquired_mechanism_id":f"{a}-mechanism",
        "predecessor_holdout_utility":[1,100],
        "successor_holdout_utility":[1,110],
        "ablated_holdout_utility":[1,90],
    }

def domain(i,independent=False):
    return {
        "domain_id":f"d{i}","domain_family":f"family-{i}","environment_id":f"env-{i}",
        "independently_maintained":independent,
        "candidate_frozen_before_holdout":True,
        "evaluator_frozen_before_candidate":True,
        "no_domain_specific_candidate_guidance":True,
        "equal_budget":True,
        "negative_evidence_retained":True,
        "predecessor_utility":[1,100],
        "successor_utility":[1,101],
    }

def episode(chosen,a,b,c):
    return {
        "available_components":["exploration","memory","verification"],
        "selected_component":chosen,
        "snapshot_frozen_before_selection":True,
        "selection_frozen_before_intervention":True,
        "equal_budget_per_component":True,
        "matched_intervention_utilities":{
            "exploration":[1,a],
            "memory":[1,b],
            "verification":[1,c],
        },
    }

def full_evidence():
    return {
        "schema":m.SCHEMA,
        "transitions":[transition("G2","G3"),transition("G3","G4"),transition("G4","G5")],
        "domain_transfer":[domain(1,True),domain(2),domain(3),domain(4)],
        "bottleneck_selection":{
            "selector_frozen_before_holdout":True,
            "selection_rule_not_human_overridden":True,
            "negative_evidence_retained":True,
            "episodes":[
                episode("exploration",30,10,5),
                episode("memory",10,35,8),
                episode("verification",10,12,40),
                episode("memory",9,30,10),
            ],
        },
    }

def test_full_fixture_reaches_l8():
    r=m.assess(full_evidence(),CONFIG)
    assert r["L6"]["positive"] is True
    assert r["L7"]["positive"] is True
    assert r["L8"]["positive"] is True
    assert r["L8"]["distinct_selected_components"] == 3

def test_l6_requires_causal_ablation():
    e=full_evidence()
    e["transitions"][1]["ablated_holdout_utility"]=[1,120]
    r=m.assess(e,CONFIG)
    assert r["L6"]["positive"] is False
    assert r["L7"]["positive"] is False
    assert r["L8"]["positive"] is False

def test_l6_requires_contiguous_chain():
    e=full_evidence()
    e["transitions"][1]["from_generation"]="OTHER"
    assert m.assess(e,CONFIG)["L6"]["positive"] is False

def test_l7_requires_independent_environment():
    e=full_evidence()
    for d in e["domain_transfer"]:
        d["independently_maintained"]=False
    r=m.assess(e,CONFIG)
    assert r["L6"]["positive"] is True
    assert r["L7"]["positive"] is False

def test_l8_rejects_always_fixed_selector_even_if_that_target_is_good():
    e=full_evidence()
    for ep in e["bottleneck_selection"]["episodes"]:
        ep["selected_component"]="memory"
    r=m.assess(e,CONFIG)
    assert r["L8"]["distinct_selected_components"] == 1
    assert r["L8"]["positive"] is False

def test_l8_requires_real_matched_component_controls():
    e=full_evidence()
    del e["bottleneck_selection"]["episodes"][0]["matched_intervention_utilities"]["verification"]
    assert m.assess(e,CONFIG)["L8"]["positive"] is False

def test_l8_requires_adaptive_strategy_to_beat_best_fixed_target():
    e=full_evidence()
    # Make exploration globally dominant but force the selector to choose weaker targets.
    e["bottleneck_selection"]["episodes"]=[
        episode("memory",100,5,4),
        episode("verification",100,4,5),
        episode("memory",100,5,4),
        episode("verification",100,4,5),
    ]
    r=m.assess(e,CONFIG)
    assert r["L8"]["adaptive_strictly_beats_best_fixed_target"] is False
    assert r["L8"]["positive"] is False

def test_thresholds_are_external_not_hardcoded():
    e=full_evidence()
    cfg=dict(CONFIG)
    cfg["l6_min_causal_transitions"]=4
    assert m.assess(e,cfg)["L6"]["positive"] is False
