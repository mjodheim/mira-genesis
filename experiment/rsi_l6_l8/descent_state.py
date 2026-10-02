#!/usr/bin/env python3
"""Deterministic state machine for repeated causal RSI meta-descent (L6 preparation)."""
from __future__ import annotations

import argparse
import importlib.util
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

HERE=Path(__file__).resolve().parent

def _load_ladder():
    path=HERE/"ladder.py"
    spec=importlib.util.spec_from_file_location("rsi_l6_descent_ladder",path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load L6-L8 ladder")
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

LADDER=_load_ladder()
SCHEMA="mira-genesis-rsi-l6-descent-state-v1"

def init_state(*,generation_id:str,generation_sha256:str,protocol_commitment_sha256:str)->dict[str,Any]:
    for name,value in (
        ("generation_sha256",generation_sha256),
        ("protocol_commitment_sha256",protocol_commitment_sha256),
    ):
        if not LADDER._is_sha256(value):
            raise ValueError(f"{name} must be lowercase SHA-256")
    if not isinstance(generation_id,str) or not generation_id:
        raise ValueError("generation_id must be non-empty")
    return {
        "schema":SCHEMA,
        "protocol_commitment_sha256":protocol_commitment_sha256,
        "start_generation_id":generation_id,
        "current_generation_id":generation_id,
        "current_generation_sha256":generation_sha256,
        "generations":[{"generation_id":generation_id,"generation_sha256":generation_sha256}],
        "transitions":[],
        "stopped":False,
        "stop_reason":None,
    }

def next_request(state:dict[str,Any])->dict[str,Any]:
    if state.get("schema")!=SCHEMA:
        raise ValueError("invalid descent state schema")
    if state["stopped"]:
        return {"can_open_next_transition":False,"reason":state["stop_reason"]}
    return {
        "can_open_next_transition":True,
        "from_generation":state["current_generation_id"],
        "from_generation_sha256":state["current_generation_sha256"],
        "transition_index":len(state["transitions"])+1,
    }

def record_transition(state:dict[str,Any],transition:dict[str,Any])->dict[str,Any]:
    if state["stopped"]:
        raise ValueError("cannot append to stopped descent")
    if transition.get("from_generation")!=state["current_generation_id"]:
        raise ValueError("transition does not start from current generation")
    if transition.get("from_generation_sha256")!=state["current_generation_sha256"]:
        raise ValueError("transition parent digest does not match current generation")
    if any(t.get("to_generation")==transition.get("to_generation") for t in state["transitions"]):
        raise ValueError("duplicate generation id")
    ok,problems=LADDER._transition_ok(transition)
    row=deepcopy(transition)
    row["causal_transition_positive"]=ok
    row["validation_problems"]=problems
    state["transitions"].append(row)
    if not ok:
        state["stopped"]=True
        state["stop_reason"]="causal_transition_not_positive"
        return state
    gid=transition["to_generation"]
    gsha=transition["to_generation_sha256"]
    state["generations"].append({"generation_id":gid,"generation_sha256":gsha})
    state["current_generation_id"]=gid
    state["current_generation_sha256"]=gsha
    return state

def readiness(state:dict[str,Any],minimum_transitions:int)->dict[str,Any]:
    if minimum_transitions<1:
        raise ValueError("minimum_transitions must be positive")
    positive=sum(int(t.get("causal_transition_positive") is True) for t in state["transitions"])
    return {
        "schema":"mira-genesis-rsi-l6-descent-readiness-v1",
        "positive_transition_count":positive,
        "minimum_transitions":minimum_transitions,
        "chain_complete":positive>=minimum_transitions and not state["stopped"],
        "stopped":state["stopped"],
        "stop_reason":state["stop_reason"],
        "current_generation_id":state["current_generation_id"],
    }

def main()->None:
    ap=argparse.ArgumentParser()
    sub=ap.add_subparsers(dest="cmd",required=True)
    p=sub.add_parser("status"); p.add_argument("state",type=Path); p.add_argument("--minimum-transitions",type=int,required=True)
    args=ap.parse_args()
    if args.cmd=="status":
        s=json.loads(args.state.read_text())
        print(json.dumps({
            "next":next_request(s),
            "readiness":readiness(s,args.minimum_transitions),
        },indent=2,sort_keys=True))

if __name__=="__main__":
    main()
