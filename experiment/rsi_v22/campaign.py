#!/usr/bin/env python3
"""Deterministic V22 cross-stack campaign state and G1/G2 planner.

This module contains no task-specific evaluator logic. It adapts real code-repair
observations into the frozen V19 search-policy view and applies the policies
without human semantic labeling.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

SCHEMA = "mira-genesis-rsi-v22-campaign-state-v1"
ROOT_FAMILY = "defect-root"
PROPOSAL_FAMILY = "external-code-repair"
ROOT_MECHANISMS = ["seed-defect"]
PROPOSAL_MECHANISMS = ["source-patch"]

HERE = Path(__file__).resolve().parent
POLICIES = {
    "g1": HERE / "policies" / "g1_search_policy.py",
    "g2": HERE / "policies" / "g2_search_policy.py",
}
EXPECTED_POLICY_SHA256 = {
    "g1": "3354f887a93a08d9f00e9c54ccb097003f727ba77c1e1b4e9997adf676d35434",
    "g2": "69d0d725601cd32adff27379dbb25f5c7be29946f9e9c6ac4858a0634cbd5fdf",
}

def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def _load_policy(arm: str):
    path = POLICIES[arm]
    actual = sha256_file(path)
    expected = EXPECTED_POLICY_SHA256[arm]
    if actual != expected:
        raise ValueError(f"{arm} policy SHA-256 mismatch: {actual} != {expected}")
    spec = importlib.util.spec_from_file_location(f"v22_{arm}_policy", path)
    if spec is None or spec.loader is None:
        raise ValueError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    metadata = tuple(module.policy_metadata())
    if len(metadata) != 10 or any(not isinstance(x, int) for x in metadata):
        raise ValueError(f"invalid {arm} metadata")
    return module, metadata

def policy_metadata(arm: str) -> dict[str, int]:
    _, raw = _load_policy(arm)
    names = (
        "parent_quality", "parent_novelty", "depth", "profile_generation",
        "champion_parent", "recovery", "root_opening", "parallelism",
        "max_rounds", "stall_rounds",
    )
    return dict(zip(names, raw, strict=True))

def _action(task_id: str, source: str, root: bool) -> dict[str, Any]:
    return {
        "family": ROOT_FAMILY if root else PROPOSAL_FAMILY,
        "target_axes": [task_id],
        "mechanisms": ROOT_MECHANISMS if root else PROPOSAL_MECHANISMS,
        "changed_regions": [source],
    }

def init_state(*, task_id: str, allowed_source_path: str, root_tree_digest: str,
               root_source_sha256: str, root_node_id: str | None = None) -> dict[str, Any]:
    root = root_node_id or f"v22-{task_id}-root"
    node = {
        "node_id": root,
        "parent_node_id": None,
        "parent_tree_digest": None,
        "tree_digest": root_tree_digest,
        "source_sha256": root_source_sha256,
        "proposal_patch_sha256": None,
        "lineage_depth": 0,
        "action": _action(task_id, allowed_source_path, True),
        "outcome": {
            "quality_milli": 0,
            "evolver_profile_generation": 0,
            "ever_champion": True,
            "root_branch_node_id": root,
        },
    }
    arm = {
        "revealed_node_ids": [root],
        "rounds": 0,
        "represented_requests": 0,
        "consecutive_stalls": 0,
        "best_quality_milli": 0,
        "stopped": False,
        "stop_reason": None,
    }
    state = {
        "schema": SCHEMA,
        "task_id": task_id,
        "allowed_source_path": allowed_source_path,
        "root_node_id": root,
        "nodes": {root: node},
        "observations": [],
        "arms": {"g1": deepcopy(arm), "g2": deepcopy(arm)},
    }
    for name in ("g1", "g2"):
        plan = plan_next(state, name)
        if plan["selected_parent_ids"] != [root]:
            raise ValueError(f"initial {name} plan is not the single shared root: {plan}")
    return state

def _row(node: dict[str, Any]) -> dict[str, Any]:
    return {
        "node_id": node["node_id"],
        "lineage_depth": node["lineage_depth"],
        "action": deepcopy(node["action"]),
        "outcome": deepcopy(node["outcome"]),
    }

def policy_view(state: dict[str, Any], arm: str) -> dict[str, Any]:
    a = state["arms"][arm]
    revealed = [_row(state["nodes"][nid]) for nid in a["revealed_node_ids"]]
    eligible = sorted(a["revealed_node_ids"])
    return {
        "root_node_id": state["root_node_id"],
        "revealed_nodes": revealed,
        "eligible_parent_ids": eligible,
    }

def plan_next(state: dict[str, Any], arm: str) -> dict[str, Any]:
    if arm not in ("g1", "g2"):
        raise ValueError("arm must be g1 or g2")
    a = state["arms"][arm]
    meta = policy_metadata(arm)
    if a["stopped"]:
        return {"arm": arm, "selected_parent_ids": [], "stop_reason": a["stop_reason"]}
    if a["rounds"] >= meta["max_rounds"]:
        return {"arm": arm, "selected_parent_ids": [], "stop_reason": "max_rounds"}
    if a["rounds"] > 0 and a["consecutive_stalls"] >= meta["stall_rounds"]:
        return {"arm": arm, "selected_parent_ids": [], "stop_reason": "stall_rounds"}
    module, _ = _load_policy(arm)
    selected = list(module.select_parent_batch(policy_view(state, arm), meta["parallelism"]))
    allowed = set(a["revealed_node_ids"])
    if len(selected) != len(set(selected)):
        raise ValueError(f"{arm} selected duplicate parents")
    if any(node_id not in allowed for node_id in selected):
        raise ValueError(f"{arm} selected an unrevealed parent")
    if len(selected) > meta["parallelism"]:
        raise ValueError(f"{arm} exceeded frozen parallelism")
    return {
        "arm": arm,
        "round": a["rounds"] + 1,
        "selected_parent_ids": selected,
        "stop_reason": None if selected else "policy_empty_batch",
    }

def _root_branch(state: dict[str, Any], parent_node_id: str, child_node_id: str) -> str:
    if parent_node_id == state["root_node_id"]:
        return child_node_id
    return state["nodes"][parent_node_id]["outcome"]["root_branch_node_id"]

def proposal_node(*, state: dict[str, Any], parent_node_id: str, tree_digest: str,
                  source_sha256: str, proposal_patch_sha256: str, quality_milli: int) -> dict[str, Any]:
    if not 0 <= int(quality_milli) <= 1000:
        raise ValueError("quality_milli must be in [0, 1000]")
    parent = state["nodes"][parent_node_id]
    node_id = f"v22-{state['task_id']}-node-{tree_digest[:12]}"
    prior_best = max(int(n["outcome"]["quality_milli"]) for n in state["nodes"].values())
    return {
        "node_id": node_id,
        "parent_node_id": parent_node_id,
        "parent_tree_digest": parent["tree_digest"],
        "tree_digest": tree_digest,
        "source_sha256": source_sha256,
        "proposal_patch_sha256": proposal_patch_sha256,
        "lineage_depth": int(parent["lineage_depth"]) + 1,
        "action": _action(state["task_id"], state["allowed_source_path"], False),
        "outcome": {
            "quality_milli": int(quality_milli),
            "evolver_profile_generation": 0,
            "ever_champion": int(quality_milli) > prior_best,
            "root_branch_node_id": _root_branch(state, parent_node_id, node_id),
        },
    }

def record_round(state: dict[str, Any], *, arm: str, parent_results: list[dict[str, Any]]) -> dict[str, Any]:
    target_arms = ("g1", "g2") if arm == "shared" else (arm,)
    if arm == "shared":
        if any(state["arms"][x]["rounds"] != 0 for x in target_arms):
            raise ValueError("shared round is allowed only at R1")
        p1 = plan_next(state, "g1")["selected_parent_ids"]
        p2 = plan_next(state, "g2")["selected_parent_ids"]
        expected = p1
        if p1 != p2:
            raise ValueError("R1 policies do not agree")
    else:
        expected = plan_next(state, arm)["selected_parent_ids"]
    supplied = [row["parent_node_id"] for row in parent_results]
    if supplied != expected:
        raise ValueError(f"round parents {supplied} do not match frozen plan {expected}")
    if not expected:
        raise ValueError("cannot record an empty stopped round")

    new_ids: list[str] = []
    for row in parent_results:
        node = proposal_node(state=state, **row)
        existing = state["nodes"].get(node["node_id"])
        if existing is not None:
            stable = (existing["tree_digest"], existing["source_sha256"], existing["outcome"]["quality_milli"])
            incoming = (node["tree_digest"], node["source_sha256"], node["outcome"]["quality_milli"])
            if stable != incoming:
                raise ValueError("content-addressed node collision with different evidence")
        else:
            state["nodes"][node["node_id"]] = node
        new_ids.append(node["node_id"])

    for target in target_arms:
        a = state["arms"][target]
        before = int(a["best_quality_milli"])
        for nid in new_ids:
            if nid not in a["revealed_node_ids"]:
                a["revealed_node_ids"].append(nid)
        a["rounds"] += 1
        a["represented_requests"] += len(parent_results)
        after = max(int(state["nodes"][nid]["outcome"]["quality_milli"]) for nid in a["revealed_node_ids"])
        a["best_quality_milli"] = after
        a["consecutive_stalls"] = 0 if after > before else a["consecutive_stalls"] + 1

    state["observations"].append({
        "arm": arm,
        "round": state["arms"][target_arms[0]]["rounds"],
        "parent_node_ids": supplied,
        "result_node_ids": new_ids,
    })
    refresh_stops(state)
    return state

def refresh_stops(state: dict[str, Any]) -> None:
    for arm in ("g1", "g2"):
        a = state["arms"][arm]
        if a["stopped"]:
            continue
        plan = plan_next(state, arm)
        if not plan["selected_parent_ids"]:
            a["stopped"] = True
            a["stop_reason"] = plan["stop_reason"]

def summary(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "task_id": state["task_id"],
        "g1": {**state["arms"]["g1"], "next": plan_next(state, "g1")["selected_parent_ids"]},
        "g2": {**state["arms"]["g2"], "next": plan_next(state, "g2")["selected_parent_ids"]},
    }

def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("summary")
    p.add_argument("state", type=Path)
    args = ap.parse_args()
    if args.cmd == "summary":
        state = json.loads(args.state.read_text())
        print(json.dumps(summary(state), indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
