from __future__ import annotations

import hashlib

import pytest

from metamorphosis.m012b_dfa import DFA
from metamorphosis.m039_engine import _candidate_id, dfa_digest
from metamorphosis.m039_lineage import (
    CycleManifest,
    derive_lineage_id,
    protocol_primitive_tool,
)
from metamorphosis.m039_search_audit import (
    M039SearchAuditError,
    audit_search,
    verify_cycle_search_audit,
)
from metamorphosis.structural import apply_atom, enumerate_words, flip, normalize_dfa


def h(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def tool(lineage_id: str, commitment: str, name: str, atom, ordinal: int):
    return protocol_primitive_tool(
        lineage_id=lineage_id,
        protocol_commitment=commitment,
        primitive_name=name,
        program=({"atom": atom.to_list()},),
        ordinal=ordinal,
    )


def setup_search():
    commitment = "m039-search-audit-test"
    lineage_id = derive_lineage_id(39, commitment)
    founder = DFA(
        alphabet=(0, 1),
        transitions=((0, 1), (1, 1)),
        accepting=(False, True),
        initial=0,
    )
    rejected_tool = tool(
        lineage_id,
        commitment,
        "reject-first",
        flip("deepest_accepting"),
        0,
    )
    accepted_tool = tool(
        lineage_id,
        commitment,
        "accept-second",
        flip("initial"),
        1,
    )
    raw_target = apply_atom(founder, flip("initial"))
    assert raw_target is not None
    target = normalize_dfa(raw_target)
    accepted_id = _candidate_id(1, (1,), (accepted_tool,), target)
    audit = audit_search(
        cycle=1,
        founder=founder,
        target=target,
        registry=(rejected_tool, accepted_tool),
        maximum_depth=1,
        expected_accepted_candidate_id=accepted_id,
        observation_words=enumerate_words(2),
    )
    cycle = CycleManifest(
        cycle=1,
        cycle_seed=1,
        starting_body_digest=dfa_digest(founder),
        target_digest=dfa_digest(target),
        ending_body_digest=dfa_digest(target),
        evidence_digest=h("evidence"),
        certificate_digest=h("certificate"),
        compact_trace_head=h("compact"),
        checkpoint_digest=h("checkpoint"),
        journal_head=h("journal"),
        decision_transcript_digest=h("decision"),
        accepted_candidate_id=accepted_id,
        accepted_program_digest=h("program"),
        used_tool_ids=(),
        constructed_tool_ids=(),
        rollback_restored_exactly=True,
        functional_counters={
            "symbolic_search_nodes": 2,
            "primitive_expansion_operations": 2,
            "candidates_constructed": 2,
        },
        audit_counters={},
    )
    return audit, cycle, founder, target, rejected_tool, accepted_tool


def test_hidden_evidence_rejection_is_committed_before_the_adopted_candidate():
    audit, cycle, *_ = setup_search()

    assert audit.evidence_rejections == 1
    assert audit.evidence_admitted_candidates == 1
    assert audit.exact_evaluations == 1
    assert audit.symbolic_search_nodes == 2
    assert audit.completed_candidates == 2
    assert audit.transcript_entries == 5
    verify_cycle_search_audit(audit, cycle)


def test_a_counter_that_preserves_the_final_candidate_but_changes_history_is_rejected():
    audit, cycle, *_ = setup_search()
    wrong = CycleManifest(
        **{
            **cycle.__dict__,
            "functional_counters": {
                **cycle.functional_counters,
                "candidates_constructed": 1,
            },
        }
    )

    with pytest.raises(M039SearchAuditError, match="candidates_constructed"):
        verify_cycle_search_audit(audit, wrong)


def test_registry_reordering_cannot_replay_as_the_same_search_history():
    audit, _, founder, target, rejected_tool, accepted_tool = setup_search()

    with pytest.raises(M039SearchAuditError, match="different candidate"):
        audit_search(
            cycle=1,
            founder=founder,
            target=target,
            registry=(accepted_tool, rejected_tool),
            maximum_depth=1,
            expected_accepted_candidate_id=audit.accepted_candidate_id,
            observation_words=enumerate_words(2),
        )


def test_transcript_digest_is_stable_for_the_same_ordered_search():
    first, _, founder, target, rejected_tool, accepted_tool = setup_search()
    second = audit_search(
        cycle=1,
        founder=founder,
        target=target,
        registry=(rejected_tool, accepted_tool),
        maximum_depth=1,
        expected_accepted_candidate_id=first.accepted_candidate_id,
        observation_words=enumerate_words(2),
    )
    assert second.mapping() == first.mapping()
