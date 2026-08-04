"""Integrity tests for the M038 causal journal.

These are the obligations listed in `docs/adr/0001-causal-journal.md`, including its
external-anchoring section. Two of them are stated realistically rather than aspirationally:
no test can prove that no two logically different structures ever collide, so what is checked
is the round trip, the rejection of malformed input, and the known confusable pairs.
"""

from __future__ import annotations

from dataclasses import replace
import hashlib

import pytest

from metamorphosis.m038_journal import (
    DOMAINS,
    DOMAIN_CAUSAL_EVENT,
    DOMAIN_COMPACT_TRACE,
    EVENT_TYPES,
    GENESIS_HASH,
    OPENING_EVENT,
    AuditCounters,
    CausalJournal,
    EscalationCheckpoint,
    JournalEvent,
    JournalIntegrityError,
    RollingCommitment,
    SerializationError,
    decode,
    digest,
    encode,
    functional_digest,
    project_archive,
    verify_chain,
    verify_projection,
)

COMMITMENT = "m038-development"


def build_checkpoint(**overrides) -> EscalationCheckpoint:
    fields = {
        "schema_version": "m038-journal/1",
        "protocol_commitment": COMMITMENT,
        "fast_trace_head": GENESIS_HASH,
        "fast_event_count": 7,
        "body": ((0, 1), (1, 0)),
        "body_digest": functional_digest({"body": "F0"}),
        "portable_learning_state": {"seen": 3},
        "tool_registry": ["walk", "grow"],
        "deterministic_counters": {"search_nodes": 12},
        "rng_algorithm_and_state": None,
        "admitted_observations": [("a", True)],
        "evidence_digest": functional_digest({"evidence": 1}),
        "incapacity_certificate": {"certified_lower_bound": 5, "body_state_count": 4},
        "escalation_reason": "proved_structural_incapacity",
    }
    fields.update(overrides)
    return EscalationCheckpoint(**fields)


def make_journal(*, counters: AuditCounters | None = None) -> CausalJournal:
    return CausalJournal.open_from_checkpoint(build_checkpoint(), counters=counters)


def verify_args(journal: CausalJournal) -> dict:
    """The arguments an honest caller supplies from its own committed record."""
    return {
        "protocol_commitment": journal.protocol_commitment,
        "expected_schema_version": journal.schema_version,
        "expected_initial_state_digest": journal.initial_state_digest,
        "expected_checkpoint_digest": journal.checkpoint_digest,
    }


# --------------------------------------------------------------------------------------
# Canonical serialisation
# --------------------------------------------------------------------------------------

ROUND_TRIP_VALUES = [
    None, True, False, 0, 1, -1, -2, 2**64,
    "", "a", "é—", b"", b"\x00\xff",
    (), (1, "1", None), [], [[], [[]]], {},
    {"a": 1, "b": [1, 2], "c": {"d": None}},
    {"z": True, "a": False},
]


@pytest.mark.parametrize("value", ROUND_TRIP_VALUES)
def test_encoding_round_trips_and_consumes_every_byte(value):
    assert decode(encode(value)) == value


def test_encoding_is_deterministic_regardless_of_mapping_insertion_order():
    assert encode({"a": 1, "b": 2}) == encode({"b": 2, "a": 1})


CONFUSABLE_PAIRS = [
    (1, "1"), (1, True), (0, False), (0, None), ("", None), ("", b""),
    (False, None), ([], ()), ([1, 2], (1, 2)), ({"a": 1}, [["a", 1]]),
    ("a\x00b", "a"), ({"ab": 1}, {"a": "b1"}),
]


@pytest.mark.parametrize("left,right", CONFUSABLE_PAIRS)
def test_known_confusable_pairs_encode_differently(left, right):
    assert encode(left) != encode(right)


