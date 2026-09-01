#!/usr/bin/env python3
"""Independent H64 checker: recompute everything from per-demand evidence.

M118's checker evaluated its guards on aggregates the runner had written, which meant a runner that
mislabelled an outcome would reproduce perfectly. This one recomputes the paired outcomes and every
measure from `entries`, cross-checks the comparator seed against the frozen constant rather than
believing the record's copy, enforces the plan's minimum bank, and asserts the provenance checks it
is handed instead of passing them through unread.

It reads no verdict the runner could have written.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from metamorphosis import m113_evaluator as evaluator  # noqa: E402
from metamorphosis import m119_arms as arms  # noqa: E402
from metamorphosis import m119_decomposition as decomposition  # noqa: E402
from metamorphosis import m119_endpoint as endpoint  # noqa: E402
from metamorphosis.blind_bank_protocol import canonical_bytes, sha256_hex  # noqa: E402

CHECK_SCHEMA = "m119-h64-check-report-v1"


class CheckError(RuntimeError):
    """The record does not reproduce. Every path fails closed."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise CheckError(message)


def recompute_outcomes(entries) -> dict[str, list[bool]]:
    """Paired primary outcomes per arm, from the per-demand evidence alone."""
    outcomes: dict[str, list[bool]] = {name: [] for name in arms.ARM_NAMES}
    for entry in entries:
        for demand_class in evaluator.DEMAND_CLASSES:
            for name in arms.ARM_NAMES:
                row = entry["arms"][name][demand_class]
                # Recomputed from the score, not read from the runner's `primary_success`.
                outcomes[name].append(endpoint.primary_success(demand_class, row["score"]))
    return outcomes


def recompute_measures(entries) -> dict[str, dict[str, Any]]:
    """Every guard measure, recounted from the per-demand evidence."""
    measures: dict[str, dict[str, Any]] = {}
    for name in arms.ARM_NAMES:
        counts = {key: 0 for key in ("invented_adapter", "false_refusal")}
        correct = examined = 0
        for entry in entries:
            for demand_class in evaluator.DEMAND_CLASSES:
                row = entry["arms"][name][demand_class]
                for key in counts:
                    counts[key] += bool(row["score"].get(key))
                if demand_class == evaluator.CLASS_REACHABLE and "attribution_correct" in row:
                    examined += 1
                    correct += bool(row["attribution_correct"])
        measures[name] = dict(counts)
        measures[name]["attribution_correct"] = correct
        measures[name]["attribution_examined"] = examined
        measures[name]["attribution_agreement_rate"] = (correct / examined) if examined else None
    return measures


