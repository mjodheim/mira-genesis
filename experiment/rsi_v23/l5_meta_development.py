#!/usr/bin/env python3
"""Frozen public meta-development landscapes and candidate evaluator for V23 L5.

These landscapes are synthetic and public. They are not the decisive L5
holdout. Their only role is to provide a deterministic development signal for
search-policy descendants before any real cross-stack holdout is exposed.
"""
from __future__ import annotations

import importlib.util
import itertools
import json
import tempfile
from pathlib import Path
from typing import Any, Mapping

HERE = Path(__file__).resolve().parent
FAMILY_PATH = HERE / "l5_policy_family.py"
SANDBOX_PATH = HERE / "sandbox_policy.py"

EXTERNAL_MAX_REQUESTS = 6
EXTERNAL_MAX_ROUNDS = 6
EXTERNAL_MAX_PARALLELISM = 2
META_MUTATION_DEPTH = 2


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


family = _load("v23_l5_family", FAMILY_PATH)
sandbox = _load("v23_l5_sandbox", SANDBOX_PATH)


def development_episodes() -> tuple[dict[str, Any], ...]:
    rows = []
    for q1, gain_location, profile_generation in itertools.product(
        (650, 730, 810), ("deep", "root"), (0, 1)
    ):
        episode_id = f"q{q1}-{gain_location}-p{profile_generation}"
        if gain_location == "root":
            root_children = (q1, 1000, 900)
            deep_children = (600, 650)
        else:
            root_children = (q1, 620, 700)
            deep_children = (720, 1000)
        rows.append(
            {
                "episode_id": episode_id,
                "q1": q1,
                "gain_location": gain_location,
                "profile_generation": profile_generation,
                "root_children": root_children,
                "deep_children": deep_children,
            }
        )
    rows.sort(key=lambda item: item["episode_id"])
    return tuple(rows)


def _node(
    node_id: str,
    parent_id: str | None,
    *,
    quality: int,
    depth: int,
    profile_generation: int,
    ever_champion: bool,
    root_branch: str,
    mechanism: str,
) -> dict[str, Any]:
    return {
        "node_id": node_id,
        "parent_node_id": parent_id,
        "lineage_depth": depth,
        "action": {
            "family": "v23-meta-development",
            "target_axes": ["search_efficiency"],
            "mechanisms": [mechanism],
            "changed_regions": ["search_policy"],
        },
        "outcome": {
            "quality_milli": int(quality),
            "evolver_profile_generation": int(profile_generation),
            "ever_champion": bool(ever_champion),
            "root_branch_node_id": root_branch,
        },
    }


