"""Integrity tests for the M038 causal journal.

These are the obligations listed in `docs/adr/0001-causal-journal.md`. Two of them are
stated realistically rather than aspirationally: no test can prove that no two logically
different structures ever collide, so what is checked is the round trip, the rejection of
malformed input, and the known confusable pairs.
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
    AuditCounters,
    CausalJournal,
    EscalationCheckpoint,
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


def make_journal(**kwargs) -> CausalJournal:
    return CausalJournal(
        protocol_commitment=COMMITMENT,
        initial_state_digest=functional_digest({"body": "F0"}),
        **kwargs,
    )


# --------------------------------------------------------------------------------------
# Canonical serialisation
# --------------------------------------------------------------------------------------

ROUND_TRIP_VALUES = [
    None,
    True,
    False,
    0,
    1,
    -1,
    -2,
    2**64,
    "",
    "a",
    "é—",
    b"",
    b"\x00\xff",
    (),
    (1, "1", None),
    [],
    [[], [[]]],
    {},
    {"a": 1, "b": [1, 2], "c": {"d": None}},
    {"z": True, "a": False},
]


@pytest.mark.parametrize("value", ROUND_TRIP_VALUES)
def test_encoding_round_trips_and_consumes_every_byte(value):
    assert decode(encode(value)) == value


def test_encoding_is_deterministic_regardless_of_mapping_insertion_order():
    assert encode({"a": 1, "b": 2}) == encode({"b": 2, "a": 1})


CONFUSABLE_PAIRS = [
    (1, "1"),
    (1, True),
    (0, False),
    (0, None),
    ("", None),
    ("", b""),
    (False, None),
    ([], ()),
    ([1, 2], (1, 2)),
    ({"a": 1}, [["a", 1]]),
    ("a\x00b", "a"),
    ({"ab": 1}, {"a": "b1"}),
]


@pytest.mark.parametrize("left,right", CONFUSABLE_PAIRS)
def test_known_confusable_pairs_encode_differently(left, right):
    assert encode(left) != encode(right)


def test_a_payload_containing_a_domain_constant_does_not_collide():
    # The failure mode that separator-joined hashing has and this encoding must not.
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
    scrambled = b"".join([
        encode("b"), encode(2), encode("a"), encode(1),
    ])
    payload = (2).to_bytes(8, "big") + scrambled
    encoded = b"M" + len(payload).to_bytes(8, "big") + payload
    with pytest.raises(SerializationError, match="canonical order"):
        decode(encoded)


def test_duplicate_mapping_fields_are_rejected():
    duplicated = b"".join([encode("a"), encode(1), encode("a"), encode(2)])
    payload = (2).to_bytes(8, "big") + duplicated
    encoded = b"M" + len(payload).to_bytes(8, "big") + payload
    with pytest.raises(SerializationError, match="canonical order"):
        decode(encoded)


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


def test_the_first_event_chains_to_the_genesis_hash():
    journal = make_journal()
    event = journal.append("CandidateProposed", result_state_digest=functional_digest({"n": 1}))
    assert event.previous_event_hash == GENESIS_HASH
    journal.verify()


def test_event_hash_excludes_itself():
    journal = make_journal()
    event = journal.append("CandidateProposed", result_state_digest=functional_digest({"n": 1}))
    assert "event_hash" not in event.hashed_fields()
    assert event.computed_hash() == event.event_hash


def test_an_altered_event_is_detected():
    journal = make_journal()
    journal.append("CandidateProposed", result_state_digest=functional_digest({"n": 1}))
    events = list(journal.events)
    events[0] = replace(events[0], operation_parameters={"tampered": True})
    with pytest.raises(JournalIntegrityError, match="altered"):
        verify_chain(
            events,
            protocol_commitment=COMMITMENT,
            expected_schema_version=events[0].schema_version,
        )


def test_a_deleted_event_is_detected():
    journal = make_journal()
    for index in range(3):
        journal.append("CandidateProposed", result_state_digest=functional_digest({"n": index}))
    events = [journal.events[0], journal.events[2]]
    with pytest.raises(JournalIntegrityError, match="sequence"):
        verify_chain(
            events,
            protocol_commitment=COMMITMENT,
            expected_schema_version=events[0].schema_version,
        )


def test_a_deleted_event_is_still_detected_after_renumbering():
    journal = make_journal()
    for index in range(3):
        journal.append("CandidateProposed", result_state_digest=functional_digest({"n": index}))
    kept = journal.events[2]
    events = [journal.events[0], replace(kept, sequence=1)]
    with pytest.raises(JournalIntegrityError, match="altered|chain"):
        verify_chain(
            events,
            protocol_commitment=COMMITMENT,
            expected_schema_version=kept.schema_version,
        )


def test_reordered_events_are_detected():
    journal = make_journal()
    for index in range(2):
        journal.append("CandidateProposed", result_state_digest=functional_digest({"n": index}))
    events = list(reversed(journal.events))
    with pytest.raises(JournalIntegrityError, match="sequence"):
        verify_chain(
            events,
            protocol_commitment=COMMITMENT,
            expected_schema_version=events[0].schema_version,
        )


def test_an_unknown_schema_version_is_a_failure_and_not_a_skip():
    journal = make_journal()
    journal.append("CandidateProposed", result_state_digest=functional_digest({"n": 1}))
    with pytest.raises(JournalIntegrityError, match="schema version"):
        journal.verify(expected_schema_version="m038-journal/999")


def test_an_event_from_another_commitment_is_detected():
    journal = make_journal()
    journal.append("CandidateProposed", result_state_digest=functional_digest({"n": 1}))
    events = [replace(journal.events[0], protocol_commitment="other")]
    with pytest.raises(JournalIntegrityError, match="another commitment"):
        verify_chain(
            events,
            protocol_commitment=COMMITMENT,
            expected_schema_version=events[0].schema_version,
        )


def test_a_break_in_state_continuity_is_detected():
    journal = make_journal()
    journal.append("CandidateProposed", result_state_digest=functional_digest({"n": 1}))
    journal.append("CandidateEvaluated", result_state_digest=functional_digest({"n": 2}))
    events = list(journal.events)
    forged = replace(events[1], previous_state_digest=functional_digest({"n": 99}))
    events[1] = replace(forged, event_hash=forged.computed_hash())
    with pytest.raises(JournalIntegrityError, match="state continuity"):
        verify_chain(
            events,
            protocol_commitment=COMMITMENT,
            expected_schema_version=events[0].schema_version,
        )


def test_a_wholly_rebuilt_chain_verifies_and_this_is_the_limit_of_the_mechanism():
    """What a hash chain does not prove, asserted rather than left implicit.

    Tampering is detected only relative to a head committed elsewhere. Someone who rewrites
    every event and recomputes every hash produces a chain that verifies — with a different
    head. ADR 0001 states this for the rolling commitment; it holds identically for the
    causal journal, and no claim built on this module may assume otherwise.
    """
    honest = make_journal()
    honest.append("CandidateProposed", result_state_digest=functional_digest({"n": 1}))
    honest.append("MutationAdopted", result_state_digest=functional_digest({"n": 2}))

    rebuilt = make_journal()
    rebuilt.append("CandidateProposed", result_state_digest=functional_digest({"n": 1}))
    rebuilt.append("MutationAdopted", result_state_digest=functional_digest({"n": 99}))

    rebuilt.verify()  # internally consistent
    assert rebuilt.head != honest.head  # and distinguishable only by the committed head


def test_an_unknown_event_type_is_refused_at_append():
    journal = make_journal()
    with pytest.raises(JournalIntegrityError, match="unknown event type"):
        journal.append("PopulationReduced", result_state_digest=functional_digest({"n": 1}))


def test_population_reduced_is_not_an_event_type():
    # M038 is a single-organism lineage; it has no population to reduce.
    assert "PopulationReduced" not in EVENT_TYPES
    assert {"RollbackRequested", "RollbackCompleted"} <= set(EVENT_TYPES)


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
    journal.verify()


def test_the_audit_state_continues_across_a_rollback():
    journal = make_journal()
    f1 = functional_digest({"body": "F1"})
    journal.append("MutationAdopted", result_state_digest=f1)
    head_before = journal.head
    counters_before = journal.counters.full_event_serializations

    journal.rollback(target_state_digest=f1, reason="forced")

    assert journal.head != head_before
    assert journal.counters.full_event_serializations > counters_before
    journal.verify()


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
# The rolling commitment
# --------------------------------------------------------------------------------------


def test_the_rolling_commitment_starts_at_genesis_and_advances():
    rolling = RollingCommitment()
    assert rolling.head == GENESIS_HASH
    rolling.record({"op": "walk", "cost": 1})
    assert rolling.head != GENESIS_HASH


def test_the_rolling_commitment_detects_reordering():
    first = RollingCommitment()
    second = RollingCommitment()
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


def test_the_rolling_commitment_does_not_digest_the_body():
    counters = AuditCounters()
    rolling = RollingCommitment(counters=counters)
    rolling.record({"op": "walk", "cost": 1})
    assert counters.hash_operations == 1
    assert counters.compact_event_serializations == 1


# --------------------------------------------------------------------------------------
# The checkpoint
# --------------------------------------------------------------------------------------


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


def test_the_checkpoint_digest_covers_every_field():
    baseline = build_checkpoint().checkpoint_digest()
    assert build_checkpoint(fast_event_count=8).checkpoint_digest() != baseline
    assert build_checkpoint(escalation_reason="other").checkpoint_digest() != baseline
    assert (
        build_checkpoint(incapacity_certificate={"certified_lower_bound": 6, "body_state_count": 4})
        .checkpoint_digest()
        != baseline
    )


def test_the_checkpoint_digest_is_stable():
    assert build_checkpoint().checkpoint_digest() == build_checkpoint().checkpoint_digest()


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
# Journalling changes the evidence, never a decision
# --------------------------------------------------------------------------------------


def test_disabling_detailed_journalling_changes_evidence_and_not_the_functional_state():
    """Arm B against a hypothetical arm C on the same decisions.

    The functional digests are identical; only the audit counters differ. This is the shape
    the B/C comparison requires, and it is asserted here rather than assumed.
    """
    quiet = make_journal(counters=AuditCounters())
    loud = make_journal(counters=AuditCounters())

    for journal, fast_events in ((quiet, 0), (loud, 5)):
        rolling = RollingCommitment(counters=journal.counters)
        for index in range(fast_events):
            rolling.record({"op": "walk", "step": index})
        journal.append("MutationAdopted", result_state_digest=functional_digest({"body": "F1"}))

    assert quiet.state_digest == loud.state_digest
    assert quiet.events[-1].result_state_digest == loud.events[-1].result_state_digest
    assert loud.counters.compact_event_serializations > quiet.counters.compact_event_serializations
    assert loud.counters.audit_deterministic_operations > quiet.counters.audit_deterministic_operations
