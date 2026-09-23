from __future__ import annotations
import sys
from pathlib import Path

V22=Path(__file__).resolve().parents[1]/"experiment"/"rsi_v22"
sys.path.insert(0,str(V22))
import campaign  # noqa: E402

def state():
    return campaign.init_state(task_id="demo",allowed_source_path="src/Demo.java",
        root_tree_digest="a"*64,root_source_sha256="b"*64)

def result(parent,tree,quality):
    return {"parent_node_id":parent,"tree_digest":tree*64,"source_sha256":tree.upper()*64,
        "proposal_patch_sha256":("c" if tree!="c" else "d")*64,"quality_milli":quality}

def test_initial_shared_root():
    s=state(); root=s["root_node_id"]
    assert campaign.plan_next(s,"g1")["selected_parent_ids"]==[root]
    assert campaign.plan_next(s,"g2")["selected_parent_ids"]==[root]

def test_1000_r1_makes_g2_stop_and_g1_choose_child_then_root():
    s=state(); root=s["root_node_id"]
    campaign.record_round(s,arm="shared",parent_results=[result(root,"c",1000)])
    child=[x for x in s["nodes"] if x!=root][0]
    assert s["arms"]["g2"]["stopped"] is True
    assert s["arms"]["g2"]["stop_reason"]=="policy_empty_batch"
    assert campaign.plan_next(s,"g1")["selected_parent_ids"]==[child,root]

def test_g1_stops_after_nonimproving_r2_at_ceiling():
    s=state(); root=s["root_node_id"]
    campaign.record_round(s,arm="shared",parent_results=[result(root,"c",1000)])
    child=[x for x in s["nodes"] if x!=root][0]
    campaign.record_round(s,arm="g1",parent_results=[result(child,"d",1000),result(root,"e",1000)])
    assert s["arms"]["g1"]["stopped"] is True
    assert s["arms"]["g1"]["stop_reason"]=="stall_rounds"
    assert s["arms"]["g1"]["represented_requests"]==3
    assert s["arms"]["g2"]["represented_requests"]==1

def test_failed_r1_stops_g1_but_g2_follows_low_quality_child():
    s=state(); root=s["root_node_id"]
    campaign.record_round(s,arm="shared",parent_results=[result(root,"c",0)])
    child=[x for x in s["nodes"] if x!=root][0]
    assert s["arms"]["g1"]["stopped"] is True
    assert s["arms"]["g1"]["stop_reason"]=="stall_rounds"
    assert campaign.plan_next(s,"g2")["selected_parent_ids"]==[child]

def test_adapter_is_semantics_free_and_stable():
    s=state(); root=s["nodes"][s["root_node_id"]]
    assert root["action"]=={"family":"defect-root","target_axes":["demo"],"mechanisms":["seed-defect"],"changed_regions":["src/Demo.java"]}
    n=campaign.proposal_node(state=s,parent_node_id=root["node_id"],tree_digest="c"*64,
        source_sha256="d"*64,proposal_patch_sha256="e"*64,quality_milli=1000)
    assert n["action"]=={"family":"external-code-repair","target_axes":["demo"],"mechanisms":["source-patch"],"changed_regions":["src/Demo.java"]}
