#!/usr/bin/env python3
"""Prospective L6-L8 evidence ladder.

This module validates *evidence shape* only. It is deliberately unable to create
scientific evidence, choose a winning generation, or invent missing controls.
Canonical thresholds remain external configuration until the relevant prior
level has been adjudicated.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

SCHEMA="mira-genesis-rsi-l6-l8-evidence-v1"

def _utility(value: Any) -> tuple[int,...]:
    if not isinstance(value,list) or not value or any(type(x) is not int for x in value):
        raise ValueError("utility must be a non-empty list of integers")
    return tuple(value)

def _strictly_better(a: Any,b: Any)->bool:
    return _utility(a) > _utility(b)

def _transition_ok(t:dict[str,Any])->tuple[bool,list[str]]:
    problems=[]
    required_true=(
        "successor_selected_without_human_ranking",
        "candidate_frozen_before_fresh_holdout",
        "evaluator_frozen_before_candidate",
        "equal_budget",
        "negative_evidence_retained",
    )
    for key in required_true:
        if t.get(key) is not True:
            problems.append(f"{key} must be true")
    if t.get("producer_generation") != t.get("from_generation"):
        problems.append("producer_generation must equal from_generation")
    if t.get("produced_generation") != t.get("to_generation"):
        problems.append("produced_generation must equal to_generation")
    if not _strictly_better(t.get("successor_holdout_utility"),t.get("predecessor_holdout_utility")):
        problems.append("successor holdout utility is not strictly greater than predecessor")
    if not _strictly_better(t.get("successor_holdout_utility"),t.get("ablated_holdout_utility")):
        problems.append("successor holdout utility is not strictly greater than causal ablation")
    if not isinstance(t.get("acquired_mechanism_id"),str) or not t["acquired_mechanism_id"]:
        problems.append("acquired_mechanism_id must be non-empty")
    return (not problems,problems)

def assess_l6(evidence:dict[str,Any],config:dict[str,Any])->dict[str,Any]:
    transitions=list(evidence.get("transitions",[]))
    minimum=int(config["l6_min_causal_transitions"])
    rows=[]
    for t in transitions:
        ok,problems=_transition_ok(t)
        rows.append({
            "from_generation":t.get("from_generation"),
            "to_generation":t.get("to_generation"),
            "ok":ok,
            "problems":problems,
        })
    contiguous=True
    for left,right in zip(transitions,transitions[1:]):
        if left.get("to_generation") != right.get("from_generation"):
            contiguous=False
            break
    positive=(len(transitions)>=minimum and contiguous and all(r["ok"] for r in rows))
    return {
        "level":"L6",
        "positive":positive,
        "minimum_causal_transitions":minimum,
        "observed_transitions":len(transitions),
        "contiguous_chain":contiguous,
        "transitions":rows,
    }

def _domain_ok(row:dict[str,Any])->tuple[bool,list[str]]:
    problems=[]
    for key in (
        "candidate_frozen_before_holdout",
        "evaluator_frozen_before_candidate",
        "no_domain_specific_candidate_guidance",
        "equal_budget",
        "negative_evidence_retained",
    ):
        if row.get(key) is not True:
            problems.append(f"{key} must be true")
    if not _strictly_better(row.get("successor_utility"),row.get("predecessor_utility")):
        problems.append("successor utility is not strictly greater than predecessor")
    for key in ("domain_id","domain_family","environment_id"):
        if not isinstance(row.get(key),str) or not row[key]:
            problems.append(f"{key} must be non-empty")
    return (not problems,problems)

def assess_l7(evidence:dict[str,Any],config:dict[str,Any],l6:dict[str,Any]|None=None)->dict[str,Any]:
    l6=l6 or assess_l6(evidence,config)
    domains=list(evidence.get("domain_transfer",[]))
    minimum=int(config["l7_min_domain_families"])
    rows=[]
    families=set()
    independent=0
    for row in domains:
        ok,problems=_domain_ok(row)
        rows.append({"domain_id":row.get("domain_id"),"ok":ok,"problems":problems})
        if ok:
            families.add(row["domain_family"])
            independent += int(row.get("independently_maintained") is True)
    positive=(
        l6["positive"]
        and len(families)>=minimum
        and independent>=int(config["l7_min_independently_maintained_domains"])
        and all(r["ok"] for r in rows)
    )
    return {
        "level":"L7",
        "positive":positive,
        "requires_l6_positive":l6["positive"],
        "distinct_domain_families":len(families),
        "minimum_domain_families":minimum,
        "independently_maintained_domains":independent,
        "minimum_independently_maintained_domains":int(config["l7_min_independently_maintained_domains"]),
        "domains":rows,
    }

def assess_l8(evidence:dict[str,Any],config:dict[str,Any],l7:dict[str,Any]|None=None)->dict[str,Any]:
    l7=l7 or assess_l7(evidence,config)
    b=dict(evidence.get("bottleneck_selection",{}))
    episodes=list(b.get("episodes",[]))
    problems=[]
    if b.get("selector_frozen_before_holdout") is not True:
        problems.append("selector_frozen_before_holdout must be true")
    if b.get("selection_rule_not_human_overridden") is not True:
        problems.append("selection_rule_not_human_overridden must be true")
    if b.get("negative_evidence_retained") is not True:
        problems.append("negative_evidence_retained must be true")

    selected=[]
    adaptive_total=None
    fixed_totals:dict[str,list[int]]={}
    episode_rows=[]
    for idx,ep in enumerate(episodes):
        eproblems=[]
        available=list(ep.get("available_components",[]))
        chosen=ep.get("selected_component")
        outcomes=dict(ep.get("matched_intervention_utilities",{}))
        if ep.get("snapshot_frozen_before_selection") is not True:
            eproblems.append("snapshot_frozen_before_selection must be true")
        if ep.get("selection_frozen_before_intervention") is not True:
            eproblems.append("selection_frozen_before_intervention must be true")
        if ep.get("equal_budget_per_component") is not True:
            eproblems.append("equal_budget_per_component must be true")
        if chosen not in available:
            eproblems.append("selected_component must be available")
        if set(outcomes) != set(available):
            eproblems.append("matched intervention outcomes must exist for every available component")
        vectors={}
        for component,value in outcomes.items():
            try:
                vectors[component]=list(_utility(value))
            except Exception as exc:
                eproblems.append(f"invalid utility for {component}: {exc}")
        if vectors:
            widths={len(v) for v in vectors.values()}
            if len(widths)!=1:
                eproblems.append("utility widths must match within an episode")
        if not eproblems:
            selected.append(chosen)
            chosen_v=vectors[chosen]
            if adaptive_total is None:
                adaptive_total=[0]*len(chosen_v)
            if len(adaptive_total)!=len(chosen_v):
                eproblems.append("utility width changed across episodes")
            else:
                adaptive_total=[a+b for a,b in zip(adaptive_total,chosen_v,strict=True)]
                for component,v in vectors.items():
                    fixed_totals.setdefault(component,[0]*len(v))
                    if len(fixed_totals[component])!=len(v):
                        eproblems.append("fixed-target utility width changed")
                    else:
                        fixed_totals[component]=[
                            a+b for a,b in zip(fixed_totals[component],v,strict=True)
                        ]
        episode_rows.append({"episode":idx+1,"selected_component":chosen,"ok":not eproblems,"problems":eproblems})

    min_episodes=int(config["l8_min_bottleneck_episodes"])
    min_targets=int(config["l8_min_distinct_selected_components"])
    common_components=set(episodes[0].get("available_components",[])) if episodes else set()
    for ep in episodes[1:]:
        common_components &= set(ep.get("available_components",[]))
    comparable_fixed={k:v for k,v in fixed_totals.items() if k in common_components}
    best_fixed=max((tuple(v) for v in comparable_fixed.values()),default=None)
    adaptive_tuple=tuple(adaptive_total) if adaptive_total is not None else None
    beats_fixed=(adaptive_tuple is not None and best_fixed is not None and adaptive_tuple>best_fixed)

    positive=(
        l7["positive"]
        and not problems
        and len(episodes)>=min_episodes
        and len(set(selected))>=min_targets
        and all(r["ok"] for r in episode_rows)
        and beats_fixed
    )
    return {
        "level":"L8",
        "positive":positive,
        "requires_l7_positive":l7["positive"],
        "minimum_episodes":min_episodes,
        "observed_episodes":len(episodes),
        "minimum_distinct_selected_components":min_targets,
        "distinct_selected_components":len(set(selected)),
        "adaptive_aggregate_utility":adaptive_total,
        "best_fixed_target_aggregate_utility":list(best_fixed) if best_fixed is not None else None,
        "adaptive_strictly_beats_best_fixed_target":beats_fixed,
        "global_problems":problems,
        "episodes":episode_rows,
    }

def assess(evidence:dict[str,Any],config:dict[str,Any])->dict[str,Any]:
    if evidence.get("schema") != SCHEMA:
        raise ValueError(f"unsupported evidence schema: {evidence.get('schema')!r}")
    l6=assess_l6(evidence,config)
    l7=assess_l7(evidence,config,l6)
    l8=assess_l8(evidence,config,l7)
    return {"schema":"mira-genesis-rsi-l6-l8-assessment-v1","L6":l6,"L7":l7,"L8":l8}

def main()->None:
    ap=argparse.ArgumentParser()
    ap.add_argument("evidence",type=Path)
    ap.add_argument("config",type=Path)
    ap.add_argument("--out",type=Path)
    args=ap.parse_args()
    result=assess(json.loads(args.evidence.read_text()),json.loads(args.config.read_text()))
    text=json.dumps(result,indent=2,sort_keys=True)+"\n"
    if args.out: args.out.write_text(text,encoding="utf-8")
    print(text,end="")

if __name__=="__main__":
    main()
