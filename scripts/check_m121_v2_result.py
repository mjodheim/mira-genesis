#!/usr/bin/env python3
"""Independent checker for an M121/H66 v2 campaign record.

The checker reimplements the schedule generator from the frozen design contract rather than
importing the apparatus one, so a generator defect cannot validate itself. It then reruns every arm
and classifies the attempt in the order the design candidate fixes: ``instrument_abort`` first,
then ``negative``, and only otherwise ``positive`` within the stated bounded claim.

A ``positive`` classification here is not evidence for H66 and does not move G7. On a DEVELOPMENT
record it means only that the apparatus dissociates as designed on a fixture salt.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from metamorphosis.evaluation_cost import verify_cost_record  # noqa: E402
from metamorphosis.m121_long_horizon_v2 import (  # noqa: E402
    ACTIVE_RECORDS,
    ARMS,
    DEFERRED_SLOTS,
    DEVELOPMENT_SALT,
    FAULT_CLASSES,
    FAULT_SUBTYPES,
    QUARTILES,
    SCHEDULE_DOMAIN,
    eligible_episodes,
    run_arm,
)

EXPECTED_FAULTS_PER_CLASS = 4


def _independent_schedule(salt: bytes, horizon: int) -> list[dict[str, Any]]:
    """Reimplementation of the frozen generator, written from the design contract.

    Collision resolution, subtype ordering and target ordering are fixed lexicographically here as
    well; if the apparatus and this function disagree the attempt is an instrument abort.
    """
    faults: list[dict[str, Any]] = []
    used_episodes: set[int] = set()
    used_targets: dict[str, set[int]] = {name: set() for name in FAULT_CLASSES}
    for quartile in QUARTILES:
        window = eligible_episodes(horizon, quartile)
        for class_index, fault_class in enumerate(FAULT_CLASSES):
            span = ACTIVE_RECORDS if fault_class == "operational" else DEFERRED_SLOTS
            counter = 0
            while True:
                digest = hashlib.sha256(
                    SCHEDULE_DOMAIN
                    + salt
                    + horizon.to_bytes(4, "big")
                    + bytes([class_index])
                    + quartile.to_bytes(4, "big")
                    + counter.to_bytes(4, "big")
                ).digest()
                episode = window[int.from_bytes(digest[:8], "big") % len(window)]
                target = digest[9] % span
                if episode in used_episodes or target in used_targets[fault_class]:
                    counter += 1
                    if counter > 1024:
                        raise RuntimeError("independent generator exhausted")
                    continue
                used_episodes.add(episode)
                used_targets[fault_class].add(target)
                faults.append(
                    {
                        "episode": episode,
                        "fault_class": fault_class,
                        "quartile": quartile,
                        "subtype": FAULT_SUBTYPES[fault_class][
                            digest[8] % len(FAULT_SUBTYPES[fault_class])
                        ],
                        "target": target,
                        "counter": counter,
                        "fault_id": "%s:q%d" % (fault_class, quartile),
                    }
                )
                break
    faults.sort(key=lambda row: (row["episode"], row["fault_class"]))
    return faults


def instrument_aborts(record: Mapping[str, Any], salt: bytes) -> list[str]:
    problems: list[str] = []
    campaign = record["campaign"]
    for key, horizon_record in sorted(campaign["horizons"].items()):
        horizon = int(horizon_record["horizon"])
        schedule = horizon_record["schedule"]
        expected = _independent_schedule(salt, horizon)
        if schedule["faults"] != expected:
            problems.append("H%d: schedule does not regenerate identically" % horizon)
        counts = {name: 0 for name in FAULT_CLASSES}
        for row in schedule["faults"]:
            counts[row["fault_class"]] = counts.get(row["fault_class"], 0) + 1
        for name, count in sorted(counts.items()):
            if count != EXPECTED_FAULTS_PER_CLASS:
                problems.append("H%d: %s fault budget is %d" % (horizon, name, count))
        for arm in ARMS:
            observed = horizon_record["arms"][arm]
            if observed["schedule_sha256"] != schedule["schedule_sha256"]:
                problems.append("H%d: arm %s ran a different schedule" % (horizon, arm))
            replayed = run_arm(arm, schedule)
            if replayed != observed:
                problems.append("H%d: arm %s does not replay identically" % (horizon, arm))
            for counter in ("model_calls", "network_calls", "remote_executions"):
                if observed.get(counter) != 0:
                    problems.append("H%d: arm %s reports nonzero %s" % (horizon, arm, counter))
        if horizon_record["arms"]["idle_floor"]["completed_work_items"] != 0:
            problems.append("H%d: the idle floor completed work" % horizon)
    problems.extend(_cost_problems(record))
    return problems


def _recomputed_deterministic_costs(campaign: Mapping[str, Any]) -> dict[str, int]:
    """Reimplementation of the runner's cost derivation, from the campaign rather than the record.

    Importing the runner's version would let one arithmetic mistake agree with itself, which is the
    defect this checker exists to avoid.
    """
    horizons = list(campaign["horizons"].values())
    work = 0
    evaluations = 0
    episodes = 0
    faults = 0
    for horizon_record in horizons:
        arms = horizon_record["arms"]
        evaluations += len(arms)
        episodes += int(horizon_record["horizon"]) * len(arms)
        faults += len(horizon_record["schedule"]["faults"])
        for arm in arms.values():
            work += int(arm["completed_work_items"])
    return {
        "budget_units_spent": faults,
        "candidate_evaluations": evaluations,
        "completion_tokens": 0,
        "episodes": episodes,
        "model_calls": 0,
        "network_requests": 0,
        "prompt_tokens": 0,
        "work_items": work,
    }


def _cost_problems(record: Mapping[str, Any]) -> list[str]:
    cost = record.get("cost")
    if not isinstance(cost, Mapping):
        return ["the record carries no G9 cost record"]
    return [
        "cost: %s" % problem
        for problem in verify_cost_record(
            cost, recomputed_deterministic=_recomputed_deterministic_costs(record["campaign"])
        )
    ]


def negative_conditions(record: Mapping[str, Any]) -> list[str]:
    problems: list[str] = []
    for key, horizon_record in sorted(record["campaign"]["horizons"].items()):
        horizon = int(horizon_record["horizon"])
        full = horizon_record["arms"]["full"]
        no_monitor = horizon_record["arms"]["no_constraint_monitor"]
        no_checkpoint = horizon_record["arms"]["no_checkpoint"]

        def note(condition: bool, message: str) -> None:
            if condition:
                problems.append("H%d: %s" % (horizon, message))

        note(
            full["operational_detections_before_harm"] != EXPECTED_FAULTS_PER_CLASS,
            "full did not detect every operational fault before harm",
        )
        note(
            no_monitor["operational_detections_before_harm"] != EXPECTED_FAULTS_PER_CLASS,
            "the monitor ablation lost operational detection, so it is not a positive control",
        )
        note(
            full["operational_detections_before_harm"]
            != no_monitor["operational_detections_before_harm"],
            "monitor removal changed operational pre-harm detection",
        )
        note(
            full["quiescent_detections_before_harm"]
            <= no_monitor["quiescent_detections_before_harm"],
            "full did not detect strictly more quiescent faults than the monitor ablation",
        )
        note(full["residual_corruption"] != 0, "full ended with residual corruption")
        note(
            full["silent_divergent_outputs"] != 0,
            "full recorded a silent divergent output",
        )
        note(
            no_checkpoint["recovery_successes"] != 0,
            "the checkpoint ablation retained restoration",
        )
        note(
            no_checkpoint["residual_corruption"] == 0,
            "the checkpoint ablation lost no repair capability",
        )
        note(
            no_checkpoint["operational_detections_before_harm"]
            != full["operational_detections_before_harm"]
            or no_checkpoint["quiescent_detections_before_harm"]
            != full["quiescent_detections_before_harm"],
            "checkpoint removal changed pre-harm detection counts",
        )
    return problems


def classify(record: Mapping[str, Any], salt: bytes) -> dict[str, Any]:
    aborts = instrument_aborts(record, salt)
    if aborts:
        return {"verdict": "instrument_abort", "problems": aborts}
    negatives = negative_conditions(record)
    if negatives:
        return {"verdict": "negative", "problems": negatives}
    return {"verdict": "positive", "problems": []}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("record", type=Path, help="path to an M121 v2 campaign record")
    arguments = parser.parse_args()
    record = json.loads(arguments.record.read_text(encoding="utf-8"))
    if record.get("canonical"):
        print("REFUSED: this checker is not authorized to score a canonical M121 attempt")
        return 2
    outcome = classify(record, DEVELOPMENT_SALT)
    outcome.update(
        {
            "scored_record": str(arguments.record),
            "is_evidence_for_h66": False,
            "advances_a_generality_gate": False,
        }
    )
    print(json.dumps(outcome, indent=2, sort_keys=True))
    return 0 if outcome["verdict"] == "positive" else 1


if __name__ == "__main__":
    raise SystemExit(main())
