"""Recompute M099's frozen stable hard-persistence verdict."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from author_m099_qualification_pool import (  # noqa: E402
    audit as audit_pool,
    build_pool,
    canonical_json,
    digest,
    load_pool,
)
from check_m098_result import Condition, _condition, _uncomputed  # noqa: E402
from check_m098_result import run_conditions as m098_run_conditions  # noqa: E402
from run_m095_qualification import file_set_digest  # noqa: E402
from run_m099_qualification import (  # noqa: E402
    EPHEMERAL_KEYS,
    M097_RESULT_PATH,
    M098_CHECK_PATH,
    M098_RESULT_PATH,
    mechanism_digest,
    run_experiment,
    stable_projection,
)

EXPERIMENT = ROOT / "experiments" / "M099"
PROTOCOL_PATH = EXPERIMENT / "PROTOCOL.json"
RESULT_PATH = EXPERIMENT / "RESULT.json"


def load_result() -> dict[str, object] | None:
    return json.loads(RESULT_PATH.read_text(encoding="utf-8")) if RESULT_PATH.exists() else None


def check_p1(protocol: dict[str, object], pool: dict[str, object]) -> Condition:
    failures = []
    if protocol.get("status") != "frozen" or pool.get("status") != "frozen":
        failures.append("protocol or pool is not frozen")
    if protocol.get("qualification_population", {}).get("pool_digest") != pool.get("pool_digest"):
        failures.append("protocol does not bind the pool")
    try:
        measured, _members = mechanism_digest(protocol)
        apparatus, _apparatus_members = file_set_digest(protocol, "qualification_apparatus")
        if measured != protocol.get("mechanism", {}).get("digest"):
            failures.append("mechanism moved after freeze")
        if apparatus != protocol.get("qualification_apparatus", {}).get("digest"):
            failures.append("apparatus moved after freeze")
    except Exception as error:  # noqa: BLE001
        failures.append(f"bindings could not be recomputed: {error}")
    m097 = json.loads(M097_RESULT_PATH.read_text(encoding="utf-8"))
    m098 = json.loads(M098_RESULT_PATH.read_text(encoding="utf-8"))
    m098_check = json.loads(M098_CHECK_PATH.read_text(encoding="utf-8"))
    inputs = protocol.get("preserved_inputs", {})
    expected = {
        "m097_result_digest": m097.get("result_digest"),
        "m097_state_digest": m097.get("scientific_evidence", {}).get(
            "extended_language_state", {}
        ).get("state_digest"),
        "m098_result_digest": m098.get("result_digest"),
        "m098_checker_digest": m098_check.get("report_digest"),
    }
    for key, value in expected.items():
        if inputs.get(key) != value:
            failures.append(f"protocol does not bind {key}")
    if m098_check.get("verdict") != "negative" or m098_check.get("failed_conditions") != ["P12"]:
        failures.append("M098 preserved predecessor is not the disclosed P12-only negative")
    if set(protocol.get("stable_projection", {}).get("excluded_keys", [])) != EPHEMERAL_KEYS:
        failures.append("protocol does not bind the complete ephemeral-key policy")
    return _condition(
        "P1", "frozen_protocol_pool_mechanism_checker_inputs_and_projection_are_bound", failures
    )


def check_p2(pool: dict[str, object]) -> Condition:
    failures = []
    if pool != build_pool(status="frozen"):
        failures.append("committed pool differs from the authored frozen population")
    audit = audit_pool(pool)
    if not audit.get("passed"):
        failures.append("one or more S0 worlds fail preflight")
    if any(audit.get(key) is not False for key in (
        "producer_was_run", "fresh_runtime_was_run", "fault_was_injected"
    )):
        failures.append("preflight crossed the process-persistence boundary")
    if len(pool.get("entries", [])) != 3:
        failures.append("qualification does not contain all three frozen worlds")
    if pool.get("m097_and_m098_worlds_excluded") is not True:
        failures.append("predecessor worlds were not explicitly excluded")
    return _condition(
        "P2", "fresh_post_m098_population_is_complete_buildable_and_unrun_before_freeze",
        failures, {"entries": len(pool.get("entries", [])), "preflight": audit.get("passed")}
    )


def check_p12(
    protocol: dict[str, object],
    pool: dict[str, object],
    result: dict[str, object],
    replay: dict[str, object],
) -> Condition:
    failures = []
    recorded_projection = stable_projection(result.get("scientific_evidence"))
    replay_projection = stable_projection(replay)
    if digest(recorded_projection) != digest(replay_projection):
        failures.append("recorded stable evidence differs from clean replay")
    if result.get("stable_evidence_digest") != digest(replay_projection):
        failures.append("stable replay digest mismatch")
    if any(key in recorded_projection.get("process_boundary", {}) for key in EPHEMERAL_KEYS):
        failures.append("stable process boundary retains an ephemeral key")
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
    m097 = json.loads(M097_RESULT_PATH.read_text(encoding="utf-8"))
    m098 = json.loads(M098_RESULT_PATH.read_text(encoding="utf-8"))
    m098_check = json.loads(M098_CHECK_PATH.read_text(encoding="utf-8"))
    expected = {
        "m097_result_digest": m097["result_digest"],
        "m097_state_digest": m097["scientific_evidence"]["extended_language_state"]["state_digest"],
        "m098_result_digest": m098["result_digest"],
        "m098_checker_digest": m098_check["report_digest"],
    }
    for key, value in expected.items():
        if result.get(key) != value:
            failures.append(f"result differs on {key}")
    measured, _members = mechanism_digest(protocol)
    apparatus, _apparatus_members = file_set_digest(protocol, "qualification_apparatus")
    if result.get("mechanism_digest") != measured:
        failures.append("result mechanism digest mismatch")
    if result.get("qualification_apparatus_digest") != apparatus:
        failures.append("result apparatus digest mismatch")
    withdrawn = sorted(path.name for path in EXPERIMENT.glob("WITHDRAWN_RESULT_*.json"))
    if result.get("prior_attempts") != withdrawn or result.get("attempt") != len(withdrawn) + 1:
        failures.append("attempt provenance does not match preserved artifacts")
    recomputed = digest({key: value for key, value in result.items() if key != "result_digest"})
    if result.get("result_digest") != recomputed:
        failures.append("result digest mismatch")
    return _condition(
        "P12", "stable_replay_chronology_track_a_and_local_only_execution", failures
    )


def run_conditions(protocol, pool, result, replay) -> list[Condition]:
    predecessor_conditions = m098_run_conditions(protocol, pool, result, replay)[:-1]
    return predecessor_conditions + [check_p12(protocol, pool, result, replay)]


def compute_report(protocol, pool, result):
    conditions = [check_p1(protocol, pool), check_p2(pool)]
    names = [
        "separate_producer_persists_exact_m097_state_then_terminates",
        "isolated_capsule_contains_only_bound_generic_runtime",
        "persisted_extension_executes_all_fresh_post_restart_worlds",
        "fresh_consumers_have_no_repository_or_acquisition_module_access",
        "persisted_extension_is_necessary_after_restart",
        "semantic_mutation_and_digest_corruption_controls_fail",
        "producer_death_and_fresh_consumer_process_boundaries_are_observed",
        "live_state_fault_suppresses_capability_in_a_new_process",
        "byte_exact_rollback_restores_capability_in_a_third_process",
        "stable_replay_chronology_track_a_and_local_only_execution",
    ]
    if result is None:
        conditions.extend(_uncomputed(f"P{index}", name) for index, name in enumerate(names, 3))
    else:
        conditions.extend(run_conditions(protocol, pool, result, run_experiment(pool)))
    failed = [item.id for item in conditions if item.computed and item.passed is False]
    uncomputed = [item.id for item in conditions if not item.computed]
    verdict = "negative" if failed else ("incomplete" if uncomputed else "positive")
    report = {
        "schema": "m099-checker-v1",
        "milestone": "M099",
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