def test_a_payload_containing_a_domain_constant_does_not_collide():
    assert digest(DOMAIN_CAUSAL_EVENT, {"a": DOMAIN_COMPACT_TRACE.decode()}) != digest(
        DOMAIN_CAUSAL_EVENT, {"a": "", "b": DOMAIN_COMPACT_TRACE.decode()}
    )


def test_length_is_a_fixed_width_field():
    encoded = encode("abc")
    assert encoded[:1] == b"S"
    assert encoded[1:9] == (3).to_bytes(8, "big")
    assert encoded[9:] == b"abc"


def test_trailing_bytes_are_rejected():
    with pytest.raises(SerializationError, match="trailing"):
        decode(encode(1) + b"\x00")


def test_a_truncated_length_field_is_rejected():
    with pytest.raises(SerializationError, match="truncated"):
        decode(encode("abc")[:5])


def test_a_truncated_payload_is_rejected():
    with pytest.raises(SerializationError, match="truncated"):
        decode(encode("abcdef")[:-2])


def test_a_declared_length_shorter_than_the_payload_is_rejected():
    encoded = bytearray(encode("abcdef"))
    encoded[1:9] = (2).to_bytes(8, "big")
    with pytest.raises(SerializationError, match="trailing"):
        decode(bytes(encoded))


def test_non_canonical_integers_are_rejected():
    for payload in (b"01", b"-0", b"+1", b"1 ", b""):
        encoded = b"I" + len(payload).to_bytes(8, "big") + payload
        with pytest.raises(SerializationError, match="non-canonical integer"):
            decode(encoded)


def test_a_boolean_payload_outside_the_two_permitted_bytes_is_rejected():
    with pytest.raises(SerializationError, match="0x00 or 0x01"):
        decode(b"B" + (1).to_bytes(8, "big") + b"\x02")


def test_mapping_fields_out_of_canonical_order_are_rejected():
    scrambled = b"".join([encode("b"), encode(2), encode("a"), encode(1)])
    payload = (2).to_bytes(8, "big") + scrambled
    with pytest.raises(SerializationError, match="canonical order"):
        decode(b"M" + len(payload).to_bytes(8, "big") + payload)


def test_duplicate_mapping_fields_are_rejected():
    duplicated = b"".join([encode("a"), encode(1), encode("a"), encode(2)])
    payload = (2).to_bytes(8, "big") + duplicated
    with pytest.raises(SerializationError, match="canonical order"):
        decode(b"M" + len(payload).to_bytes(8, "big") + payload)


def test_an_unknown_tag_is_rejected():
    with pytest.raises(SerializationError, match="unknown type tag"):
        decode(b"Q" + (0).to_bytes(8, "big"))


def test_unencodable_values_are_refused_rather_than_coerced():
    with pytest.raises(SerializationError, match="no canonical encoding"):
        encode(1.5)
    with pytest.raises(SerializationError, match="no canonical encoding"):
        encode({1, 2})
    with pytest.raises(SerializationError, match="keys must be strings"):
        encode({1: "a"})


# --------------------------------------------------------------------------------------
# Domain separators
# --------------------------------------------------------------------------------------


def test_no_domain_constant_is_a_prefix_of_another():
    for left in DOMAINS:
        for right in DOMAINS:
            if left is not right:
                assert not left.startswith(right)


def test_a_caller_supplied_domain_is_refused():
    with pytest.raises(SerializationError, match="closed set"):
        digest(b"whatever-the-caller-likes", {"a": 1})


def test_genesis_hash_is_a_constant_and_not_a_zero_digest():
    assert GENESIS_HASH == hashlib.sha256(b"m038-causal-journal-genesis-v1").digest()
    assert GENESIS_HASH != bytes(32)


def test_the_same_value_digests_differently_under_different_domains():
    assert digest(DOMAIN_CAUSAL_EVENT, {"a": 1}) != digest(DOMAIN_COMPACT_TRACE, {"a": 1})


# --------------------------------------------------------------------------------------
# The chain
# --------------------------------------------------------------------------------------


