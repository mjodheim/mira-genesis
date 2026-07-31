from __future__ import annotations

from pathlib import Path

from metamorphosis.m012b_dfa import exact_equivalence
from metamorphosis.m013e_lab import make_development_positive_machine
from metamorphosis.m013e_runtime import opaque_body_to_dfa
from metamorphosis.m014b_engine import PortablePlasticityEngine
from metamorphosis.m014b_lab import (
    BehavioralUpdateOracle,
    make_development_demonstrations,
    make_development_positive_case,
    make_nondeterministic_oracle,
    make_state_adding_target,
    make_three_edit_target,
)
from metamorphosis.m014b_policy import (
    LEARNABLE_SCHEMAS,
    PlasticityPassport,
    generic_no_passport_baseline,
    identify_update,
    train_plasticity_passport,
)
from metamorphosis.m014b_scratch import learn_dfa_from_scratch_lstar


def learned_passport() -> PlasticityPassport:
    return train_plasticity_passport(make_development_demonstrations())


def test_plasticity_passport_is_learned_serializable_and_machine_independent() -> None:
    passport = learned_passport()
    assert passport.hypothesis_language == LEARNABLE_SCHEMAS
    raw = passport.to_json()
    assert PlasticityPassport.from_json(raw).to_json() == raw
    assert passport.sha256() == PlasticityPassport.from_json(raw).sha256()
    lowered = raw.lower()
    for forbidden in ("evaluation_seed", "expected_answers", "opcode_map", "machine_specific_compiler"):
        assert forbidden not in lowered


def test_active_policy_identifies_all_development_update_families() -> None:
    passport = learned_passport()
    for index in range(12):
        base, selected = make_development_positive_case(index)
        inference = identify_update(
            base,
            BehavioralUpdateOracle(selected.dfa),
            passport,
            query_budget=192,
            search_seed=34_000 + index,
        )
        assert inference.status == "success", (index, inference.reason)
        assert inference.updated_passport is not None
        assert exact_equivalence(inference.updated_passport, selected.dfa)[0]
        assert inference.raw_oracle_calls <= 192


def test_active_policy_and_generic_baselines_are_operational() -> None:
    passport = learned_passport()
    generic = generic_no_passport_baseline()
    base, selected = make_development_positive_case(0)
    active = identify_update(
        base,
        BehavioralUpdateOracle(selected.dfa),
        passport,
        search_seed=35_001,
    )
    random_policy = identify_update(
        base,
        BehavioralUpdateOracle(selected.dfa),
        passport,
        policy="random",
        search_seed=35_001,
    )
    no_passport = identify_update(
        base,
        BehavioralUpdateOracle(selected.dfa),
        generic,
        search_seed=35_001,
    )
    assert active.status == "success"
    assert random_policy.status in {"success", "abstained"}
    assert no_passport.status in {"success", "abstained"}
    assert active.initial_candidates <= no_passport.initial_candidates


def test_privileged_scratch_lstar_recovers_development_target() -> None:
    _, selected = make_development_positive_case(1)
    oracle = BehavioralUpdateOracle(selected.dfa)
    result = learn_dfa_from_scratch_lstar(selected.dfa, oracle)
    assert result.status == "success", result.reason
    assert result.hypothesis is not None
    assert exact_equivalence(result.hypothesis, selected.dfa)[0]


def test_complete_portable_chain_works_on_three_development_machine_families() -> None:
    passport = learned_passport()
    raw = passport.to_json()
    base, selected = make_development_positive_case(2)
    for family in range(3):
        machine = make_development_positive_machine(family)
        certificate = PortablePlasticityEngine().adapt(
            base,
            machine,
            raw,
            BehavioralUpdateOracle(selected.dfa),
            36_000 + family,
        )
        assert certificate.status == "success", (family, certificate.reason)
        assert certificate.old_body is not None
        assert certificate.new_body is not None
        assert certificate.updated_passport is not None
        assert certificate.old_body_bit_exact
        assert certificate.plasticity_round_trip_exact
        assert exact_equivalence(base, opaque_body_to_dfa(certificate.old_body, machine))[0]
        assert exact_equivalence(selected.dfa, opaque_body_to_dfa(certificate.new_body, machine))[0]


def test_negative_families_abstain_without_mutating_archive() -> None:
    passport = learned_passport()
    raw = passport.to_json()
    base, _ = make_development_positive_case(3)
    targets = [
        BehavioralUpdateOracle(make_three_edit_target(base, 37_001)),
        BehavioralUpdateOracle(make_state_adding_target(base, 37_002)),
        make_nondeterministic_oracle(base, 37_003, 0),
    ]
    for index, oracle in enumerate(targets):
        machine = make_development_positive_machine(index)
        certificate = PortablePlasticityEngine().adapt(
            base,
            machine,
            raw,
            oracle,
            37_100 + index,
        )
        assert certificate.status == "abstained", (index, certificate.reason)
        assert certificate.new_body is None
        assert certificate.old_body is not None
        assert certificate.old_body_bit_exact


def test_public_engine_and_policy_do_not_import_private_update_lab_or_sealed_cases() -> None:
    root = Path(__file__).resolve().parents[1]
    source = "\n".join(
        (root / path).read_text(encoding="utf-8")
        for path in (
            "metamorphosis/m014b_policy.py",
            "metamorphosis/m014b_engine.py",
        )
    )
    assert "m014b_lab" not in source
    assert "m014b_sealed" not in source
    assert "_audit_target" not in source
    sealed_nonce_symbol = "runtime" + "_" + "nonce"
    assert sealed_nonce_symbol not in source
