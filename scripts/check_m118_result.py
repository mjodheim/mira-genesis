#!/usr/bin/env python3
"""Independent H63 checker: recompute the verdict, never believe it.

The runner records measurements. This recomputes every number the verdict depends on from the
committed measurements alone -- the paired contingency table, the exact p-value, the risk
difference, every no-harm guard, the factorial decomposition and the final verdict -- and refuses a
record whose own arithmetic does not reproduce.

It deliberately does **not** read any verdict field the runner might have written. A checker that
agrees with a boolean it was handed checks nothing.
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

from metamorphosis import m118_arms as arms  # noqa: E402
from metamorphosis import m118_decomposition as decomposition  # noqa: E402
from metamorphosis import m118_endpoint as endpoint  # noqa: E402
from metamorphosis.blind_bank_protocol import canonical_bytes, sha256_hex  # noqa: E402

CHECK_SCHEMA = "m118-h63-check-report-v1"


class CheckError(RuntimeError):
    """The record does not reproduce. Every path fails closed."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise CheckError(message)


def _recompute(measurements: Mapping[str, Any]) -> tuple[dict[str, list[bool]], dict[str, Any]]:
    """Rebuild the paired outcomes and the guard measures from the per-demand record."""
    from metamorphosis import m113_evaluator as evaluator
    from scripts import run_m118_qualification as runner

    outcomes: dict[str, list[bool]] = {name: [] for name in arms.ARM_NAMES}
    counts: dict[str, dict[str, int]] = {
        name: {key: 0 for key in runner.SCORE_KEYS} for name in arms.ARM_NAMES}
    attribution: dict[str, list[int]] = {name: [0, 0] for name in arms.ARM_NAMES}
    for entry in measurements.get("entries") or []:
        truth = entry.get("ground_truth_component")
        for name in arms.ARM_NAMES:
            arm = entry["arms"][name]
            for demand_class in evaluator.DEMAND_CLASSES:
                row = arm[demand_class]
                outcomes[name].append(bool(row["primary_success"]))
                for key, value in row["score"].items():
                    if value:
                        counts[name][key] += 1
                if demand_class == evaluator.CLASS_REACHABLE and "attributed_component" in row:
                    attribution[name][row["attributed_component"] == truth] += 1
    measures: dict[str, Any] = {}
    for name in arms.ARM_NAMES:
        correct, seen = attribution[name][True], sum(attribution[name])
        measures[name] = dict(counts[name])
        measures[name]["attribution_correct"] = correct
        measures[name]["attribution_examined"] = seen
        measures[name]["attribution_agreement_rate"] = correct / seen if seen else None
    return outcomes, measures


