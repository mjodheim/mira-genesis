from __future__ import annotations
import importlib.util
import json
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
