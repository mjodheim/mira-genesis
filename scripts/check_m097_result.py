"""Recompute M097's frozen endogenous operation-acquisition verdict."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from author_m097_qualification_pool import (  # noqa: E402
    audit as audit_pool,
    build_pool,
    canonical_json,
    digest,
    load_pool,
)
from run_m095_qualification import file_set_digest  # noqa: E402
from run_m097_qualification import mechanism_digest, run_experiment  # noqa: E402

EXPERIMENT = ROOT / "experiments" / "M097"
PROTOCOL_PATH = EXPERIMENT / "PROTOCOL.json"
RESULT_PATH = EXPERIMENT / "RESULT.json"


@dataclass
class Condition:
    id: str
    name: str
    computed: bool
    passed: bool | None
    evidence: str
    detail: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "computed": self.computed,
            "passed": self.passed,
            "evidence": self.evidence,
            "detail": self.detail,
        }


def _condition(identifier: str, name: str, failures: list[str], detail=None) -> Condition:
    return Condition(
        identifier, name, True, not failures,
        "satisfied" if not failures else "; ".join(failures), detail or {}
    )


def _uncomputed(identifier: str, name: str) -> Condition:
    return Condition(
        identifier, name, False, None,
        "no armed RESULT.json exists; development evidence is not substituted"
    )


def load_result() -> dict[str, object] | None:
    return json.loads(RESULT_PATH.read_text(encoding="utf-8")) if RESULT_PATH.exists() else None


def check_p1(protocol: dict[str, object], pool: dict[str, object]) -> Condition:
    failures = []
    if protocol.get("status") != "frozen" or pool.get("status") != "frozen":
        failures.append("protocol or pool is not frozen")
    if protocol.get("qualification_population", {}).get("pool_digest") != pool.get("pool_digest"):
        failures.append("protocol does not bind the pool")
    try:
        mechanism, _members = mechanism_digest(protocol)
        apparatus, _apparatus_members = file_set_digest(protocol, "qualification_apparatus")
        if mechanism != protocol.get("mechanism", {}).get("digest"):
            failures.append("mechanism moved after freeze")
        if apparatus != protocol.get("qualification_apparatus", {}).get("digest"):
            failures.append("apparatus moved after freeze")
    except Exception as error:  # noqa: BLE001
        failures.append(f"bindings could not be recomputed: {error}")
    return _condition("P1", "frozen_protocol_pool_mechanism_and_checker_are_bound", failures)


def check_p2(pool: dict[str, object]) -> Condition:
    failures = []
    if pool != build_pool(status="frozen"):
        failures.append("committed pool differs from the authored frozen population")
    audit = audit_pool(pool)
    if not audit["passed"]:
        failures.append("one or more S0 worlds fail preflight")
    if audit["acquisition_was_run"] is not False or audit["extended_search_was_run"] is not False:
        failures.append("preflight crossed the acquisition boundary")
    if len(pool.get("entries", [])) != 4:
        failures.append("qualification does not contain all four frozen worlds")
    return _condition(
        "P2", "fresh_population_is_complete_buildable_and_unrun_before_freeze",
        failures, {"entries": len(pool.get("entries", [])), "preflight": audit["passed"]}
    )


def run_conditions(
    protocol: dict[str, object],
    pool: dict[str, object],
    result: dict[str, object],
    replay: dict[str, object],
) -> list[Condition]:
    del protocol
    failures = []
    certificate = replay["inherited_insufficiency"]
    if certificate.get("outside_constructive_image_at_any_bound") is not True:
        failures.append("inherited closure certificate does not exclude the requirement")
    if replay["inherited_before"].get("execution_confirmed") is not False:
        failures.append("inherited language reached the development requirement")
    p3 = _condition("P3", "inherited_language_is_provably_insufficient_at_any_bound", failures)

    failures = []
    acquisition = replay["acquisition"]
    if int(acquisition.get("candidates_assembled", 0)) != 2800:
        failures.append("assembly did not exhaust all 2,800 bounded programs")
    adopted = acquisition.get("adopted") or {}
    body = adopted.get("body", []) if isinstance(adopted, dict) else []
    if len(body) != 3:
        failures.append("adopted definition is not a minimal three-instruction construction")
    if int(acquisition.get("accepted_candidates", 0)) < 1:
        failures.append("assembly accepted no operation")
    if not acquisition.get("rejection_counts"):
        failures.append("assembly exposes no rejected candidate classes")
    p4 = _condition("P4", "operation_is_assembled_from_microinstructions_not_selected_finished", failures)

    validation = replay["independent_validation"]
    failures = []
    if validation.get("accepted") is not True:
        failures.append("independent validator refused the adopted definition")
    if int(validation.get("cases_passed", 0)) != 5:
        failures.append("validator did not pass all five development cases")
    p5 = _condition("P5", "independent_validator_accepts_without_qualification_access", failures)

    before = replay["inherited_language_state"]
    after = replay["extended_language_state"]
    failures = []
    if len(before.get("extensions", [])) != 0 or len(after.get("extensions", [])) != 1:
        failures.append("registration did not change the language from zero to one extension")
    if before.get("state_digest") == after.get("state_digest"):
        failures.append("registered state has the inherited digest")
    p6 = _condition("P6", "registration_changes_the_state_owned_operation_language", failures)

    failures = []
    if replay["inherited_before"].get("execution_confirmed") is not False:
        failures.append("development requirement was reachable before registration")
    if replay["development_after_registration"].get("execution_confirmed") is not True:
        failures.append("development requirement was not execution-confirmed after registration")
    p7 = _condition("P7", "registration_changes_real_python_constructive_reach", failures)

    failures = []
    rows = replay["qualification"]
    if len(rows) != len(pool["entries"]):
        failures.append("not every qualification world ran")
    for row in rows:
        if row["inherited"].get("execution_confirmed") is not False:
            failures.append(f"{row['entry']} was reachable in the inherited language")
        if row["extended"].get("execution_confirmed") is not True:
            failures.append(f"{row['entry']} was not reached by the acquired operation")
    p8 = _condition(
        "P8", "acquired_operation_generalizes_to_every_fresh_real_python_world",
        failures, {"extended": sum(bool(row["extended"]["execution_confirmed"]) for row in rows),
                   "required": len(pool["entries"])}
    )

    failures = []
    budget = replay["controls"]["more_budget_same_language"]
    if budget.get("same_language_more_budget_cannot_help") is not True:
        failures.append("same-language more-budget control is not closed by the invariant")
    if replay["controls"].get("acquisition_ablated_correct_worlds") != 0:
        failures.append("acquisition-ablated language solved a qualification world")
    p9 = _condition("P9", "more_budget_and_acquisition_ablation_close_nothing", failures)

    failures = []
    if replay["built_not_registered"].get("execution_confirmed") is not False:
        failures.append("a built but unregistered operation changed reach")
    p10 = _condition("P10", "building_without_registration_changes_nothing", failures)

    failures = []
    if replay.get("restored_state_equals_extended") is not True:
        failures.append("serialized language state did not round-trip")
    conservation = replay["conservation"]
    if conservation.get("inherited_unchanged") is not True:
        failures.append("inherited operation language changed during extension")
    if (conservation.get("extensions_before"), conservation.get("extensions_after")) != (0, 1):
        failures.append("extension census differs across persistence")
    p11 = _condition("P11", "serialized_extension_round_trips_and_inherited_language_is_conserved", failures)

    failures = []
    if digest(result.get("scientific_evidence")) != digest(replay):
        failures.append("recorded scientific evidence differs from clean replay")
    if result.get("track") != "A":
        failures.append("result is not Track A")
    if result.get("model_calls") != 0 or result.get("network_calls") != 0:
        failures.append("model or network calls entered qualification")
    if result.get("remote_execution") is not False:
        failures.append("qualification was not local-only")
    if result.get("working_tree_was_dirty_at_recording") is not False:
        failures.append("qualification did not start from a clean freeze commit")
    if result.get("pool_digest") != pool.get("pool_digest"):
        failures.append("result used another pool")
    if result.get("protocol_raw_sha256") != hashlib.sha256(PROTOCOL_PATH.read_bytes()).hexdigest():
        failures.append("result used another protocol")
    withdrawn = sorted(path.name for path in EXPERIMENT.glob("WITHDRAWN_RESULT_*.json"))
    if result.get("prior_attempts") != withdrawn or result.get("attempt") != len(withdrawn) + 1:
        failures.append("attempt provenance does not match preserved artifacts")
    recomputed = digest({key: value for key, value in result.items() if key != "result_digest"})
    if result.get("result_digest") != recomputed:
        failures.append("result digest mismatch")
    p12 = _condition("P12", "replay_chronology_track_a_and_local_only_execution", failures)
    return [p3, p4, p5, p6, p7, p8, p9, p10, p11, p12]


def compute_report(protocol, pool, result):
    conditions = [check_p1(protocol, pool), check_p2(pool)]
    names = [
        "inherited_language_is_provably_insufficient_at_any_bound",
        "operation_is_assembled_from_microinstructions_not_selected_finished",
        "independent_validator_accepts_without_qualification_access",
        "registration_changes_the_state_owned_operation_language",
        "registration_changes_real_python_constructive_reach",
        "acquired_operation_generalizes_to_every_fresh_real_python_world",
        "more_budget_and_acquisition_ablation_close_nothing",
        "building_without_registration_changes_nothing",
        "serialized_extension_round_trips_and_inherited_language_is_conserved",
        "replay_chronology_track_a_and_local_only_execution",
    ]
    if result is None:
        conditions.extend(_uncomputed(f"P{index}", name) for index, name in enumerate(names, 3))
    else:
        conditions.extend(run_conditions(protocol, pool, result, run_experiment(pool)))
    failed = [item.id for item in conditions if item.computed and item.passed is False]
    uncomputed = [item.id for item in conditions if not item.computed]
    verdict = "negative" if failed else ("incomplete" if uncomputed else "positive")
    report = {
        "schema": "m097-checker-v1",
        "milestone": "M097",
        "verdict": verdict,
        "passed": sum(bool(item.passed) for item in conditions if item.computed),
        "failed": len(failed),
        "uncomputed": len(uncomputed),
        "failed_conditions": failed,
        "uncomputed_conditions": uncomputed,
        "conditions": {item.id: item.to_dict() for item in conditions},
        "verdict_rule": "positive only when all twelve frozen conditions are computed and true",
    }
    report["report_digest"] = digest(report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--require-result", action="store_true")
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args()
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    pool = load_pool()
    report = compute_report(protocol, pool, load_result())
    if not args.no_write:
        (EXPERIMENT / "CHECK_REPORT.json").write_text(
            canonical_json(report) + "\n", encoding="utf-8", newline="\n"
        )
    print(json.dumps(report, indent=2, sort_keys=True))
    if args.require_result and report["verdict"] != "positive":
        return 1
    if args.strict and report["failed"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
