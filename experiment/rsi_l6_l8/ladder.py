#!/usr/bin/env python3
"""Prospective L6-L8 evidence ladder.

This module validates *evidence shape* only. It is deliberately unable to create
scientific evidence, choose a winning generation, or invent missing controls.
Canonical thresholds remain external configuration until the relevant prior
level has been adjudicated.
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
    spec=importlib.util.spec_from_file_location("rsi_l8_bottleneck_selector_runtime",path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load bottleneck selector")
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

SELECTOR=_load_selector()

SCHEMA="mira-genesis-rsi-l6-l8-evidence-v1"

def _utility(value: Any) -> tuple[int,...]:
    if not isinstance(value,list) or not value or any(type(x) is not int for x in value):
        raise ValueError("utility must be a non-empty list of integers")
    return tuple(value)

def _strictly_better(a: Any,b: Any)->bool:
    return _utility(a) > _utility(b)

def _is_sha256(value:Any)->bool:
    return isinstance(value,str) and len(value)==64 and all(ch in "0123456789abcdef" for ch in value)

def _transition_ok(t:dict[str,Any])->tuple[bool,list[str]]:
    problems=[]
    required_true=(
        "successor_selected_without_human_ranking",
        "candidate_frozen_before_fresh_holdout",
        "evaluator_frozen_before_candidate",
        "negative_evidence_retained",
    )
    for key in required_true:
        if t.get(key) is not True:
            problems.append(f"{key} must be true")
    if t.get("producer_generation") != t.get("from_generation"):
        problems.append("producer_generation must equal from_generation")
    if t.get("produced_generation") != t.get("to_generation"):
        problems.append("produced_generation must equal to_generation")

    budgets=t.get("budgets")
    if not isinstance(budgets,dict) or set(budgets)!={"predecessor","successor","ablation"}:
        problems.append("budgets must contain predecessor, successor and ablation")
    else:
        if any(type(v) is not int or v <= 0 for v in budgets.values()):
            problems.append("transition budgets must be positive integers")
        elif len(set(budgets.values())) != 1:
            problems.append("transition budgets are not equal")

    for key in (
        "from_generation_sha256",
        "to_generation_sha256",
        "evaluator_commitment_sha256",
        "holdout_commitment_sha256",
        "mechanism_commitment_sha256",
        "selection_record_sha256",
    ):
        if not _is_sha256(t.get(key)):
            problems.append(f"{key} must be lowercase SHA-256")

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
        "negative_evidence_retained",
    ):
        if row.get(key) is not True:
            problems.append(f"{key} must be true")
    budgets=row.get("budgets")
    if not isinstance(budgets,dict) or set(budgets)!={"predecessor","successor"}:
        problems.append("domain budgets must contain predecessor and successor")
    else:
        if any(type(v) is not int or v <= 0 for v in budgets.values()):
            problems.append("domain budgets must be positive integers")
        elif budgets["predecessor"] != budgets["successor"]:
            problems.append("domain predecessor/successor budgets are not equal")
    if not _strictly_better(row.get("successor_utility"),row.get("predecessor_utility")):
        problems.append("successor utility is not strictly greater than predecessor")
    for key in ("domain_id","domain_family","environment_id","maintainer_id"):
        if not isinstance(row.get(key),str) or not row[key]:
            problems.append(f"{key} must be non-empty")
    for key in (
        "environment_commitment_sha256",
        "evaluator_commitment_sha256",
        "holdout_commitment_sha256",
        "candidate_commitment_sha256",
    ):
        if not _is_sha256(row.get(key)):
            problems.append(f"{key} must be lowercase SHA-256")
    return (not problems,problems)

def assess_l7(evidence:dict[str,Any],config:dict[str,Any],l6:dict[str,Any]|None=None)->dict[str,Any]:
    l6=l6 or assess_l6(evidence,config)
    domains=list(evidence.get("domain_transfer",[]))
    minimum=int(config["l7_min_domain_families"])
    min_external=int(config["l7_min_external_maintained_domains"])
    internal=set(config.get("internal_maintainer_ids",[]))
    rows=[]
    families=set()
    external=0
    external_maintainers=set()
    for row in domains:
        ok,problems=_domain_ok(row)
        is_external=(ok and row.get("maintainer_id") not in internal)
        rows.append({
            "domain_id":row.get("domain_id"),
            "maintainer_id":row.get("maintainer_id"),
            "external_maintainer":is_external,
            "ok":ok,
            "problems":problems,
        })
        if ok:
            families.add(row["domain_family"])
            if is_external:
                external += 1
                external_maintainers.add(row["maintainer_id"])
    positive=(
        l6["positive"]
        and len(families)>=minimum
        and external>=min_external
        and all(r["ok"] for r in rows)
    )
    return {
        "level":"L7",
        "positive":positive,
        "requires_l6_positive":l6["positive"],
        "distinct_domain_families":len(families),
        "minimum_domain_families":minimum,
        "external_maintained_domains":external,
        "distinct_external_maintainers":len(external_maintainers),
        "minimum_external_maintained_domains":min_external,
        "domains":rows,
    }

def assess_l8(evidence:dict[str,Any],config:dict[str,Any],l7:dict[str,Any]|None=None)->dict[str,Any]:
    l7=l7 or assess_l7(evidence,config)
    b=dict(evidence.get("bottleneck_selection",{}))
    episodes=list(b.get("episodes",[]))
    problems=[]

    selector_program=b.get("selector_program")
    selector_hash=b.get("selector_sha256")
    try:
        selector_meta=SELECTOR.validate_program(selector_program)
    except Exception as exc:
        selector_meta=None
        problems.append(f"invalid selector program: {exc}")
    if selector_meta is not None and selector_hash != selector_meta["sha256"]:
        problems.append("selector_sha256 does not match canonical selector program")

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
        snapshot=ep.get("snapshot")
        snapshot_hash=ep.get("snapshot_sha256")
        if selector_meta is not None:
            try:
                choice=SELECTOR.choose(selector_program,snapshot)
            except Exception as exc:
                choice=None
                eproblems.append(f"selector could not evaluate snapshot: {exc}")
        else:
            choice=None
        if choice is not None and snapshot_hash != choice["snapshot_sha256"]:
            eproblems.append("snapshot_sha256 does not match canonical snapshot")
        chosen=ep.get("selected_component")
        if choice is not None and chosen != choice["selected_component"]:
            eproblems.append("selected_component does not match frozen selector output")

        available=[]
        if isinstance(snapshot,dict) and isinstance(snapshot.get("components"),list):
            available=[row.get("id") for row in snapshot["components"] if isinstance(row,dict)]

        outcomes=dict(ep.get("matched_intervention_utilities",{}))
        budgets=dict(ep.get("component_budgets",{}))
        commitments=dict(ep.get("intervention_evidence_sha256",{}))

        if ep.get("snapshot_frozen_before_selection") is not True:
            eproblems.append("snapshot_frozen_before_selection must be true")
        if ep.get("selection_frozen_before_intervention") is not True:
            eproblems.append("selection_frozen_before_intervention must be true")
        if chosen not in available:
            eproblems.append("selected_component must be available")
        if set(outcomes) != set(available):
            eproblems.append("matched intervention outcomes must exist for every available component")
        if set(budgets) != set(available):
            eproblems.append("numeric component budget must exist for every available component")
        if set(commitments) != set(available):
            eproblems.append("intervention evidence commitment must exist for every available component")
        if budgets:
            if any(type(v) is not int or v <= 0 for v in budgets.values()):
                eproblems.append("all component budgets must be positive integers")
            if len(set(budgets.values())) != 1:
                eproblems.append("component budgets are not equal")
        if commitments and any(not _is_sha256(v) for v in commitments.values()):
            eproblems.append("intervention evidence commitments must be lowercase SHA-256")

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

        episode_rows.append({
            "episode":idx+1,
            "selected_component":chosen,
            "selector_selected_component":choice["selected_component"] if choice is not None else None,
            "selector_tie_count":choice["tie_count"] if choice is not None else None,
            "ok":not eproblems,
            "problems":eproblems,
        })

    min_episodes=int(config["l8_min_bottleneck_episodes"])
    min_targets=int(config["l8_min_distinct_selected_components"])
    common_components=set()
    if episodes and isinstance(episodes[0].get("snapshot"),dict):
        common_components={row.get("id") for row in episodes[0]["snapshot"].get("components",[]) if isinstance(row,dict)}
    for ep in episodes[1:]:
        snapshot=ep.get("snapshot",{})
        ids={row.get("id") for row in snapshot.get("components",[]) if isinstance(row,dict)}
        common_components &= ids
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
        "selector_sha256":selector_meta["sha256"] if selector_meta is not None else None,
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
