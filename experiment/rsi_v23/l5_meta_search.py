#!/usr/bin/env python3
"""Deterministic V23 L5 meta-search over the frozen G2 descendant family.

Four controllers search the same candidate tree:
A: exact G2, B: exact G1, C: exact G2 with only its L4-validated
strong-result early-stop rule removed, D: fixed lexicographic breadth-first.

This module is apparatus only until the V23 L5 freeze record is committed.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
from pathlib import Path
from typing import Any, Mapping

HERE = Path(__file__).resolve().parent
V22 = HERE.parent / "rsi_v22"
FAMILY_PATH = HERE / "l5_policy_family.py"
DEV_PATH = HERE / "l5_meta_development.py"
SANDBOX_PATH = HERE / "sandbox_policy.py"

META_REQUEST_BUDGET = 9
META_ROUND_BUDGET = 8
META_MAX_PARALLELISM = 2
META_MUTATION_DEPTH = 2


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


family = _load("v23_l5_family_search", FAMILY_PATH)
dev = _load("v23_l5_dev_search", DEV_PATH)
sandbox = _load("v23_l5_sandbox_search", SANDBOX_PATH)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def g2_ablation_source() -> str:
    src = family.root_source()
    block = "    if best >= 780:\n        return []\n\n"
    if src.count(block) != 1:
        raise RuntimeError("G2 early-stop block changed")
    return src.replace(block, "")


def controller_source(arm: str) -> str | None:
    if arm == "g2_meta":
        return (V22 / "policies" / "g2_search_policy.py").read_text(encoding="utf-8")
    if arm == "g1_meta":
        return (V22 / "policies" / "g1_search_policy.py").read_text(encoding="utf-8")
    if arm == "g2_ablation":
        return g2_ablation_source()
    if arm == "no_meta":
        return None
    raise ValueError("unknown L5 meta-search arm")


def _node(
    node_id: str,
    parent_id: str | None,
    *,
    candidate: Mapping[str, Any],
    lineage_depth: int,
    mutation_axis: str,
    ever_champion: bool,
    root_branch: str,
) -> dict[str, Any]:
    return {
        "node_id": node_id,
        "parent_node_id": parent_id,
        "candidate": dict(candidate),
        "lineage_depth": int(lineage_depth),
        "action": {
            "family": "search-policy-descendant",
            "target_axes": ["meta-development-process-utility"],
            "mechanisms": [mutation_axis],
            "changed_regions": ["search_policy"],
        },
        "outcome": {
            "quality_milli": int(candidate["quality_milli"]),
            "evolver_profile_generation": int(candidate["mutation_depth"]),
            "ever_champion": bool(ever_champion),
            "root_branch_node_id": root_branch,
        },
    }


def _candidate_index() -> dict[str, dict[str, Any]]:
    return {row["params_digest"]: row for row in dev.evaluate_universe()}


def _children_for(
    node: Mapping[str, Any],
    index: Mapping[str, dict[str, Any]],
) -> tuple[dict[str, Any], ...]:
    depth = int(node["candidate"]["mutation_depth"])
    if depth >= META_MUTATION_DEPTH:
        return ()
    rows = []
    for mutation in family.neighbors(node["candidate"]["params"]):
        child = index.get(mutation["params_digest"])
        if child is None:
            continue
        if int(child["mutation_depth"]) != depth + 1:
            continue
        rows.append({**mutation, "candidate": child})
    rows.sort(key=lambda row: (row["axis"], row["to"], row["candidate"]["params_digest"]))
    return tuple(rows)


def _view(
    nodes: Mapping[str, dict[str, Any]],
    revealed: list[str],
    cursors: Mapping[str, int],
    index: Mapping[str, dict[str, Any]],
) -> dict[str, Any]:
    eligible = []
    for node_id in revealed:
        children = _children_for(nodes[node_id], index)
        if cursors.get(node_id, 0) < len(children):
            eligible.append(node_id)
    return {
        "root_node_id": "g2-root",
        "revealed_nodes": [
            {
                "node_id": node_id,
                "lineage_depth": nodes[node_id]["lineage_depth"],
                "action": nodes[node_id]["action"],
                "outcome": nodes[node_id]["outcome"],
            }
            for node_id in revealed
        ],
        "eligible_parent_ids": sorted(eligible),
    }


def _selected_successor(nodes: Mapping[str, dict[str, Any]], revealed: list[str]) -> dict[str, Any]:
    candidates = []
    for node_id in revealed:
        row = nodes[node_id]
        candidates.append(
            (
                tuple(row["candidate"]["development_utility"]),
                str(row["candidate"]["source_sha256"]),
                node_id,
            )
        )
    candidates.sort(key=lambda item: (item[0], item[1]))
    _, _, node_id = candidates[-1]
    return {
        "node_id": node_id,
        "candidate": dict(nodes[node_id]["candidate"]),
    }


def run_arm(arm: str) -> dict[str, Any]:
    index = _candidate_index()
    root_candidate = index[family.params_digest(family.ROOT_PARAMS)]
    root = _node(
        "g2-root",
        None,
        candidate=root_candidate,
        lineage_depth=0,
        mutation_axis="seed-g2",
        ever_champion=True,
        root_branch="g2-root",
    )
    nodes: dict[str, dict[str, Any]] = {"g2-root": root}
    revealed = ["g2-root"]
    cursors: dict[str, int] = {}
    requests = 0
    rounds = 0
    stalls = 0
    best_quality = int(root_candidate["quality_milli"])
    stop_reason = None

    source = controller_source(arm)
    with tempfile.TemporaryDirectory(prefix="v23-l5-meta-controller-") as td:
        policy_path = None
        metadata = None
        if source is not None:
            policy_path = Path(td) / f"{arm}.py"
            policy_path.write_text(source, encoding="utf-8")
            meta = sandbox.metadata(policy_path, [])
            if not meta.get("accepted"):
                raise RuntimeError(f"{arm} controller rejected: {meta}")
            metadata = list(meta["metadata"])

        while requests < META_REQUEST_BUDGET and rounds < META_ROUND_BUDGET:
            view = _view(nodes, revealed, cursors, index)
            eligible = list(view["eligible_parent_ids"])
            if not eligible:
                stop_reason = "candidate_family_exhausted"
                break

            if arm == "no_meta":
                parents = [eligible[0]]
            else:
                assert policy_path is not None and metadata is not None
                policy_max_rounds = int(metadata[8])
                policy_stall_rounds = int(metadata[9])
                policy_parallelism = int(metadata[7])
                if rounds >= policy_max_rounds:
                    stop_reason = "policy_max_rounds"
                    break
                if rounds > 0 and stalls >= policy_stall_rounds:
                    stop_reason = "policy_stall_rounds"
                    break
                cap = min(
                    META_MAX_PARALLELISM,
                    policy_parallelism,
                    META_REQUEST_BUDGET - requests,
                )
                selected = sandbox.execute(policy_path, view, cap, [])
                if not selected.get("accepted"):
                    raise RuntimeError(f"{arm} controller failed: {selected}")
                parents = list(selected["selected_parent_ids"])
                if not parents:
                    stop_reason = "policy_empty_batch"
                    break

            before = best_quality
            for parent_id in parents:
                parent = nodes[parent_id]
                children = _children_for(parent, index)
                child_index = cursors.get(parent_id, 0)
                if child_index >= len(children):
                    raise RuntimeError("controller selected non-expandable parent")
                expansion = children[child_index]
                cursors[parent_id] = child_index + 1
                candidate = expansion["candidate"]
                node_id = "m-" + hashlib.sha256(
                    f"{parent_id}|{expansion['params_digest']}|{child_index}".encode()
                ).hexdigest()[:16]
                prior_best = max(int(nodes[x]["outcome"]["quality_milli"]) for x in revealed)
                root_branch = node_id if parent_id == "g2-root" else parent["outcome"]["root_branch_node_id"]
                nodes[node_id] = _node(
                    node_id,
                    parent_id,
                    candidate=candidate,
                    lineage_depth=int(parent["lineage_depth"]) + 1,
                    mutation_axis=str(expansion["axis"]),
                    ever_champion=int(candidate["quality_milli"]) > prior_best,
                    root_branch=root_branch,
                )
                revealed.append(node_id)
                best_quality = max(best_quality, int(candidate["quality_milli"]))
                requests += 1
            rounds += 1
            stalls = 0 if best_quality > before else stalls + 1

        if stop_reason is None:
            if requests >= META_REQUEST_BUDGET:
                stop_reason = "external_request_budget"
            elif rounds >= META_ROUND_BUDGET:
                stop_reason = "external_round_budget"
            else:
                stop_reason = "stopped"

    selected = _selected_successor(nodes, revealed)
    root_utility = tuple(root_candidate["development_utility"])
    selected_utility = tuple(selected["candidate"]["development_utility"])
    result = {
        "schema": "mira-genesis-rsi-v23-l5-meta-arm-v1",
        "arm": arm,
        "controller_sha256": None if source is None else _sha(source),
        "represented_requests": requests,
        "rounds": rounds,
        "stop_reason": stop_reason,
        "revealed_node_ids": revealed,
        "selected_successor": selected,
        "root_g2_development_utility": root_utility,
        "successor_development_utility": selected_utility,
        "successor_strictly_better_than_g2_on_development": selected_utility > root_utility,
        "meta_process_utility": (*selected_utility, -requests, -rounds),
    }
    return result


def run_all() -> dict[str, Any]:
    arms = {arm: run_arm(arm) for arm in ("g2_meta", "g1_meta", "g2_ablation", "no_meta")}
    a = arms["g2_meta"]
    b = arms["g1_meta"]
    c = arms["g2_ablation"]
    return {
        "schema": "mira-genesis-rsi-v23-l5-meta-search-v1",
        "budgets": {
            "represented_requests_per_arm": META_REQUEST_BUDGET,
            "rounds_per_arm": META_ROUND_BUDGET,
            "max_parallelism": META_MAX_PARALLELISM,
            "mutation_depth": META_MUTATION_DEPTH,
        },
        "arms": arms,
        "pre_holdout_facts": {
            "g2_meta_found_development_improvement": bool(
                a["successor_strictly_better_than_g2_on_development"]
            ),
            "g2_meta_process_beats_g1_meta": tuple(a["meta_process_utility"]) > tuple(b["meta_process_utility"]),
            "g2_ablation_selects_same_successor": (
                a["selected_successor"]["candidate"]["source_sha256"]
                == c["selected_successor"]["candidate"]["source_sha256"]
            ),
            "g2_ablation_meta_process_equal": tuple(a["meta_process_utility"]) == tuple(c["meta_process_utility"]),
        },
    }


def main() -> None:
    print(json.dumps(run_all(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
