#!/usr/bin/env python3
"""Run one frozen V23/L5 holdout task under one executable search policy."""
from __future__ import annotations
import argparse, hashlib, importlib.util, json, tempfile
from pathlib import Path

HERE=Path(__file__).resolve().parent
V23=HERE.parent

MAX_REQUESTS=9
MAX_ROUNDS=8
MAX_PARALLELISM=2

def _load(name,path):
 spec=importlib.util.spec_from_file_location(name,path)
 if spec is None or spec.loader is None: raise RuntimeError(f"cannot load {path}")
 m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

gen=_load("l5_holdout_generator",HERE/"candidate_generator.py")
ev=_load("l5_holdout_evaluator",HERE/"evaluate_candidate.py")
sandbox=_load("l5_holdout_sandbox",V23/"sandbox_policy.py")

def _sha(text): return hashlib.sha256(text.encode()).hexdigest()

def _action(task_id,root=False):
 return {
  "family":"defect-root" if root else "external-code-repair",
  "target_axes":[task_id],
  "mechanisms":["seed-defect"] if root else ["source-locus-mutation"],
  "changed_regions":[gen.TASKS[task_id]["path"]],
 }

def _view(nodes,revealed,cursors,task_id):
 eligible=[]
 for node_id in revealed:
  children=gen.children(task_id,nodes[node_id]["source"])
  if cursors.get(node_id,0)<len(children): eligible.append(node_id)
 return {
  "root_node_id":"root",
  "revealed_nodes":[{
    "node_id":nid,
    "lineage_depth":nodes[nid]["lineage_depth"],
    "action":nodes[nid]["action"],
    "outcome":nodes[nid]["outcome"],
   } for nid in revealed],
  "eligible_parent_ids":sorted(eligible),
 }

def run(task_id,policy_path,host_root,apparatus_root):
 root_source=ev.defect_root_source(task_id,host_root,apparatus_root)
 root={
  "node_id":"root","parent_node_id":None,"source":root_source,
  "source_sha256":_sha(root_source),"lineage_depth":0,
  "action":_action(task_id,True),
  "outcome":{"quality_milli":0,"evolver_profile_generation":0,"ever_champion":True,"root_branch_node_id":"root"},
 }
 nodes={"root":root}; revealed=["root"]; cursors={}
 requests=rounds=stalls=0; best=0; observations=[]; stop_reason=None
 meta=sandbox.metadata(policy_path,[])
 if not meta.get("accepted"): raise RuntimeError(f"policy rejected: {meta}")
 md=list(meta["metadata"]); ppar=int(md[7]); prounds=int(md[8]); pstall=int(md[9])
 while requests<MAX_REQUESTS and rounds<min(MAX_ROUNDS,prounds):
  if rounds>0 and stalls>=pstall:
   stop_reason="policy_stall_rounds"; break
  view=_view(nodes,revealed,cursors,task_id)
  if not view["eligible_parent_ids"]:
   stop_reason="candidate_family_exhausted"; break
  cap=min(MAX_PARALLELISM,ppar,MAX_REQUESTS-requests)
  selected=sandbox.execute(policy_path,view,cap,[])
  if not selected.get("accepted"): raise RuntimeError(f"policy execution failed: {selected}")
  parents=list(selected["selected_parent_ids"])
  if not parents:
   stop_reason="policy_empty_batch"; break
  before=best; new_ids=[]
  for parent_id in parents:
   candidates=gen.children(task_id,nodes[parent_id]["source"])
   i=cursors.get(parent_id,0)
   if i>=len(candidates): raise RuntimeError("selected non-expandable parent")
   child=candidates[i]; cursors[parent_id]=i+1
   result=ev.evaluate(task_id,child["source"],host_root,apparatus_root)
   nid="n-"+hashlib.sha256(f"{parent_id}|{child['source_sha256']}|{i}".encode()).hexdigest()[:16]
   parent=nodes[parent_id]
   prior=max(int(nodes[x]["outcome"]["quality_milli"]) for x in revealed)
   branch=nid if parent_id=="root" else parent["outcome"]["root_branch_node_id"]
   nodes[nid]={
    "node_id":nid,"parent_node_id":parent_id,"source":child["source"],
    "source_sha256":child["source_sha256"],"lineage_depth":int(parent["lineage_depth"])+1,
    "mutation_locus":child["locus"],"action":_action(task_id,False),
    "outcome":{"quality_milli":int(result["quality_milli"]),"evolver_profile_generation":0,
      "ever_champion":int(result["quality_milli"])>prior,"root_branch_node_id":branch},
    "evaluation":result,
   }
   revealed.append(nid); new_ids.append(nid); requests+=1
   best=max(best,int(result["quality_milli"]))
  rounds+=1; stalls=0 if best>before else stalls+1
  observations.append({"round":rounds,"parent_node_ids":parents,"result_node_ids":new_ids})
 if stop_reason is None:
  stop_reason="external_request_budget" if requests>=MAX_REQUESTS else ("external_round_budget" if rounds>=MAX_ROUNDS else "stopped")
 compact={}
 for nid,n in nodes.items():
  compact[nid]={k:v for k,v in n.items() if k!="source"}
 return {
  "schema":"mira-genesis-rsi-v23-l5-holdout-task-result-v1",
  "task_id":task_id,"policy_sha256":hashlib.sha256(policy_path.read_bytes()).hexdigest(),
  "root_source_sha256":root["source_sha256"],"best_quality_milli":best,
  "represented_requests":requests,"rounds":rounds,"stop_reason":stop_reason,
  "utility":[best,-requests,-rounds],"nodes":compact,"observations":observations,
 }

def main():
 ap=argparse.ArgumentParser(); ap.add_argument("task_id"); ap.add_argument("policy",type=Path)
 ap.add_argument("--host-root",type=Path,required=True); ap.add_argument("--apparatus-root",type=Path,default=Path("."))
 ap.add_argument("--out",type=Path)
 a=ap.parse_args(); r=run(a.task_id,a.policy,a.host_root,a.apparatus_root.resolve())
 text=json.dumps(r,indent=2,sort_keys=True)+"\n"
 if a.out: a.out.write_text(text,encoding="utf-8")
 print(text,end="")
if __name__=="__main__": main()
