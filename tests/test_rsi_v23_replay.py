from __future__ import annotations
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
REPLAY_PATH=ROOT/"experiment"/"rsi_v23"/"replay.py"
spec=importlib.util.spec_from_file_location("v23_replay_test",REPLAY_PATH)
assert spec is not None and spec.loader is not None
replay=importlib.util.module_from_spec(spec)
spec.loader.exec_module(replay)

def write_policy(tmp_path:Path,body:str)->Path:
    p=tmp_path/"policy.py"; p.write_text(body); return p

def state():
    root="root"; c1="c1"; c2="c2"
    def node(n,parent,depth,q):
        return {"node_id":n,"parent_node_id":parent,"lineage_depth":depth,
                "action":{"family":"x","target_axes":[],"mechanisms":[],"changed_regions":[]},
                "outcome":{"quality_milli":q,"evolver_profile_generation":0,"ever_champion":q>0,
                           "root_branch_node_id":n if parent==root else (root if parent is None else c1)}}
    return {"task_id":"demo","root_node_id":root,
            "nodes":{root:node(root,None,0,0),c1:node(c1,root,1,1000),c2:node(c2,root,1,1000)},
            "observations":[
                {"arm":"shared","round":1,"parent_node_ids":[root],"result_node_ids":[c1]},
                {"arm":"g1","round":2,"parent_node_ids":[root],"result_node_ids":[c2]},
            ]}

BASE='''def policy_metadata(): return (1,1,1,1,1,1,1,1,8,2)\n'''

def test_fifo_replays_repeated_root_expansions(tmp_path):
    p=write_policy(tmp_path,BASE+'''
def select_parent_batch(view,max_parallelism):
    return [view["root_node_id"]] if len(view["revealed_nodes"]) < 3 else []
''')
    r=replay.replay_state(state(),p)
    assert r["fully_supported"] is True
    assert r["represented_requests"] == 2
    assert [x["child_node_id"] for x in r["used_expansions"]] == ["c1","c2"]

def test_unseen_counterfactual_is_explicitly_unsupported(tmp_path):
    p=write_policy(tmp_path,BASE+'''
def select_parent_batch(view,max_parallelism):
    if len(view["revealed_nodes"]) == 1: return [view["root_node_id"]]
    return ["c1"]
''')
    r=replay.replay_state(state(),p)
    assert r["fully_supported"] is False
    assert r["stop_reason"] == "unsupported_historical_expansion"
    assert r["unsupported"]["unsupported_parent_ids"] == ["c1"]
    assert r["represented_requests"] == 1

def test_policy_cannot_select_unrevealed_parent(tmp_path):
    p=write_policy(tmp_path,BASE+'''
def select_parent_batch(view,max_parallelism): return ["c1"]
''')
    try:
        replay.replay_state(state(),p)
    except ValueError as e:
        assert "unrevealed" in str(e)
    else:
        raise AssertionError("unrevealed parent selection was accepted")

def test_empty_policy_stops_without_fabricated_cost(tmp_path):
    p=write_policy(tmp_path,BASE+'''
def select_parent_batch(view,max_parallelism): return []
''')
    r=replay.replay_state(state(),p)
    assert r["fully_supported"] is True
    assert r["represented_requests"] == 0
    assert r["best_quality_milli"] == 0
    assert r["stop_reason"] == "policy_empty_batch"

def test_external_request_budget_caps_candidate_metadata(tmp_path):
    p=write_policy(tmp_path,'''def policy_metadata(): return (1,1,1,1,1,1,1,8,99,99)
def select_parent_batch(view,max_parallelism):
    return [view["root_node_id"]] if max_parallelism > 0 else []
''')
    r=replay.replay_state(state(),p,max_requests=1,max_rounds=10,max_parallelism=4)
    assert r["represented_requests"] == 1
    assert r["stop_reason"] == "external_request_budget"
    assert r["effective_limits"] == {"max_requests":1,"max_rounds":10,"max_parallelism":4}

def test_nonpositive_policy_control_metadata_is_rejected(tmp_path):
    p=write_policy(tmp_path,'''def policy_metadata(): return (1,1,1,1,1,1,1,0,8,2)
def select_parent_batch(view,max_parallelism): return []
''')
    try:
        replay.replay_state(state(),p)
    except ValueError as e:
        assert "must be positive" in str(e)
    else:
        raise AssertionError("nonpositive control metadata was accepted")

def test_cli_returns_nonzero_when_exact_replay_is_unsupported(tmp_path):
    policy=write_policy(tmp_path,BASE+'''
def select_parent_batch(view,max_parallelism):
    if len(view["revealed_nodes"]) == 1: return [view["root_node_id"]]
    return ["c1"]
''')
    state_path=tmp_path/"state.json"
    state_path.write_text(json.dumps(state()))
    p=subprocess.run(
        [sys.executable,str(REPLAY_PATH),str(policy),str(state_path)],
        text=True,capture_output=True,
    )
    assert p.returncode == 3
    payload=json.loads(p.stdout)
    assert payload["all_fully_supported"] is False
    assert payload["results"][0]["eligible_for_exact_comparison"] is False
