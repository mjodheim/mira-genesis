#!/usr/bin/env python3
"""H64 qualification: run the four arms over the revealed bank and record per-demand evidence.

This runner **records and decides nothing**. Every parameter that could change a verdict comes from
the committed analysis plan, not the command line: M118's runner took `--session-budget` from argv,
which is a forking path that could be walked after the reveal until a budget suited.

It writes per-demand evidence rather than aggregates, so `scripts/check_m119_result.py` can
recompute the measures, the paired outcomes and the verdict from the evidence instead of trusting
a number this script wrote.
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
from metamorphosis import m119_arms as arms  # noqa: E402
from metamorphosis import m119_chronology as chronology  # noqa: E402
from metamorphosis import m119_endpoint as endpoint  # noqa: E402
from metamorphosis.blind_bank_protocol import canonical_bytes, sha256_hex  # noqa: E402
from scripts import run_m113_qualification as inherited  # noqa: E402

MEASUREMENTS_SCHEMA = "m119-h64-measurements-v1"
SCORE_KEYS = inherited.SCORE_KEYS


class QualificationError(RuntimeError):
    """H64 qualification cannot proceed honestly. Every path fails closed."""


def restore_acquired() -> dict[str, Any]:
    """The acquired cascade and policy, from the producers' frozen bytes.

    Taken out of the inherited restoration rather than decoded again, so the provenance path is the
    one the predecessor milestones already prove.
    """
    restored = inherited.restore_arms()
    cascades = restored["cascades"]
    cascade_rules = cascades["M2"]["rules"]
    policy = cascades["M3"]["policy"]
    if not policy:
        raise QualificationError("the acquired diagnostic policy did not restore")
    if not cascade_rules:
        raise QualificationError("the acquired cascade did not restore")
    return {"cascade_rules": cascade_rules, "policy": policy,
            "pooled_record": restored["record"],
            "provenance_checks": restored["provenance_checks"],
            "corruption": restored["corruption"]}


def load_carriers(path: Path, nonce: str) -> list[dict[str, Any]]:
    """The revealed carrier payload, read as the payload it is.

    `reveal_m119_bank.py` writes the frozen carrier payload -- an object carrying `schema`,
    `bank_nonce` and `carriers` -- not a bare list. Reading it as a list would silently iterate the
    payload's keys and measure nothing, so the shape and the nonce are both checked here.
    """
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping) or not isinstance(value.get("carriers"), list):
        raise QualificationError(
            "the carrier file is not a revealed carrier payload carrying a `carriers` list")
    if value.get("bank_nonce") != nonce:
        raise QualificationError(
            "the carrier payload was enveloped under a different bank nonce than the one supplied")
    return [dict(carrier) for carrier in value["carriers"]]


def measure(carriers: Sequence[Mapping[str, Any]], nonce: str, plan: Mapping[str, Any],
            *, provenance: Mapping[str, Any]) -> dict[str, Any]:
    """Every arm, every qualifying carrier, every demand. Evidence only."""
    session_budget = int(plan["session_budget"])
    acquired = restore_acquired()
    entries: list[dict[str, Any]] = []
    qualifying = 0
    signatures: Counter = Counter()

    for index, carrier in enumerate(carriers):
        if not evaluator.qualification_report(carrier)["qualifies"]:
            continue
        qualifying += 1
        signatures[host.structural_signature(carrier)] += 1
        reference = carrier.get("carrier_ref") or inherited.opaque_domain_id(nonce, index)

        for pair in evaluator.derive_demand_pairs(carrier, reference, session_budget):
            evaluator.assert_demand_pair_delta(pair)
            truth = pair["ground_truth"]
            cascades = arms.build_arms(acquired["cascade_rules"], acquired["policy"],
                                       str(reference), str(pair["pair_digest"]))
            # The inherited state builder, unchanged. The pooled record accompanies the policy
            # because it is the record the policy consults; a policy without it would be inert.
            # That is acquired state, and it is disclosed as such rather than described as
            # "the policy alone".
            states = inherited.build_states(cascades, acquired["pooled_record"],
                                            pair["shared"]["entry"])
            record: dict[str, Any] = {
                "carrier_ref": str(reference),
                "carrier_digest": carrier["carrier_digest"],
                "pair_digest": pair["pair_digest"],
                "ground_truth_component": truth["component"],
                "ground_truth_row": truth["row_index"],
                "arms": {},
            }
            for name in arms.ALL_ARM_NAMES:
                state = states[name]
                budget = session_budget * arms.BUDGET_MULTIPLIER.get(name, 1)
                arm_record: dict[str, Any] = {"budget": budget}
                for demand_class in evaluator.DEMAND_CLASSES:
                    demand = evaluator.materialize_twin(pair, demand_class)
                    channel = host.Channel(carrier, reference, budget)
                    outcome = runtime.resolve(state, channel, demand)
                    score = evaluator.score_attempt(carrier, demand, outcome)
                    row: dict[str, Any] = {
                        "verdict": outcome["verdict"],
                        "invocations_used": outcome["invocations_used"],
                        "probes_spent": outcome["probes_spent"],
                        "budget": budget,
                        # Recorded per demand so a negative can be attributed rather than
                        # guessed at: an exploration that runs out of observations does not
                        # close, and everything downstream of it is `undetermined`.
                        "budget_exhausted": bool(
                            outcome["invocations_used"] >= budget),
                        "within_budget": bool(score["within_budget"]),
                        "primary_success": endpoint.primary_success(demand_class, score),
                        "score": {key: bool(score[key]) for key in SCORE_KEYS},
                    }
                    if outcome["trace"] and demand_class == evaluator.CLASS_REACHABLE:
                        attributed = outcome["trace"][0]["attribution"]["component"]
                        row["attributed_component"] = attributed
                        row["attribution_correct"] = bool(attributed == truth["component"])
                    arm_record[demand_class] = row
                record["arms"][name] = arm_record
            entries.append(record)

    record = {
        "schema": MEASUREMENTS_SCHEMA,
        "milestone": "M119", "hypothesis": "H64",
        "arms_version": arms.ARMS_VERSION,
        "endpoint_version": endpoint.ENDPOINT_VERSION,
        "arm_names": list(arms.ARM_NAMES),
        "diagnostic_arm_names": list(arms.DIAGNOSTIC_ARM_NAMES),
        "budget_multiplier": dict(arms.BUDGET_MULTIPLIER),
        "descendant_arm": arms.DESCENDANT_ARM,
        "comparator_arm": arms.COMPARATOR_ARM,
        "fresh_seed": arms.FRESH_SEED,
        "fresh_seed_source": arms.FRESH_SEED_SOURCE,
        "action_space": arms.action_space_statement(),
        "provenance_checks": acquired["provenance_checks"],
        "corruption": acquired["corruption"],
        "analysis_plan_commitment_sha256": plan["plan_commitment_sha256"],
        "session_budget": session_budget,
        "session_budget_came_from_the_committed_plan_not_the_command_line": True,
        "carriers_seen": len(carriers),
        "qualifying_carriers": qualifying,
        "distinct_qualifying_structures": len(signatures),
        "demand_classes": list(evaluator.DEMAND_CLASSES),
        "entries": entries,
        "the_runner_records_evidence_and_decides_nothing": True,
        # What this measurement is bound to: the tested-system freeze it ran under and the reveal
        # whose carriers it read. Digested once, below, with everything else.
        "freeze_commitment_sha256": provenance["freeze_commitment_sha256"],
        "reveal_record_sha256": provenance["reveal_record_sha256"],
        "carrier_bank_sha256": provenance["carrier_bank_sha256"],
        "measurements_sha256": "",
    }
    record["measurements_sha256"] = sha256_hex(
        canonical_bytes({k: v for k, v in record.items() if k != "measurements_sha256"}))
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--carriers", type=Path, required=True)
    parser.add_argument("--nonce", required=True)
    parser.add_argument("--plan", type=Path, required=True,
                        help="the committed H64 analysis plan; the budget comes from here")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    try:
        # The pre-generation freeze is necessary and not sufficient. Once a completion exists,
        # nothing in that earlier check stops an edit to the evaluator, the demand derivation or
        # the scoring before the result is computed, so the freeze is re-proved here.
        permission = chronology.assert_frozen_system_unchanged(ROOT, phase="scoring")
        reveal = json.loads((ROOT / chronology.REVEAL_RECORD).read_text(encoding="utf-8"))
        carrier_digest = sha256_hex(canonical_bytes(
            json.loads(args.carriers.read_text(encoding="utf-8"))))
        if carrier_digest != reveal["carrier_bank_sha256"]:
            raise QualificationError(
                "these carriers are not the ones the committed reveal record names")
        plan = json.loads(args.plan.read_text(encoding="utf-8"))
        carriers = load_carriers(args.carriers, args.nonce)
        record = measure(carriers, args.nonce, plan, provenance={
            "freeze_commitment_sha256": permission["freeze_commitment_sha256"],
            "reveal_record_sha256": reveal["reveal_record_sha256"],
            "carrier_bank_sha256": carrier_digest,
        })
    except (QualificationError, chronology.ChronologyError, endpoint.EndpointError) as exc:
        print("REFUSED: %s" % exc)
        return 1
    args.out.write_bytes(canonical_bytes(record) + b"\n")
    print(json.dumps({"qualifying_carriers": record["qualifying_carriers"],
                      "paired_demands": len(record["entries"]) * len(evaluator.DEMAND_CLASSES),
                      "measurements_sha256": record["measurements_sha256"]},
                     indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
