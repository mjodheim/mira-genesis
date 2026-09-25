from __future__ import annotations
import importlib.util
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
P=ROOT/"experiment"/"rsi_l6_l8"/"selector_search.py"
spec=importlib.util.spec_from_file_location("rsi_l8_selector_search_test",P)
assert spec is not None and spec.loader is not None
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

def episode(needs,outcomes):
    return {
        "snapshot":{
            "schema":m.SELECTOR.SNAPSHOT_SCHEMA,
            "components":[
                {"id":"exploration","metrics":{"need":needs[0],"cost":5}},
                {"id":"memory","metrics":{"need":needs[1],"cost":5}},
                {"id":"verification","metrics":{"need":needs[2],"cost":5}},
            ],
        },
        "matched_intervention_utilities":{
            "exploration":[1,outcomes[0]],
            "memory":[1,outcomes[1]],
            "verification":[1,outcomes[2]],
        },
    }

def test_search_discovers_need_metric_without_component_identity():
    episodes=[
        episode((9,2,1),(90,20,10)),
        episode((1,8,2),(10,80,20)),
        episode((2,1,7),(20,10,70)),
    ]
    r=m.search(episodes)
    assert r["development_only"] is True
    assert r["holdout_consumed"] is False
    assert r["selected_program"]["expression"]=={"metric":"need"}
    assert [x["selected_component"] for x in r["selected_choices"]]==[
        "exploration","memory","verification"
    ]

def test_search_refuses_missing_counterfactual_outcome():
    episodes=[episode((9,2,1),(90,20,10))]
    del episodes[0]["matched_intervention_utilities"]["verification"]
    try:
        m.search(episodes)
    except ValueError as e:
        assert "matched outcomes" in str(e)
    else:
        raise AssertionError("search fabricated a missing intervention outcome")

def test_candidate_programs_never_contain_component_ids():
    programs=m.candidate_programs(["need","cost"])
    rendered=str(programs)
    assert "exploration" not in rendered
    assert "memory" not in rendered
    assert "verification" not in rendered

def test_search_is_deterministic():
    episodes=[
        episode((9,2,1),(90,20,10)),
        episode((1,8,2),(10,80,20)),
    ]
    assert m.search(episodes)==m.search(episodes)
