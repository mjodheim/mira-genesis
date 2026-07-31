from __future__ import annotations

import json
import os
from pathlib import Path
import platform
import secrets
import sys

from metamorphosis.m012b import (
    AutonomousMorphogenesisEngine,
    derive_runtime_seeds,
    evaluation_catalogs,
    exact_equivalence,
    insufficient_catalog,
    native_body_to_dfa,
    random_minimal_dfa,
    synthesize_native_body,
)
from m012b_eval_support import (
    HIDDEN_WORDS_PER_SUCCESS,
    ROOT,
    SEARCH_REPETITIONS,
    TARGET_COUNT,
    HiddenSuite,
    evaluate_body,
    hidden_words,
    median,
    report,
    sha256_bytes,
    source_isolation_audit,
    unstable_oracle,
)

def run(
    *,
    git_commit: str,
    output_dir: Path,
    canonical: bool,
    master_nonce_hex: str | None,
    github_run_id: str,
    github_run_attempt: int,
    event_action: str,
) -> dict[str, object]:
    protocol_path = ROOT / "experiments" / "M012b" / "protocol.yaml"
    protocol_hash = sha256_bytes(protocol_path.read_bytes())

    if canonical:
        if os.environ.get("GITHUB_ACTIONS") != "true":
            raise RuntimeError("canonical evaluation must run inside GitHub Actions")
        if github_run_attempt != 1 or event_action != "opened":
            raise RuntimeError("canonical M012b must be the first PR-opened workflow attempt")
    if master_nonce_hex is None:
        master_nonce_hex = secrets.token_hex(32)

    target_seeds = derive_runtime_seeds(master_nonce_hex, TARGET_COUNT, "target")
    search_seeds = derive_runtime_seeds(master_nonce_hex, SEARCH_REPETITIONS, "search")
    hidden_seeds = derive_runtime_seeds(master_nonce_hex, TARGET_COUNT, "hidden")
    targets = [random_minimal_dfa(seed) for seed in target_seeds]
    hidden_suites = [HiddenSuite(target, hidden_words(seed)) for target, seed in zip(targets, hidden_seeds)]
    catalogs = evaluation_catalogs()
    engine = AutonomousMorphogenesisEngine()

    trace_base = {
        "git_commit": git_commit,
        "protocol_sha256": protocol_hash,
        "github_run_id": github_run_id,
        "github_run_attempt": github_run_attempt,
        "event_action": event_action,
        "master_nonce_sha256": sha256_bytes(bytes.fromhex(master_nonce_hex)),
    }

    main_runs: list[dict[str, object]] = []
    for target_index, target in enumerate(targets):
        for catalog in catalogs:
            for repetition, search_seed in enumerate(search_seeds):
                trace = {
                    **trace_base,
                    "target_index": target_index,
                    "catalog_id": catalog.catalog_id,
                    "repetition": repetition,
                    "search_seed": search_seed,
                }
                certificate = engine.birth(target.accepts, catalog, search_seed, trace)
                record: dict[str, object] = {
                    **trace,
                    "status": certificate.status,
                    "reason": certificate.reason,
                    "behavioural_queries": certificate.behavioural_queries,
                    "candidate_evaluations": certificate.candidate_evaluations,
                    "native_components": certificate.native_components,
                    "serialized_bytes": certificate.serialized_bytes,
                    "elapsed_seconds": certificate.elapsed_seconds,
                    "discovery_rounds": certificate.discovery_rounds,
                    "counterexamples": certificate.counterexamples,
                    "discovered_states": certificate.discovered_dfa.n_states if certificate.discovered_dfa else None,
                    "exact": False,
                    "hidden_accuracy": 0.0,
                    "serialization_round_trip": False,
                }
                if certificate.body is not None:
                    record.update(evaluate_body(target, certificate.body, hidden_suites[target_index]))
                main_runs.append(record)

    principals: list[dict[str, object]] = []
    for target_index in range(TARGET_COUNT):
        for catalog in catalogs:
            group = [
                row
                for row in main_runs
                if row["target_index"] == target_index and row["catalog_id"] == catalog.catalog_id
            ]
            exact = all(
                row["status"] == "success"
                and row["exact"] is True
                and row["hidden_accuracy"] == 1.0
                and row["serialization_round_trip"] is True
                for row in group
            )
            principals.append(
                {
                    "target_index": target_index,
                    "catalog_id": catalog.catalog_id,
                    "exact": exact,
                }
            )

    oracle_ceiling: list[dict[str, object]] = []
    for target_index, target in enumerate(targets):
        for catalog in catalogs:
            body, candidates, reason = synthesize_native_body(
                target, catalog, search_seeds[0], engine.candidate_budget
            )
            exact = False
            if body is not None:
                exact = exact_equivalence(target, native_body_to_dfa(body))[0]
            oracle_ceiling.append(
                {
                    "target_index": target_index,
                    "catalog_id": catalog.catalog_id,
                    "exact": exact,
                    "candidate_evaluations": candidates,
                    "reason": reason,
                }
            )

    negative_runs: list[dict[str, object]] = []
    consistency_triggers = [(), (0,), (1,), (0, 1), (1, 0), (1, 1)]
    for index, trigger in enumerate(consistency_triggers):
        target = targets[index]
        certificate = engine.birth(
            unstable_oracle(target, trigger),
            catalogs[index % len(catalogs)],
            search_seeds[0],
            {**trace_base, "negative_control": f"unstable_{index}"},
        )
        negative_runs.append(
            {
                "control": f"unstable_{index}",
                "status": certificate.status,
                "reason": certificate.reason,
                "false_success": certificate.body is not None,
            }
        )
    for index in range(6):
        target = targets[index + 6]
        certificate = engine.birth(
            target.accepts,
            insufficient_catalog(),
            search_seeds[0],
            {**trace_base, "negative_control": f"insufficient_{index}"},
        )
        negative_runs.append(
            {
                "control": f"insufficient_{index}",
                "status": certificate.status,
                "reason": certificate.reason,
                "false_success": certificate.body is not None,
            }
        )

    exact_principals = sum(bool(row["exact"]) for row in principals)
    exact_executions = sum(
        row["status"] == "success" and row["exact"] is True for row in main_runs
    )
    per_catalog = {
        catalog.catalog_id: sum(
            bool(row["exact"])
            for row in principals
            if row["catalog_id"] == catalog.catalog_id
        )
        for catalog in catalogs
    }
    oracle_exact = sum(bool(row["exact"]) for row in oracle_ceiling)
    correct_abstentions = sum(
        row["status"] == "abstained" and not row["false_success"] for row in negative_runs
    )
    false_negative_successes = sum(bool(row["false_success"]) for row in negative_runs)
    isolation = source_isolation_audit()

    successful = [row for row in main_runs if row["status"] == "success"]
    aggregates = {
        "exact_principal_births": exact_principals,
        "exact_executions": exact_executions,
        "per_catalog_exact": per_catalog,
        "oracle_ceiling_exact": oracle_exact,
        "median_behavioural_queries": median([int(row["behavioural_queries"]) for row in main_runs]),
        "max_behavioural_queries": max(int(row["behavioural_queries"]) for row in main_runs),
        "median_candidate_evaluations": median([int(row["candidate_evaluations"]) for row in main_runs]),
        "max_native_components": max(int(row["native_components"]) for row in main_runs),
        "max_serialized_bytes": max(int(row["serialized_bytes"]) for row in main_runs),
        "correct_negative_abstentions": correct_abstentions,
        "false_negative_successes": false_negative_successes,
        "isolation_audit": isolation,
    }

    criteria = {
        "exact_principal_births_at_least_32_of_36": exact_principals >= 32,
        "at_least_10_of_12_per_catalogue": all(value >= 10 for value in per_catalog.values()),
        "all_claimed_successes_exact_and_perfect_hidden": all(
            row["exact"] is True and row["hidden_accuracy"] == 1.0 for row in successful
        ),
        "at_least_96_of_108_exact_executions": exact_executions >= 96,
        "oracle_gap_at_most_two_principal_births": exact_principals >= oracle_exact - 2,
        "correct_negative_abstentions_12_of_12": correct_abstentions == 12,
        "zero_false_negative_successes": false_negative_successes == 0,
        "all_successes_within_resource_budgets": all(
            int(row["behavioural_queries"]) <= 20_000
            and int(row["candidate_evaluations"]) <= 50_000
            and int(row["native_components"]) <= 256
            and int(row["serialized_bytes"]) <= 16_777_216
            and float(row["elapsed_seconds"]) <= 120.0
            for row in successful
        ),
        "sealed_case_and_source_isolation_audit": bool(isolation["passed"])
        and isolation["runtime_nonce_calls_in_runner"] == 1,
        "complete_first_run_traceability": bool(git_commit)
        and bool(github_run_id)
        and (not canonical or (github_run_attempt == 1 and event_action == "opened"))
        and all(
            row["git_commit"] == git_commit
            and row["protocol_sha256"] == protocol_hash
            and row["github_run_id"] == github_run_id
            for row in main_runs
        ),
    }

    if canonical:
        status = "VALIDATED" if all(criteria.values()) else "FAILED"
    else:
        status = "DEVELOPMENT_ONLY"

    result: dict[str, object] = {
        "experiment": "M012b",
        "status": status,
        "canonical": canonical,
        "git_commit": git_commit,
        "protocol_sha256": protocol_hash,
        "github_run_id": github_run_id,
        "github_run_attempt": github_run_attempt,
        "event_action": event_action,
        "master_nonce": master_nonce_hex,
        "master_nonce_sha256": trace_base["master_nonce_sha256"],
        "target_seeds": target_seeds,
        "search_seeds": search_seeds,
        "hidden_seeds": hidden_seeds,
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
        },
        "main_runs": main_runs,
        "principal_births": principals,
        "oracle_ceiling": oracle_ceiling,
        "negative_controls": negative_runs,
        "aggregates": aggregates,
        "acceptance_criteria": criteria,
        "all_criteria_passed": all(criteria.values()),
        "interpretation_limit": "Finite deterministic regular-language body morphogenesis from runtime-sealed cases and human-declared Boolean primitive catalogues.",
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    full_path = output_dir / "M012b_full.json"
    summary_path = output_dir / "summary.json"
    report_path = output_dir / "REPORT.md"
    full_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    summary = {
        key: result[key]
        for key in (
            "experiment",
            "status",
            "canonical",
            "git_commit",
            "protocol_sha256",
            "github_run_id",
            "github_run_attempt",
            "event_action",
            "master_nonce",
            "master_nonce_sha256",
            "target_seeds",
            "search_seeds",
            "hidden_seeds",
            "aggregates",
            "acceptance_criteria",
            "all_criteria_passed",
            "interpretation_limit",
        )
    }
    summary["full_result_sha256"] = sha256_bytes(full_path.read_bytes())
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    report_path.write_text(report(result), encoding="utf-8")
    return result