def test_the_opening_event_chains_to_the_genesis_hash_and_binds_the_checkpoint():
    checkpoint = build_checkpoint()
    journal = CausalJournal.open_from_checkpoint(checkpoint)
    opening = journal.events[0]
    assert opening.event_type == OPENING_EVENT
    assert opening.previous_event_hash == GENESIS_HASH
    assert checkpoint.checkpoint_digest() in opening.immutable_input_digests
    journal.verify_internal_consistency()


def test_event_hash_excludes_itself():
    journal = make_journal()
    event = journal.append("CandidateProposed", result_state_digest=functional_digest({"n": 1}))
    assert "event_hash" not in event.hashed_fields()
    assert "event_hash" in event.persisted_fields()
    assert event.computed_hash() == event.event_hash


def test_an_altered_event_is_detected():
    journal = make_journal()
    journal.append("CandidateProposed", result_state_digest=functional_digest({"n": 1}))
    events = list(journal.events)
    events[1] = replace(events[1], operation_parameters={"tampered": True})
    with pytest.raises(JournalIntegrityError, match="altered"):
        verify_chain(events, **verify_args(journal))


def test_a_deleted_event_is_detected():
    journal = make_journal()
    for index in range(3):
        journal.append("CandidateProposed", result_state_digest=functional_digest({"n": index}))
    events = [journal.events[0], journal.events[1], journal.events[3]]
    with pytest.raises(JournalIntegrityError, match="sequence"):
        verify_chain(events, **verify_args(journal))


def test_a_deleted_event_is_still_detected_after_renumbering():
    journal = make_journal()
    for index in range(3):
        journal.append("CandidateProposed", result_state_digest=functional_digest({"n": index}))
    events = [journal.events[0], journal.events[1], replace(journal.events[3], sequence=2)]
    with pytest.raises(JournalIntegrityError, match="altered|chain"):
        verify_chain(events, **verify_args(journal))


def test_reordered_events_are_detected():
    journal = make_journal()
    for index in range(2):
        journal.append("CandidateProposed", result_state_digest=functional_digest({"n": index}))
    events = [journal.events[0], journal.events[2], journal.events[1]]
    with pytest.raises(JournalIntegrityError, match="sequence"):
        verify_chain(events, **verify_args(journal))


def test_an_unknown_schema_version_is_a_failure_and_not_a_skip():
    journal = make_journal()
    journal.append("CandidateProposed", result_state_digest=functional_digest({"n": 1}))
    with pytest.raises(JournalIntegrityError, match="schema version"):
        verify_chain(
            journal.events,
            **{**verify_args(journal), "expected_schema_version": "m038-journal/999"},
        )


def test_an_event_from_another_commitment_is_detected():
    journal = make_journal()
    with pytest.raises(JournalIntegrityError, match="another commitment"):
        verify_chain(journal.events, **{**verify_args(journal), "protocol_commitment": "other"})


def test_a_break_in_state_continuity_is_detected():
    journal = make_journal()
    journal.append("CandidateProposed", result_state_digest=functional_digest({"n": 1}))
    journal.append("CandidateEvaluated", result_state_digest=functional_digest({"n": 2}))
    events = list(journal.events)
    forged = replace(events[2], previous_state_digest=functional_digest({"n": 99}))
    events[2] = replace(forged, event_hash=forged.computed_hash())
    with pytest.raises(JournalIntegrityError, match="state continuity"):
        verify_chain(events, **verify_args(journal))


def test_an_unknown_event_type_is_refused_at_append():
    journal = make_journal()
    with pytest.raises(JournalIntegrityError, match="unknown event type"):
        journal.append("PopulationReduced", result_state_digest=functional_digest({"n": 1}))


def test_population_reduced_is_not_an_event_type():
    # M038 is a single-organism lineage; it has no population to reduce.
    assert "PopulationReduced" not in EVENT_TYPES
    assert {"RollbackRequested", "RollbackCompleted"} <= set(EVENT_TYPES)


