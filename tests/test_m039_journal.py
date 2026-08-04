from __future__ import annotations

from dataclasses import replace

import pytest

from metamorphosis.m038_journal import decode, encode
from metamorphosis.m039_journal import (
    LineageEvent,
    LineageJournal,
    M039JournalError,
    state_digest,
    verify_lineage_records,
)


PROTOCOL = "m039-development"
LINEAGE = "a" * 64


def state(body: str, cycle: int = 0) -> bytes:
    return state_digest({"body": body, "cycle": cycle, "registry": []})


def complete_journal() -> LineageJournal:
    initial = state("F0")
    journal = LineageJournal(
        protocol_commitment=PROTOCOL,
        lineage_id=LINEAGE,
        initial_state_digest=initial,
    )
    journal.start(immutable_input_digests=(b"s" * 32,))
    current = initial
    for cycle in (1, 2, 3):
        journal.open_cycle(
            cycle,
            result_state_digest=current,
            operation_parameters={"cycle": cycle},
            immutable_input_digests=(bytes([cycle]) * 32,),
        )
        journal.append(
            "StructuralIncapacityCertified",
            result_state_digest=current,
            operation_parameters={"proved": True},
        )
        adopted = state(f"F{cycle}", cycle)
        journal.append(
            "MutationAdopted",
            result_state_digest=adopted,
            operation_parameters={"candidate": cycle},
        )
        if cycle == 2:
            provisional = state("bad", cycle)
            journal.append(
                "MutationProvisionallyAdopted",
                result_state_digest=provisional,
                operation_parameters={"forced": True},
            )
            journal.rollback(target_state_digest=adopted, reason="forced probe")
        journal.complete_cycle(
            result_state_digest=adopted,
            operation_parameters={"accepted": True},
        )
        current = adopted
    journal.complete_lineage(
        result_state_digest=current,
        operation_parameters={"accepted_cycles": 3},
        immutable_input_digests=(b"m" * 32,),
    )
    return journal


def test_one_chain_spans_three_ordered_cycles_and_verifies_against_external_anchors():
    journal = complete_journal()

    journal.verify_internal_consistency()
    journal.verify_against(
        expected_initial_state_digest=state("F0"),
        expected_head=journal.head,
        expected_final_state_digest=state("F3", 3),
    )
    assert journal.completed_cycles == 3
    assert journal.events[0].event_type == "LineageStarted"
    assert journal.events[-1].event_type == "LineageCompleted"
    assert journal.counters()["events"] == len(journal.records)
    assert journal.counters()["persisted_bytes"] == sum(map(len, journal.records))


def test_rollback_restores_functional_state_without_erasing_audit_history():
    journal = complete_journal()
    requested = next(event for event in journal.events if event.event_type == "RollbackRequested")
    completed = next(event for event in journal.events if event.event_type == "RollbackCompleted")
    cycle_two_completion = next(
        event
        for event in journal.events
        if event.event_type == "CycleCompleted" and event.cycle == 2
    )

    assert completed.sequence == requested.sequence + 1
    assert completed.result_state_digest == cycle_two_completion.result_state_digest
    assert len(journal.events) > completed.sequence + 1


def test_a_fourth_cycle_or_out_of_order_cycle_is_rejected():
    journal = LineageJournal(
        protocol_commitment=PROTOCOL,
        lineage_id=LINEAGE,
        initial_state_digest=state("F0"),
    )
    journal.start()

    with pytest.raises(M039JournalError, match="expected cycle 1"):
        journal.open_cycle(
            2,
            result_state_digest=state("F0"),
            operation_parameters={},
            immutable_input_digests=(),
        )


def test_lineage_cannot_complete_before_three_closed_cycles():
    journal = LineageJournal(
        protocol_commitment=PROTOCOL,
        lineage_id=LINEAGE,
        initial_state_digest=state("F0"),
    )
    journal.start()

    with pytest.raises(M039JournalError, match="exactly three"):
        journal.complete_lineage(
            result_state_digest=state("F0"),
            operation_parameters={},
        )


def test_altering_a_persisted_event_breaks_the_chain():
    journal = complete_journal()
    records = list(journal.records)
    fields = decode(records[3])
    assert isinstance(fields, dict)
    fields["operation_parameters"] = {"altered": True}
    records[3] = encode(fields)

    with pytest.raises(M039JournalError, match="altered"):
        verify_lineage_records(
            records,
            protocol_commitment=PROTOCOL,
            lineage_id=LINEAGE,
            expected_initial_state_digest=state("F0"),
        )


def test_reordering_or_deleting_an_event_is_detected():
    journal = complete_journal()
    reordered = list(journal.records)
    reordered[2], reordered[3] = reordered[3], reordered[2]
    with pytest.raises(M039JournalError):
        verify_lineage_records(
            reordered,
            protocol_commitment=PROTOCOL,
            lineage_id=LINEAGE,
            expected_initial_state_digest=state("F0"),
        )

    deleted = list(journal.records)
    del deleted[4]
    with pytest.raises(M039JournalError):
        verify_lineage_records(
            deleted,
            protocol_commitment=PROTOCOL,
            lineage_id=LINEAGE,
            expected_initial_state_digest=state("F0"),
        )


def test_external_head_and_final_state_anchors_are_required_to_match():
    journal = complete_journal()

    with pytest.raises(M039JournalError, match="external anchor"):
        journal.verify_against(
            expected_initial_state_digest=state("F0"),
            expected_head=b"x" * 32,
            expected_final_state_digest=state("F3", 3),
        )
    with pytest.raises(M039JournalError, match="final functional state"):
        journal.verify_against(
            expected_initial_state_digest=state("F0"),
            expected_head=journal.head,
            expected_final_state_digest=b"x" * 32,
        )


def test_a_cycle_event_cannot_be_relabelled_as_cycle_zero():
    journal = complete_journal()
    records = list(journal.records)
    fields = decode(records[2])
    assert isinstance(fields, dict)
    original = LineageEvent.from_mapping(fields)
    forged = replace(original, cycle=0, event_hash=b"")
    forged = replace(forged, event_hash=forged.computed_hash())
    records[2] = encode(forged.persisted_fields())

    with pytest.raises(M039JournalError, match="outside its active cycle"):
        verify_lineage_records(
            records,
            protocol_commitment=PROTOCOL,
            lineage_id=LINEAGE,
            expected_initial_state_digest=state("F0"),
        )
