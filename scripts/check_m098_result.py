"""Recompute M098's frozen hard process-death persistence verdict."""

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

from author_m098_qualification_pool import (  # noqa: E402
    audit as audit_pool,
    build_pool,
    canonical_json,
    digest,
    load_pool,
)
from run_m095_qualification import file_set_digest  # noqa: E402
from run_m098_qualification import (  # noqa: E402
    M097_RESULT_PATH,
    mechanism_digest,
    run_experiment,
    stable_projection,
)

EXPERIMENT = ROOT / "experiments" / "M098"
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
        identifier,
        name,
        True,
        not failures,
        "satisfied" if not failures else "; ".join(failures),
        detail or {},
    )


def _uncomputed(identifier: str, name: str) -> Condition:
    return Condition(
        identifier,
        name,
        False,
        None,
        "no armed RESULT.json exists; development evidence is not substituted",
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
        measured, _members = mechanism_digest(protocol)
        apparatus, _apparatus_members = file_set_digest(protocol, "qualification_apparatus")
        if measured != protocol.get("mechanism", {}).get("digest"):
            failures.append("mechanism moved after freeze")
        if apparatus != protocol.get("qualification_apparatus", {}).get("digest"):
            failures.append("apparatus moved after freeze")
    except Exception as error:  # noqa: BLE001
        failures.append(f"bindings could not be recomputed: {error}")
    m097 = json.loads(M097_RESULT_PATH.read_text(encoding="utf-8"))
    state = m097.get("scientific_evidence", {}).get("extended_language_state", {})
    binding = protocol.get("m097_input", {})
    if binding.get("result_digest") != m097.get("result_digest"):
        failures.append("protocol does not bind the preserved M097 result")
    if binding.get("state_digest") != state.get("state_digest"):
        failures.append("protocol does not bind the preserved M097 state")
    return _condition("P1", "frozen_protocol_pool_mechanism_checker_and_m097_input_are_bound", failures)


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
    if pool.get("m097_development_and_qualification_worlds_excluded") is not True:
        failures.append("M097 worlds were not explicitly excluded")
    return _condition(
        "P2",
        "fresh_post_m097_population_is_complete_buildable_and_unrun_before_freeze",
        failures,
        {"entries": len(pool.get("entries", [])), "preflight": audit.get("passed")},
    )


def _consumer_runs(evidence: dict[str, object]) -> list[dict[str, object]]:
    return (
        [row["fresh"] for row in evidence["post_restart_worlds"]]
        + list(evidence["controls"].values())
        + [evidence["rollback"]["during_fault"], evidence["rollback"]["after_restore"]]
    )


def run_conditions(
    protocol: dict[str, object],
    pool: dict[str, object],
    result: dict[str, object],
    replay: dict[str, object],
) -> list[Condition]:
    m097 = json.loads(M097_RESULT_PATH.read_text(encoding="utf-8"))
    m097_state = m097["scientific_evidence"]["extended_language_state"]

    producer = replay["producer"]
    state = replay["state"]
    failures = []
    if producer.get("producer_returncode") != 0:
        failures.append("producer did not exit successfully")
    if producer.get("producer_process_is_terminated") is not True:
        failures.append("producer remained alive")
    if producer.get("producer_stdout_matches_manifest") is not True:
        failures.append("producer stdout differs from its disk manifest")
    if producer.get("m097_result_digest") != m097.get("result_digest"):
        failures.append("producer persisted another M097 result")
    if producer.get("state_digest") != m097_state.get("state_digest"):
        failures.append("producer persisted another M097 state")
    if producer.get("state_raw_sha256") != state.get("raw_sha256"):
        failures.append("consumer input bytes differ from producer output")
    if producer.get("bytes_written") != state.get("bytes"):
        failures.append("persisted byte count differs")
    p3 = _condition("P3", "separate_producer_persists_exact_m097_state_then_terminates", failures)

    failures = []
    capsule = replay["capsule"]
    if capsule.get("members") != ["m098_runtime.py", "run.py"]:
        failures.append("capsule has an unexpected member census")
    if capsule.get("contains_only_runtime_and_entrypoint") is not True:
        failures.append("capsule purity assertion is false")
    expected_digests = {
        "m098_runtime.py": hashlib.sha256(
            (ROOT / "metamorphosis" / "m098_runtime.py").read_bytes()
        ).hexdigest(),
        "run.py": hashlib.sha256(
            (ROOT / "scripts" / "run_m098_fresh_process.py").read_bytes()
        ).hexdigest(),
    }
    if capsule.get("member_digests") != expected_digests:
        failures.append("capsule members differ from the frozen runtime sources")
    required = {
        "metamorphosis/m098_runtime.py",
        "scripts/run_m098_fresh_process.py",
        "scripts/run_m098_persist_producer.py",
    }
    if not required <= set(protocol.get("mechanism", {}).get("files", [])):
        failures.append("frozen mechanism omits a process-boundary component")
    p4 = _condition("P4", "isolated_capsule_contains_only_bound_generic_runtime", failures)

    failures = []
    worlds = replay["post_restart_worlds"]
    expected_entries = {entry["id"]: entry for entry in pool["entries"]}
    if {row.get("entry") for row in worlds} != set(expected_entries):
        failures.append("post-restart world census differs from the frozen population")
    for row in worlds:
        entry = expected_entries.get(row.get("entry"))
        fresh = row.get("fresh", {})
        runtime = fresh.get("runtime", {})
        if entry is None or row.get("entry_digest") != entry.get("entry_digest"):
            failures.append(f"{row.get('entry')} has the wrong content address")
        if fresh.get("returncode") != 0 or runtime.get("confirmed") is not True:
            failures.append(f"{row.get('entry')} was not confirmed after restart")
        if runtime.get("cases") != 4 or runtime.get("extensions_loaded") != 1:
            failures.append(f"{row.get('entry')} did not use four cases and one extension")
        if runtime.get("state_digest") != m097_state.get("state_digest"):
            failures.append(f"{row.get('entry')} did not load the M097 state")
    p5 = _condition(
        "P5",
        "persisted_extension_executes_all_fresh_post_restart_worlds",
        failures,
        {"confirmed": sum(bool(row["fresh"]["runtime"].get("confirmed")) for row in worlds),
         "required": len(pool["entries"])},
    )

    failures = []
    consumer_runs = _consumer_runs(replay)
    root_text = str(ROOT.resolve()).casefold()
    for index, run in enumerate(consumer_runs):
        runtime = run.get("runtime", {})
        if runtime.get("isolated_mode") is not True:
            failures.append(f"consumer {index} was not launched in isolated mode")
        if runtime.get("imported_project_modules") != []:
            failures.append(f"consumer {index} imported project modules")
        if any(root_text in str(path).casefold() for path in runtime.get("search_path", [])):
            failures.append(f"consumer {index} retained a repository search path")
    p6 = _condition("P6", "fresh_consumers_have_no_repository_or_acquisition_module_access", failures)

    inherited = replay["controls"]["inherited_without_extension"]
    failures = []
    if inherited.get("returncode") != 1 or inherited["runtime"].get("confirmed") is not False:
        failures.append("extension-absent control did not fail normally")
    if inherited["runtime"].get("extensions_loaded") != 0:
        failures.append("extension-absent control loaded an extension")
    if inherited["runtime"].get("extensions_tested") != 0:
        failures.append("extension-absent control tested an extension")
    p7 = _condition("P7", "persisted_extension_is_necessary_after_restart", failures)

    mutation = replay["controls"]["semantic_mutation"]
    corrupt = replay["controls"]["corrupt_digest"]
    failures = []
    if mutation.get("returncode") != 1 or mutation["runtime"].get("confirmed") is not False:
        failures.append("semantic mutation control did not fail")
    if mutation["runtime"].get("extensions_loaded") != 1:
        failures.append("semantic mutation did not preserve a well-formed extension")
    if corrupt.get("returncode") != 3 or corrupt["runtime"].get("failed_closed") is not True:
        failures.append("corrupt state did not fail closed")
    if corrupt["runtime"].get("confirmed") is not False:
        failures.append("corrupt state was confirmed")
    p8 = _condition("P8", "semantic_mutation_and_digest_corruption_controls_fail", failures)

    boundary = replay["process_boundary"]
    failures = []
    if boundary.get("producer_terminated_before_consumers") is not True:
        failures.append("producer termination was not established before consumers")
    if boundary.get("fresh_process_invocations") != 8:
        failures.append("fresh-process invocation census is not eight")
    if boundary.get("consumer_pid_records_present") is not True:
        failures.append("one or more consumers omitted its process identifier")
    if boundary.get("all_consumers_are_distinct_from_producer") is not True:
        failures.append("a consumer ran in the producer process")
    if len(boundary.get("consumer_pids", [])) != 8:
        failures.append("consumer PID census is not eight")
    p9 = _condition("P9", "producer_death_and_fresh_consumer_process_boundaries_are_observed", failures)

    rollback = replay["rollback"]
    failures = []
    if rollback.get("before_fault_sha256") != state.get("raw_sha256"):
        failures.append("fault did not start from the canonical persisted bytes")
    during = rollback["during_fault"]
    if during.get("returncode") != 1 or during["runtime"].get("confirmed") is not False:
        failures.append("live semantic fault did not suppress the capability")
    if during["runtime"].get("state_raw_sha256") != mutation["runtime"].get("state_raw_sha256"):
        failures.append("live fault bytes differ from the semantic mutation control")
    p10 = _condition("P10", "live_state_fault_suppresses_capability_in_a_new_process", failures)

    failures = []
    after = rollback["after_restore"]
    if rollback.get("restored_bytes_equal") is not True:
        failures.append("rollback was not byte exact")
    if rollback.get("after_restore_sha256") != rollback.get("before_fault_sha256"):
        failures.append("restored raw digest differs from the pre-fault digest")
    if after.get("returncode") != 0 or after["runtime"].get("confirmed") is not True:
        failures.append("fresh process did not recover the capability after rollback")
    if after["runtime"].get("state_digest") != m097_state.get("state_digest"):
        failures.append("recovered process loaded another state")
    p11 = _condition("P11", "byte_exact_rollback_restores_capability_in_a_third_process", failures)

    failures = []
    if digest(stable_projection(result.get("scientific_evidence"))) != digest(stable_projection(replay)):
        failures.append("recorded stable evidence differs from clean replay")
    if result.get("stable_evidence_digest") != digest(stable_projection(replay)):
        failures.append("stable replay digest mismatch")
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
    if result.get("m097_result_digest") != m097.get("result_digest"):
        failures.append("result used another M097 result")
    if result.get("m097_state_digest") != m097_state.get("state_digest"):
        failures.append("result used another M097 state")
    if result.get("protocol_raw_sha256") != hashlib.sha256(PROTOCOL_PATH.read_bytes()).hexdigest():
        failures.append("result used another protocol")
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
    p12 = _condition("P12", "stable_replay_chronology_track_a_and_local_only_execution", failures)

    return [p3, p4, p5, p6, p7, p8, p9, p10, p11, p12]


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
        "schema": "m098-checker-v1",
        "milestone": "M098",
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
