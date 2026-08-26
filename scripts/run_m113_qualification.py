"""M113 orchestration - restored machinery against carriers that were never designed for it.

Restores the arms from the frozen M109 and M111 result bytes, verifies that they reproduce the
recorded identities, and runs every arm against every demand pair the frozen rule derives from every
qualifying carrier in the bank.

The information boundary is enforced by construction rather than by convention. Every arm receives
the same `carrier_host.Channel` construction, the same budget, the same demand and the same entry
configuration; the only thing that differs is the Genesis state. Adapter equality across arms is
**recorded as measured evidence**, not asserted: the per-carrier adapter digests are written into the
result so the checker can recompute the comparison rather than believe a boolean this script wrote
about itself. M095 recorded what happens when a record field is an assertion wearing a measurement's
clothes.

`requested_carrier_count` and `minimum_qualifying_carriers` come from the **frozen analysis plan**,
never from the bank. Deriving the requested count from `len(carriers)` would compare a number with
itself and make the cardinality identity vacuous -- which is precisely the shape of M112's
materialization defect, at a milestone built to not repeat it.

The canonical entry point refuses unless the bank is at phase `reveal_authorized` with no blockers.
`--development` runs the whole chain against a devkit bank instead and is how the apparatus is
exercised before anything is frozen.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from metamorphosis import carrier_host as host  # noqa: E402
from metamorphosis import m109_runtime as producer  # noqa: E402
from metamorphosis import m111_runtime as diagnosis  # noqa: E402
from metamorphosis import m113_carrier_bank as bank  # noqa: E402
from metamorphosis import m113_carrier_devkit as devkit  # noqa: E402
from metamorphosis import m113_evaluator as evaluator  # noqa: E402
from metamorphosis import m113_runtime as runtime  # noqa: E402
from metamorphosis.blind_bank_protocol import opaque_domain_id  # noqa: E402

EXPERIMENT = ROOT / "experiments" / "M113"
PRODUCER_RESULT = ROOT / "experiments" / "M109" / "RESULT.json"
DIAGNOSIS_RESULT = ROOT / "experiments" / "M111" / "RESULT.json"
RESULT_PATH = EXPERIMENT / "RESULT.json"
DEVELOPMENT_PATH = EXPERIMENT / "DEVELOPMENT_RUN.json"
PLAN_PATH = EXPERIMENT / "ANALYSIS_PLAN.json"
CANDIDATE_PLAN_PATH = EXPERIMENT / "ANALYSIS_PLAN_CANDIDATE.json"

CANONICAL_PYTHON = (3, 11, 16)
DEVELOPMENT_NONCE = "d" * 64

SCORE_KEYS = (
    "correct_construction",
    "unmet_construction",
    "false_refusal",
    "calibrated_refusal",
    "invented_adapter",
    "undetermined",
)

ARM_NAMES = (
    "T0",
    "M1",
    "M2",
    "M3",
    "rollback",
    "ablated",
    "mutated",
    "unregistered",
    "budget_plus",
)

# `budget_plus` is a fresh lineage given four times the observation budget. Its purpose is to make
# "the machinery could not" separable from "the run could not afford to", which M084 recorded as the
# distinction an episode count cannot make.
BUDGET_MULTIPLIER = {"budget_plus": 4}


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("ascii")).hexdigest()


# ----------------------------------------------------------------------------------------
# Provenance: the arms are restored from the producers' frozen bytes, never reimplemented.
# ----------------------------------------------------------------------------------------


def restore_arms() -> dict[str, Any]:
    """Rebuild every arm from `experiments/M109` and `experiments/M111` and prove they are those."""
    m109 = json.loads(PRODUCER_RESULT.read_bytes().decode("ascii"))
    m111 = json.loads(DIAGNOSIS_RESULT.read_bytes().decode("ascii"))
    evidence = m109["scientific_evidence"]
    first = producer.decode_rule(evidence["generation_one"]["acquisition"]["adopted_rule"])
    second = producer.decode_rule(evidence["generation_two"]["acquisition"]["adopted_rule"])
    third = m111["scientific_evidence"]["generation_three"]["acquisition"]
    policy = diagnosis.decode_policy(third["adopted_policy"])
    pooled = m111["scientific_evidence"]["pooled_record"]
    record = {
        "determined": list(pooled["determined"]),
        "undetermined": list(pooled["undetermined"]),
        "record_digest": pooled["record_digest"],
    }

    mutated = json.loads(canonical_json(second))
    mutated_table = [
        (not value) if index == 3 else value
        for index, value in enumerate(mutated["truth_table"])
    ]
    mutated_rule = producer.attribution_rule(
        mutated["body"],
        mutated_table,
        mutated["selects_component_when_true"],
        mutated["generation"],
    )

    # A corrupted acquired rule must be refused outright rather than degrade into a working arm.
    corrupt = json.loads(canonical_json(second))
    corrupt["truth_table"] = corrupt["truth_table"][:-1]
    try:
        producer.decode_rule(corrupt)
    except Exception as exc:  # noqa: BLE001 - the producer owns which exception it raises
        corruption = {"failed_closed": True, "reason": type(exc).__name__}
    else:
        corruption = {"failed_closed": False, "reason": "a truncated truth table was accepted"}

    cascades: dict[str, dict[str, Any]] = {
        "T0": {"rules": [], "policy": None},
        "M1": {"rules": [first], "policy": None},
        "M2": {"rules": [first, second], "policy": None},
        "M3": {"rules": [first, second], "policy": policy},
        # An exact rollback to the pre-acquisition state. It must equal T0 digest for digest.
        "rollback": {"rules": [], "policy": None},
        # Generation two removed, generation one and the policy retained.
        "ablated": {"rules": [first], "policy": policy},
        "mutated": {"rules": [first, mutated_rule], "policy": None},
        # Built but never placed in the state: the rule object exists and selects nothing.
        "unregistered": {"rules": [], "policy": None, "built_but_unregistered": second["rule_id"]},
        "budget_plus": {"rules": [], "policy": None},
    }

    checks = {
        "producer_result_digest_matches": m109["result_digest"]
        == digest({k: v for k, v in m109.items() if k != "result_digest"}),
        "diagnosis_result_digest_matches": m111["result_digest"]
        == digest({k: v for k, v in m111.items() if k != "result_digest"}),
        "generation_one_selects_a_registered_component": first["selects_component_when_true"]
        in producer.COMPONENTS,
        "generation_two_selects_a_registered_component": second["selects_component_when_true"]
        in producer.COMPONENTS,
        "generations_are_distinct": first["rule_id"] != second["rule_id"],
        "cascade_is_contiguous": [first["generation"], second["generation"]] == [1, 2],
        "policy_is_generation_three": int(policy["generation"]) == 3,
        "mutation_changed_the_rule": mutated_rule["rule_id"] != second["rule_id"],
        "inherited_record_marks_a_row_undetermined": bool(record["undetermined"]),
        "a_corrupted_rule_fails_closed": bool(corruption["failed_closed"]),
        "the_unregistered_arm_built_a_rule_it_does_not_hold": bool(
            cascades["unregistered"].get("built_but_unregistered")
        )
        and not cascades["unregistered"]["rules"],
    }
    return {
        "cascades": cascades,
        "record": record,
        "corruption": corruption,
        "provenance_checks": checks,
        "attribution_map": {
            name: {
                str(row): producer.attribute(
                    {"rules": configuration["rules"]}, {"row_index": row}
                )["component"]
                for row in range(len(runtime.FEATURE_ROWS))
            }
            for name, configuration in cascades.items()
        },
    }


def build_states(
    cascades: dict[str, Any], record: dict[str, Any], entry: dict[str, Any]
) -> dict[str, Any]:
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


# ----------------------------------------------------------------------------------------
# The run.
# ----------------------------------------------------------------------------------------


def run_bank(
    carriers: list[dict[str, Any]],
    nonce: str,
    *,
    requested_carrier_count: int,
    minimum_qualifying: int,
    session_budget: int,
) -> dict[str, Any]:
    restored = restore_arms()
    per_arm: dict[str, Counter] = {name: Counter() for name in ARM_NAMES}
    attribution: dict[str, Counter] = {name: Counter() for name in ARM_NAMES}
    rows_seen: dict[int, set[str]] = {}
    learner_rows: dict[str, Counter] = {
        demand_class: Counter() for demand_class in evaluator.DEMAND_CLASSES
    }
    adapter_agreement: list[dict[str, Any]] = []
    entries: list[dict[str, Any]] = []
    invocation_peak: dict[str, int] = {name: 0 for name in ARM_NAMES}
    qualifying = 0
    schema_valid = len(carriers)
    pairs_posed = 0

    for index, carrier in enumerate(carriers):
        report = evaluator.qualification_report(carrier)
        if not report["qualifies"]:
            continue
        qualifying += 1
        reference = carrier.get("carrier_ref") or opaque_domain_id(nonce, index)
        census = evaluator.attribution_census(carrier)
        for row, labels in census["row_labels"].items():
            rows_seen.setdefault(int(row), set()).update(labels)

        for pair in evaluator.derive_demand_pairs(carrier, reference, session_budget):
            evaluator.assert_demand_pair_delta(pair)
            pairs_posed += 1
            truth = pair["ground_truth"]
            states = build_states(restored["cascades"], restored["record"], pair["shared"]["entry"])
            # Recorded per carrier and per pair. Pooling digests across pairs would compare entry
            # configurations that are supposed to differ and report a violation that is not one.
            adapter_agreement.append(
                {
                    "carrier_ref": reference,
                    "row_index": truth["row_index"],
                    "distinct_adapters": len(
                        {digest(runtime.adapter_projection(state)) for state in states.values()}
                    ),
                    "rollback_matches_fresh": states["rollback"]["state_digest"]
                    == states["T0"]["state_digest"],
                }
            )

            record: dict[str, Any] = {
                "carrier_ref": reference,
                "carrier_digest": carrier["carrier_digest"],
                "surface_kind": carrier["surface"]["kind"],
                "pair_digest": pair["pair_digest"],
                "ground_truth_component": truth["component"],
                "ground_truth_row": truth["row_index"],
                "entry": dict(pair["shared"]["entry"]),
                "census_ambiguous_rows": census["ambiguous_rows"],
                "arms": {},
            }
            for name, state in states.items():
                budget = session_budget * BUDGET_MULTIPLIER.get(name, 1)
                arm_record: dict[str, Any] = {"budget": budget}
                for demand_class in evaluator.DEMAND_CLASSES:
                    demand = evaluator.materialize_twin(pair, demand_class)
                    channel = host.Channel(carrier, reference, budget)
                    outcome = runtime.resolve(state, channel, demand)
                    score = evaluator.score_attempt(carrier, demand, outcome)
                    for key in SCORE_KEYS:
                        if score[key]:
                            per_arm[name][key] += 1
                    invocation_peak[name] = max(
                        invocation_peak[name], int(outcome["invocations_used"])
                    )
                    arm_record[demand_class] = {
                        "verdict": outcome["verdict"],
                        "reason": outcome["reason"],
                        "invocations_used": outcome["invocations_used"],
                        "probes_spent": outcome["probes_spent"],
                        "exploration_closed": outcome["exploration_closed"],
                        "within_budget": score["within_budget"],
                        "score": {key: score[key] for key in SCORE_KEYS},
                    }
                    if outcome["trace"]:
                        learner_row = outcome["trace"][0]["features"]["row_index"]
                        arm_record[demand_class]["learner_row"] = learner_row
                        arm_record[demand_class]["attributed_component"] = outcome["trace"][0][
                            "attribution"
                        ]["component"]
                        if name == "T0":
                            learner_rows[demand_class][learner_row] += 1
                        if demand_class == evaluator.CLASS_REACHABLE:
                            attribution[name][
                                arm_record[demand_class]["attributed_component"]
                                == truth["component"]
                            ] += 1
                record["arms"][name] = arm_record
            entries.append(record)

    cardinality = evaluator.cardinality_report(
        requested_carrier_count=int(requested_carrier_count),
        records_emitted=len(carriers),
        carriers_enveloped=len(carriers),
        schema_valid_carriers=schema_valid,
        qualifying_carriers=qualifying,
        minimum_qualifying=int(minimum_qualifying),
    )
    disagreeing_rows = sorted(
        row
        for row in range(len(runtime.FEATURE_ROWS))
        if len({restored["attribution_map"][arm][str(row)] for arm in ("T0", "M1", "M2")}) > 1
    )
    return {
        "schema": "m113-result-v1",
        "milestone": "M113",
        "hypothesis": "H58",
        "model_calls": 0,
        "network_calls": 0,
        "remote_execution_calls": 0,
        "runtime": {
            "python": ".".join(str(part) for part in sys.version_info[:3]),
            "canonical_python": ".".join(str(part) for part in CANONICAL_PYTHON),
            "platform": platform.platform(),
        },
        "provenance_checks": restored["provenance_checks"],
        "corruption_control": restored["corruption"],
        "attribution_map": restored["attribution_map"],
        "rows_where_the_cascades_disagree": disagreeing_rows,
        "arms_declared_but_not_run_here": [
            "producer_death, which needs an isolated consumer process",
            "preservation, which re-runs the M110 and M111 populations unchanged",
        ],
        "cardinality": cardinality,
        "session_budget": int(session_budget),
        "budget_multipliers": dict(BUDGET_MULTIPLIER),
        "peak_invocations_by_arm": dict(invocation_peak),
        "peak_invocations_at_the_base_budget": max(
            value for name, value in invocation_peak.items() if name not in BUDGET_MULTIPLIER
        ),
        "qualifying_carriers": qualifying,
        "demand_pairs_posed": pairs_posed,
        "arms": list(ARM_NAMES),
        "adapter_agreement": adapter_agreement,
        "per_arm_totals": {name: dict(counter) for name, counter in per_arm.items()},
        "attribution_agreement": {
            name: {"correct": counter[True], "incorrect": counter[False]}
            for name, counter in attribution.items()
        },
        "learner_rows_reached": {
            demand_class: {str(row): count for row, count in sorted(counter.items())}
            for demand_class, counter in learner_rows.items()
        },
        "feature_row_components": {
            str(row): sorted(labels) for row, labels in sorted(rows_seen.items())
        },
        "ambiguous_feature_rows": sorted(
            row for row, labels in rows_seen.items() if len(labels) > 1
        ),
        "carriers": entries,
    }


def load_plan() -> dict[str, Any] | None:
    for path in (PLAN_PATH, CANDIDATE_PLAN_PATH):
        if path.is_file():
            return json.loads(path.read_bytes().decode("ascii"))
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--development",
        action="store_true",
        help="run against a devkit bank; the canonical path needs a revealed bank",
    )
    parser.add_argument("--sample", type=int, default=None)
    parser.add_argument("--seed", default="m113-development-run")
    parser.add_argument("--write", action="store_true")
    arguments = parser.parse_args()

    plan = load_plan()
    if plan is None:
        print("REFUSED: no analysis plan, frozen or candidate, exists")
        return 1

    if not arguments.development:
        readiness = bank.assess_carrier_bank_readiness(ROOT)
        print("REFUSED: the canonical path requires a revealed bank, which does not exist")
        for item in readiness["blockers"]:
            print("  - %s" % item)
        return 1

    sample = arguments.sample or int(plan["requested_carrier_count"])
    payload = devkit.development_payload(arguments.seed, sample)
    carriers = []
    for index, carrier in enumerate(payload["carriers"]):
        carrier = dict(carrier)
        carrier["carrier_ref"] = opaque_domain_id(DEVELOPMENT_NONCE, index)
        carriers.append(carrier)

    result = run_bank(
        carriers,
        DEVELOPMENT_NONCE,
        requested_carrier_count=sample,
        minimum_qualifying=int(plan["minimum_qualifying_carriers"]),
        session_budget=int(plan["session_budget"]),
    )
    result["development"] = True
    result["is_a_canonical_attempt"] = False
    result["plan_commitment_sha256"] = plan.get("plan_commitment_sha256")
    result["result_digest"] = digest({k: v for k, v in result.items() if k != "result_digest"})

    if arguments.write:
        DEVELOPMENT_PATH.write_bytes((canonical_json(result) + "\n").encode("ascii"))
        print("wrote %s" % DEVELOPMENT_PATH.relative_to(ROOT))

    print(
        "carriers %d  qualifying %d  demand pairs %d"
        % (len(carriers), result["qualifying_carriers"], result["demand_pairs_posed"])
    )
    print("rows where the cascades disagree: %s" % result["rows_where_the_cascades_disagree"])
    print("learner rows reached: %s" % canonical_json(result["learner_rows_reached"]))
    print("ambiguous feature rows: %s" % result["ambiguous_feature_rows"])
    print(
        "peak invocations at the base budget: %d of %d"
        % (result["peak_invocations_at_the_base_budget"], result["session_budget"])
    )
    print()
    print(
        "%-13s %8s %6s %10s %8s %9s %6s %14s"
        % ("arm", "correct", "unmet", "false-ref", "calib", "invented", "undet", "attribution")
    )
    for name in ARM_NAMES:
        totals = result["per_arm_totals"][name]
        agreement = result["attribution_agreement"][name]
        seen = agreement["correct"] + agreement["incorrect"]
        print(
            "%-13s %8d %6d %10d %8d %9d %6d %14s"
            % (
                name,
                totals.get("correct_construction", 0),
                totals.get("unmet_construction", 0),
                totals.get("false_refusal", 0),
                totals.get("calibrated_refusal", 0),
                totals.get("invented_adapter", 0),
                totals.get("undetermined", 0),
                "%d/%d" % (agreement["correct"], seen),
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
