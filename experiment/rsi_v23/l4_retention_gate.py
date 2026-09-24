#!/usr/bin/env python3
"""Zero-tolerance retention gate for a frozen V23 G3 against positive L4 R1 histories."""
from __future__ import annotations
import argparse, hashlib, importlib.util, json
from pathlib import Path

HERE=Path(__file__).resolve().parent
SANDBOX=HERE/"sandbox_policy.py"

L4_TASKS=(
 ("brewstead-catalog-crop-ingredient-name","src/main/java/be/mjodheim/brewstead/service/CatalogService.java"),
 ("brewstead-game-state-estate-max-fields","src/main/java/be/mjodheim/brewstead/service/GameStateService.java"),
 ("brewstead-progression-merchant-coin-bonus","src/main/java/be/mjodheim/brewstead/service/ProgressionService.java"),
)

def _load():
 spec=importlib.util.spec_from_file_location("v23_retention_sandbox",SANDBOX)
 if spec is None or spec.loader is None: raise RuntimeError("cannot load sandbox")
 m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

sandbox=_load()

def view(task_id,source):
 root="root"; child="r1-quality-1000"
 def action(is_root):
  return {"family":"defect-root" if is_root else "external-code-repair",
   "target_axes":[task_id],"mechanisms":["seed-defect"] if is_root else ["source-patch"],
   "changed_regions":[source]}
 return {
  "root_node_id":root,
  "revealed_nodes":[
   {"node_id":root,"lineage_depth":0,"action":action(True),
    "outcome":{"quality_milli":0,"evolver_profile_generation":0,"ever_champion":True,"root_branch_node_id":root}},
   {"node_id":child,"lineage_depth":1,"action":action(False),
    "outcome":{"quality_milli":1000,"evolver_profile_generation":0,"ever_champion":True,"root_branch_node_id":child}},
  ],
  "eligible_parent_ids":[root,child],
 }

def check(policy:Path)->dict:
 meta=sandbox.metadata(policy,[])
 if not meta.get("accepted"): raise RuntimeError(f"policy rejected: {meta}")
 parallelism=min(2,int(meta["metadata"][7]))
 rows=[]
 for task_id,source in L4_TASKS:
  result=sandbox.execute(policy,view(task_id,source),parallelism,[])
  if not result.get("accepted"): raise RuntimeError(f"policy execution failed: {result}")
  selected=list(result["selected_parent_ids"])
  rows.append({"task_id":task_id,"selected_parent_ids":selected,"retained":selected==[]})
 positive=all(x["retained"] for x in rows)
 return {
  "schema":"mira-genesis-rsi-v23-l4-retention-v1",
  "policy_sha256":hashlib.sha256(policy.read_bytes()).hexdigest(),
  "l4_reference_per_task_utility":[1000,-1,-1],
  "tasks":rows,
  "zero_tolerance_retention":positive,
 }

def main():
 ap=argparse.ArgumentParser(); ap.add_argument("policy",type=Path); ap.add_argument("--out",type=Path)
 a=ap.parse_args(); r=check(a.policy); t=json.dumps(r,indent=2,sort_keys=True)+"\n"
 if a.out:a.out.write_text(t,encoding="utf-8")
 print(t,end=""); raise SystemExit(0 if r["zero_tolerance_retention"] else 3)
if __name__=="__main__":main()
