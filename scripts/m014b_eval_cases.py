from __future__ import annotations

from typing import Any

from metamorphosis.m012b_dfa import exact_equivalence, random_minimal_dfa
from metamorphosis.m013e_lab import make_positive_machine
from metamorphosis.m014b_engine import PortablePlasticityEngine
from metamorphosis.m014b_lab import (
    BehavioralUpdateOracle,
    make_development_demonstrations,
    make_nondeterministic_oracle,
    make_positive_update,
    make_state_adding_target,
    make_three_edit_target,
)
from metamorphosis.m014b_policy import (
    generic_no_passport_baseline,
    normalize_dfa,
    train_plasticity_passport,
)
from metamorphosis.m014b_scratch import learn_dfa_from_scratch_lstar
from m014b_eval_support import (
    HiddenSuite,
    MACHINE_COUNT,
    evaluate_chain,
    evaluate_oracle_ceiling,
    hidden_words,
)


def build_assets(spec):
    plasticity = train_plasticity_passport(make_development_demonstrations())
    plasticity_json = plasticity.to_json()
    generic_json = generic_no_passport_baseline().to_json()
    bases = [normalize_dfa(random_minimal_dfa(seed)) for seed in spec.base_passport_seeds]
    updates = [
        make_positive_update(base, update_seed)
        for base, update_seed in zip(bases, spec.update_seeds)
    ]
    targets = [update.dfa for update in updates]
    old_suites = [
        HiddenSuite(base, hidden_words(seed))
        for base, seed in zip(bases, spec.hidden_old_seeds)
    ]
    new_suites = [
        HiddenSuite(target, hidden_words(seed))
        for target, seed in zip(targets, spec.hidden_new_seeds)
    ]
    return plasticity, plasticity_json, generic_json, bases, targets, old_suites, new_suites


