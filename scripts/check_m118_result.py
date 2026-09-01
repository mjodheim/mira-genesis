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

    verdict = endpoint.decide(
        outcomes[descendant_arm], outcomes[fresh_arm],
        measurements["measures"][descendant_arm], measurements["measures"][fresh_arm])

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