# --------------------------------------------------------------------------------------
# Anchoring the first state
# --------------------------------------------------------------------------------------


def test_the_initial_digest_never_moves_while_the_current_one_follows():
    journal = make_journal()
    initial = journal.initial_state_digest
    journal.append("MutationAdopted", result_state_digest=functional_digest({"body": "F1"}))
    assert journal.initial_state_digest == initial
    assert journal.state_digest != initial


def test_a_forged_first_state_is_detected_even_with_every_hash_recomputed():
    """The gap that an unanchored `previous_state = None` left open.

    The whole chain is rebuilt so that it is internally perfect; only the state the journal
    claims to have started from is a lie. Without the initial-state anchor, nothing catches
    it.
    """
    journal = make_journal()
    journal.append("MutationAdopted", result_state_digest=functional_digest({"body": "F1"}))

    forged: list[JournalEvent] = []
    previous_hash = GENESIS_HASH
    for event in journal.events:
        candidate = replace(event, previous_event_hash=previous_hash)
        if candidate.sequence == 0:
            candidate = replace(
                candidate,
                previous_state_digest=functional_digest({"body": "not the checkpoint"}),
            )
        candidate = replace(candidate, event_hash=candidate.computed_hash())
        forged.append(candidate)
        previous_hash = candidate.event_hash

    # Internally flawless: every hash recomputed, every link intact.
    for position, event in enumerate(forged):
        assert event.computed_hash() == event.event_hash
        assert event.previous_event_hash == (GENESIS_HASH if position == 0 else forged[position - 1].event_hash)

    with pytest.raises(JournalIntegrityError, match="expected state"):
        verify_chain(forged, **verify_args(journal))


# --------------------------------------------------------------------------------------
# External anchoring
# --------------------------------------------------------------------------------------


def test_internal_consistency_alone_accepts_a_wholly_rebuilt_chain():
    """The limit ADR 0001 now states, asserted rather than left implicit."""
    honest = make_journal()
    honest.append("MutationAdopted", result_state_digest=functional_digest({"n": 2}))

    rebuilt = make_journal()
    rebuilt.append("MutationAdopted", result_state_digest=functional_digest({"n": 99}))

    rebuilt.verify_internal_consistency()
    assert rebuilt.head != honest.head


def test_the_external_head_separates_the_rebuilt_chain_from_the_committed_one():
    honest = make_journal()
    honest.append("MutationAdopted", result_state_digest=functional_digest({"n": 2}))
    committed_head = honest.head

    rebuilt = make_journal()
    rebuilt.append("MutationAdopted", result_state_digest=functional_digest({"n": 99}))

    honest.verify_against(
        expected_initial_state_digest=honest.initial_state_digest,
        expected_head=committed_head,
        expected_checkpoint_digest=honest.checkpoint_digest,
    )
    with pytest.raises(JournalIntegrityError, match="externally committed head"):
        rebuilt.verify_against(
            expected_initial_state_digest=rebuilt.initial_state_digest,
            expected_head=committed_head,
            expected_checkpoint_digest=rebuilt.checkpoint_digest,
        )


def test_verify_against_requires_every_expected_value_and_defaults_to_none_of_them():
    """An anchor read back from the thing it anchors would prove nothing."""
    journal = make_journal()
    parameters = CausalJournal.verify_against.__kwdefaults__ or {}
    for name in ("expected_initial_state_digest", "expected_head", "expected_checkpoint_digest"):
        assert name not in parameters, f"{name} must not have a default"

    with pytest.raises(TypeError):
        journal.verify_against(expected_initial_state_digest=journal.initial_state_digest)


def test_an_empty_journal_cannot_match_a_non_genesis_head():
    with pytest.raises(JournalIntegrityError, match="empty journal"):
        verify_chain(
            [],
            protocol_commitment=COMMITMENT,
            expected_schema_version="m038-journal/1",
            expected_initial_state_digest=functional_digest({"body": "F0"}),
            expected_head=b"\x01" * 32,
        )


