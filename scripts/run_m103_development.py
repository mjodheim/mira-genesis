"""Run non-canonical M103 development rehearsals without writing scientific evidence."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import check_m103_result as result_checker  # noqa: E402
from scripts import run_m103_qualification as qualification  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replay", action="store_true")
    arguments = parser.parse_args()
    if qualification.RESULT_PATH.exists() or qualification.CHECK_PATH.exists():
        raise SystemExit("development rehearsal refuses to touch a preserved canonical result")
    pool = json.loads(qualification.POOL_PATH.read_text(encoding="ascii"))
    first = qualification.run_experiment(pool)
    first_conditions = result_checker.evaluate_conditions(first)
    report: dict[str, object] = {
        "schema": "m103-development-rehearsal-v1",
        "canonical": False,
        "scientific_verdict": False,
        "conditions": first_conditions,
        "passed": sum(first_conditions.values()),
        "total": len(first_conditions),
        "stable_evidence_digest": qualification.digest(qualification.stable_projection(first)),
        "model_calls": 0,
        "network_calls": 0,
        "remote_execution_calls": 0,
    }
    if arguments.replay:
        second = qualification.run_experiment(pool)
        replay_equal = qualification.stable_projection(first) == qualification.stable_projection(
            second
        )
        first_conditions = result_checker.evaluate_conditions(
            first, replay_confirmed=replay_equal
        )
        second_conditions = result_checker.evaluate_conditions(
            second, replay_confirmed=replay_equal
        )
        report["conditions"] = first_conditions
        report["passed"] = sum(first_conditions.values())
        report["replay_stable_evidence_digest"] = qualification.digest(
            qualification.stable_projection(second)
        )
        report["replay_equal"] = replay_equal
        report["replay_conditions_equal"] = first_conditions == second_conditions
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if all(first_conditions.values()) and report.get("replay_equal", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
