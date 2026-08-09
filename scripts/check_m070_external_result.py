#!/usr/bin/env python3
"""Verify the committed M070 external result and its memory-ledger evidence."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
M070 = ROOT / "experiments" / "M070"


def _canonical_digest(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _verify_memory(filename: str, expected: str) -> None:
    memory = json.loads((M070 / filename).read_text(encoding="utf-8"))
    previous = "0" * 64
    for index, event in enumerate(memory["events"]):
        assert event["index"] == index
        assert event["previous_digest"] == previous
        material = {
            "index": index,
            "kind": event["kind"],
            "payload": event["payload"],
            "previous": previous,
        }
        encoded = json.dumps(
            material, sort_keys=True, separators=(",", ":")
        ).encode()
        assert event["digest"] == hashlib.sha256(
            b"mira-memory-event-v1\0" + encoded
        ).hexdigest()
        previous = event["digest"]
    assert memory["head_digest"] == previous == expected


def _verify_external_artifacts(result: dict[str, object]) -> bool:
    jobs = Path(str(result["external_jobs_root"]))
    if not jobs.exists():
        return False
    paths = {
        ("rstan-to-pystan", "nop_job_result_sha256"):
            jobs / "m070-rstan-nop" / "result.json",
        ("rstan-to-pystan", "nop_trial_result_sha256"):
            jobs / "m070-rstan-nop" / "rstan-to-pystan__wUsxqEK" / "result.json",
        ("rstan-to-pystan", "job_result_sha256"):
            jobs / "m070-rstan-mira" / "result.json",
        ("rstan-to-pystan", "trial_result_sha256"):
            jobs / "m070-rstan-mira" / "rstan-to-pystan__KCZthdV" / "result.json",
        ("rstan-to-pystan", "manifest_sha256"):
            jobs / "m070-rstan-mira" / "rstan-to-pystan__KCZthdV"
            / "agent" / "mira_manifest.json",
        ("rstan-to-pystan", "memory_sha256"):
            jobs / "m070-rstan-mira" / "rstan-to-pystan__KCZthdV"
            / "agent" / "mira_memory.json",
        ("llm-inference-batching-scheduler", "nop_job_result_sha256"):
            jobs / "m070-llm-scheduler-nop" / "result.json",
        ("llm-inference-batching-scheduler", "nop_trial_result_sha256"):
            jobs / "m070-llm-scheduler-nop"
            / "llm-inference-batching-scheduler__2txSGao" / "result.json",
        ("llm-inference-batching-scheduler", "job_result_sha256"):
            jobs / "m070-llm-scheduler-mira" / "result.json",
        ("llm-inference-batching-scheduler", "trial_result_sha256"):
            jobs / "m070-llm-scheduler-mira"
            / "llm-inference-batching-scheduler__p7pjuaM" / "result.json",
        ("llm-inference-batching-scheduler", "manifest_sha256"):
            jobs / "m070-llm-scheduler-mira"
            / "llm-inference-batching-scheduler__p7pjuaM"
            / "agent" / "mira_manifest.json",
        ("llm-inference-batching-scheduler", "memory_sha256"):
            jobs / "m070-llm-scheduler-mira"
            / "llm-inference-batching-scheduler__p7pjuaM"
            / "agent" / "mira_memory.json",
    }
    artifacts = result["external_artifacts"]
    assert isinstance(artifacts, dict)
    for (task, field), path in paths.items():
        assert path.is_file(), path
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        task_artifacts = artifacts[task]
        assert isinstance(task_artifacts, dict)
        assert digest == task_artifacts[field], path
    return True


def main() -> None:
    result = json.loads((M070 / "EXTERNAL_RESULT.json").read_text(encoding="utf-8"))
    assert result["status"] == "failed_falsifiable_threshold"
    assert result["claim_passed"] is False
    assert result["falsifiable_threshold"] == {
        "observed_successes": 0, "required_successes": 1, "selected_task_count": 2,
    }
    assert all(trial["reward"] == 0.0 for trial in result["trials"])
    assert all(trial["network_mode"] == "no-network" for trial in result["trials"])
    assert all(trial["agent_claimed_success"] is False for trial in result["trials"])
    assert result["controls"]["nop_control_confound"] is False
    _verify_memory("RStan_MIRA_MEMORY.json", result["trials"][0]["memory_digest"])
    _verify_memory("Scheduler_MIRA_MEMORY.json", result["trials"][1]["memory_digest"])
    external_verified = _verify_external_artifacts(result)
    print(json.dumps({
        "external_artifacts_verified": external_verified,
        "result_sha256": _canonical_digest(result),
        "status": result["status"],
        "successes": 0,
        "tasks": 2,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
