"""Independently recompute M100's frozen cumulative-acquisition verdict."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from scripts.author_m100_qualification_pool import (
    audit as audit_pool,
    build_pool,
    canonical_json,
    digest,
    load_pool,
)
from scripts.check_m098_result import Condition, _condition, _uncomputed
from scripts.run_m095_qualification import file_set_digest
from scripts.run_m100_qualification import (
    EPHEMERAL_KEYS,
    M097_RESULT_PATH,
    M099_CHECK_PATH,
    M099_RESULT_PATH,
    mechanism_digest,
    run_experiment,
    stable_projection,
)

EXPERIMENT = ROOT / "experiments" / "M100"
PROTOCOL_PATH = EXPERIMENT / "PROTOCOL.json"
RESULT_PATH = EXPERIMENT / "RESULT.json"


def load_result() -> dict[str, object] | None:
    return json.loads(RESULT_PATH.read_text(encoding="utf-8")) if RESULT_PATH.exists() else None


def _success(row: dict[str, object]) -> bool:
    return row.get("returncode") == 0 and row.get("runtime", {}).get("confirmed") is True


def _failure(row: dict[str, object]) -> bool:
    return row.get("returncode") != 0 and row.get("runtime", {}).get("confirmed") is False


def _runtime_rows(value: object) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    if isinstance(value, dict):
        if value.get("schema") == "m100-isolated-runtime-v1":
            rows.append(value)
        for item in value.values():
            rows.extend(_runtime_rows(item))
    elif isinstance(value, list):
        for item in value:
            rows.extend(_runtime_rows(item))
    return rows


def _accepted_count(row: dict[str, object]) -> object:
    return row.get("runtime", {}).get("acquisition", {}).get("accepted_candidates")


def _independent_signature(
    body: list[str], signatures: dict[str, tuple[int, int]]
) -> tuple[int, int] | None:
    stack: list[tuple[int, int]] = []
    for token in body:
        if token == "PUSH_LEFT":
            stack.append((1, 0))
        elif token == "PUSH_RIGHT":
            stack.append((0, 1))
        elif token == "NEG":
            if not stack:
                return None
            left, right = stack.pop()
            stack.append((-left, -right))
        elif token == "SWAP":
            if len(stack) < 2:
                return None
            stack[-1], stack[-2] = stack[-2], stack[-1]
        else:
            if len(stack) < 2:
                return None
            right = stack.pop()
            left = stack.pop()
            if token == "ADD":
                stack.append((left[0] + right[0], left[1] + right[1]))
            elif token == "SUB":
                stack.append((left[0] - right[0], left[1] - right[1]))
            elif token.startswith("CALL:") and token[5:] in signatures:
                a, b = signatures[token[5:]]
                stack.append((
                    a * left[0] + b * right[0],
                    a * left[1] + b * right[1],
                ))
            else:
                return None
    return stack[0] if len(stack) == 1 else None


def check_p1(protocol: dict[str, object], pool: dict[str, object]) -> Condition:
    failures = []
    if protocol.get("status") != "frozen" or pool.get("status") != "frozen":
        failures.append("protocol or pool is not frozen")
    if protocol.get("publication", {}).get("disposition") != "PUBLIC_AGPL_COMMERCIAL_OPTION":
        failures.append("public M100 disposition is not bound")
    if protocol.get("qualification_population", {}).get("pool_digest") != pool.get("pool_digest"):
        failures.append("protocol does not bind the pool")
    try:
        measured, _members = mechanism_digest(protocol)
        apparatus, _apparatus_members = file_set_digest(protocol, "qualification_apparatus")
        if protocol.get("mechanism", {}).get("digest") != measured:
            failures.append("mechanism moved after freeze")
        if protocol.get("qualification_apparatus", {}).get("digest") != apparatus:
            failures.append("apparatus moved after freeze")
    except Exception as error:  # noqa: BLE001
        failures.append(f"bindings could not be recomputed: {error}")
    m097 = json.loads(M097_RESULT_PATH.read_text(encoding="utf-8"))
    m099 = json.loads(M099_RESULT_PATH.read_text(encoding="utf-8"))
    m099_check = json.loads(M099_CHECK_PATH.read_text(encoding="utf-8"))
    expected = {
        "m097_result_digest": m097["result_digest"],
        "m097_extended_state_digest": m097["scientific_evidence"]["extended_language_state"][
            "state_digest"
        ],
        "m097_inherited_state_digest": m097["scientific_evidence"]["inherited_language_state"][
            "state_digest"
        ],
        "m099_result_digest": m099["result_digest"],
        "m099_checker_digest": m099_check["report_digest"],
    }
    for key, value in expected.items():
        if protocol.get("preserved_inputs", {}).get(key) != value:
            failures.append(f"protocol does not bind {key}")
    return _condition(
        "P1", "frozen_public_protocol_pool_mechanism_checker_and_predecessors_are_bound",
        failures,
    )


def check_p2(pool: dict[str, object]) -> Condition:
    failures = []
    if pool != build_pool(status="frozen"):
        failures.append("committed pool differs from the authored frozen population")
    audit = audit_pool(pool)
    if not audit.get("passed"):
        failures.append("one or more worlds fail source-only preflight")
    if len(pool.get("entries", [])) != 9 or pool.get("cycle_counts") != {"A": 3, "B": 3, "C": 3}:
        failures.append("population is not the complete three-by-three design")
    if pool.get("m097_through_m099_worlds_excluded") is not True:
        failures.append("predecessor worlds were not explicitly excluded")
    if any(audit.get(key) is not False for key in (
        "migration_was_run", "acquisition_was_run", "fresh_runtime_was_run", "fault_was_injected"
    )):
        failures.append("preflight crossed the frozen qualification boundary")
    return _condition(
        "P2", "complete_fresh_three_by_three_population_was_source_only_before_freeze",
        failures, {"entries": len(pool.get("entries", [])), "preflight": audit.get("passed")},
    )


def check_p3(evidence: dict[str, object]) -> Condition:
    failures = []
    migrations = evidence.get("migrations", {})
    chain = evidence.get("acquisition_chain", {})
    if not all(_success(migrations.get(key, {})) for key in (
        "pre_acquisition_to_s0", "acquired_a_to_s1"
    )):
        failures.append("pre/post-M097 states did not migrate in fresh processes")
    if migrations.get("pre_acquisition_to_s0", {}).get("runtime", {}).get("operations") != 0:
        failures.append("pre-acquisition migration did not produce S0 with zero operations")
    if migrations.get("acquired_a_to_s1", {}).get("runtime", {}).get("operations") != 1:
        failures.append("extended migration did not produce S1 with one operation")
    if not _failure(chain.get("s0_without_a_for_b", {})) or _accepted_count(
        chain.get("s0_without_a_for_b", {})
    ) != 0:
        failures.append("B was not absent before A")
    if not _failure(chain.get("s1_without_b_for_c", {})) or _accepted_count(
        chain.get("s1_without_b_for_c", {})
    ) != 0:
        failures.append("C was not absent before B")
    built = chain.get("b_built_not_registered", {})
    if not _success(built) or built.get("runtime", {}).get("acquisition", {}).get(
        "registered"
    ) is not False:
        failures.append("the unregistered B build did not produce a candidate")
    if chain.get("s1_unchanged_after_unregistered_build") is not True:
        failures.append("building B without registration changed S1")
    if not _failure(chain.get("c_after_unregistered_b", {})) or _accepted_count(
        chain.get("c_after_unregistered_b", {})
    ) != 0:
        failures.append("unregistered B incorrectly enabled C")
    for key, length in (("acquire_and_register_b", 4), ("acquire_and_register_c", 5)):
        row = chain.get(key, {})
        acquisition = row.get("runtime", {}).get("acquisition", {})
        if not _success(row) or acquisition.get("registered") is not True:
            failures.append(f"{key} did not succeed and register")
        if acquisition.get("shortest_accepted_length") != length:
            failures.append(f"{key} shortest accepted length changed")
    return _condition(
        "P3", "fresh_process_cycles_require_registration_and_acquire_b_then_c_in_order", failures
    )


def check_p4(evidence: dict[str, object]) -> Condition:
    failures = []
    states = evidence.get("states", {})
    operation_counts = []
    for name in ("S0", "S1", "S2", "S3"):
        state = states.get(name, {}).get("state", {})
        payload = {key: item for key, item in state.items() if key != "state_digest"}
        if state.get("state_digest") != digest(payload):
            failures.append(f"{name} state digest mismatch")
        raw_sha256 = hashlib.sha256(canonical_json(state).encode("ascii")).hexdigest()
        if states.get(name, {}).get("raw_sha256") != raw_sha256:
            failures.append(f"{name} raw-state hash mismatch")
        operation_counts.append(len(state.get("operations", [])))
    if operation_counts != [0, 1, 2, 3]:
        failures.append("state operation census is not 0/1/2/3")
    s1_operations = states.get("S1", {}).get("state", {}).get("operations", [])
    s2_operations = states.get("S2", {}).get("state", {}).get("operations", [])
    s3_operations = states.get("S3", {}).get("state", {}).get("operations", [])
    if states.get("s1_prefix_conserved_in_s2") is not True or s2_operations[:1] != s1_operations:
        failures.append("S1 is not conserved exactly in S2")
    if states.get("s2_prefix_conserved_in_s3") is not True or s3_operations[:2] != s2_operations:
        failures.append("S2 is not conserved exactly in S3")
    signatures: dict[str, tuple[int, int]] = {}
    for definition in states.get("S3", {}).get("state", {}).get("operations", []):
        operation_id = str(definition.get("operation_id"))
        signature = _independent_signature(definition.get("body", []), signatures)
        if signature is None:
            failures.append(f"{operation_id} has no independent signature")
            break
        signatures[operation_id] = signature
    if list(signatures.values()) != [(1, -1), (1, 1), (1, 2)]:
        failures.append("independent cumulative signatures are not A/B/C")
    return _condition(
        "P4", "s0_s1_s2_s3_strictly_grow_and_conserve_all_prior_definitions", failures
    )


def check_p5(pool: dict[str, object], evidence: dict[str, object]) -> Condition:
    failures = []
    worlds = evidence.get("fresh_worlds_after_s3", [])
    if len(worlds) != 9 or not all(_success(row.get("fresh", {})) for row in worlds):
        failures.append("not all nine fresh worlds execute after S3")
    counts = {
        cycle: sum(row.get("cycle") == cycle for row in worlds) for cycle in ("A", "B", "C")
    }
    if counts != {"A": 3, "B": 3, "C": 3}:
        failures.append("fresh-world execution does not conserve three worlds per operation")
    expected = {(item["id"], item["entry_digest"]) for item in pool.get("entries", [])}
    observed = {(item.get("entry"), item.get("entry_digest")) for item in worlds}
    if observed != expected:
        failures.append("executed population differs from the frozen pool")
    entries = {item["id"]: item for item in pool.get("entries", [])}
    operation_ids = evidence.get("states", {}).get("operation_ids", {})
    for row in worlds:
        entry = entries.get(row.get("entry"))
        execution = row.get("fresh", {}).get("runtime", {}).get("execution", {})
        if entry is None:
            continue
        if execution.get("requirement", {}).get("signature") != entry.get("signature"):
            failures.append(f"{row.get('entry')} executed a different affine demand")
        if row.get("operation_id") != operation_ids.get(row.get("cycle")):
            failures.append(f"{row.get('entry')} did not use its conserved operation")
        if execution.get("cases") != 4 or execution.get("cases_passed") != 4:
            failures.append(f"{row.get('entry')} did not pass all four cases")
    return _condition(
        "P5", "all_acquired_operations_remain_reusable_on_nine_fresh_worlds_after_s3",
        failures, {"cycle_counts": counts},
    )


def check_p6(evidence: dict[str, object]) -> Condition:
    facts = evidence.get("process_boundary", {})
    rows = _runtime_rows(evidence)
    failures = []
    if facts.get("all_invocations_isolated") is not True or not all(
        row.get("isolated_mode") is True for row in rows
    ):
        failures.append("one or more fresh invocations was not isolated")
    if facts.get("no_project_modules_imported") is not True or not all(
        row.get("imported_project_modules") == [] for row in rows
    ):
        failures.append("a capsule imported a project module")
    repository_text = str(ROOT).casefold()
    paths_are_clean = all(
        all(repository_text not in str(path).casefold() for path in row.get("search_path", []))
        for row in rows
    )
    if facts.get("repository_absent_from_search_paths") is not True or not paths_are_clean:
        failures.append("the repository leaked into an isolated search path")
    return _condition(
        "P6", "every_migration_acquisition_control_and_execution_is_process_isolated", failures
    )


def check_p7(evidence: dict[str, object]) -> Condition:
    failures = []
    operations = evidence.get("states", {}).get("S3", {}).get("state", {}).get("operations", [])
    if len(operations) != 3:
        failures.append("S3 does not contain three operations")
    else:
        a, b, c = operations
        expected_keys = {"schema", "operation_id", "origin", "body", "dependency_ids"}
        for label, definition, origin in (
            ("A", a, "m097"), ("B", b, "m100-cycle"), ("C", c, "m100-cycle")
        ):
            if set(definition) != expected_keys:
                failures.append(f"{label} is not a closed operation record")
            if definition.get("schema") != "m100-cumulative-operation-v1":
                failures.append(f"{label} operation schema changed")
            if definition.get("origin") != origin:
                failures.append(f"{label} origin changed")
            if origin == "m097":
                identifier_payload = {
                    "schema": "m097-expression-operation-v1", "body": definition.get("body")
                }
                expected_id = "derived-expression-" + digest(identifier_payload)[:16]
            else:
                identifier_payload = {
                    "schema": "m100-cumulative-operation-v1",
                    "body": definition.get("body"),
                    "dependency_ids": definition.get("dependency_ids"),
                }
                expected_id = "cumulative-expression-" + digest(identifier_payload)[:16]
            if definition.get("operation_id") != expected_id:
                failures.append(f"{label} content-addressed identifier mismatch")
        if b.get("dependency_ids") != [a.get("operation_id")]:
            failures.append("B does not retain its live A dependency")
        if c.get("dependency_ids") != [b.get("operation_id")]:
            failures.append("C does not retain its live B dependency")
        allowed = {"PUSH_LEFT", "PUSH_RIGHT", "NEG", "SWAP"}
        for label, definition in (("B", b), ("C", c)):
            if any(
                token not in allowed and not str(token).startswith("CALL:")
                for token in definition.get("body", [])
            ):
                failures.append(f"{label} bypasses the registered operation language")
            ordered_calls = []
            for token in definition.get("body", []):
                if str(token).startswith("CALL:") and str(token)[5:] not in ordered_calls:
                    ordered_calls.append(str(token)[5:])
            if definition.get("dependency_ids") != ordered_calls:
                failures.append(f"{label} dependency record differs from its calls")
    return _condition(
        "P7", "new_definitions_use_only_static_stack_tokens_and_live_predecessor_calls", failures
    )


def check_p8(evidence: dict[str, object]) -> Condition:
    controls = evidence.get("dependency_controls", {})
    failures = []
    mutate_a = controls.get("mutate_a_breaks_b", {})
    if not _failure(mutate_a) or mutate_a.get("runtime", {}).get("failed_closed") is True:
        failures.append("digest-valid A mutation did not break B")
    mutate_b = controls.get("mutate_b_breaks_c", {})
    if not _failure(mutate_b) or mutate_b.get("runtime", {}).get("failed_closed") is True:
        failures.append("digest-valid B mutation did not break C")
    return _condition(
        "P8", "digest_valid_semantic_mutations_prove_live_transitive_dependency", failures
    )


def check_p9(evidence: dict[str, object]) -> Condition:
    controls = evidence.get("dependency_controls", {})
    failures = []
    for key in ("ablate_a", "ablate_b", "corrupt_digest"):
        row = controls.get(key, {})
        if not _failure(row) or row.get("runtime", {}).get("failed_closed") is not True:
            failures.append(f"{key} did not fail closed")
    return _condition(
        "P9", "predecessor_ablation_and_state_corruption_fail_closed", failures
    )


def check_p10(evidence: dict[str, object]) -> Condition:
    rollback = evidence.get("rollback", {})
    failures = []
    if rollback.get("faulty_state_differs") is not True:
        failures.append("live S2 fault did not change bytes")
    if not _failure(rollback.get("during_fault", {})) or _accepted_count(
        rollback.get("during_fault", {})
    ) != 0:
        failures.append("live S2 fault did not suppress C acquisition")
    if rollback.get("restored_bytes_equal") is not True:
        failures.append("rollback did not restore exact S2 bytes")
    if rollback.get("before_fault_sha256") != rollback.get("after_restore_sha256"):
        failures.append("restored S2 hash differs")
    if not _success(rollback.get("after_restore", {})):
        failures.append("C acquisition did not return after rollback")
    canonical_c = evidence.get("acquisition_chain", {}).get(
        "acquire_and_register_c", {}
    ).get("runtime", {}).get("acquisition", {}).get("adopted")
    restored_c = rollback.get("after_restore", {}).get("runtime", {}).get(
        "acquisition", {}
    ).get("adopted")
    if restored_c != canonical_c:
        failures.append("post-rollback C definition differs from canonical C")
    if rollback.get("restored_s3_equals_original") is not True:
        failures.append("post-rollback S3 differs from canonical S3")
    return _condition(
        "P10", "live_fault_suppresses_c_and_byte_exact_rollback_restores_it", failures
    )


def check_p11(evidence: dict[str, object]) -> Condition:
    capsule = evidence.get("capsule", {})
    facts = evidence.get("process_boundary", {})
    failures = []
    if capsule.get("contains_only_runtime_and_entrypoint") is not True:
        failures.append("capsule contains more than the runtime and entrypoint")
    if capsule.get("members") != ["m100_runtime.py", "run.py"]:
        failures.append("capsule member census changed")
    rows = _runtime_rows(evidence)
    if facts.get("fresh_process_invocations") != 24 or len(rows) != 24:
        failures.append("fresh process census is not the frozen 24 invocations")
    if facts.get("pid_records_present") is not True or not all(
        isinstance(row.get("pid"), int) for row in rows
    ):
        failures.append("one or more process records lacks a PID")
    if facts.get("all_key_cycle_processes_distinct") is not True:
        failures.append("migration, B acquisition and C acquisition did not use distinct processes")
    return _condition(
        "P11", "capsule_census_and_complete_fresh_process_chronology_are_observed", failures
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
        failures.append("stable projection retains a frozen ephemeral field")
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
    m099 = json.loads(M099_RESULT_PATH.read_text(encoding="utf-8"))
    m099_check = json.loads(M099_CHECK_PATH.read_text(encoding="utf-8"))
    expected = {
        "m097_result_digest": m097["result_digest"],
        "m097_extended_state_digest": m097["scientific_evidence"]["extended_language_state"][
            "state_digest"
        ],
        "m097_inherited_state_digest": m097["scientific_evidence"]["inherited_language_state"][
            "state_digest"
        ],
        "m099_result_digest": m099["result_digest"],
        "m099_checker_digest": m099_check["report_digest"],
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
    if result.get("result_digest") != digest({
        key: value for key, value in result.items() if key != "result_digest"
    }):
        failures.append("result digest mismatch")
    return _condition(
        "P12", "stable_replay_chronology_track_a_and_local_only_execution", failures
    )


def run_conditions(
    protocol: dict[str, object], pool: dict[str, object], result: dict[str, object],
    replay: dict[str, object],
) -> list[Condition]:
    evidence = result.get("scientific_evidence", {})
    return [
        check_p3(evidence), check_p4(evidence), check_p5(pool, evidence), check_p6(evidence),
        check_p7(evidence), check_p8(evidence), check_p9(evidence), check_p10(evidence),
        check_p11(evidence), check_p12(protocol, pool, result, replay),
    ]


NAMES = [
    "fresh_process_cycles_require_registration_and_acquire_b_then_c_in_order",
    "s0_s1_s2_s3_strictly_grow_and_conserve_all_prior_definitions",
    "all_acquired_operations_remain_reusable_on_nine_fresh_worlds_after_s3",
    "every_migration_acquisition_control_and_execution_is_process_isolated",
    "new_definitions_use_only_static_stack_tokens_and_live_predecessor_calls",
    "digest_valid_semantic_mutations_prove_live_transitive_dependency",
    "predecessor_ablation_and_state_corruption_fail_closed",
    "live_fault_suppresses_c_and_byte_exact_rollback_restores_it",
    "capsule_census_and_complete_fresh_process_chronology_are_observed",
    "stable_replay_chronology_track_a_and_local_only_execution",
]


def compute_report(
    protocol: dict[str, object], pool: dict[str, object], result: dict[str, object] | None
) -> dict[str, object]:
    conditions = [check_p1(protocol, pool), check_p2(pool)]
    if result is None:
        conditions.extend(_uncomputed(f"P{index}", name) for index, name in enumerate(NAMES, 3))
    else:
        conditions.extend(run_conditions(protocol, pool, result, run_experiment(pool)))
    failed = [item.id for item in conditions if item.computed and item.passed is False]
    uncomputed = [item.id for item in conditions if not item.computed]
    verdict = "negative" if failed else ("incomplete" if uncomputed else "positive")
    report = {
        "schema": "m100-checker-v1",
        "milestone": "M100",
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
