#!/usr/bin/env python3
"""H63 qualification: run every arm over the revealed bank and record measurements.

This runner is H63-specific. M113's runner and checker are historical records and are not modified;
this one reuses their frozen machinery -- the producers' bytes, the evaluator, the carrier host and
the runtime -- and changes only what the owner authorized: the arm set and the primary endpoint.

**It records measurements. It does not decide.** The verdict is computed by
`scripts/check_m118_result.py` from the committed measurements, independently, so a verdict can
never be a boolean this script wrote.

The arms are the corrected factorial set:

                     policy absent        policy present
    rules absent      T0 / fresh_uniform   probe_only
    rules present     M2                   M3

with `probe_only_budget_plus` as a budget control that can actually take the probing action, and
the legacy arms retained for regression.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from metamorphosis import carrier_host as host  # noqa: E402
from metamorphosis import m113_evaluator as evaluator  # noqa: E402
from metamorphosis import m113_runtime as runtime  # noqa: E402
from metamorphosis import m118_arms as arms  # noqa: E402
from metamorphosis import m118_endpoint as endpoint  # noqa: E402
from metamorphosis.blind_bank_protocol import canonical_bytes, sha256_hex  # noqa: E402
from scripts import run_m113_qualification as inherited  # noqa: E402

MEASUREMENTS_SCHEMA = "m118-h63-measurements-v1"
SCORE_KEYS = inherited.SCORE_KEYS


class QualificationError(RuntimeError):
    """H63 qualification cannot proceed honestly. Every path fails closed."""


def restore_h63_arms() -> dict[str, Any]:
    """The M118 arm set, built from the same frozen producer bytes M113 restores from.

    The pieces are taken out of the inherited restoration rather than decoded again here, so the
    provenance path is literally the one the predecessor milestones already prove, and a divergence
    would be an import error rather than a silent second implementation.
    """
    restored = inherited.restore_arms()
    cascades = restored["cascades"]
    first = cascades["M1"]["rules"][0]
    second = cascades["M2"]["rules"][1]
    policy = cascades["M3"]["policy"]
    mutated_rule = cascades["mutated"]["rules"][1]
    if not policy:
        raise QualificationError("the acquired diagnostic policy did not restore")
    return {
        "cascades": arms.build_arms(first, second, policy, mutated_rule),
        "record": restored["record"],
        "corruption": restored["corruption"],
        "provenance_checks": restored["provenance_checks"],
        "fresh_uniform_is_information_free": arms.is_information_free(
            arms.fresh_uniform_rules()),
        "fresh_uniform_seed": arms.FRESH_UNIFORM_SEED,
        "action_space": arms.action_space_statement(),
    }


def _states(cascades: Mapping[str, Any], record: Mapping[str, Any],
            entry: Mapping[str, Any]) -> dict[str, Any]:
    return {
        name: runtime.create_state(
            action_width=entry["action_width"],
            observation_width=entry["observation_width"],
            composition_space=entry["composition_space"],
            rules=configuration["rules"],
            policy=configuration["policy"],
            pooled_record=record if configuration["policy"] else None,
        )
        for name, configuration in cascades.items()
    }


def measure(carriers: Sequence[Mapping[str, Any]], nonce: str, *,
            session_budget: int) -> dict[str, Any]:
    """Every arm, every qualifying carrier, every demand. Measurements only."""
    restored = restore_h63_arms()
    cascades = restored["cascades"]
    per_arm: dict[str, Counter] = {name: Counter() for name in arms.ARM_NAMES}
    attribution: dict[str, Counter] = {name: Counter() for name in arms.ARM_NAMES}
    # The paired primary outcomes, in a fixed demand order so the checker can recompute the exact
    # contingency table rather than trusting a count.
    primary: dict[str, list[bool]] = {name: [] for name in arms.ARM_NAMES}
    demands: list[dict[str, Any]] = []
    entries: list[dict[str, Any]] = []
    qualifying = 0
    qualifying_signatures: Counter = Counter()

    for index, carrier in enumerate(carriers):
        report = evaluator.qualification_report(carrier)
        if not report["qualifies"]:
            continue
        qualifying += 1
        qualifying_signatures[host.structural_signature(carrier)] += 1
        reference = carrier.get("carrier_ref") or inherited.opaque_domain_id(nonce, index)

        for pair in evaluator.derive_demand_pairs(carrier, reference, session_budget):
            evaluator.assert_demand_pair_delta(pair)
            truth = pair["ground_truth"]
            states = _states(cascades, restored["record"], pair["shared"]["entry"])
            record: dict[str, Any] = {
                "carrier_ref": reference,
                "carrier_digest": carrier["carrier_digest"],
                "pair_digest": pair["pair_digest"],
                "ground_truth_component": truth["component"],
                "ground_truth_row": truth["row_index"],
                "arms": {},
            }
            for demand_class in evaluator.DEMAND_CLASSES:
                demands.append({"pair_digest": pair["pair_digest"],
                                "demand_class": demand_class})
            for name, state in states.items():
                budget = session_budget * arms.BUDGET_MULTIPLIER.get(name, 1)
                arm_record: dict[str, Any] = {"budget": budget}
                for demand_class in evaluator.DEMAND_CLASSES:
                    demand = evaluator.materialize_twin(pair, demand_class)
                    channel = host.Channel(carrier, reference, budget)
                    outcome = runtime.resolve(state, channel, demand)
                    score = evaluator.score_attempt(carrier, demand, outcome)
                    for key in SCORE_KEYS:
                        if score[key]:
                            per_arm[name][key] += 1
                    succeeded = endpoint.primary_success(demand_class, score)
                    primary[name].append(bool(succeeded))
                    arm_record[demand_class] = {
                        "verdict": outcome["verdict"],
                        "invocations_used": outcome["invocations_used"],
                        "probes_spent": outcome["probes_spent"],
                        "within_budget": score["within_budget"],
                        "primary_success": bool(succeeded),
                        "score": {key: bool(score[key]) for key in SCORE_KEYS},
                    }
                    if outcome["trace"] and demand_class == evaluator.CLASS_REACHABLE:
                        attributed = outcome["trace"][0]["attribution"]["component"]
                        arm_record[demand_class]["attributed_component"] = attributed
                        attribution[name][attributed == truth["component"]] += 1
                record["arms"][name] = arm_record
            entries.append(record)

    measures = {}
    for name in arms.ARM_NAMES:
        seen = attribution[name][True] + attribution[name][False]
        measures[name] = {key: int(per_arm[name][key]) for key in SCORE_KEYS}
        measures[name]["attribution_correct"] = int(attribution[name][True])
        measures[name]["attribution_examined"] = int(seen)
        measures[name]["attribution_agreement_rate"] = (
            attribution[name][True] / seen if seen else None)

    record = {
        "schema": MEASUREMENTS_SCHEMA,
        "milestone": "M118", "hypothesis": "H63",
        "arms_version": arms.ARMS_VERSION,
        "endpoint_version": endpoint.ENDPOINT_VERSION,
        "descendant_arm": arms.DESCENDANT_ARM,
        "primary_fresh_arm": arms.PRIMARY_FRESH_ARM,
        "legacy_fresh_arm": arms.LEGACY_FRESH_ARM,
        "fresh_uniform_seed": restored["fresh_uniform_seed"],
        "fresh_uniform_is_information_free": restored["fresh_uniform_is_information_free"],
        "action_space": restored["action_space"],
        "provenance_checks": restored["provenance_checks"],
        "corruption": restored["corruption"],
        "session_budget": session_budget,
        "budget_multiplier": dict(arms.BUDGET_MULTIPLIER),
        "carriers_seen": len(carriers),
        "qualifying_carriers": qualifying,
        "distinct_qualifying_structures": len(qualifying_signatures),
        "demand_order": demands,
        "paired_primary_outcomes": {name: primary[name] for name in arms.ARM_NAMES},
        "measures": measures,
        "entries": entries,
        "the_runner_records_measurements_and_decides_nothing": True,
        "measurements_sha256": "",
    }
    record["measurements_sha256"] = sha256_hex(
        canonical_bytes({k: v for k, v in record.items() if k != "measurements_sha256"}))
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--carriers", type=Path, required=True,
                        help="revealed carrier bodies, as committed JSON")
    parser.add_argument("--nonce", required=True)
    parser.add_argument("--session-budget", type=int, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    carriers = json.loads(args.carriers.read_text(encoding="utf-8"))
    record = measure(carriers, args.nonce, session_budget=args.session_budget)
    args.out.write_bytes(canonical_bytes(record) + b"\n")
    print(json.dumps({"qualifying_carriers": record["qualifying_carriers"],
                      "paired_demands": len(record["demand_order"]),
                      "measurements_sha256": record["measurements_sha256"]},
                     indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
