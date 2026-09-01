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
from metamorphosis import m119_chronology as chronology  # noqa: E402
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
    outcomes: dict[str, list[bool]] = {name: [] for name in arms.ALL_ARM_NAMES}
    for entry in entries:
        for demand_class in evaluator.DEMAND_CLASSES:
            for name in arms.ALL_ARM_NAMES:
                row = entry["arms"][name][demand_class]
                # Recomputed from the score, not read from the runner's `primary_success`.
                outcomes[name].append(endpoint.primary_success(demand_class, row["score"]))
    return outcomes


def recompute_measures(entries) -> dict[str, dict[str, Any]]:
    """Every guard measure, recounted from the per-demand evidence."""
    measures: dict[str, dict[str, Any]] = {}
    for name in arms.ALL_ARM_NAMES:
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


def budget_attribution(entries, rates: Mapping[str, Any], verdict: str) -> dict[str, Any]:
    """Was a negative the machinery's, or the observation budget's?

    The policy gates a diagnostic probe, the probe consumes observations, and an exploration that
    runs out does not close -- so at a fixed budget an arm that probes can be penalised for the cost
    of probing rather than for what it acquired. This is computed from evidence the runner already
    records, and it can attribute a negative. It can never create a positive: it is reported beside
    the verdict, never fed into it.
    """
    exhausted = {name: 0 for name in arms.ALL_ARM_NAMES}
    undetermined_at_the_ceiling = {name: 0 for name in arms.ALL_ARM_NAMES}
    for entry in entries:
        for demand_class in evaluator.DEMAND_CLASSES:
            for name in arms.ALL_ARM_NAMES:
                row = entry["arms"][name][demand_class]
                if row.get("budget_exhausted"):
                    exhausted[name] += 1
                    if row.get("verdict") == "undetermined":
                        undetermined_at_the_ceiling[name] += 1
    descendant = rates.get(arms.DESCENDANT_ARM)
    at_higher_budget = rates.get(arms.FULL_BUDGET_PLUS)
    improves = (None if descendant is None or at_higher_budget is None
                else at_higher_budget - descendant)
    return {
        "schema": "m119-budget-attribution-v1",
        "budget_exhausted_demands": exhausted,
        "undetermined_at_the_invocation_ceiling": undetermined_at_the_ceiling,
        "descendant_success_rate": descendant,
        "descendant_success_rate_at_%dx_budget" % arms.BUDGET_MULTIPLIER[arms.FULL_BUDGET_PLUS]:
            at_higher_budget,
        "improvement_from_budget_alone": improves,
        "reading": (
            "not applicable: the verdict is not negative" if verdict != endpoint.NEGATIVE
            else "the negative is not explained by the observation budget: the same machinery does "
                 "no better with four times as many observations"
            if improves is not None and improves < endpoint.MINIMUM_RISK_DIFFERENCE
            else "the negative may be a budget cost rather than a competence cost: the same "
                 "machinery does materially better with four times as many observations, so this "
                 "run does not separate 'the policy does not help' from 'the policy is too "
                 "expensive at this budget'"),
        "this_can_attribute_a_negative_and_never_create_a_positive": True,
    }


def assert_binds_the_committed_reveal(measurements: Mapping[str, Any],
                                      reveal_record: Mapping[str, Any]) -> None:
    """Is this measurement of the bank that was actually sealed, revealed and committed?

    `check` can only ask whether the record *names* a reveal and a carrier bank; naming one is not
    being one. The freeze commitment is no help here: it is derivable from the source and the
    re-derivable plan, spec and nonce, so it is knowable before the generation and identical for
    every measurement taken under this freeze. A measurement produced from a stale bank, a
    rehearsal bank, or edited outcomes carries a perfectly valid freeze commitment.

    What authenticates a one-shot artifact is the committed record of the reveal that produced it.
    """
    for key in ("reveal_record_sha256", "carrier_bank_sha256"):
        if measurements.get(key) != reveal_record.get(key):
            raise CheckError(
                "the measurement does not match the committed reveal: %s is %r, the committed "
                "reveal record says %r"
                % (key, measurements.get(key), reveal_record.get(key)))


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
             "the principal arm set is not the frozen one")
    _require(list(measurements.get("diagnostic_arm_names") or [])
             == list(arms.DIAGNOSTIC_ARM_NAMES),
             "the diagnostic arm set is not the frozen one")
    _require(arms.DESCENDANT_ARM not in arms.DIAGNOSTIC_ARM_NAMES
             and arms.COMPARATOR_ARM not in arms.DIAGNOSTIC_ARM_NAMES,
             "a diagnostic arm is standing in the primary comparison")
    _require(int(measurements.get("session_budget", -1)) == int(plan["session_budget"]),
             "the run used a budget the plan does not specify")

    # Provenance is asserted, not passed through.
    provenance = measurements.get("provenance_checks") or {}
    failed = sorted(k for k, v in provenance.items() if v is not True)
    _require(not failed, "producer provenance checks failed: %s" % ", ".join(failed))
    _require((measurements.get("corruption") or {}).get("failed_closed") is True,
             "a corrupted acquired rule was not refused")

    # The measurement must name what it ran under. Whether the named freeze is the live one is
    # checked where the live tree can be read, in `main`; here the record must at least carry the
    # binding, so a measurement that names nothing can never be scored.
    # Presence and shape only. Whether the named reveal is the committed one is decided where the
    # committed record can be read, by `assert_binds_the_committed_reveal`; naming a reveal is not
    # being one, and this function must not be mistaken for that check.
    for key in ("freeze_commitment_sha256", "reveal_record_sha256", "carrier_bank_sha256"):
        _require(isinstance(measurements.get(key), str) and len(measurements[key]) == 64,
                 "the measurement does not bind %s" % key)

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
    # The decomposition sees the principal cells only. A diagnostic arm attributes a negative; it
    # is never an input to what the four cells are said to show.
    decomposed = decomposition.decompose(
        {name: rates[name] for name in arms.ARM_NAMES}, verdict=verdict["verdict"])
    budget = budget_attribution(entries, rates, verdict["verdict"])

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
        "budget_attribution": budget,
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
    try:
        # An independent replay is only independent of the run, not of the freeze: the tested
        # system must still be the frozen one at the moment the verdict is computed.
        permission = chronology.assert_frozen_system_unchanged(ROOT, phase="replay")
        measurements = json.loads(args.measurements.read_text(encoding="utf-8"))
        if measurements.get("freeze_commitment_sha256") != permission["freeze_commitment_sha256"]:
            raise CheckError("the measurement was taken under a different tested-system freeze")
        # The committed reveal, read from the repository rather than from the record being scored.
        reveal_record = json.loads(
            (ROOT / chronology.REVEAL_RECORD).read_text(encoding="utf-8"))
        assert_binds_the_committed_reveal(measurements, reveal_record)
        report = check(measurements, json.loads(args.plan.read_text(encoding="utf-8")))
    except (CheckError, chronology.ChronologyError, endpoint.EndpointError, ValueError) as exc:
        print("REFUSED: %s" % exc)
        return 1
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