def _episode_tree(spec: Mapping[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    root = "root"
    nodes = {
        root: _node(
            root,
            None,
            quality=0,
            depth=0,
            profile_generation=0,
            ever_champion=True,
            root_branch=root,
            mechanism="root",
        )
    }
    root_children = []
    for index, quality in enumerate(spec["root_children"], 1):
        node_id = f"r{index}"
        root_children.append(
            {
                "node_id": node_id,
                "quality": int(quality),
                "profile_generation": int(spec["profile_generation"]) if index == 1 else 0,
            }
        )
    expansions: dict[str, list[dict[str, Any]]] = {root: root_children}

    q_deep1, q_deep2 = spec["deep_children"]
    expansions["r1"] = [{"node_id": "d1", "quality": int(q_deep1), "profile_generation": 0}]
    expansions["d1"] = [{"node_id": "d2", "quality": int(q_deep2), "profile_generation": 0}]
    return nodes, expansions


def _view(nodes: Mapping[str, dict[str, Any]], revealed: list[str], expansions: Mapping[str, list[dict[str, Any]]], cursors: Mapping[str, int]) -> dict[str, Any]:
    eligible = sorted(
        node_id
        for node_id in revealed
        if cursors.get(node_id, 0) < len(expansions.get(node_id, []))
    )
    rows = []
    for node_id in revealed:
        node = nodes[node_id]
        rows.append(
            {
                "node_id": node_id,
                "lineage_depth": node["lineage_depth"],
                "action": node["action"],
                "outcome": node["outcome"],
            }
        )
    return {
        "root_node_id": "root",
        "revealed_nodes": rows,
        "eligible_parent_ids": eligible,
    }


def run_episode(source: str, spec: Mapping[str, Any]) -> dict[str, Any]:
    nodes, expansions = _episode_tree(spec)
    revealed = ["root"]
    cursors: dict[str, int] = {}
    requests = 0
    rounds = 0
    stalls = 0
    best = 0

    with tempfile.TemporaryDirectory(prefix="v23-l5-policy-") as td:
        policy_path = Path(td) / "candidate.py"
        policy_path.write_text(source, encoding="utf-8")
        metadata = sandbox.metadata(policy_path, [])
        if not metadata.get("accepted"):
            return {
                "accepted": False,
                "episode_id": spec["episode_id"],
                "best_quality_milli": 0,
                "represented_requests": 0,
                "rounds": 0,
                "solved": False,
                "error": metadata,
            }
        raw_meta = list(metadata["metadata"])
        policy_parallelism = int(raw_meta[7])
        policy_max_rounds = int(raw_meta[8])
        policy_stall_rounds = int(raw_meta[9])

        while requests < EXTERNAL_MAX_REQUESTS and rounds < min(EXTERNAL_MAX_ROUNDS, policy_max_rounds):
            if rounds > 0 and stalls >= policy_stall_rounds:
                break
            view = _view(nodes, revealed, expansions, cursors)
            if not view["eligible_parent_ids"]:
                break
            max_parallelism = min(
                EXTERNAL_MAX_PARALLELISM,
                policy_parallelism,
                EXTERNAL_MAX_REQUESTS - requests,
            )
            selected = sandbox.execute(policy_path, view, max_parallelism, [])
            if not selected.get("accepted"):
                return {
                    "accepted": False,
                    "episode_id": spec["episode_id"],
                    "best_quality_milli": best,
                    "represented_requests": requests,
                    "rounds": rounds,
                    "solved": best == 1000,
                    "error": selected,
                }
            parents = list(selected["selected_parent_ids"])
            if not parents:
                break
            before = best
            for parent_id in parents:
                index = cursors.get(parent_id, 0)
                queue = expansions.get(parent_id, [])
                if index >= len(queue):
                    raise RuntimeError("policy selected a parent outside eligible expansion set")
                child = dict(queue[index])
                cursors[parent_id] = index + 1
                parent = nodes[parent_id]
                node_id = child["node_id"]
                quality = int(child["quality"])
                prior_best = max(int(nodes[x]["outcome"]["quality_milli"]) for x in revealed)
                root_branch = node_id if parent_id == "root" else parent["outcome"]["root_branch_node_id"]
                nodes[node_id] = _node(
                    node_id,
                    parent_id,
                    quality=quality,
                    depth=int(parent["lineage_depth"]) + 1,
                    profile_generation=int(child["profile_generation"]),
                    ever_champion=quality > prior_best,
                    root_branch=root_branch,
                    mechanism="synthetic-expansion",
                )
                if node_id not in revealed:
                    revealed.append(node_id)
                best = max(best, quality)
                requests += 1
            rounds += 1
            stalls = 0 if best > before else stalls + 1

    return {
        "accepted": True,
        "episode_id": spec["episode_id"],
        "best_quality_milli": best,
        "represented_requests": requests,
        "rounds": rounds,
        "solved": best == 1000,
    }


def development_utility(source: str) -> tuple[tuple[int, ...], tuple[dict[str, Any], ...]]:
    results = tuple(run_episode(source, spec) for spec in development_episodes())
    if not all(row["accepted"] for row in results):
        return ((-1, -1, -1, 0, 0), results)
    solved = sum(int(row["solved"]) for row in results)
    accepted = sum(int(row["accepted"]) for row in results)
    quality = sum(int(row["best_quality_milli"]) for row in results)
    requests = sum(int(row["represented_requests"]) for row in results)
    rounds = sum(int(row["rounds"]) for row in results)
    return ((solved, accepted, quality, -requests, -rounds), results)


def evaluate_universe() -> tuple[dict[str, Any], ...]:
    records = []
    for item in family.universe(META_MUTATION_DEPTH):
        source = family.render_source(item["params"])
        utility, episodes = development_utility(source)
        records.append({**item, "development_utility": utility, "episodes": episodes})

    tiers = sorted({tuple(row["development_utility"]) for row in records})
    denom = max(1, len(tiers) - 1)
    tier_quality = {
        utility: (1000 if len(tiers) == 1 else (1000 * index) // denom)
        for index, utility in enumerate(tiers)
    }
    for row in records:
        row["quality_milli"] = tier_quality[tuple(row["development_utility"])]
    records.sort(key=lambda row: row["params_digest"])
    return tuple(records)


def main() -> None:
    payload = {
        "schema": "mira-genesis-rsi-v23-l5-meta-development-v1",
        "episodes": development_episodes(),
        "universe": evaluate_universe(),
    }
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
