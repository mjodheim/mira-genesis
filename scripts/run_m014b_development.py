from __future__ import annotations

import json
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from metamorphosis.m012b_dfa import exact_equivalence
from metamorphosis.m013e_lab import make_development_positive_machine
from metamorphosis.m013e_runtime import opaque_body_to_dfa
from metamorphosis.m014b_engine import PortablePlasticityEngine
from metamorphosis.m014b_lab import (
    BehavioralUpdateOracle,
    hidden_accuracy,
    hidden_words,
    make_development_demonstrations,
    make_development_positive_case,
    make_nondeterministic_oracle,
    make_state_adding_target,
    make_three_edit_target,
)
from metamorphosis.m014b_policy import (
    generic_no_passport_baseline,
    train_plasticity_passport,
)
from metamorphosis.m014b_scratch import learn_dfa_from_scratch_lstar


def median(values: list[int | float]) -> float:
    return float(statistics.median(values)) if values else 0.0


def evaluate_chain(
    base,
    target,
    machine,
    plasticity_json: str,
    search_seed: int,
    *,
    policy_override: str | None = None,
) -> dict[str, object]:
    certificate = PortablePlasticityEngine().adapt(
        base,
        machine,
        plasticity_json,
        BehavioralUpdateOracle(target),
        search_seed,
        policy_override=policy_override,
    )
    exact_old = False
    exact_new = False
    old_hidden = 0.0
    new_hidden = 0.0
    if certificate.old_body is not None:
        old_candidate = opaque_body_to_dfa(certificate.old_body, machine)
        exact_old = exact_equivalence(base, old_candidate)[0]
        old_hidden = hidden_accuracy(base, old_candidate, hidden_words(search_seed ^ 0x0D1D))
    if certificate.new_body is not None:
        new_candidate = opaque_body_to_dfa(certificate.new_body, machine)
        exact_new = exact_equivalence(target, new_candidate)[0]
        new_hidden = hidden_accuracy(target, new_candidate, hidden_words(search_seed ^ 0x0E2E))
    return {
        "status": certificate.status,
        "reason": certificate.reason,
        "exact_old": exact_old,
        "exact_new": exact_new,
        "old_hidden_accuracy": old_hidden,
        "new_hidden_accuracy": new_hidden,
        "old_body_bit_exact": certificate.old_body_bit_exact,
        "plasticity_round_trip_exact": certificate.plasticity_round_trip_exact,
        "inference_calls": certificate.inference.raw_oracle_calls if certificate.inference else 0,
        "confirmation_calls": certificate.confirmation.raw_oracle_calls if certificate.confirmation else 0,
        "total_update_calls": certificate.total_update_oracle_calls,
        "initial_candidates": certificate.inference.initial_candidates if certificate.inference else 0,
        "selected_schema": (
            certificate.inference.selected_hypothesis.kind
            if certificate.inference and certificate.inference.selected_hypothesis
            else None
        ),
        "old_probe_calls": certificate.old_migration.probe_calls,
        "new_candidate_evaluations": (
            certificate.new_migration.candidate_evaluations
            if certificate.new_migration is not None
            else 0
        ),
        "success": bool(
            certificate.status == "success"
            and exact_old
            and exact_new
            and old_hidden == 1.0
            and new_hidden == 1.0
            and certificate.old_body_bit_exact
            and certificate.plasticity_round_trip_exact
        ),
    }


