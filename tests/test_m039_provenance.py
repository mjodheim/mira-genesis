from __future__ import annotations

from dataclasses import replace
import hashlib

import pytest

from metamorphosis.m039_journal import LineageJournal, state_digest
from metamorphosis.m039_lineage import (
    CycleManifest,
    LineageManifest,
    M039IntegrityError,
    ToolUse,
    compose_lineage_tool,
    derive_lineage_id,
    protocol_primitive_tool,
)
from metamorphosis.m039_provenance import journal_verified_gate2_tool_ids


def h(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def cycle(index: int, start: str, end: str, *, used=(), constructed=()):
    return CycleManifest(
        cycle=index,
        cycle_seed=index,
        starting_body_digest=start,
        target_digest=h(f"target-{index}"),
        ending_body_digest=end,
        evidence_digest=h(f"evidence-{index}"),
        certificate_digest=h(f"certificate-{index}"),
        compact_trace_head=h(f"compact-{index}"),
        checkpoint_digest=h(f"checkpoint-{index}"),
        journal_head=h(f"journal-{index}"),
        decision_transcript_digest=h(f"transcript-{index}"),
        accepted_candidate_id=h(f"candidate-{index}"),
        accepted_program_digest=h(f"program-{index}"),
        used_tool_ids=tuple(used),
        constructed_tool_ids=tuple(constructed),
        rollback_restored_exactly=True,
        functional_counters={},
        audit_counters={},
    )


def build(*, mismatched_construction=False, unclaimed_reuse=False):
    commitment = "m039-provenance-test"
    lineage_id = derive_lineage_id(39, commitment)
    primitive = protocol_primitive_tool(
        lineage_id=lineage_id,
        protocol_commitment=commitment,
        primitive_name="p0",
        program=({"atom": ["flip", "initial"]},),
        ordinal=0,
    )
    construction_id = h("construction")
    macro = compose_lineage_tool(
        lineage_id=lineage_id,
        protocol_commitment=commitment,
        introduced_cycle=1,
        introduced_by_event=construction_id,
        input_tools=(primitive,),
        program=({"atom": ["flip", "initial"]},),
    )
    use = ToolUse(
        tool_id=macro.tool_id,
        cycle=2,
        candidate_id=h("candidate-use"),
        adopted=True,
        proposing_block_index=0,
    )

    initial = state_digest({"body": "F0"})
    journal = LineageJournal(
        protocol_commitment=commitment,
        lineage_id=lineage_id,
        initial_state_digest=initial,
    )
    journal.start()
    current = initial
    journal.open_cycle(
        1,
        result_state_digest=current,
        operation_parameters={},
        immutable_input_digests=(),
    )
    described_tool = replace(macro, replay_digest=h("wrong")) if mismatched_construction else macro
    journal.append(
        "ToolConstructed",
        result_state_digest=current,
        operation_parameters={
            "construction_event_id": construction_id,
            "tool": described_tool.mapping(),
        },
    )
    current = state_digest({"body": "F1", "registry": [macro.tool_id]})
    journal.complete_cycle(result_state_digest=current, operation_parameters={})

    journal.open_cycle(
        2,
        result_state_digest=current,
        operation_parameters={},
        immutable_input_digests=(),
    )
    journal.append(
        "ToolReused",
        result_state_digest=current,
        operation_parameters=use.mapping(),
    )
    current = state_digest({"body": "F2", "registry": [macro.tool_id]})
    journal.complete_cycle(result_state_digest=current, operation_parameters={})

    journal.open_cycle(
        3,
        result_state_digest=current,
        operation_parameters={},
        immutable_input_digests=(),
    )
    current = state_digest({"body": "F3", "registry": [macro.tool_id]})
    journal.complete_cycle(result_state_digest=current, operation_parameters={})
    journal.complete_lineage(result_state_digest=current, operation_parameters={})
    journal.verify_internal_consistency()

    c1 = cycle(1, h("F0"), h("F1"), constructed=(macro.tool_id,))
    c2 = cycle(2, h("F1"), h("F2"), used=(macro.tool_id,))
    c3 = cycle(3, h("F2"), h("F3"))
    manifest = LineageManifest(
        master_seed=39,
        protocol_commitment=commitment,
        lineage_id=lineage_id,
        initial_body_digest=h("F0"),
        cycles=(c1, c2, c3),
        tool_registry=(primitive, macro),
        tool_uses=() if unclaimed_reuse else (use,),
        ablation_required_tool_ids=(macro.tool_id,),
        final_body_digest=h("F3"),
    )
    return manifest, journal.records, macro.tool_id


def test_gate2_tool_requires_exact_construction_and_reuse_events_in_the_journal():
    manifest, records, tool_id = build()
    assert journal_verified_gate2_tool_ids(manifest, records) == (tool_id,)


def test_self_reported_provenance_does_not_survive_a_mismatched_construction_event():
    manifest, records, _ = build(mismatched_construction=True)
    with pytest.raises(M039IntegrityError, match="does not exactly describe"):
        journal_verified_gate2_tool_ids(manifest, records)


def test_a_reuse_event_missing_from_the_manifest_is_rejected():
    manifest, records, _ = build(unclaimed_reuse=True)
    with pytest.raises(M039IntegrityError, match="absent from the manifest"):
        journal_verified_gate2_tool_ids(manifest, records)


def test_deleting_the_construction_record_breaks_byte_authority_before_eligibility():
    manifest, records, _ = build()
    truncated = tuple(record for index, record in enumerate(records) if index != 2)
    with pytest.raises(Exception):
        journal_verified_gate2_tool_ids(manifest, truncated)
