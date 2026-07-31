from __future__ import annotations

import hashlib

from metamorphosis.m012b_dfa import exact_equivalence
from metamorphosis.m014c_lab import (
    DEVELOPMENT_PROFILES,
    HELD_OUT_PROFILES,
    PROGRAM_LIBRARY,
    BehavioralOracle,
    development_demonstrations,
    generate_environment_sequence,
)
from metamorphosis.m014c_meta import (
    MetaPlasticityPassport,
    MetaPlasticitySession,
    apply_program,
    generate_candidates,
    role_state,
    train_meta_passport,
)


def passport() -> MetaPlasticityPassport:
    return train_meta_passport(PROGRAM_LIBRARY, development_demonstrations())


def test_structural_roles_and_programs_are_applicable_and_ambiguous() -> None:
    sequence = generate_environment_sequence(
        DEVELOPMENT_PROFILES["dev-mixed"], 61_001, episodes=8
    )
    for base, target, program in sequence:
        assert role_state(base, "initial") == base.initial
        assert len(generate_candidates(base, PROGRAM_LIBRARY)) >= 7
        rebuilt = apply_program(base, program)
        assert rebuilt is not None
        assert exact_equivalence(rebuilt, target)[0]


def test_meta_passport_round_trip_and_integer_trace_contract() -> None:
    learned = passport()
    raw = learned.to_json()
    restored = MetaPlasticityPassport.from_json(raw)
    assert restored.to_json() == raw
    assert restored.sha256() == hashlib.sha256(raw.encode()).hexdigest()
    assert "integers_only" in raw
    assert "evaluation_seed" not in raw


def test_adaptive_session_learns_held_out_environment_sequence() -> None:
    learned = passport()
    for env_index, profile in enumerate(HELD_OUT_PROFILES.values()):
        sequence = generate_environment_sequence(
            profile, 62_000 + env_index, episodes=10, min_states=7, max_states=10
        )
        session = MetaPlasticitySession(learned, adaptive=True)
        for episode_index, (base, target, expected_program) in enumerate(sequence):
            result = session.identify(
                base,
                BehavioralOracle(target),
                search_seed=63_000 + env_index * 100 + episode_index,
            )
            assert result.status == "success", (env_index, episode_index, result.reason)
            assert result.updated_passport is not None
            assert exact_equivalence(result.updated_passport, target)[0]
            assert result.program_id == expected_program.program_id
            assert result.trace_digest_sha256


def test_adaptive_session_beats_static_on_dominant_held_out_profiles() -> None:
    learned = passport()
    adaptive_calls: list[int] = []
    static_calls: list[int] = []
    for env_index, profile in enumerate(HELD_OUT_PROFILES.values()):
        sequence = generate_environment_sequence(
            profile, 64_000 + env_index, episodes=20, min_states=7, max_states=10
        )
        adaptive = MetaPlasticitySession(learned, adaptive=True)
        static = MetaPlasticitySession(learned, adaptive=False)
        for episode_index, (base, target, _) in enumerate(sequence):
            a = adaptive.identify(
                base,
                BehavioralOracle(target),
                search_seed=65_000 + env_index * 100 + episode_index,
            )
            s = static.identify(
                base,
                BehavioralOracle(target),
                search_seed=65_000 + env_index * 100 + episode_index,
            )
            assert a.status == s.status == "success"
            if episode_index >= 4:
                adaptive_calls.append(a.identification_calls)
                static_calls.append(s.identification_calls)
    assert sum(adaptive_calls) < sum(static_calls), (sum(adaptive_calls), sum(static_calls))


def test_trace_digest_is_reproducible() -> None:
    learned = passport()
    base, target, _ = generate_environment_sequence(
        HELD_OUT_PROFILES["held-expand"], 66_001, episodes=1, min_states=7, max_states=10
    )[0]
    first = MetaPlasticitySession(learned).identify(
        base, BehavioralOracle(target), search_seed=66_002
    )
    second = MetaPlasticitySession(learned).identify(
        base, BehavioralOracle(target), search_seed=66_002
    )
    assert first.trace_digest_sha256 == second.trace_digest_sha256


def test_persistent_engine_reuses_discovered_substrate_and_preserves_bodies() -> None:
    from metamorphosis.m013e_lab import make_development_positive_machine
    from metamorphosis.m013e_runtime import opaque_body_to_dfa
    from metamorphosis.m014c_engine import DistributionGeneralPlasticityEngine

    learned = passport()
    machine = make_development_positive_machine(0)
    engine = DistributionGeneralPlasticityEngine(machine, learned.to_json())
    sequence = generate_environment_sequence(
        HELD_OUT_PROFILES["held-combo"], 67_001, episodes=3, min_states=6, max_states=8
    )
    first_probe_count = None
    for index, (base, target, _) in enumerate(sequence):
        certificate = engine.adapt_episode(
            base,
            BehavioralOracle(target),
            search_seed=67_100 + index,
        )
        assert certificate.status == "success", certificate.reason
        assert certificate.old_body is not None and certificate.new_body is not None
        assert certificate.updated_passport is not None
        assert certificate.old_body_bit_exact
        assert certificate.meta_passport_round_trip_exact
        assert exact_equivalence(base, opaque_body_to_dfa(certificate.old_body, machine))[0]
        assert exact_equivalence(target, opaque_body_to_dfa(certificate.new_body, machine))[0]
        if first_probe_count is None:
            first_probe_count = certificate.old_migration.probe_calls
            assert first_probe_count > 0
        else:
            assert certificate.old_migration.probe_calls == first_probe_count
    assert engine.discovered_substrate is not None
