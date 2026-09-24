#!/usr/bin/env python3
"""Build the final prospective V23/L5 freeze record.

Must run on the apparatus commit immediately before the freeze-only commit.
"""
from __future__ import annotations
import argparse, hashlib, importlib.util, json, subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
FORBIDDEN_PRE_FREEZE=(
 "results/rsi-v23",
 "experiment/rsi_v23/G3_SELECTED.py",
 "experiment/rsi_v23/G1_META_SELECTED.py",
 "experiment/rsi_v23/V23_META_SEARCH_RESULT.json",
)

def sha256(path:Path)->str:
 return hashlib.sha256(path.read_bytes()).hexdigest()

def git_head()->str:
 return subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()

def required_files()->list[Path]:
 paths=[]
 for p in sorted((ROOT/"experiment/rsi_v23").rglob("*")):
  if p.is_file() and p.name!="V23_FREEZE.json": paths.append(p)
 for p in sorted((ROOT/"tests").glob("test_rsi_v23*.py")):
  if p.is_file(): paths.append(p)
 paths += [
  ROOT/"experiment/rsi_v22/policies/g1_search_policy.py",
  ROOT/"experiment/rsi_v22/policies/g2_search_policy.py",
  ROOT/"results/rsi-v22r/V22R_FINAL_ADJUDICATION.json",
  ROOT/"docs/rsi-v22r/V22R_FREEZE.json",
 ]
 unique={str(p.relative_to(ROOT)):p for p in paths}
 return [unique[k] for k in sorted(unique)]

def _load_meta_search():
 p=ROOT/"experiment/rsi_v23/l5_meta_search.py"
 spec=importlib.util.spec_from_file_location("v23_l5_freeze_meta_search",p)
 if spec is None or spec.loader is None: raise SystemExit("cannot load L5 meta-search")
 m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def _verify_calibrations(calibration_run_id:int)->None:
 paths=[
  ROOT/"experiment/rsi_v23/calibration/V23_L5_BREWSTEAD_CALIBRATION.json",
  ROOT/"experiment/rsi_v23/calibration/V23_L5_BREWTRACK_CALIBRATION.json",
 ]
 for p in paths:
  d=json.loads(p.read_text())
  if d.get("schema")!="mira-genesis-rsi-v23-l5-holdout-calibration-record-v1":
   raise SystemExit(f"wrong calibration schema: {p}")
  if d.get("status")!="GREEN_BEFORE_META_SEARCH":
   raise SystemExit(f"calibration not green before meta-search: {p}")
  if int(d.get("workflow_run_id",-1))!=int(calibration_run_id):
   raise SystemExit(f"calibration run id mismatch: {p}")

def build(apparatus_commit:str,calibration_run_id:int)->dict:
 actual=git_head()
 if actual!=apparatus_commit:
  raise SystemExit(f"apparatus commit mismatch: {actual} != {apparatus_commit}")
 for rel in FORBIDDEN_PRE_FREEZE:
  if (ROOT/rel).exists():
   raise SystemExit(f"pre-freeze result contamination: {rel}")
 files=required_files()
 missing=[str(p.relative_to(ROOT)) for p in files if not p.exists()]
 if missing: raise SystemExit("missing required freeze files: "+", ".join(missing))
 calibration=[p for p in files if "calibration" in p.name.lower() or "/calibration/" in str(p)]
 if len(calibration)<2:
  raise SystemExit("two retained L5 calibration records are required before freeze")
 _verify_calibrations(calibration_run_id)
 meta_search=_load_meta_search()
 ablation_source=meta_search.g2_ablation_source()
 payload={
  "schema":"mira-genesis-rsi-v23-l5-freeze-v1",
  "status":"FROZEN_BEFORE_ANY_V23_META_SEARCH",
  "apparatus_commit":apparatus_commit,
  "l4_canonical_main_commit":"0f7ac3875cc262b40b54ec533ca8ae11eaeefd12",
  "calibration_workflow_run_id":int(calibration_run_id),
  "g1_source_sha256":"3354f887a93a08d9f00e9c54ccb097003f727ba77c1e1b4e9997adf676d35434",
  "g2_source_sha256":"69d0d725601cd32adff27379dbb25f5c7be29946f9e9c6ac4858a0634cbd5fdf",
  "g2_ablation_source_sha256":hashlib.sha256(ablation_source.encode("utf-8")).hexdigest(),
  "g2_ablation_definition":"exact G2 with only the strong-result block 'if best >= 780: return []' removed",
  "files":{str(p.relative_to(ROOT)):sha256(p) for p in files},
 }
 raw=json.dumps(payload,sort_keys=True,separators=(",",":")).encode()
 return {**payload,"freeze_payload_sha256":hashlib.sha256(raw).hexdigest()}

def main():
 ap=argparse.ArgumentParser(); ap.add_argument("--apparatus-commit",required=True); ap.add_argument("--calibration-run-id",type=int,required=True); ap.add_argument("--out",type=Path,required=True)
 a=ap.parse_args(); result=build(a.apparatus_commit,a.calibration_run_id)
 a.out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
 print(json.dumps(result,indent=2,sort_keys=True))
if __name__=="__main__":main()
