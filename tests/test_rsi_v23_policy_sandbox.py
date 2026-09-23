from __future__ import annotations
import importlib.util
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
P=ROOT/"experiment"/"rsi_v23"/"sandbox_policy.py"
spec=importlib.util.spec_from_file_location("v23_sandbox_test",P)
assert spec is not None and spec.loader is not None
s=importlib.util.module_from_spec(spec); spec.loader.exec_module(s)

VIEW={"root_node_id":"root","revealed_nodes":[],"eligible_parent_ids":["root"]}

def write(tmp_path:Path,text:str)->Path:
    p=tmp_path/"candidate.py"; p.write_text(text); return p

GOOD='''def policy_metadata(): return (1,1,1,1,1,1,1,1,3,1)
def select_parent_batch(view,max_parallelism): return [view["root_node_id"]]
'''

def test_good_policy_runs_out_of_process(tmp_path):
    r=s.execute(write(tmp_path,GOOD),VIEW,1,[])
    assert r["accepted"] is True
    assert r["selected_parent_ids"]==["root"]

def test_guarded_io_never_reaches_worker(tmp_path):
    r=s.execute(write(tmp_path,GOOD+"\ndef x(): return open('secret')\n"),VIEW,1,[])
    assert r["accepted"] is False
    assert r["phase"]=="static_guard"

def test_infinite_policy_times_out(tmp_path):
    src='''def policy_metadata(): return (1,1,1,1,1,1,1,1,3,1)
def select_parent_batch(view,max_parallelism):
    while True:
        pass
'''
    r=s.execute(write(tmp_path,src),VIEW,1,[],0.25)
    assert r["accepted"] is False
    assert r["error"]=="timeout"

def test_parallelism_violation_is_rejected(tmp_path):
    src='''def policy_metadata(): return (1,1,1,1,1,1,1,2,3,1)
def select_parent_batch(view,max_parallelism): return ["a","b"]
'''
    r=s.execute(write(tmp_path,src),VIEW,1,[])
    assert r["accepted"] is False
    assert r["error"]=="parallelism_exceeded"
