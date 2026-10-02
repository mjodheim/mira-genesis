#!/usr/bin/env python3
"""Identity-blind bottleneck selector DSL for prospective RSI L8.

A selector expression receives only numeric metrics for one component at a time.
It cannot inspect component identifiers, source paths, domain names or outcomes
from interventions that occur after selection.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

PROGRAM_SCHEMA="mira-genesis-rsi-l8-selector-program-v1"
SNAPSHOT_SCHEMA="mira-genesis-rsi-l8-bottleneck-snapshot-v1"
MAX_NODES=64
MAX_DEPTH=12
ALLOWED_OPS={"add","sub","mul","min","max","neg","abs"}

def _canonical(value:Any)->bytes:
    return (json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False)+"\n").encode()

def sha256(value:Any)->str:
    return hashlib.sha256(_canonical(value)).hexdigest()

def _shape(expr:Any,depth:int=1)->tuple[int,int,set[str]]:
    if depth>MAX_DEPTH:
        raise ValueError("selector expression exceeds maximum depth")
    if not isinstance(expr,dict) or len(expr)!=1:
        raise ValueError("selector expression node must be a one-key object")
    key,value=next(iter(expr.items()))
    if key=="const":
        if type(value) is not int:
            raise ValueError("const must be an integer")
        return 1,depth,set()
    if key=="metric":
        if not isinstance(value,str) or not value or value.startswith("_"):
            raise ValueError("metric name must be a non-empty public identifier")
        return 1,depth,{value}
    if key!="op" or not isinstance(value,dict):
        raise ValueError("unknown selector expression node")
    name=value.get("name")
    args=value.get("args")
    if name not in ALLOWED_OPS:
        raise ValueError(f"unsupported selector op: {name!r}")
    if not isinstance(args,list):
        raise ValueError("op args must be a list")
    if name in {"neg","abs"} and len(args)!=1:
        raise ValueError(f"{name} requires exactly one arg")
    if name in {"sub","mul"} and len(args)!=2:
        raise ValueError(f"{name} requires exactly two args")
    if name in {"add","min","max"} and len(args)<2:
        raise ValueError(f"{name} requires at least two args")
    nodes=1
    deepest=depth
    metrics=set()
    for arg in args:
        n,d,m=_shape(arg,depth+1)
        nodes+=n; deepest=max(deepest,d); metrics|=m
    if nodes>MAX_NODES:
        raise ValueError("selector expression exceeds maximum node count")
    return nodes,deepest,metrics

def validate_program(program:dict[str,Any])->dict[str,Any]:
    if program.get("schema")!=PROGRAM_SCHEMA:
        raise ValueError("invalid selector program schema")
    if set(program)!={"schema","expression"}:
        raise ValueError("selector program has unexpected fields")
    nodes,depth,metrics=_shape(program["expression"])
    return {"nodes":nodes,"depth":depth,"metrics":sorted(metrics),"sha256":sha256(program)}

def _eval(expr:dict[str,Any],metrics:dict[str,int])->int:
    key,value=next(iter(expr.items()))
    if key=="const":
        return int(value)
    if key=="metric":
        if value not in metrics:
            raise ValueError(f"snapshot missing metric {value!r}")
        metric=metrics[value]
        if type(metric) is not int:
            raise ValueError(f"metric {value!r} must be integer")
        return metric
    name=value["name"]
    vals=[_eval(arg,metrics) for arg in value["args"]]
    if name=="add": return sum(vals)
    if name=="sub": return vals[0]-vals[1]
    if name=="mul": return vals[0]*vals[1]
    if name=="min": return min(vals)
    if name=="max": return max(vals)
    if name=="neg": return -vals[0]
    if name=="abs": return abs(vals[0])
    raise AssertionError(name)

def validate_snapshot(snapshot:dict[str,Any],required_metrics:set[str])->dict[str,Any]:
    if snapshot.get("schema")!=SNAPSHOT_SCHEMA:
        raise ValueError("invalid bottleneck snapshot schema")
    components=snapshot.get("components")
    if not isinstance(components,list) or len(components)<2:
        raise ValueError("snapshot requires at least two components")
    ids=[]
    for row in components:
        if not isinstance(row,dict) or set(row)!={"id","metrics"}:
            raise ValueError("component row must contain exactly id and metrics")
        cid=row["id"]
        if not isinstance(cid,str) or not cid:
            raise ValueError("component id must be non-empty")
        if cid in ids:
            raise ValueError("duplicate component id")
        ids.append(cid)
        metrics=row["metrics"]
        if not isinstance(metrics,dict):
            raise ValueError("component metrics must be an object")
        if any(not isinstance(k,str) or type(v) is not int for k,v in metrics.items()):
            raise ValueError("all component metrics must be integer-valued")
        missing=required_metrics-set(metrics)
        if missing:
            raise ValueError(f"component {cid!r} missing metrics: {sorted(missing)}")
    return {"component_ids":ids,"sha256":sha256(snapshot)}

def choose(program:dict[str,Any],snapshot:dict[str,Any])->dict[str,Any]:
    p=validate_program(program)
    s=validate_snapshot(snapshot,set(p["metrics"]))
    scored=[]
    for row in snapshot["components"]:
        scored.append((int(_eval(program["expression"],row["metrics"])),row["id"]))
    # Stable tie-break is apparatus-owned and independent of candidate expression.
    best=max(score for score,_ in scored)
    winners=sorted(cid for score,cid in scored if score==best)
    return {
        "selected_component":winners[0],
        "selected_score":best,
        "tie_count":len(winners),
        "scores":{cid:score for score,cid in scored},
        "program_sha256":p["sha256"],
        "snapshot_sha256":s["sha256"],
    }