def run_main_and_oracle(
    spec,
    trace_base: dict[str, object],
    plasticity_json: str,
    bases,
    targets,
    old_suites,
    new_suites,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    engine = PortablePlasticityEngine(query_budget=192)
    main_runs: list[dict[str, object]] = []
    oracle_runs: list[dict[str, object]] = []
    for case_index, (base, target) in enumerate(zip(bases, targets)):
        for machine_index, (machine_seed, family) in enumerate(
            zip(spec.machine_seeds, spec.machine_families)
        ):
            search_seed = spec.search_seeds[case_index * MACHINE_COUNT + machine_index]
            trace = {
                **trace_base,
                "case_index": case_index,
                "machine_index": machine_index,
                "search_seed": search_seed,
            }
            machine = make_positive_machine(machine_seed, family)
            certificate = engine.adapt(
                base,
                machine,
                plasticity_json,
                BehavioralUpdateOracle(target),
                search_seed,
                trace,
            )
            main_runs.append({
                **trace,
                **evaluate_chain(
                    certificate,
                    base,
                    target,
                    machine,
                    old_suites[case_index],
                    new_suites[case_index],
                ),
            })
            oracle_machine = make_positive_machine(machine_seed, family)
            oracle_runs.append({
                **trace,
                **evaluate_oracle_ceiling(
                    base,
                    target,
                    oracle_machine,
                    search_seed,
                    trace,
                ),
            })
    return main_runs, oracle_runs


def run_baselines(
    spec,
    trace_base: dict[str, object],
    plasticity_json: str,
    generic_json: str,
    bases,
    targets,
) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    engine = PortablePlasticityEngine(query_budget=192)
    random_runs: list[dict[str, object]] = []
    generic_runs: list[dict[str, object]] = []
    scratch_runs: list[dict[str, object]] = []
    for case_index, (base, target) in enumerate(zip(bases, targets)):
        machine_index = case_index % MACHINE_COUNT
        machine_seed = spec.machine_seeds[machine_index]
        family = spec.machine_families[machine_index]
        base_search_seed = spec.search_seeds[case_index * MACHINE_COUNT + machine_index]

        random_seed = base_search_seed ^ 0xA11C_E001
        random_trace = {
            **trace_base,
            "case_index": case_index,
            "machine_index": machine_index,
            "baseline": "random_query_policy",
            "search_seed": random_seed,
        }
        random_machine = make_positive_machine(machine_seed, family)
        random_certificate = engine.adapt(
            base,
            random_machine,
            plasticity_json,
            BehavioralUpdateOracle(target),
            random_seed,
            random_trace,
            policy_override="random",
        )
        random_runs.append({
            **random_trace,
            **evaluate_chain(random_certificate, base, target, random_machine, None, None),
        })

        generic_seed = base_search_seed ^ 0xB45E_0001
        generic_trace = {
            **trace_base,
            "case_index": case_index,
            "machine_index": machine_index,
            "baseline": "no_learned_plasticity_passport",
            "search_seed": generic_seed,
        }
        generic_machine = make_positive_machine(machine_seed, family)
        generic_certificate = engine.adapt(
            base,
            generic_machine,
            generic_json,
            BehavioralUpdateOracle(target),
            generic_seed,
            generic_trace,
        )
        generic_runs.append({
            **generic_trace,
            **evaluate_chain(generic_certificate, base, target, generic_machine, None, None),
        })

        scratch_oracle = BehavioralUpdateOracle(target)
        scratch = learn_dfa_from_scratch_lstar(target, scratch_oracle)
        scratch_runs.append({
            **trace_base,
            "case_index": case_index,
            "baseline": "scratch_lstar",
            "status": scratch.status,
            "reason": scratch.reason,
            "membership_queries": scratch.unique_membership_queries,
            "equivalence_queries": scratch.equivalence_queries,
            "success": bool(
                scratch.status == "success"
                and scratch.hypothesis is not None
                and exact_equivalence(scratch.hypothesis, target)[0]
            ),
        })
    return random_runs, generic_runs, scratch_runs


def run_negative_controls(
    spec,
    trace_base: dict[str, object],
    plasticity_json: str,
) -> list[dict[str, object]]:
    engine = PortablePlasticityEngine(query_budget=192)
    negative_runs: list[dict[str, object]] = []
    for index, (base_seed, update_seed, kind) in enumerate(
        zip(spec.negative_base_seeds, spec.negative_update_seeds, spec.negative_kinds)
    ):
        base = normalize_dfa(random_minimal_dfa(base_seed))
        if kind == 0:
            target = make_three_edit_target(base, update_seed)
            oracle = BehavioralUpdateOracle(target)
            kind_name = "three_edit_out_of_language"
        elif kind == 1:
            target = make_state_adding_target(base, update_seed)
            oracle = BehavioralUpdateOracle(target)
            kind_name = "state_adding_out_of_language"
        else:
            oracle = make_nondeterministic_oracle(base, update_seed, index)
            target = oracle._audit_target()
            kind_name = "nondeterministic_or_changing_oracle"
        machine_index = index % MACHINE_COUNT
        machine = make_positive_machine(
            spec.machine_seeds[machine_index],
            spec.machine_families[machine_index],
        )
        search_seed = spec.search_seeds[index * MACHINE_COUNT + machine_index] ^ 0x0E6A_71F0
        trace = {
            **trace_base,
            "negative_index": index,
            "negative_kind": kind_name,
            "machine_index": machine_index,
            "search_seed": search_seed,
        }
        certificate = engine.adapt(
            base,
            machine,
            plasticity_json,
            oracle,
            search_seed,
            trace,
        )
        evaluated = evaluate_chain(certificate, base, target, machine, None, None)
        false_success = bool(certificate.status == "success" or certificate.new_body is not None)
        archive_mutation = not certificate.old_body_bit_exact
        correct_abstention = bool(
            certificate.status == "abstained"
            and certificate.new_body is None
            and certificate.old_body_bit_exact
            and evaluated["old_body"]["exact"] is True
            and evaluated["old_body"]["serialization_round_trip"] is True
        )
        negative_runs.append({
            **trace,
            **evaluated,
            "false_success": false_success,
            "archive_mutation": archive_mutation,
            "correct_abstention": correct_abstention,
        })
    return negative_runs