def check(measurements: Mapping[str, Any], plan: Mapping[str, Any]) -> dict[str, Any]:
    _require(measurements.get("schema") == "m119-h64-measurements-v1",
             "not an M119 measurements record")
    _require(measurements.get("measurements_sha256") == sha256_hex(canonical_bytes(
        {k: v for k, v in measurements.items() if k != "measurements_sha256"})),
        "the measurements digest does not reproduce")
    _require(measurements.get("analysis_plan_commitment_sha256")
             == plan.get("plan_commitment_sha256"),
             "the measurements were produced under a different analysis plan")

    # The comparator must be the frozen one, checked against the constant rather than the record.
    _require(measurements.get("fresh_seed") == arms.FRESH_SEED,
             "the comparator seed is not the frozen one")
    _require(measurements.get("fresh_seed_source") == arms.FRESH_SEED_SOURCE,
             "the comparator seed derivation is not the frozen one")
    _require(measurements.get("descendant_arm") == arms.DESCENDANT_ARM
             and measurements.get("comparator_arm") == arms.COMPARATOR_ARM,
             "the primary comparison is not the frozen one")
    _require(list(measurements.get("arm_names") or []) == list(arms.ARM_NAMES),
             "the arm set is not the frozen one")
    _require(int(measurements.get("session_budget", -1)) == int(plan["session_budget"]),
             "the run used a budget the plan does not specify")

    # Provenance is asserted, not passed through.
    provenance = measurements.get("provenance_checks") or {}
    failed = sorted(k for k, v in provenance.items() if v is not True)
    _require(not failed, "producer provenance checks failed: %s" % ", ".join(failed))
    _require((measurements.get("corruption") or {}).get("failed_closed") is True,
             "a corrupted acquired rule was not refused")

    entries = measurements.get("entries") or []
    outcomes = recompute_outcomes(entries)
    measures = recompute_measures(entries)

    # Admissibility, from the plan rather than from whatever the bank happened to yield.
    instrument_failures: list[str] = []
    if measurements["qualifying_carriers"] < int(plan["minimum_qualifying_carriers"]):
        instrument_failures.append("fewer qualifying carriers than the plan requires")
    if measurements["distinct_qualifying_structures"] < int(
            plan["minimum_distinct_qualifying_structures"]):
        instrument_failures.append("fewer distinct structures than the plan requires")
    if not entries:
        instrument_failures.append("no paired demand was posed")

    verdict = endpoint.decide(
        outcomes[arms.DESCENDANT_ARM], outcomes[arms.COMPARATOR_ARM],
        measures[arms.DESCENDANT_ARM], measures[arms.COMPARATOR_ARM],
        instrument_valid=not instrument_failures,
        instrument_failures=instrument_failures)

    rates = {name: (sum(1 for x in series if x) / len(series) if series else None)
             for name, series in outcomes.items()}
    decomposed = decomposition.decompose(rates, verdict=verdict["verdict"])

    report = {
        "schema": CHECK_SCHEMA,
        "milestone": "M119", "hypothesis": "H64",
        "measurements_sha256": measurements["measurements_sha256"],
        "analysis_plan_commitment_sha256": plan["plan_commitment_sha256"],
        "qualifying_carriers": measurements["qualifying_carriers"],
        "distinct_qualifying_structures": measurements["distinct_qualifying_structures"],
        "paired_demands": len(outcomes[arms.DESCENDANT_ARM]),
        "primary_comparison": "%s vs %s" % (arms.DESCENDANT_ARM, arms.COMPARATOR_ARM),
        "outcomes_recomputed_from_per_demand_evidence": True,
        "measures_recomputed_from_per_demand_evidence": True,
        "runner_verdict_was_not_read": True,
        "arm_success_rates": rates,
        "recomputed_measures": measures,
        "primary": verdict,
        "decomposition": decomposed,
        "hypothesis_status": {
            endpoint.POSITIVE: "supported",
            endpoint.NEGATIVE: "not_supported",
            endpoint.INCONCLUSIVE: "inconclusive",
            endpoint.INSTRUMENT_ABORTED: "untested",
        }[verdict["verdict"]],
        "verdict": verdict["verdict"],
        "report_sha256": "",
    }
    report["report_sha256"] = sha256_hex(
        canonical_bytes({k: v for k, v in report.items() if k != "report_sha256"}))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--measurements", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    report = check(json.loads(args.measurements.read_text(encoding="utf-8")),
                   json.loads(args.plan.read_text(encoding="utf-8")))
    if args.out:
        args.out.write_bytes(canonical_bytes(report) + b"\n")
    print(json.dumps({"verdict": report["verdict"],
                      "hypothesis_status": report["hypothesis_status"],
                      "p_value": report["primary"]["p_value"],
                      "risk_difference": report["primary"]["risk_difference"],
                      "guards_failed": report["primary"]["no_harm"]["failed"],
                      "statement": report["decomposition"]["strongest_supported_statement"],
                      "report_sha256": report["report_sha256"]}, indent=2, sort_keys=True))
    return 0 if report["verdict"] in (endpoint.POSITIVE, endpoint.NEGATIVE) else 1


if __name__ == "__main__":
    raise SystemExit(main())