def check(measurements: Mapping[str, Any]) -> dict[str, Any]:
    _require(measurements.get("schema") == "m118-h63-measurements-v1",
             "not an M118 measurements record")

    recomputed_digest = sha256_hex(canonical_bytes(
        {k: v for k, v in measurements.items() if k != "measurements_sha256"}))
    _require(measurements.get("measurements_sha256") == recomputed_digest,
             "the measurements digest does not reproduce")

    outcomes = measurements["paired_primary_outcomes"]
    descendant_arm = measurements["descendant_arm"]
    fresh_arm = measurements["primary_fresh_arm"]
    _require(descendant_arm == arms.DESCENDANT_ARM,
             "the descendant arm is not the frozen one")
    _require(fresh_arm == arms.PRIMARY_FRESH_ARM,
             "the primary comparator is not the frozen one; beating T0 is not the test")
    _require(fresh_arm != arms.LEGACY_FRESH_ARM,
             "the legacy constant arm cannot be the primary comparator")

    # Every arm must have answered exactly the same demands, in the same order.
    lengths = {name: len(series) for name, series in outcomes.items()}
    _require(len(set(lengths.values())) == 1,
             "arms did not see the same number of demands: %s" % lengths)
    _require(lengths[descendant_arm] == len(measurements["demand_order"]),
             "the paired outcomes do not match the recorded demand order")

    # The comparator must not have degenerated into a constant on this bank.
    freshness = arms.is_information_free(arms.fresh_uniform_rules(
        measurements["fresh_uniform_seed"]))
    _require(freshness["carries_no_acquired_rule"], "the comparator carries an acquired rule")
    _require(freshness["is_non_constant"], "the comparator is constant")
    _require(freshness["no_row_is_claimed_twice"],
             "the comparator claims a feature row twice")
    _require(freshness["effective_assignment_is_total"],
             "the comparator leaves a feature row unassigned")
    _require(freshness["reaches_every_component"],
             "the comparator cannot name every component")
    _require(freshness["every_rule_is_seed_derived"],
             "a comparator rule is not seed-derived")
    _require(freshness["unlike_t0_which_reaches_the_fallthrough_on_every_row"],
             "the comparator degenerated into the constant fallthrough")

    # The record carries every per-demand boolean under `entries`, so the aggregates the guards are
    # evaluated on are recomputed here rather than believed. A runner that mislabelled a
    # primary_success or miscounted a measure would otherwise reproduce perfectly.
    recomputed_outcomes, recomputed_measures = _recompute(measurements)
    for arm, series in recomputed_outcomes.items():
        _require(series == outcomes.get(arm),
                 "recomputed primary outcomes disagree with the record for %s" % arm)
    for arm, values in recomputed_measures.items():
        recorded = measurements["measures"].get(arm) or {}
        for key, value in values.items():
            _require(recorded.get(key) == value,
                     "recomputed %s disagrees with the record for %s" % (key, arm))

    # The comparator's seed decides the comparator. Recomputing freshness from a seed the record
    # supplies, without checking it is the frozen one, would let an attacker-chosen seed through.
    _require(measurements["fresh_uniform_seed"] == arms.FRESH_UNIFORM_SEED,
             "the recorded comparator seed is not the frozen one")

    # Provenance and versions are recorded by the runner; unasserted they are decoration.
    provenance = measurements.get("provenance_checks") or {}
    _require(bool(provenance) and all(provenance.values()),
             "a producer provenance check did not hold: %s"
             % sorted(k for k, v in provenance.items() if not v))
    _require((measurements.get("corruption") or {}).get("failed_closed") is True,
             "a corrupted acquired rule did not fail closed")
    _require(measurements.get("arms_version") == arms.ARMS_VERSION,
             "the record was produced by a different arm set")
    _require(measurements.get("endpoint_version") == endpoint.ENDPOINT_VERSION,
             "the record was produced by a different endpoint")

    # The minimum bank the plan requires, enforced rather than copied.
    minimum = measurements.get("minimum_qualifying_carriers")
    minimum_structures = measurements.get("minimum_distinct_qualifying_structures")
    _require(measurements.get("session_budget_came_from_the_committed_plan") is True,
             "the session budget did not come from the committed plan")
    _require(isinstance(minimum, int) and isinstance(minimum_structures, int),
             "the record does not carry the plan's minimum bank")
    _require(measurements["qualifying_carriers"] >= minimum,
             "the bank is below the minimum qualifying carriers the plan requires")
    _require(measurements["distinct_qualifying_structures"] >= minimum_structures,
             "the bank is below the minimum distinct structures the plan requires")

    verdict = endpoint.decide(
        outcomes[descendant_arm], outcomes[fresh_arm],
        measurements["measures"][descendant_arm], measurements["measures"][fresh_arm],
        dominance={name: outcomes[name] for name in (arms.LEGACY_FRESH_ARM, "M2")})

    rates = decomposition.rates_from_outcomes(outcomes)
    decomposed = decomposition.decompose(rates, positive=verdict["positive"])

    # The legacy comparison, reported and explicitly not decisive.
    legacy = endpoint.decide(
        outcomes[descendant_arm], outcomes[arms.LEGACY_FRESH_ARM],
        measurements["measures"][descendant_arm],
        measurements["measures"][arms.LEGACY_FRESH_ARM])

    report = {
        "schema": CHECK_SCHEMA,
        "milestone": "M118", "hypothesis": "H63",
        "measurements_sha256": recomputed_digest,
        "qualifying_carriers": measurements["qualifying_carriers"],
        "distinct_qualifying_structures": measurements["distinct_qualifying_structures"],
        "paired_demands": lengths[descendant_arm],
        "primary_comparison": "%s vs %s" % (descendant_arm, fresh_arm),
        "verdict_recomputed_independently": True,
        "runner_verdict_was_not_read": True,
        "primary": verdict,
        "decomposition": decomposed,
        "legacy_t0_comparison_not_decisive": {
            "p_value": legacy["p_value"],
            "risk_difference": legacy["risk_difference"],
            "note": "reported for regression only; T0 is a constant function and beating it is "
                    "not evidence for H63",
        },
        "arm_success_rates": rates,
        # An underpowered bank is not a refutation. Reporting it as "not_supported" would let a
        # bank too small for significance to be arithmetically attainable masquerade as evidence
        # against the hypothesis, which is the mirror of letting one event masquerade as support.
        "hypothesis_status": ("supported" if verdict["positive"]
                              else "not_supported" if verdict["verdict"] == "negative"
                              else "inconclusive" if verdict["verdict"] == "inconclusive"
                              else "not_computed"),
        "verdict": verdict["verdict"],
        "report_sha256": "",
    }
    report["report_sha256"] = sha256_hex(
        canonical_bytes({k: v for k, v in report.items() if k != "report_sha256"}))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--measurements", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    measurements = json.loads(args.measurements.read_text(encoding="utf-8"))
    report = check(measurements)
    if args.out:
        args.out.write_bytes(canonical_bytes(report) + b"\n")
    print(json.dumps({
        "verdict": report["verdict"],
        "hypothesis_status": report["hypothesis_status"],
        "p_value": report["primary"]["p_value"],
        "risk_difference": report["primary"]["risk_difference"],
        "guards_failed": report["primary"]["no_harm"]["failed"],
        "strongest_supported_statement":
            report["decomposition"]["strongest_supported_statement"],
        "report_sha256": report["report_sha256"],
    }, indent=2, sort_keys=True))
    return 0 if report["verdict"] != "not_computed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
