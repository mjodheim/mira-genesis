#!/usr/bin/env python3
"""Verify the committed M071 result and its memory-ledger/external evidence."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from check_m071_execution_protocol import verify_protocol


ROOT = Path(__file__).resolve().parents[1]
M071 = ROOT / "experiments" / "M071"


def _canonical_digest(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _verify_memory(filename: str, expected: str) -> None:
    memory = json.loads((M071 / filename).read_text(encoding="utf-8"))
    previous = "0" * 64
    for index, event in enumerate(memory["events"]):
        if event["index"] != index or event["previous_digest"] != previous:
            raise ValueError(f"broken M071 memory chain in {filename}")
        material = {
            "index": index,
            "kind": event["kind"],
            "payload": event["payload"],
            "previous": previous,
        }
        encoded = json.dumps(material, sort_keys=True, separators=(",", ":")).encode()
        observed = hashlib.sha256(b"mira-memory-event-v1\0" + encoded).hexdigest()
        if event["digest"] != observed:
            raise ValueError(f"invalid M071 memory event in {filename}")
        previous = event["digest"]
    if memory["head_digest"] != previous or previous != expected:
        raise ValueError(f"M071 memory head mismatch in {filename}")


def _verify_external_artifacts(result: dict[str, object]) -> bool:
    jobs = Path(str(result["external_jobs_root"]))
    if not jobs.exists():
        return False
    names = {
        "sqlite-with-gcov": {
            "nop": ("m071-sqlite-nop", "sqlite-with-gcov__wW3dAYy"),
            "mira": ("m071-sqlite-mira", "sqlite-with-gcov__NcgHJWY"),
        },
        "custom-memory-heap-crash": {
            "nop": ("m071-custom-memory-nop", "custom-memory-heap-crash__PxWrLGf"),
            "mira": ("m071-custom-memory-mira", "custom-memory-heap-crash__zyfmiQY"),
        },
    }
    artifacts = result["external_artifacts"]
    if not isinstance(artifacts, dict):
        raise ValueError("M071 external artifact map is invalid")
    for task, records in names.items():
        nop_job, nop_trial = records["nop"]
        mira_job, mira_trial = records["mira"]
        paths = {
            "nop_job_result_sha256": jobs / nop_job / "result.json",
            "nop_trial_result_sha256": jobs / nop_job / nop_trial / "result.json",
            "job_result_sha256": jobs / mira_job / "result.json",
            "trial_result_sha256": jobs / mira_job / mira_trial / "result.json",
            "manifest_sha256": jobs / mira_job / mira_trial / "agent" / "mira_manifest.json",
            "memory_sha256": jobs / mira_job / mira_trial / "agent" / "mira_memory.json",
        }
        task_artifacts = artifacts[task]
        if not isinstance(task_artifacts, dict):
            raise ValueError(f"M071 artifact record is invalid for {task}")
        for field, path in paths.items():
            if not path.is_file():
                raise ValueError(f"missing M071 external artifact: {path}")
            if hashlib.sha256(path.read_bytes()).hexdigest() != task_artifacts[field]:
                raise ValueError(f"M071 external artifact mismatch: {path}")
    return True


def verify_result() -> dict[str, object]:
    protocol = verify_protocol()
    result = json.loads((M071 / "EXTERNAL_RESULT.json").read_text(encoding="utf-8"))
    if result["status"] != "passed_falsifiable_threshold" or result["claim_passed"] is not True:
        raise ValueError("M071 positive threshold is not recorded")
    if result["execution_protocol_sha256"] != protocol["protocol_sha256"]:
        raise ValueError("M071 result does not match frozen protocol")
    if result["falsifiable_threshold"] != {
        "observed_successes": 1, "required_successes": 1, "selected_task_count": 2,
    }:
        raise ValueError("M071 threshold counts are invalid")
    rewards = {trial["task"]: trial["reward"] for trial in result["trials"]}
    if rewards != {"sqlite-with-gcov": 0.0, "custom-memory-heap-crash": 1.0}:
        raise ValueError("M071 rewards differ from the frozen result")
    if any(trial["network_mode"] != "no-network" for trial in result["trials"]):
        raise ValueError("M071 agent trial had network authority")
    if any(trial["agent_claimed_success"] is not False for trial in result["trials"]):
        raise ValueError("M071 agent improperly claimed success")
    if any(trial["reward"] != 0.0 for trial in result["nop_trials"]):
        raise ValueError("M071 nop floor is confounded")
    if result["controls"]["all_jobs_retries"] != 0:
        raise ValueError("M071 contains a retry")
    if result["attribution"]["genesis_gate_2_evidence"] is not False:
        raise ValueError("M071 improperly claims Genesis ownership")
    if result["preservation"]["passed"] != 1225:
        raise ValueError("M071 preservation suite is not recorded")
    _verify_memory("SQLite_MIRA_MEMORY.json", result["trials"][0]["memory_digest"])
    _verify_memory("CustomMemory_MIRA_MEMORY.json", result["trials"][1]["memory_digest"])
    external_verified = _verify_external_artifacts(result)
    return {
        "external_artifacts_verified": external_verified,
        "result_sha256": _canonical_digest(result),
        "status": result["status"],
        "successes": 1,
        "tasks": 2,
    }


def main() -> None:
    print(json.dumps(verify_result(), sort_keys=True))


if __name__ == "__main__":
    main()