# --------------------------------------------------------------------------------------
# Binding the checkpoint to the start of the journal
# --------------------------------------------------------------------------------------


def test_a_journal_must_open_with_the_checkpoint_event():
    journal = CausalJournal(
        protocol_commitment=COMMITMENT,
        initial_state_digest=build_checkpoint().functional_state_digest(),
        checkpoint_digest=build_checkpoint().checkpoint_digest(),
    )
    with pytest.raises(JournalIntegrityError, match="first event must be"):
        journal.append("CandidateProposed", result_state_digest=functional_digest({"n": 1}))


def test_the_opening_event_may_not_reappear():
    journal = make_journal()
    with pytest.raises(JournalIntegrityError, match="only once"):
        journal.append(OPENING_EVENT, result_state_digest=journal.state_digest)
    with pytest.raises(JournalIntegrityError, match="already open"):
        journal.open_cycle()


def test_a_journal_opening_with_another_event_type_is_refused_by_verification():
    journal = make_journal()
    journal.append("CandidateProposed", result_state_digest=functional_digest({"n": 1}))
    with pytest.raises(JournalIntegrityError, match="must open with"):
        verify_chain(journal.events[1:], **verify_args(journal))


def test_an_opening_event_not_referencing_the_expected_checkpoint_is_refused():
    journal = make_journal()
    other = build_checkpoint(escalation_reason="a different escalation").checkpoint_digest()
    with pytest.raises(JournalIntegrityError, match="expected checkpoint"):
        verify_chain(
            journal.events,
            **{**verify_args(journal), "expected_checkpoint_digest": other},
        )


def test_an_initial_state_differing_from_the_checkpoint_is_refused():
    checkpoint = build_checkpoint()
    journal = CausalJournal.open_from_checkpoint(checkpoint)
    with pytest.raises(JournalIntegrityError, match="functional state held in the checkpoint"):
        verify_chain(
            journal.events,
            protocol_commitment=journal.protocol_commitment,
            expected_schema_version=journal.schema_version,
            expected_initial_state_digest=functional_digest({"body": "somewhere else"}),
            expected_checkpoint=checkpoint,
        )


def test_a_checkpoint_object_and_a_mismatched_digest_are_refused_together():
    journal = make_journal()
    with pytest.raises(JournalIntegrityError, match="not this checkpoint"):
        verify_chain(
            journal.events,
            protocol_commitment=journal.protocol_commitment,
            expected_schema_version=journal.schema_version,
            expected_initial_state_digest=journal.initial_state_digest,
            expected_checkpoint_digest=b"\x02" * 32,
            expected_checkpoint=build_checkpoint(),
        )


def test_the_checkpoint_digest_covers_every_field():
    baseline = build_checkpoint().checkpoint_digest()
    assert build_checkpoint(fast_event_count=8).checkpoint_digest() != baseline
    assert build_checkpoint(escalation_reason="other").checkpoint_digest() != baseline
    assert (
        build_checkpoint(incapacity_certificate={"certified_lower_bound": 6, "body_state_count": 4})
        .checkpoint_digest()
        != baseline
    )


def test_the_checkpoint_functional_digest_covers_only_the_functional_half():
    baseline = build_checkpoint().functional_state_digest()
    assert build_checkpoint(body=((1, 1), (0, 0))).functional_state_digest() != baseline
    # Audit-side fields do not move the functional state.
    assert build_checkpoint(fast_event_count=99).functional_state_digest() == baseline
    assert build_checkpoint(evidence_digest=b"\x03" * 32).functional_state_digest() == baseline


# --------------------------------------------------------------------------------------
# Rollback: functional state restored, audit state continuing
# --------------------------------------------------------------------------------------


