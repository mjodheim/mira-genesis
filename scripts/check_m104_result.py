"""Independent M104 checker with a directly executable repository entry point."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import check_m103_result as predicate_checker  # noqa: E402


EXPERIMENT = ROOT / "experiments" / "M104"
RESULT_PATH = EXPERIMENT / "RESULT.json"
REPORT_PATH = EXPERIMENT / "CHECK_REPORT.json"
PROTOCOL_PATH = EXPERIMENT / "PROTOCOL.json"
POOL_PATH = EXPERIMENT / "QUALIFICATION_POOL.json"
EXPECTED_PREDICATES = [f"P{index}" for index in range(1, 16)]


canonical_json = predicate_checker.canonical_json
digest = predicate_checker.digest
stable_projection = predicate_checker.stable_projection


def entrypoint_preflight() -> dict[str, Any]:
    from scripts import run_m104_qualification as qualification

    source = Path(__file__).read_bytes()
    return {
        "schema": "m104-checker-entrypoint-preflight-v1",
        "confirmed": ROOT == qualification.ROOT,
        "repository_root_resolved": ROOT == qualification.ROOT,
        "checker_raw_sha256": hashlib.sha256(source).hexdigest(),
        "runner_imported": qualification.__name__ == "scripts.run_m104_qualification",
        "qualification_pool_opened": False,
        "result_opened": False,
        "report_opened": False,
    }


def check_result(result: dict[str, Any], *, replay: bool) -> dict[str, Any]:
    if result.get("schema") != "m104-result-v1" or result.get("attempt") != 1:
        raise ValueError("M104 result identity is invalid")
    payload = {key: value for key, value in result.items() if key != "result_digest"}
    if result.get("result_digest") != digest(payload):
        raise ValueError("M104 result digest mismatch")
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="ascii"))
    pool = json.loads(POOL_PATH.read_text(encoding="ascii"))
    if result.get("protocol_digest") != protocol.get("protocol_digest"):
        raise ValueError("M104 result protocol binding mismatch")
    if result.get("pool_digest") != pool.get("pool_digest"):
        raise ValueError("M104 result pool binding mismatch")
    evidence = result["scientific_evidence"]
    measured_stable = digest(stable_projection(evidence))
    if result.get("stable_evidence_digest") != measured_stable:
        raise ValueError("M104 stable evidence digest mismatch")
    replay_equal = False
    replay_digest: str | None = None
    if replay:
        from scripts import run_m104_qualification as qualification

        replay_evidence = qualification.run_experiment(pool)
        replay_digest = digest(stable_projection(replay_evidence))
        replay_equal = stable_projection(replay_evidence) == stable_projection(evidence)
    conditions = predicate_checker.evaluate_conditions(evidence, replay_confirmed=replay_equal)
    if sorted(conditions, key=lambda key: int(key[1:])) != EXPECTED_PREDICATES:
        raise ValueError("M104 checker predicate set changed")
    failed = [key for key in EXPECTED_PREDICATES if not conditions[key]]
    report: dict[str, Any] = {
        "schema": "m104-check-report-v1",
        "scientific_verdict": True,
        "verdict": "positive" if not failed else "negative",
        "attempt": 1,
        "conditions": conditions,
        "passed": len(conditions) - len(failed),
        "failed": len(failed),
        "uncomputed": 0,
        "failed_predicates": failed,
        "result_digest": result["result_digest"],
        "stable_evidence_digest": measured_stable,
        "replay_performed": replay,
        "replay_equal": replay_equal,
        "replay_stable_evidence_digest": replay_digest,
        "model_calls": result.get("model_calls"),
        "network_calls": result.get("network_calls"),
        "remote_execution_calls": result.get("remote_execution_calls"),
        "predicate_semantics_source": "frozen_M103_independent_checker",
        "imports_m103_runtime_for_predicates": False,
        "direct_script_root_bootstrap": True,
    }
    report["report_digest"] = digest(report)
    return report


def _failure_report(error: Exception) -> dict[str, Any]:
    report: dict[str, Any] = {
        "schema": "m104-check-report-v1",
        "scientific_verdict": True,
        "verdict": "negative",
        "failed_closed": True,
        "error": f"{type(error).__name__}: {error}",
        "attempt": 1,
    }
    report["report_digest"] = digest(report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", default=str(RESULT_PATH))
    parser.add_argument("--replay", action="store_true")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--entrypoint-preflight", action="store_true")
    arguments = parser.parse_args()
    if arguments.entrypoint_preflight:
        report = entrypoint_preflight()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["confirmed"] else 3
    try:
        result = json.loads(Path(arguments.result).read_text(encoding="ascii"))
        report = check_result(result, replay=arguments.replay)
    except Exception as error:
        report = _failure_report(error)
        if arguments.write and not REPORT_PATH.exists():
            with REPORT_PATH.open("xb") as handle:
                handle.write(canonical_json(report).encode("ascii"))
        print(json.dumps(report, indent=2, sort_keys=True))
        return 3
    if arguments.write:
        with REPORT_PATH.open("xb") as handle:
            handle.write(canonical_json(report).encode("ascii"))
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["verdict"] == "positive" else 1


if __name__ == "__main__":
    raise SystemExit(main())
