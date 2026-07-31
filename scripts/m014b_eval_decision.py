from __future__ import annotations

from m014b_eval_support import MACHINE_COUNT, median, source_isolation_audit


def decide(
    *,
    main_runs: list[dict[str, object]],
    oracle_runs: list[dict[str, object]],
    random_runs: list[dict[str, object]],
    generic_runs: list[dict[str, object]],
    scratch_runs: list[dict[str, object]],
    negative_runs: list[dict[str, object]],
    plasticity,
    plasticity_json: str,
    git_commit: str,
    protocol_hash: str,
    github_run_id: str,
    github_run_attempt: int,
    event_action: str,
    canonical: bool,
) -> tuple[dict[str, object], dict[str, bool]]:
    successful_main = [row for row in main_runs if row["success"]]
    successful_random = [row for row in random_runs if row["success"]]
    successful_generic = [row for row in generic_runs if row["success"]]
    successful_scratch = [row for row in scratch_runs if row["success"]]

    exact_principals = len(successful_main)
    oracle_exact = sum(bool(row["success"]) for row in oracle_runs)
    per_machine = {
        str(machine_index): sum(
            bool(row["success"])
            for row in main_runs
            if row["machine_index"] == machine_index
        )
        for machine_index in range(MACHINE_COUNT)
    }
    active_identification = [int(row["identification_calls"]) for row in successful_main]
    active_confirmation = [int(row["confirmation_calls"]) for row in successful_main]
    active_total = [int(row["total_update_calls"]) for row in successful_main]
    random_identification = [int(row["identification_calls"]) for row in successful_random]
    generic_identification = [int(row["identification_calls"]) for row in successful_generic]
    scratch_membership = [int(row["membership_queries"]) for row in successful_scratch]

    correct_abstentions = sum(bool(row["correct_abstention"]) for row in negative_runs)
    false_successes = sum(bool(row["false_success"]) for row in negative_runs)
    archive_mutations = sum(bool(row["archive_mutation"]) for row in negative_runs)
    isolation = source_isolation_audit()

    aggregates: dict[str, object] = {
        "exact_principal_chains": exact_principals,
        "per_machine_exact": per_machine,
        "oracle_ceiling_exact": oracle_exact,
        "median_active_identification_calls": median(active_identification),
        "max_active_identification_calls": max(active_identification) if active_identification else 0,
        "median_active_confirmation_calls": median(active_confirmation),
        "median_active_total_update_calls": median(active_total),
        "max_active_total_update_calls": max(active_total) if active_total else 0,
        "random_policy_successes": len(successful_random),
        "median_random_identification_calls": median(random_identification),
        "generic_no_passport_successes": len(successful_generic),
        "median_generic_identification_calls": median(generic_identification),
        "scratch_lstar_successes": len(successful_scratch),
        "median_scratch_membership_queries": median(scratch_membership),
        "correct_negative_abstentions": correct_abstentions,
        "false_negative_successes": false_successes,
        "negative_archive_mutations": archive_mutations,
        "plasticity_passport_sha256": plasticity.sha256(),
        "plasticity_passport_bytes": len(plasticity_json.encode("utf-8")),
        "development_provenance_sha256": plasticity.development_provenance_sha256,
        "learned_hypothesis_language": list(plasticity.hypothesis_language),
        "learned_prior": dict(plasticity.learned_prior),
        "isolation_audit": isolation,
    }

    all_successes_exact = all(
        row["old_body"]["exact"] is True
        and row["new_body"]["exact"] is True
        and row["old_body"]["hidden_accuracy"] == 1.0
        and row["new_body"]["hidden_accuracy"] == 1.0
        and row["old_body"]["serialization_round_trip"] is True
        and row["new_body"]["serialization_round_trip"] is True
        and row["updated_passport_exact"] is True
        and row["old_body_bit_exact"] is True
        and row["plasticity_round_trip_exact"] is True
        and row["old_semantic_exact_used"] is True
        and row["new_semantic_exact_used"] is True
        and row["consolidation_record_sha256"] is not None
        for row in successful_main
    )
    med_active = float(aggregates["median_active_identification_calls"])
    med_random = float(aggregates["median_random_identification_calls"])
    med_generic = float(aggregates["median_generic_identification_calls"])
    med_scratch = float(aggregates["median_scratch_membership_queries"])

    criteria = {
        "exact_principal_chains_at_least_32_of_36": exact_principals >= 32,
        "at_least_10_of_12_per_machine": all(value >= 10 for value in per_machine.values()),
        "all_claimed_successes_exact_hidden_serialized_semantic_and_archive_safe": all_successes_exact,
        "median_identification_calls_at_most_24": med_active <= 24.0,
        "identification_at_least_25_percent_better_than_scratch_lstar": len(successful_scratch) >= 10
        and med_active <= 0.75 * med_scratch,
        "identification_at_least_20_percent_better_than_random_and_no_passport": len(successful_random) >= 10
        and len(successful_generic) >= 10
        and med_active <= 0.80 * med_random
        and med_active <= 0.80 * med_generic,
        "bounded_total_update_cost_median_52_max_72": float(aggregates["median_active_total_update_calls"]) <= 52.0
        and int(aggregates["max_active_total_update_calls"]) <= 72,
        "oracle_transformation_gap_at_most_four": exact_principals >= oracle_exact - 4,
        "negative_controls_12_of_12_zero_false_success_zero_archive_mutation": correct_abstentions == 12
        and false_successes == 0
        and archive_mutations == 0,
        "complete_sealed_traceability_and_portable_passport": bool(isolation["passed"])
        and isolation["runtime_nonce_calls_in_runner"] == 1
        and len(plasticity_json.encode("utf-8")) <= 2048
        and bool(plasticity.development_provenance_sha256)
        and bool(git_commit)
        and bool(github_run_id)
        and (not canonical or (github_run_attempt == 1 and event_action == "opened"))
        and all(
            row["git_commit"] == git_commit
            and row["protocol_sha256"] == protocol_hash
            and row["github_run_id"] == github_run_id
            and row["plasticity_passport_sha256"] == plasticity.sha256()
            for row in main_runs
        ),
    }
    return aggregates, criteria