def test_rollback_restores_the_functional_state_without_erasing_anything():
    journal = make_journal()
    f1 = functional_digest({"body": "F1"})
    journal.append("MutationAdopted", result_state_digest=f1)
    journal.append("MutationProvisionallyAdopted", result_state_digest=functional_digest({"body": "bad"}))

    before = len(journal.events)
    journal.rollback(target_state_digest=f1, reason="forced failing attempt")

    assert journal.state_digest == f1
    assert len(journal.events) == before + 2
    assert [event.event_type for event in journal.events[-2:]] == [
        "RollbackRequested",
        "RollbackCompleted",
    ]
    journal.verify_internal_consistency()


def test_the_audit_state_continues_across_a_rollback():
    journal = make_journal()
    f1 = functional_digest({"body": "F1"})
    journal.append("MutationAdopted", result_state_digest=f1)
    head_before = journal.head
    persisted_before = journal.counters.persisted_event_serializations

    journal.rollback(target_state_digest=f1, reason="forced")

    assert journal.head != head_before
    assert journal.counters.persisted_event_serializations > persisted_before
    journal.verify_internal_consistency()


def test_rollback_to_f1_is_not_a_rollback_to_the_founder():
    journal = make_journal()
    f0 = journal.state_digest
    f1 = functional_digest({"body": "F1"})
    journal.append("MutationAdopted", result_state_digest=f1)
    journal.append("MutationProvisionallyAdopted", result_state_digest=functional_digest({"body": "bad"}))
    journal.rollback(target_state_digest=f1, reason="forced")

    assert journal.state_digest == f1
    assert journal.state_digest != f0


# --------------------------------------------------------------------------------------
# Real immutability
# --------------------------------------------------------------------------------------


def test_mutating_a_read_event_cannot_reach_the_record():
    journal = make_journal()
    journal.append(
        "CandidateProposed",
        result_state_digest=functional_digest({"n": 1}),
        operation_parameters={"candidate": "c0"},
        costs={"units": 3},
    )
    read = journal.events[1]
    read.operation_parameters["candidate"] = "tampered"
    read.costs["units"] = 999

    assert journal.events[1].operation_parameters == {"candidate": "c0"}
    assert journal.events[1].costs == {"units": 3}
    journal.verify_internal_consistency()


def test_the_authority_is_the_stored_bytes():
    journal = make_journal()
    journal.append("CandidateProposed", result_state_digest=functional_digest({"n": 1}))
    assert len(journal.records) == len(journal.events)
    for record, event in zip(journal.records, journal.events):
        assert decode(record) == event.persisted_fields()


def test_each_read_returns_an_independent_copy():
    journal = make_journal()
    assert journal.events[0] is not journal.events[0]
    assert journal.events[0] == journal.events[0]


# --------------------------------------------------------------------------------------
# The rolling commitment
# --------------------------------------------------------------------------------------


def test_the_rolling_commitment_starts_at_genesis_and_advances():
    rolling = RollingCommitment()
    assert rolling.head == GENESIS_HASH
    rolling.record({"op": "walk", "cost": 1})
    assert rolling.head != GENESIS_HASH


def test_the_rolling_commitment_detects_reordering():
    first, second = RollingCommitment(), RollingCommitment()
    for event in ({"op": "a"}, {"op": "b"}):
        first.record(event)
    for event in ({"op": "b"}, {"op": "a"}):
        second.record(event)
    assert first.head != second.head


def test_batching_folds_only_at_the_boundary_and_flush_is_idempotent():
    rolling = RollingCommitment(batch_size=3)
    rolling.record({"op": "a"})
    rolling.record({"op": "b"})
    assert rolling.head == GENESIS_HASH
    assert rolling.pending == 2
    rolling.record({"op": "c"})
    folded = rolling.head
    assert folded != GENESIS_HASH
    assert rolling.flush() == folded


# --------------------------------------------------------------------------------------
# Counters: each increment matches an operation actually performed
# --------------------------------------------------------------------------------------


