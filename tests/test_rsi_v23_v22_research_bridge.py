from __future__ import annotations
import importlib.util
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
P=ROOT/"experiment"/"rsi_v23"/"v22_research_bridge.py"
spec=importlib.util.spec_from_file_location("v23_v22_bridge_test",P)
assert spec is not None and spec.loader is not None
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


def adjudication(*, win=True):
    rows=[]
    for i in range(3):
        rows.append({
            "task_id":f"task-{i}",
            "g1_process_utility":[1000,-3,-2],
            "g2_process_utility":[1000,-1,-1],
            "g2_strictly_better":win,
            "g1_best_quality_milli":1000,
            "g2_best_quality_milli":1000,
            "g1_requests":3,
            "g2_requests":1,
            "g1_rounds":2,
            "g2_rounds":1,
        })
    return {
        "schema":"mira-genesis-rsi-v22-final-adjudication-v1",
        "tasks":rows,
        "g1_global_utility":[3,3000,-9,-6],
        "g2_global_utility":[3,3000,-3,-3],
        "g2_tasks_solved_without_regression":3,
        "g2_strict_process_wins":3 if win else 0,
        "v22_positive":win,
    }


def test_mapping_is_fixed_and_uses_only_adjudication_aggregates():
    result=m.bridge(adjudication())
    assert result["family"]=="real-project-search-policy-transfer"
    assert len(result["events"])==3
    first=result["events"][0]
    assert first["mechanisms"]==["parent_selection","continuation_and_stopping"]
    assert first["changed_regions"]==["search_policy"]
    assert first["capability_deltas"]=={
        "repair_best_quality":0,
        "represented_request_efficiency":2,
        "round_efficiency":1,
    }
    assert first["improvements"]==["g2_strict_process_utility_win"]
    assert first["regressions"]==[]
    assert first["parent_digest"]==m.G1_POLICY_SHA256
    assert first["child_digest"]==m.G2_POLICY_SHA256


def test_mapping_does_not_turn_lower_quality_into_a_promotion_only():
    a=adjudication()
    a["tasks"][0]["g2_best_quality_milli"]=0
    a["tasks"][0]["g2_strictly_better"]=False
    result=m.bridge(a)
    row=next(x for x in result["events"] if x["task_id"]=="task-0")
    assert row["hard_pass"] is False
    assert row["capability_deltas"]["repair_best_quality"]==-1000
    assert "g2_lower_best_quality" in row["regressions"]


def test_event_identity_is_invariant_to_input_task_order():
    a=adjudication()
    b={**a,"tasks":list(reversed(a["tasks"]))}
    left=m.bridge(a)["events"]
    right=m.bridge(b)["events"]
    assert left==right


def test_extra_adjudication_text_does_not_change_event_semantics():
    a=adjudication()
    b={**a,"commentary":"post hoc narrative must not classify the events"}
    assert m.bridge(a)["events"]==m.bridge(b)["events"]
