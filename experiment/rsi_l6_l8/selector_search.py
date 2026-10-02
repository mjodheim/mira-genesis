#!/usr/bin/env python3
"""Development-only search over identity-blind L8 selector programs.

The search consumes only episodes for which every available component already
has a matched realized intervention outcome. It never invents a counterfactual
outcome and does not touch the future L8 holdout.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any

HERE=Path(__file__).resolve().parent

def _load_selector():
    path=HERE/"bottleneck_selector.py"
    spec=importlib.util.spec_from_file_location("rsi_l8_selector_search_runtime",path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load bottleneck selector")
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

SELECTOR=_load_selector()

def _metric_names(episodes:list[dict[str,Any]])->list[str]:
    names=None
    for ep in episodes:
        snapshot=ep.get("snapshot",{})
        components=snapshot.get("components",[])
        for row in components:
            metrics=set(row.get("metrics",{}))
            names=metrics if names is None else names & metrics
    return sorted(names or set())

def candidate_programs(metric_names:list[str])->list[dict[str,Any]]:
    programs=[]
    def p(expr): programs.append({"schema":SELECTOR.PROGRAM_SCHEMA,"expression":expr})
    for m in metric_names:
        p({"metric":m})
        p({"op":{"name":"neg","args":[{"metric":m}]}})
        p({"op":{"name":"abs","args":[{"metric":m}]}})
    for i,a in enumerate(metric_names):
        for b in metric_names[i+1:]:
            p({"op":{"name":"add","args":[{"metric":a},{"metric":b}]}})
            p({"op":{"name":"sub","args":[{"metric":a},{"metric":b}]}})
            p({"op":{"name":"sub","args":[{"metric":b},{"metric":a}]}})
            p({"op":{"name":"min","args":[{"metric":a},{"metric":b}]}})
            p({"op":{"name":"max","args":[{"metric":a},{"metric":b}]}})
    unique={}
    for program in programs:
        unique[SELECTOR.sha256(program)]=program
    return [unique[k] for k in sorted(unique)]

def _utility(value:Any)->tuple[int,...]:
    if not isinstance(value,list) or not value or any(type(x) is not int for x in value):
        raise ValueError("intervention utility must be a non-empty integer list")
    return tuple(value)

def score_program(program:dict[str,Any],episodes:list[dict[str,Any]])->dict[str,Any]:
    meta=SELECTOR.validate_program(program)
    aggregate=None
    choices=[]
    for index,ep in enumerate(episodes,1):
        snapshot=ep.get("snapshot")
        choice=SELECTOR.choose(program,snapshot)
        available={row["id"] for row in snapshot["components"]}
        outcomes=dict(ep.get("matched_intervention_utilities",{}))
        if set(outcomes)!=available:
            raise ValueError(f"episode {index} lacks matched outcomes for every component")
        utility=_utility(outcomes[choice["selected_component"]])
        if aggregate is None:
            aggregate=[0]*len(utility)
        if len(aggregate)!=len(utility):
            raise ValueError("utility width changes across development episodes")
        aggregate=[a+b for a,b in zip(aggregate,utility,strict=True)]
        choices.append({
            "episode":index,
            "selected_component":choice["selected_component"],
            "utility":list(utility),
        })
    return {
        "program":program,
        "program_sha256":meta["sha256"],
        "nodes":meta["nodes"],
        "aggregate_utility":aggregate or [],
        "choices":choices,
    }

def search(episodes:list[dict[str,Any]])->dict[str,Any]:
    metrics=_metric_names(episodes)
    if not metrics:
        raise ValueError("no metric is common to all development components")
    rows=[score_program(p,episodes) for p in candidate_programs(metrics)]
    if not rows:
        raise ValueError("candidate grammar generated no programs")
    rows.sort(
        key=lambda r:(tuple(r["aggregate_utility"]),-int(r["nodes"]),r["program_sha256"]),
        reverse=True,
    )
    best_utility=tuple(rows[0]["aggregate_utility"])
    best_nodes=rows[0]["nodes"]
    tied=[r for r in rows if tuple(r["aggregate_utility"])==best_utility and r["nodes"]==best_nodes]
    winner=min(tied,key=lambda r:r["program_sha256"])
    return {
        "schema":"mira-genesis-rsi-l8-selector-search-v1",
        "development_only":True,
        "holdout_consumed":False,
        "metric_names":metrics,
        "candidate_count":len(rows),
        "selected_program":winner["program"],
        "selected_program_sha256":winner["program_sha256"],
        "selected_development_utility":winner["aggregate_utility"],
        "selected_nodes":winner["nodes"],
        "selected_choices":winner["choices"],
    }

def main()->None:
    ap=argparse.ArgumentParser()
    ap.add_argument("episodes",type=Path)
    ap.add_argument("--out",type=Path)
    args=ap.parse_args()
    payload=json.loads(args.episodes.read_text())
    episodes=payload["episodes"] if isinstance(payload,dict) else payload
    result=search(list(episodes))
    text=json.dumps(result,indent=2,sort_keys=True)+"\n"
    if args.out: args.out.write_text(text,encoding="utf-8")
    print(text,end="")

if __name__=="__main__":
    main()