def test_recording_a_compact_event_is_not_a_batch_serialisation():
    counters = AuditCounters()
    rolling = RollingCommitment(batch_size=4, counters=counters)
    for index in range(3):
        rolling.record({"op": "walk", "step": index})

    assert counters.compact_events_recorded == 3
    assert counters.compact_batches_serialized == 0  # nothing encoded yet
    assert counters.hash_operations == 0

    rolling.flush()
    assert counters.compact_batches_serialized == 1
    assert counters.hash_operations == 1
    assert counters.compact_trace_bytes > 0


def test_an_appended_event_counts_one_hashed_payload_and_one_persisted_record():
    counters = AuditCounters()
    journal = make_journal(counters=counters)
    hashed_before = counters.hashed_event_payload_serializations
    persisted_before = counters.persisted_event_serializations
    bytes_before = counters.journal_bytes_persisted

    event = journal.append("CandidateProposed", result_state_digest=functional_digest({"n": 1}))

    assert counters.hashed_event_payload_serializations == hashed_before + 1
    assert counters.persisted_event_serializations == persisted_before + 1
    # journal_bytes_persisted counts the persisted event, which is strictly larger than the
    # payload that was hashed, because it carries the hash as well.
    persisted = counters.journal_bytes_persisted - bytes_before
    assert persisted == len(encode(event.persisted_fields()))
    assert persisted > len(encode(event.hashed_fields()))


def test_audit_deterministic_operations_is_the_sum_of_its_named_parts():
    counters = AuditCounters()
    journal = make_journal(counters=counters)
    journal.append("CandidateProposed", result_state_digest=functional_digest({"n": 1}))
    project_archive(journal.events, counters=counters)

    assert counters.audit_deterministic_operations == sum(
        getattr(counters, name) for name in AuditCounters.COUNTED_OPERATIONS
    )
    # Byte totals and peaks are magnitudes, not operations, and stay out of the sum.
    assert counters.journal_bytes_persisted > 0
    assert counters.audit_deterministic_operations < counters.journal_bytes_persisted
    assert "journal_bytes_persisted" not in AuditCounters.COUNTED_OPERATIONS
    assert "peak_persistent_audit_artifacts" not in AuditCounters.COUNTED_OPERATIONS


def test_the_protocol_dimensions_all_exist_in_the_counter_schema():
    """The schema may not change in the middle of the experiment."""
    counters = AuditCounters().as_mapping()
    for name in (
        "body_serializations",
        "full_checkpoint_serializations",
        "peak_persistent_audit_artifacts",
        "journal_bytes_persisted",
        "audit_deterministic_operations",
    ):
        assert name in counters


def test_peak_persistent_artifacts_tracks_the_maximum():
    counters = AuditCounters()
    journal = make_journal(counters=counters)
    for index in range(4):
        journal.append("CandidateProposed", result_state_digest=functional_digest({"n": index}))
    assert counters.peak_persistent_audit_artifacts == len(journal.events)


def test_building_a_checkpoint_digest_counts_a_checkpoint_serialisation():
    counters = AuditCounters()
    build_checkpoint().checkpoint_digest(counters=counters)
    assert counters.full_checkpoint_serializations == 1
    assert counters.body_serializations == 1


# --------------------------------------------------------------------------------------
# The projected archive
# --------------------------------------------------------------------------------------


def populated_journal() -> CausalJournal:
    journal = make_journal()
    f1 = functional_digest({"body": "F1"})
    journal.append("StructuralIncapacityCertified", result_state_digest=journal.state_digest)
    journal.append("CandidateProposed", result_state_digest=journal.state_digest)
    journal.append("CandidateRejected", result_state_digest=journal.state_digest,
                   operation_parameters={"candidate": "c0"})
    journal.append("ToolConstructed", result_state_digest=journal.state_digest,
                   operation_parameters={"tool_id": "compose-1"})
    journal.append("MutationAdopted", result_state_digest=f1,
                   operation_parameters={"candidate": "c1"})
    journal.append("MutationProvisionallyAdopted",
                   result_state_digest=functional_digest({"body": "bad"}))
    journal.rollback(target_state_digest=f1, reason="forced")
    journal.append("CycleCompleted", result_state_digest=f1)
    return journal


