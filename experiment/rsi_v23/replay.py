#!/usr/bin/env python3
"""Exact replay over realized Genesis RSI discovery trees.

This module never predicts an unobserved child. A candidate policy is replayable
only while every requested parent expansion is already present in the retained
history. Unsupported requests are surfaced explicitly instead of assigned a
fabricated reward.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from collections import defaultdict, deque
from copy import deepcopy
from pathlib import Path
from typing import Any

REPLAY_SCHEMA = "mira-genesis-rsi-v23-exact-replay-v1"

def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def load_sandbox():
    path=Path(__file__).resolve().parent/"sandbox_policy.py"
    spec=importlib.util.spec_from_file_location("v23_replay_sandbox",path)
    if spec is None or spec.loader is None:
        raise ValueError(f"cannot load sandbox: {path}")
    module=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=module
    spec.loader.exec_module(module)
    return module

def policy_metadata(path:Path,forbidden_tokens:list[str])->tuple[object,dict[str,int],list[int]]:
    sandbox=load_sandbox()
    result=sandbox.metadata(path,forbidden_tokens)
    if not result.get("accepted"):
        raise ValueError(f"policy metadata rejected: {result}")
    raw=list(result["metadata"])
    names=(
        "parent_quality","parent_novelty","depth","profile_generation",
        "champion_parent","recovery","root_opening","parallelism",
        "max_rounds","stall_rounds",
    )
    return sandbox,dict(zip(names,raw,strict=True)),raw

def _row(node: dict[str, Any]) -> dict[str, Any]:
    return {
        "node_id": node["node_id"],
        "lineage_depth": int(node["lineage_depth"]),
        "action": deepcopy(node["action"]),
        "outcome": deepcopy(node["outcome"]),
    }

def expansion_queues(state: dict[str, Any]) -> dict[str, deque[str]]:
    """Return historical child expansions in the exact order they occurred."""
    queues: dict[str, deque[str]] = defaultdict(deque)
    for observation in state["observations"]:
        parents = list(observation["parent_node_ids"])
        results = list(observation["result_node_ids"])
        if len(parents) != len(results):
            raise ValueError("observation parent/result arity mismatch")
        for parent, child in zip(parents, results, strict=True):
            if parent not in state["nodes"] or child not in state["nodes"]:
                raise ValueError("observation references an absent node")
            if state["nodes"][child]["parent_node_id"] != parent:
                raise ValueError("observation edge disagrees with node parent")
            queues[parent].append(child)
    return dict(queues)

def replay_state(
    state: dict[str, Any],
    policy_path: Path,
    forbidden_tokens: list[str] | None = None,
    *,
    max_requests: int | None = None,
    max_rounds: int | None = None,
    max_parallelism: int | None = None,
) -> dict[str, Any]:
    forbidden_tokens=list(forbidden_tokens or [])
    sandbox,metadata,metadata_raw=policy_metadata(policy_path,forbidden_tokens)
    if metadata["parallelism"] < 1 or metadata["max_rounds"] < 1 or metadata["stall_rounds"] < 1:
        raise ValueError("policy parallelism, max_rounds and stall_rounds must be positive")
    if max_requests is not None and max_requests < 0:
        raise ValueError("max_requests must be non-negative")
    if max_rounds is not None and max_rounds < 1:
        raise ValueError("max_rounds must be positive")
    if max_parallelism is not None and max_parallelism < 1:
        raise ValueError("max_parallelism must be positive")
    effective_round_cap=min(metadata["max_rounds"],max_rounds) if max_rounds is not None else metadata["max_rounds"]
    effective_parallelism=min(metadata["parallelism"],max_parallelism) if max_parallelism is not None else metadata["parallelism"]
    root = state["root_node_id"]
    nodes = state["nodes"]
    if root not in nodes:
        raise ValueError("root missing from state")

    queues = expansion_queues(state)
    revealed = [root]
    used_expansions: list[dict[str, str]] = []
    requests = 0
    rounds = 0
    best = int(nodes[root]["outcome"]["quality_milli"])
    stalls = 0
    stop_reason = None
    unsupported: dict[str, Any] | None = None

    while True:
        if max_requests is not None and requests >= max_requests:
            stop_reason = "external_request_budget"
            break
        if rounds >= effective_round_cap:
            stop_reason = "max_rounds"
            break
        if rounds > 0 and stalls >= metadata["stall_rounds"]:
            stop_reason = "stall_rounds"
            break

        view = {
            "root_node_id": root,
            "revealed_nodes": [_row(nodes[node_id]) for node_id in revealed],
            "eligible_parent_ids": sorted(revealed),
        }
        call_parallelism=effective_parallelism
        if max_requests is not None:
            call_parallelism=min(call_parallelism,max_requests-requests)
        call=sandbox.execute(policy_path,view,call_parallelism,forbidden_tokens)
        if not call.get("accepted"):
            raise ValueError(f"policy selection rejected: {call}")
        if list(call["metadata"]) != metadata_raw:
            raise ValueError("policy metadata changed between isolated calls")
        selected=list(call["selected_parent_ids"])
        if len(selected) != len(set(selected)):
            raise ValueError("candidate policy selected duplicate parents")
        if len(selected) > call_parallelism:
            raise ValueError("candidate policy exceeded effective parallelism")
        allowed = set(revealed)
        if any(parent not in allowed for parent in selected):
            raise ValueError("candidate policy selected an unrevealed parent")
        if not selected:
            stop_reason = "policy_empty_batch"
            break

        missing = [parent for parent in selected if not queues.get(parent)]
        if missing:
            unsupported = {
                "round": rounds + 1,
                "requested_parent_ids": selected,
                "unsupported_parent_ids": missing,
            }
            stop_reason = "unsupported_historical_expansion"
            break

        before = best
        new_children = []
        for parent in selected:
            child = queues[parent].popleft()
            requests += 1
            new_children.append(child)
            used_expansions.append({"parent_node_id": parent, "child_node_id": child})
        rounds += 1

        for child in new_children:
            if child not in revealed:
                revealed.append(child)
            best = max(best, int(nodes[child]["outcome"]["quality_milli"]))
        stalls = 0 if best > before else stalls + 1

    return {
        "schema": REPLAY_SCHEMA,
        "replay_semantics": "recorded_realized_expansion_tape",
        "counterfactual_generation_claim": False,
        "task_id": state["task_id"],
        "policy_sha256": sha256_file(policy_path),
        "declared_policy_metadata": metadata,
        "effective_limits": {
            "max_requests": max_requests,
            "max_rounds": effective_round_cap,
            "max_parallelism": effective_parallelism,
        },
        "fully_supported": unsupported is None,
        "eligible_for_exact_comparison": unsupported is None,
        "stop_reason": stop_reason,
        "unsupported": unsupported,
        "best_quality_milli": best,
        "represented_requests": requests,
        "rounds": rounds,
        "revealed_node_ids": revealed,
        "used_expansions": used_expansions,
        "unused_recorded_expansions": {
            parent: list(children)
            for parent, children in sorted(queues.items())
            if children
        },
    }

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("policy", type=Path)
    ap.add_argument("states", type=Path, nargs="+")
    ap.add_argument("--forbidden-token-file", type=Path)
    ap.add_argument("--max-requests", type=int)
    ap.add_argument("--max-rounds", type=int)
    ap.add_argument("--max-parallelism", type=int)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    tokens=[] if args.forbidden_token_file is None else [
        x.strip() for x in args.forbidden_token_file.read_text().splitlines() if x.strip()
    ]

    results = [
        replay_state(
            json.loads(path.read_text()),
            args.policy,
            tokens,
            max_requests=args.max_requests,
            max_rounds=args.max_rounds,
            max_parallelism=args.max_parallelism,
        )
        for path in args.states
    ]
    payload = {
        "schema": "mira-genesis-rsi-v23-replay-batch-v1",
        "policy_sha256": sha256_file(args.policy),
        "all_fully_supported": all(row["fully_supported"] for row in results),
        "results": results,
    }
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.write_text(text, encoding="utf-8")
    print(text, end="")
    if not payload["all_fully_supported"]:
        raise SystemExit(3)

if __name__ == "__main__":
    main()
