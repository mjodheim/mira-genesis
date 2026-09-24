#!/usr/bin/env python3
"""Derive development-only literal tokens that V23 policy candidates may not embed."""
from __future__ import annotations
import argparse,json
from pathlib import Path

def tokens_from_state(state:dict)->set[str]:
    out={str(state["task_id"]),str(state["root_node_id"]),str(state["allowed_source_path"])}
    out.update(str(x) for x in state["nodes"])
    for node in state["nodes"].values():
        action=node.get("action",{})
        for value in action.get("target_axes",[]):
            out.add(str(value))
        for value in action.get("changed_regions",[]):
            out.add(str(value))
    return {x for x in out if x}

def main()->None:
    ap=argparse.ArgumentParser(); ap.add_argument("states",type=Path,nargs="+"); ap.add_argument("--out",type=Path,required=True)
    a=ap.parse_args(); tokens=set()
    for path in a.states:
        tokens |= tokens_from_state(json.loads(path.read_text()))
    text="\n".join(sorted(tokens))+"\n"; a.out.write_text(text,encoding="utf-8"); print(text,end="")
if __name__=="__main__": main()
