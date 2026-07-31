from __future__ import annotations

import json
import os
from pathlib import Path
import platform
import sys

from metamorphosis.m012b_dfa import random_minimal_dfa
from metamorphosis.m013e_engine import (
    UnknownSubstrateMigrator,
    fixed_role_baseline,
    random_semantics_baseline,
)
from metamorphosis.m013e_lab import make_negative_machine, make_positive_machine
from metamorphosis.m013e_sealed import runtime_nonce, sealed_spec
from m013e_eval_support import (
    HIDDEN_WORDS_PER_SUCCESS,
    MACHINE_COUNT,
    ROOT,
    SEARCH_REPETITIONS,
    TARGET_COUNT,
    HiddenSuite,
    evaluate_certificate,
    hidden_words,
    median,
    oracle_substrate,
    report,
    sha256_bytes,
    source_isolation_audit,
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
    protocol_path = ROOT / "experiments" / "M013e" / "protocol.yaml"
    protocol_hash = sha256_bytes(protocol_path.read_bytes())

    if canonical:
        if os.environ.get("GITHUB_ACTIONS") != "true":
            raise RuntimeError("canonical evaluation must run inside GitHub Actions")
        if github_run_attempt != 1 or event_action != "opened":
            raise RuntimeError("canonical M013e must be the first PR-opened workflow attempt")
    if master_nonce_hex is None:
        master_nonce_hex = runtime_nonce()

    spec = sealed_spec(master_nonce_hex)
    passports = [random_minimal_dfa(seed) for seed in spec.passport_seeds]
    suites = [
        HiddenSuite(passport, hidden_words(seed))
        for passport, seed in zip(passports, spec.hidden_seeds)
    ]
    migrator = UnknownSubstrateMigrator()
    trace_base = {
        "git_commit": git_commit,
        "protocol_sha256": protocol_hash,
        "github_run_id": github_run_id,
        "github_run_attempt": github_run_attempt,
        "event_action": event_action,
        "master_nonce_sha256": sha256_bytes(bytes.fromhex(master_nonce_hex)),
    }

    main_runs: list[dict[str, object]] = []
    oracle_runs: list[dict[str, object]] = []
    for passport_index, passport in enumerate(passports):
        for machine_index, (machine_seed, family) in enumerate(zip(spec.machine_seeds, spec.machine_families)):
            for repetition, search_seed in enumerate(spec.search_seeds):
                trace = {
                    **trace_base,
                    "passport_index": passport_index,
                    "machine_index": machine_index,
                    "repetition": repetition,
                    "search_seed": search_seed,
                }
                machine = make_positive_machine(machine_seed, family)
                certificate = migrator.migrate(passport, machine, search_seed, trace)
                main_runs.append({
                    **trace,
                    **evaluate_certificate(certificate, passport, machine, suites[passport_index], True),
                })

                oracle_machine = make_positive_machine(machine_seed, family)
                oracle_certificate = migrator.migrate(
                    passport,
                    oracle_machine,
                    search_seed,
                    trace,
                    supplied_substrate=oracle_substrate(oracle_machine),
                )
                oracle_runs.append({
                    **trace,
                    **evaluate_certificate(oracle_certificate, passport, oracle_machine, None, False),
                })

    no_probe_runs: list[dict[str, object]] = []
    random_runs: list[dict[str, object]] = []
    for passport_index, passport in enumerate(passports):
        for machine_index, (machine_seed, family) in enumerate(zip(spec.machine_seeds, spec.machine_families)):
            trace = {
                **trace_base,
                "passport_index": passport_index,
                "machine_index": machine_index,
                "search_seed": spec.search_seeds[0],
            }
            fixed_machine = make_positive_machine(machine_seed, family)
            fixed_certificate = migrator.migrate(
                passport,
                fixed_machine,
                spec.search_seeds[0],
                trace,
                supplied_substrate=fixed_role_baseline(fixed_machine.describe()),
            )
            no_probe_runs.append({
                **trace,
                **evaluate_certificate(fixed_certificate, passport, fixed_machine, None, False),
            })

            random_machine = make_positive_machine(machine_seed, family)
            random_certificate = migrator.migrate(
                passport,
                random_machine,
                spec.search_seeds[0],
                trace,
                supplied_substrate=random_semantics_baseline(
                    random_machine.describe(),
                    spec.passport_seeds[passport_index] ^ machine_seed,
                ),
            )
            random_runs.append({
                **trace,
                **evaluate_certificate(random_certificate, passport, random_machine, None, False),
            })

    negative_runs: list[dict[str, object]] = []
    negative_passport = passports[0]
    for index, (seed, kind) in enumerate(zip(spec.negative_seeds, spec.negative_kinds)):
        machine = make_negative_machine(seed, kind)
        trace = {
            **trace_base,
            "negative_index": index,
            "negative_kind": kind,
            "search_seed": spec.search_seeds[0],
        }
        certificate = migrator.migrate(negative_passport, machine, spec.search_seeds[0], trace)
        record = {
            **trace,
            **evaluate_certificate(certificate, negative_passport, machine, None, False),
        }
        record["false_success"] = bool(record["status"] == "success" and record["exact"] is True)
        negative_runs.append(record)

    principals: list[dict[str, object]] = []
    oracle_principals: list[dict[str, object]] = []
    for passport_index in range(TARGET_COUNT):
        for machine_index in range(MACHINE_COUNT):
            group = [
                row for row in main_runs
                if row["passport_index"] == passport_index and row["machine_index"] == machine_index
            ]
            principals.append({
                "passport_index": passport_index,
                "machine_index": machine_index,
                "exact": all(
                    row["status"] == "success"
                    and row["exact"] is True
                    and row["hidden_accuracy"] == 1.0
                    and row["serialization_round_trip"] is True
                    and row["semantic_exact_used"] is True
                    for row in group
                ),
            })
            oracle_group = [
                row for row in oracle_runs
                if row["passport_index"] == passport_index and row["machine_index"] == machine_index
            ]
            oracle_principals.append({
                "passport_index": passport_index,
                "machine_index": machine_index,
                "exact": all(row["status"] == "success" and row["exact"] is True for row in oracle_group),
            })

    exact_principals = sum(bool(row["exact"]) for row in principals)
    exact_executions = sum(row["status"] == "success" and row["exact"] is True for row in main_runs)
    oracle_exact = sum(bool(row["exact"]) for row in oracle_principals)
    per_machine = {
        str(machine_index): sum(
            bool(row["exact"]) for row in principals if row["machine_index"] == machine_index
        )
        for machine_index in range(MACHINE_COUNT)
    }
    no_probe_exact = sum(row["status"] == "success" and row["exact"] is True for row in no_probe_runs)
    random_exact = sum(row["status"] == "success" and row["exact"] is True for row in random_runs)
    correct_abstentions = sum(row["status"] == "abstained" for row in negative_runs)
    false_successes = sum(bool(row["false_success"]) for row in negative_runs)
    isolation = source_isolation_audit()
    successful = [row for row in main_runs if row["status"] == "success"]

    aggregates = {
        "exact_principal_migrations": exact_principals,
        "exact_executions": exact_executions,
        "per_machine_exact": per_machine,
        "oracle_ceiling_exact": oracle_exact,
        "median_probe_calls": median([int(row["probe_calls"]) for row in main_runs]),
        "max_probe_calls": max(int(row["probe_calls"]) for row in main_runs),
        "median_candidate_evaluations": median([int(row["candidate_evaluations"]) for row in main_runs]),
        "max_native_components": max(int(row["native_components"]) for row in main_runs),
        "max_serialized_bytes": max(int(row["serialized_bytes"]) for row in main_runs),
        "no_probe_exact": no_probe_exact,
        "random_semantics_exact": random_exact,
        "correct_negative_abstentions": correct_abstentions,
        "false_negative_successes": false_successes,
        "isolation_audit": isolation,
    }

    criteria = {
        "exact_principal_migrations_at_least_32_of_36": exact_principals >= 32,
        "at_least_10_of_12_per_machine": all(value >= 10 for value in per_machine.values()),
        "all_used_stable_semantics_identified_exactly": all(
            row["semantic_exact_used"] is True for row in successful
        ),
        "all_claimed_successes_exact_and_perfect_hidden": all(
            row["exact"] is True and row["hidden_accuracy"] == 1.0 for row in successful
        ),
        "no_success_exceeds_120_probes": all(int(row["probe_calls"]) <= 120 for row in successful),
        "advantage_at_least_12_over_best_zero_information_baseline": exact_principals - max(no_probe_exact, random_exact) >= 12,
        "oracle_gap_at_most_two_principal_migrations": exact_principals >= oracle_exact - 2,
        "correct_negative_abstentions_12_of_12": correct_abstentions == 12,
        "zero_false_negative_successes": false_successes == 0,
        "complete_sealed_first_run_traceability": bool(isolation["passed"])
        and isolation["runtime_nonce_calls_in_runner"] == 1
        and bool(git_commit)
        and bool(github_run_id)
        and (not canonical or (github_run_attempt == 1 and event_action == "opened"))
        and all(
            row["git_commit"] == git_commit
            and row["protocol_sha256"] == protocol_hash
            and row["github_run_id"] == github_run_id
            for row in main_runs
        ),
    }

    status = ("VALIDATED" if all(criteria.values()) else "FAILED") if canonical else "DEVELOPMENT_ONLY"
    result: dict[str, object] = {
        "experiment": "M013e",
        "status": status,
        "canonical": canonical,
        "git_commit": git_commit,
        "protocol_sha256": protocol_hash,
        "github_run_id": github_run_id,
        "github_run_attempt": github_run_attempt,
        "event_action": event_action,
        "master_nonce": master_nonce_hex,
        "master_nonce_sha256": trace_base["master_nonce_sha256"],
        "passport_seeds": spec.passport_seeds,
        "machine_seeds": spec.machine_seeds,
        "machine_families": spec.machine_families,
        "search_seeds": spec.search_seeds,
        "hidden_seeds": spec.hidden_seeds,
        "negative_seeds": spec.negative_seeds,
        "negative_kinds": spec.negative_kinds,
        "environment": {"python": sys.version, "platform": platform.platform()},
        "main_runs": main_runs,
        "principal_migrations": principals,
        "oracle_runs": oracle_runs,
        "oracle_principals": oracle_principals,
        "no_probe_runs": no_probe_runs,
        "random_semantics_runs": random_runs,
        "negative_controls": negative_runs,
        "aggregates": aggregates,
        "acceptance_criteria": criteria,
        "all_criteria_passed": all(criteria.values()),
        "interpretation_limit": "Runtime-sealed discovery of finite opaque Boolean opcode semantics; not arbitrary continuous or physical substrate adaptation.",
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    full_path = output_dir / "M013e_full.json"
    summary_path = output_dir / "summary.json"
    report_path = output_dir / "REPORT.md"
    full_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    summary_keys = (
        "experiment", "status", "canonical", "git_commit", "protocol_sha256",
        "github_run_id", "github_run_attempt", "event_action", "master_nonce",
        "master_nonce_sha256", "passport_seeds", "machine_seeds", "machine_families",
        "search_seeds", "hidden_seeds", "negative_seeds", "negative_kinds",
        "aggregates", "acceptance_criteria", "all_criteria_passed", "interpretation_limit",
    )
    summary = {key: result[key] for key in summary_keys}
    summary["full_result_sha256"] = sha256_bytes(full_path.read_bytes())
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    report_path.write_text(report(result), encoding="utf-8")
    return result
