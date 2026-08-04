from __future__ import annotations

import inspect
import json

import pytest

from metamorphosis.m012b_dfa import exact_equivalence
from metamorphosis.m038_two_speed import (
    OBSERVATION_WORDS,
    _candidate_stream,
    _tool_registry,
    compare_arms_b_and_c,
    make_m038_task,
    run_m038_development_cycle,
)


@pytest.fixture(scope="module")
def comparison():
    return run_m038_development_cycle()


def test_the_committed_development_task_is_deterministic_and_requires_growth():
    first = make_m038_task(380_038)
    second = make_m038_task(380_038)

    assert first.founder == second.founder
    assert first.target == second.target
    assert first.generating_program == second.generating_program
    assert first.founder.n_states == 4
    assert first.target.n_states > first.founder.n_states
    assert 1 <= len(first.generating_program) <= 3
    assert len(first.observation_words) == len(OBSERVATION_WORDS) == 127


def test_arm_a_stays_at_f0_and_fails_by_proved_capacity_impossibility(comparison):
    arm = comparison.arm_a

    assert not arm.solved
    assert arm.control_impossibility_proved
    assert not arm.infrastructure_cycle_valid
    assert not arm.functional_metamorphosis_supported
    assert arm.initial_state_digest == arm.final_state_digest
    assert arm.checkpoint_digest is None
    assert arm.journal_records == ()


def test_arms_b_and_c_complete_the_full_f0_to_f1_sequence(comparison):
    for arm in (comparison.arm_b, comparison.arm_c):
        assert arm.solved
        assert arm.infrastructure_cycle_valid
        assert arm.functional_metamorphosis_supported
        assert arm.final_state_digest != arm.initial_state_digest
        assert exact_equivalence(arm.final_body, comparison.task.target)[0]
        assert not exact_equivalence(comparison.task.founder, comparison.task.target)[0]


def test_b_and_c_have_the_same_decisions_and_functional_outcome(comparison):
    b = comparison.arm_b
    c = comparison.arm_c

    assert comparison.decision_equivalent
    assert b.decision_transcript == c.decision_transcript
    assert b.decision_transcript_digest == c.decision_transcript_digest
    assert b.final_body == c.final_body
    assert b.final_state_digest == c.final_state_digest
    assert b.functional_counters == c.functional_counters
    assert b.checkpoint_digest == c.checkpoint_digest
    assert b.journal_head == c.journal_head
    assert b.journal_records == c.journal_records


def test_c_is_an_instrumental_strict_superset_of_b(comparison):
    b = comparison.arm_b
    c = comparison.arm_c

    assert comparison.compact_trace_equal
    assert b.rolling_head == c.rolling_head
    assert comparison.evidence_strict_subset
    assert b.full_fast_path_records == ()
    assert len(c.full_fast_path_records) == len(OBSERVATION_WORDS)
    assert c.full_fast_path_head is not None


def test_the_pre_registered_efficiency_rule_is_satisfied(comparison):
    b = comparison.arm_b.audit_counters
    c = comparison.arm_c.audit_counters

    assert comparison.efficiency_claim_supported
    assert b["body_serializations"] <= c["body_serializations"]
    for name in (
        "persisted_event_serializations",
        "journal_bytes_persisted",
        "audit_deterministic_operations",
    ):
        assert b[name] < c[name]


def test_the_cycle_records_adoption_rejection_and_rollback(comparison):
    event_types = [
        row["event_type"]
        for row in (
            __import__("metamorphosis.m038_journal", fromlist=["decode"]).decode(record)
            for record in comparison.arm_b.journal_records
        )
    ]

    assert event_types[0] == "EscalationCheckpointCreated"
    assert "StructuralIncapacityCertified" in event_types
    assert "MutationAdopted" in event_types
    assert "MutationProvisionallyAdopted" in event_types
    assert "CandidateRejected" in event_types
    assert "RollbackRequested" in event_types
    assert "RollbackCompleted" in event_types
    assert event_types[-1] == "CycleCompleted"
    assert "ToolConstructed" not in event_types


def test_the_exact_certificate_drives_the_boundary(comparison):
    for arm in (comparison.arm_a, comparison.arm_b, comparison.arm_c):
        certificate = arm.certificate
        assert certificate["certificate_status"] == "available"
        assert certificate["certified_lower_bound"] > certificate["body_state_count"]

    assert comparison.arm_a.functional_counters["escalations"] == 0
    assert comparison.arm_b.functional_counters["escalations"] == 1
    assert comparison.arm_c.functional_counters["escalations"] == 1
    assert comparison.arm_b.functional_counters["false_escalations"] == 0
    assert comparison.arm_b.functional_counters["missed_escalations"] == 0


def test_the_slow_path_recomputes_the_certificate(comparison):
    a = comparison.arm_a.functional_counters
    b = comparison.arm_b.functional_counters
    c = comparison.arm_c.functional_counters

    assert b["certificate_search_nodes"] == c["certificate_search_nodes"]
    assert b["certificate_pair_tests"] == c["certificate_pair_tests"]
    assert b["certificate_suffix_probes"] == c["certificate_suffix_probes"]
    assert b["certificate_search_nodes"] == 2 * a["certificate_search_nodes"]
    assert b["certificate_pair_tests"] == 2 * a["certificate_pair_tests"]
    assert b["certificate_suffix_probes"] == 2 * a["certificate_suffix_probes"]


def test_the_proposal_surface_has_no_hidden_target_argument():
    signature = inspect.signature(_candidate_stream)
    source = inspect.getsource(_candidate_stream)

    assert "target" not in signature.parameters
    assert "target" not in source


def test_the_registry_contains_only_protocol_supplied_primitives():
    registry = _tool_registry()

    assert registry
    assert all(tool["origin"] == "protocol_supplied" for tool in registry)
    assert all(tool["construction_kind"] == "primitive" for tool in registry)
    assert all(tool["introduction_phase"] == "birth" for tool in registry)
    assert all(tool["eligible_for_gate2"] is False for tool in registry)


def test_the_cycle_is_reproducible_and_uses_no_rng_draws(comparison):
    reproduced = run_m038_development_cycle()

    assert comparison.summary() == reproduced.summary()
    assert comparison.arm_b.functional_counters["rng_draws"] == 0
    assert comparison.arm_c.functional_counters["rng_draws"] == 0


def test_the_comparison_helper_rejects_a_decision_divergence(comparison):
    from dataclasses import replace

    changed = replace(
        comparison.arm_c,
        decision_transcript_digest="0" * 64,
    )
    decision, _, _, efficiency = compare_arms_b_and_c(comparison.arm_b, changed)

    assert not decision
    assert not efficiency


def test_the_summary_is_json_serialisable_and_the_combined_claim_is_supported(comparison):
    rendered = json.dumps(comparison.summary(), sort_keys=True)

    assert "combined_expected_claim_supported" in rendered
    assert comparison.combined_expected_claim_supported