def run() -> dict[str, object]:
    plasticity = train_plasticity_passport(make_development_demonstrations())
    plasticity_json = plasticity.to_json()
    generic_json = generic_no_passport_baseline().to_json()
    cases = [make_development_positive_case(index) for index in range(12)]

    main_runs: list[dict[str, object]] = []
    for case_index, (base, selected) in enumerate(cases):
        for family in range(3):
            row = evaluate_chain(
                base,
                selected.dfa,
                make_development_positive_machine(family),
                plasticity_json,
                41_000 + case_index * 10 + family,
            )
            row.update({"case_index": case_index, "machine_family": family})
            main_runs.append(row)

    random_runs: list[dict[str, object]] = []
    generic_runs: list[dict[str, object]] = []
    scratch_runs: list[dict[str, object]] = []
    for case_index, (base, selected) in enumerate(cases):
        random_row = evaluate_chain(
            base,
            selected.dfa,
            make_development_positive_machine(case_index % 3),
            plasticity_json,
            42_000 + case_index,
            policy_override="random",
        )
        random_row["case_index"] = case_index
        random_runs.append(random_row)

        generic_row = evaluate_chain(
            base,
            selected.dfa,
            make_development_positive_machine(case_index % 3),
            generic_json,
            43_000 + case_index,
        )
        generic_row["case_index"] = case_index
        generic_runs.append(generic_row)

        oracle = BehavioralUpdateOracle(selected.dfa)
        scratch = learn_dfa_from_scratch_lstar(selected.dfa, oracle)
        scratch_runs.append(
            {
                "case_index": case_index,
                "status": scratch.status,
                "reason": scratch.reason,
                "membership_queries": scratch.unique_membership_queries,
                "equivalence_queries": scratch.equivalence_queries,
                "success": bool(
                    scratch.status == "success"
                    and scratch.hypothesis is not None
                    and exact_equivalence(scratch.hypothesis, selected.dfa)[0]
                ),
            }
        )

    negative_runs: list[dict[str, object]] = []
    for index in range(12):
        base, _ = cases[index]
        family = index % 3
        negative_family = index // 4
        if negative_family == 0:
            oracle = BehavioralUpdateOracle(make_three_edit_target(base, 44_000 + index))
            kind = "three_edit"
        elif negative_family == 1:
            oracle = BehavioralUpdateOracle(make_state_adding_target(base, 44_000 + index))
            kind = "state_adding"
        else:
            oracle = make_nondeterministic_oracle(base, 44_000 + index, index)
            kind = "nondeterministic"
        certificate = PortablePlasticityEngine().adapt(
            base,
            make_development_positive_machine(family),
            plasticity_json,
            oracle,
            45_000 + index,
        )
        negative_runs.append(
            {
                "index": index,
                "kind": kind,
                "status": certificate.status,
                "reason": certificate.reason,
                "old_body_bit_exact": certificate.old_body_bit_exact,
                "new_body_absent": certificate.new_body is None,
                "correct_abstention": bool(
                    certificate.status == "abstained"
                    and certificate.new_body is None
                    and certificate.old_body_bit_exact
                ),
            }
        )

    active_calls = [int(row["total_update_calls"]) for row in main_runs if row["success"]]
    random_calls = [int(row["total_update_calls"]) for row in random_runs if row["success"]]
    generic_calls = [int(row["total_update_calls"]) for row in generic_runs if row["success"]]
    scratch_calls = [int(row["membership_queries"]) for row in scratch_runs if row["success"]]
    aggregates = {
        "main_successes": sum(bool(row["success"]) for row in main_runs),
        "main_total": len(main_runs),
        "per_machine_successes": {
            str(family): sum(
                bool(row["success"])
                for row in main_runs
                if row["machine_family"] == family
            )
            for family in range(3)
        },
        "median_active_total_update_calls": median(active_calls),
        "max_active_total_update_calls": max(active_calls) if active_calls else 0,
        "median_active_identification_calls": median(
            [int(row["inference_calls"]) for row in main_runs if row["success"]]
        ),
        "random_successes": sum(bool(row["success"]) for row in random_runs),
        "median_random_total_update_calls": median(random_calls),
        "generic_no_passport_successes": sum(bool(row["success"]) for row in generic_runs),
        "median_generic_total_update_calls": median(generic_calls),
        "scratch_successes": sum(bool(row["success"]) for row in scratch_runs),
        "median_scratch_membership_queries": median(scratch_calls),
        "active_vs_scratch_query_factor": (
            median(scratch_calls) / median(active_calls)
            if active_calls and median(active_calls) > 0
            else 0.0
        ),
        "correct_negative_abstentions": sum(
            bool(row["correct_abstention"]) for row in negative_runs
        ),
        "plasticity_passport_sha256": plasticity.sha256(),
        "plasticity_passport_bytes": len(plasticity_json.encode("utf-8")),
        "learned_hypothesis_language": list(plasticity.hypothesis_language),
        "learned_prior": dict(plasticity.learned_prior),
        "learned_length_penalty": plasticity.length_penalty,
    }
    return {
        "experiment": "M014b",
        "status": "DEVELOPMENT_ONLY",
        "plasticity_passport": json.loads(plasticity_json),
        "main_runs": main_runs,
        "random_policy_runs": random_runs,
        "generic_no_passport_runs": generic_runs,
        "scratch_lstar_runs": scratch_runs,
        "negative_controls": negative_runs,
        "aggregates": aggregates,
    }


def main() -> None:
    result = run()
    output = ROOT / "results" / "M014b_development.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result["aggregates"], indent=2))


if __name__ == "__main__":
    main()
