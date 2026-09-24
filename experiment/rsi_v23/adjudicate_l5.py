#!/usr/bin/env python3
"""Final frozen adjudicator for V23/L5 causal recursive meta-improvement."""
from __future__ import annotations
import argparse,json
from pathlib import Path

TASK_IDS={
 "brewtrack-brewmath-precision",
 "brewtrack-recipemath-units-water",
 "brewstead-effect-rounding",
 "brewstead-brew-lifecycle-thresholds",
}

def global_utility(rows):
 if {r["task_id"] for r in rows}!=TASK_IDS: raise ValueError("holdout task population mismatch")
 return [
  sum(int(r["best_quality_milli"])==1000 for r in rows),
  sum(int(r["best_quality_milli"]) for r in rows),
  -sum(int(r["represented_requests"]) for r in rows),
  -sum(int(r["rounds"]) for r in rows),
 ]

def adjudicate(meta,retention,g3_rows,g2_rows,g1meta_rows):
 if meta.get("schema")!="mira-genesis-rsi-v23-l5-meta-search-v1": raise ValueError("wrong meta schema")
 if retention.get("schema")!="mira-genesis-rsi-v23-l4-retention-v1": raise ValueError("wrong retention schema")
 arms=meta["arms"]; a=arms["g2_meta"]; b=arms["g1_meta"]; c=arms["g2_ablation"]
 ug3=global_utility(g3_rows); ug2=global_utility(g2_rows); ub=global_utility(g1meta_rows)
 predicates={
  "g2_meta_selects_strict_development_improvement":bool(a["successor_strictly_better_than_g2_on_development"]),
  "g3_retains_l4_zero_tolerance":bool(retention["zero_tolerance_retention"]),
  "g3_fresh_global_utility_strictly_beats_g2":tuple(ug3)>tuple(ug2),
  "g3_fresh_global_utility_strictly_beats_g1_meta_successor":tuple(ug3)>tuple(ub),
  "g2_meta_process_strictly_beats_g2_ablation":tuple(a["meta_process_utility"])>tuple(c["meta_process_utility"]),
 }
 return {
  "schema":"mira-genesis-rsi-v23-l5-final-adjudication-v1",
  "meta_selected_source_sha256":a["selected_successor"]["candidate"]["source_sha256"],
  "g1_meta_selected_source_sha256":b["selected_successor"]["candidate"]["source_sha256"],
  "g2_ablation_selected_source_sha256":c["selected_successor"]["candidate"]["source_sha256"],
  "g3_global_utility":ug3,"g2_global_utility":ug2,"g1_meta_successor_global_utility":ub,
  "predicates":predicates,
  "l5_positive":all(predicates.values()),
 }

def load_rows(paths):
 return [json.loads(Path(p).read_text()) for p in paths]

def main():
 ap=argparse.ArgumentParser(); ap.add_argument("--meta",type=Path,required=True); ap.add_argument("--retention",type=Path,required=True)
 ap.add_argument("--g3",nargs=4,required=True); ap.add_argument("--g2",nargs=4,required=True); ap.add_argument("--g1-meta",dest="g1meta",nargs=4,required=True); ap.add_argument("--out",type=Path)
 a=ap.parse_args()
 r=adjudicate(json.loads(a.meta.read_text()),json.loads(a.retention.read_text()),load_rows(a.g3),load_rows(a.g2),load_rows(a.g1meta))
 t=json.dumps(r,indent=2,sort_keys=True)+"\n"
 if a.out:a.out.write_text(t,encoding="utf-8")
 print(t,end="")
if __name__=="__main__":main()