def test_the_archive_reconstructed_from_the_journal_matches_the_persisted_digest():
    journal = populated_journal()
    persisted = project_archive(journal.events).archive_digest()
    archive = verify_projection(journal.events, persisted)
    assert len(archive.adopted) == 1
    assert len(archive.rejected) == 1
    assert len(archive.rollbacks) == 1
    assert len(archive.tools_constructed) == 1


def test_an_archive_modified_without_a_corresponding_event_is_detected():
    journal = populated_journal()
    archive = project_archive(journal.events)
    forged = replace(archive, adopted=archive.adopted + ({"sequence": 99},))
    with pytest.raises(JournalIntegrityError, match="diverges"):
        verify_projection(journal.events, forged.archive_digest())


def test_the_projection_is_a_function_of_the_journal_alone():
    first = project_archive(populated_journal().events).archive_digest()
    second = project_archive(populated_journal().events).archive_digest()
    assert first == second


# --------------------------------------------------------------------------------------
# The B/C comparison, on identical decisions and identical compact traces
# --------------------------------------------------------------------------------------


def run_arm(*, journal_the_fast_path: bool) -> tuple[CausalJournal, RollingCommitment, AuditCounters]:
    """One arm of the comparison.

    Arm C is an instrumental superset of arm B: it produces every compact event and every
    rolling commitment B produces, and then adds a full causal event with the required state
    digests for each fast-path operation. An earlier version of this test gave B zero
    fast-path events, which measured a difference in instrumentation rather than the cost of
    proof.
    """
    counters = AuditCounters()
    journal = make_journal(counters=counters)
    rolling = RollingCommitment(counters=counters)

    for index in range(5):
        compact = {"op": "walk", "step": index}
        rolling.record(compact)
        if journal_the_fast_path:
            journal.append(
                "CandidateEvaluated",
                result_state_digest=journal.state_digest,
                operation_parameters=compact,
            )

    journal.append("MutationAdopted", result_state_digest=functional_digest({"body": "F1"}))
    return journal, rolling, counters


def test_arm_c_is_an_instrumental_superset_of_arm_b():
    b_journal, b_rolling, b_counters = run_arm(journal_the_fast_path=False)
    c_journal, c_rolling, c_counters = run_arm(journal_the_fast_path=True)

    # Identical functional transcript.
    assert b_journal.state_digest == c_journal.state_digest
    assert b_journal.initial_state_digest == c_journal.initial_state_digest

    # Identical compact trace: C reproduces B's instrumentation rather than replacing it.
    assert b_rolling.head == c_rolling.head
    assert b_counters.compact_events_recorded == c_counters.compact_events_recorded
    assert b_counters.compact_batches_serialized == c_counters.compact_batches_serialized

    # Strictly more evidence in C, on the proof-cost dimensions only.
    assert c_counters.persisted_event_serializations > b_counters.persisted_event_serializations
    assert c_counters.journal_bytes_persisted > b_counters.journal_bytes_persisted
    assert c_counters.audit_deterministic_operations > b_counters.audit_deterministic_operations
    assert c_counters.peak_persistent_audit_artifacts > b_counters.peak_persistent_audit_artifacts

    b_types = [event.event_type for event in b_journal.events]
    c_types = [event.event_type for event in c_journal.events]
    assert set(b_types) <= set(c_types)


def test_both_arms_reach_the_same_final_adoption():
    b_journal, _, _ = run_arm(journal_the_fast_path=False)
    c_journal, _, _ = run_arm(journal_the_fast_path=True)
    assert b_journal.events[-1].event_type == c_journal.events[-1].event_type == "MutationAdopted"
    assert b_journal.events[-1].result_state_digest == c_journal.events[-1].result_state_digest
