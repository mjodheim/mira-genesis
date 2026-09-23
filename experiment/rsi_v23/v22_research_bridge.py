#!/usr/bin/env python3
"""Prospective V22 -> recursive-research aggregate bridge for V23 development.

This adapter consumes only the final public/machine-readable V22 adjudication record.
It never reads task source, proposer transcripts, reserved evaluator source or evaluator logs.
The semantic mapping is fixed before V22 adjudication so a later result cannot be manually
relabelled into a more favorable research-memory event.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from genesis import recursive_research_strategy as research

SCHEMA = "mira-genesis-rsi-v23-v22-research-bridge-v1"
FAMILY = "real-project-search-policy-transfer"
TARGET_AXES = (
    "repair_best_quality",
    "represented_request_efficiency",
    "round_efficiency",
)
MECHANISMS = (
    "parent_selection",
    "continuation_and_stopping",
)
CHANGED_REGIONS = ("search_policy",)
G1_POLICY_SHA256 = "3354f887a93a08d9f00e9c54ccb097003f727ba77c1e1b4e9997adf676d35434"
G2_POLICY_SHA256 = "69d0d725601cd32adff27379dbb25f5c7be29946f9e9c6ac4858a0634cbd5fdf"


class BridgeError(RuntimeError):
    pass


def _digest(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()


def _int(row: dict[str, Any], key: str) -> int:
    value = row.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise BridgeError(f"{key} must be an integer")
    return value


def bridge(adjudication: dict[str, Any]) -> dict[str, Any]:
    if adjudication.get("schema") != "mira-genesis-rsi-v22-final-adjudication-v1":
        raise BridgeError("unexpected V22 adjudication schema")
    tasks = adjudication.get("tasks")
    if not isinstance(tasks, list) or len(tasks) != 3:
        raise BridgeError("V22 bridge requires exactly three task rows")
    task_ids = [str(row.get("task_id") or "") for row in tasks if isinstance(row, dict)]
    if len(task_ids) != 3 or any(not x for x in task_ids) or len(set(task_ids)) != 3:
        raise BridgeError("V22 task identities are missing or duplicated")

    events = []
    for attempt, row in enumerate(sorted(tasks, key=lambda item: str(item["task_id"])), 1):
        g1q = _int(row, "g1_best_quality_milli")
        g2q = _int(row, "g2_best_quality_milli")
        g1r = _int(row, "g1_requests")
        g2r = _int(row, "g2_requests")
        g1round = _int(row, "g1_rounds")
        g2round = _int(row, "g2_rounds")
        process_win = row.get("g2_strictly_better")
        if type(process_win) is not bool:
            raise BridgeError("g2_strictly_better must be boolean")

        deltas = {
            "repair_best_quality": g2q - g1q,
            "represented_request_efficiency": g1r - g2r,
            "round_efficiency": g1round - g2round,
        }
        improvements = []
        regressions = []
        if process_win:
            improvements.append("g2_strict_process_utility_win")
        if g2q < g1q:
            regressions.append("g2_lower_best_quality")
        if g2r > g1r:
            regressions.append("g2_more_represented_requests")
        if g2round > g1round:
            regressions.append("g2_more_rounds")

        source_digest = _digest(
            {
                "task_id": row["task_id"],
                "g1_best_quality_milli": g1q,
                "g2_best_quality_milli": g2q,
                "g1_requests": g1r,
                "g2_requests": g2r,
                "g1_rounds": g1round,
                "g2_rounds": g2round,
                "g2_strictly_better": process_win,
            }
        )
        outcome = research.create_outcome(
            attempt=attempt,
            family=FAMILY,
            target_axes=TARGET_AXES,
            mechanisms=MECHANISMS,
            changed_regions=CHANGED_REGIONS,
            hard_pass=g2q == 1000,
            capability_deltas=deltas,
            improvements=improvements,
            regressions=regressions,
            parent_kind="champion",
            parent_lineage_depth=0,
            parent_digest=G1_POLICY_SHA256,
            child_digest=G2_POLICY_SHA256,
            source_digest=source_digest,
        )
        events.append({"task_id": str(row["task_id"]), "outcome": outcome})

    summary = {
        "schema": SCHEMA,
        "source_adjudication_digest": _digest(adjudication),
        "family": FAMILY,
        "mapping_version": 1,
        "events": events,
        "v22_positive": adjudication.get("v22_positive"),
    }
    if type(summary["v22_positive"]) is not bool:
        raise BridgeError("v22_positive must be boolean")
    summary["bridge_digest"] = _digest(summary)
    return summary


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("adjudication", type=Path)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    result = bridge(json.loads(args.adjudication.read_text(encoding="utf-8")))
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.write_text(text, encoding="utf-8")
    print(text, end="")


if __name__ == "__main__":
    main()
