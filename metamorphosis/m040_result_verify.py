"""Independent verifier for persisted M040 result artefacts.

The operational engine is not trusted to validate its own summary.  This module consumes only
one persisted result mapping plus an optional external file digest and cross-checks the
scientific verdict, all six arms, both audit layers and the append-only M040 journal.
"""

from __future__ import annotations

import hashlib
import re
from typing import Mapping, Sequence

from .m038_journal import decode, encode
from .m040_engine import EVENT_DOMAIN, EVENT_GENESIS, EVENT_TYPES

_SHA256 = re.compile(r"\A[0-9a-f]{64}\Z")
_EXPECTED_EVENT_SEQUENCE = (
    "PreMigrationLineageCompleted",
    "SubstrateDiscovered",
    "ParentMigrated",
    "PacketCommitted",
    "PacketRehydrated",
    "PostMigrationTaskRevealed",
    "StructuralIncapacityCertified",
    "ControlNativeSynthesised",
    "ControlEvaluated",
    "ControlEvaluated",
    "ControlEvaluated",
    "ControlEvaluated",
    "ControlEvaluated",
    "ControlEvaluated",
    "SearchAuditCommitted",
    "CandidateAdopted",
    "NativeBodySynthesised",
    "RollbackRequested",
    "RollbackCompleted",
    "LineageCompleted",
)
_REQUIRED_ARMS = (
    "complete_migrated_lineage",
    "fresh_on_b",
    "learned_tool_ablated",
    "learning_state_ablated",
    "output_only",
    "unchanged_parent_migrated",
)


class M040ResultVerificationError(ValueError):
    """A persisted M040 result does not support the claimed bounded verdict."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise M040ResultVerificationError(message)


def _sha(value: object, name: str) -> str:
    text = str(value)
    _require(bool(_SHA256.match(text)), f"{name} is not canonical SHA-256 hexadecimal")
    return text


def _mapping(value: object, name: str) -> Mapping[str, object]:
    _require(isinstance(value, Mapping), f"{name} must be a mapping")
    return value  # type: ignore[return-value]


def _sequence(value: object, name: str) -> Sequence[object]:
    _require(
        isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)),
        f"{name} must be a sequence",
    )
    return value  # type: ignore[return-value]


def _decode_and_verify_journal(payload: Mapping[str, object]) -> tuple[Mapping[str, object], ...]:
    records_hex = _sequence(payload.get("journal_records"), "journal records")
    expected_count = int(payload["journal_record_count"])
    _require(len(records_hex) == expected_count, "journal record count differs from persisted records")
    records: list[bytes] = []
    for index, value in enumerate(records_hex):
        text = str(value)
        try:
            records.append(bytes.fromhex(text))
        except ValueError as error:
            raise M040ResultVerificationError(f"journal record {index} is not hexadecimal") from error
    actual_records_digest = hashlib.sha256(b"".join(records)).hexdigest()
    _require(
        actual_records_digest == _sha(payload["journal_records_sha256"], "journal records digest"),
        "journal-record digest mismatch",
    )
    previous = EVENT_GENESIS
    decoded: list[Mapping[str, object]] = []
    for index, raw in enumerate(records):
        value = decode(raw)
        event = _mapping(value, f"journal event {index}")
        _require(int(event["sequence"]) == index, "journal sequence is discontinuous")
        event_type = str(event["event_type"])
        _require(event_type in EVENT_TYPES, f"unknown M040 event type {event_type!r}")
        _require(bytes(event["previous_hash"]) == previous, "journal previous hash is discontinuous")
        actual_hash = bytes(event["event_hash"])
        base = {
            "sequence": index,
            "event_type": event_type,
            "previous_hash": previous,
            "payload": dict(_mapping(event["payload"], f"journal payload {index}")),
        }
        expected_hash = hashlib.sha256(EVENT_DOMAIN + encode(base)).digest()
        _require(actual_hash == expected_hash, "journal event hash mismatch")
        previous = actual_hash
        decoded.append(event)
    _require(previous.hex() == _sha(payload["journal_head"], "journal head"), "journal head mismatch")
    event_types = tuple(str(event["event_type"]) for event in decoded)
    _require(event_types == _EXPECTED_EVENT_SEQUENCE, "M040 causal event order differs from the protocol")
    return tuple(decoded)


def _verify_audits(payload: Mapping[str, object]) -> None:
    arms = _mapping(payload["arms"], "arms")
    post_audits = _mapping(payload["post_migration_search_audits"], "post-migration audits")
    _require(set(arms) == set(_REQUIRED_ARMS), "M040 arm set differs from the frozen comparison")
    _require(set(post_audits) == set(arms), "post-migration audits do not cover every arm")
    counter_names = (
        "symbolic_search_nodes",
        "primitive_expansion_operations",
        "candidates_constructed",
        "candidates_evaluated",
        "evidence_checks",
        "tool_symbols_used",
    )
    for name in _REQUIRED_ARMS:
        arm = _mapping(arms[name], f"arm {name}")
        audit = _mapping(post_audits[name], f"audit {name}")
        _sha(audit["transcript_digest"], f"audit transcript {name}")
        _require(int(audit["transcript_entries"]) > 0, f"audit {name} has no transcript entries")
        for field in ("exact", "reason", "quality_numerator", "quality_denominator", "accepted_candidate_id"):
            _require(audit[field] == arm[field], f"audit {name} disagrees on {field}")
        _require(
            tuple(str(value) for value in _sequence(audit["accepted_tool_ids"], f"audit tools {name}"))
            == tuple(str(value) for value in _sequence(arm["accepted_tool_ids"], f"arm tools {name}")),
            f"audit {name} disagrees on accepted tools",
        )
        counters = _mapping(arm["counters"], f"arm counters {name}")
        for counter in counter_names:
            _require(int(audit[counter]) == int(counters[counter]), f"audit {name} disagrees on {counter}")

    pre_audits = _sequence(payload["pre_migration_search_audits"], "pre-migration audits")
    _require(len(pre_audits) == 3, "pre-migration lineage must contain exactly three audited cycles")
    for expected_cycle, raw in enumerate(pre_audits, start=1):
        audit = _mapping(raw, f"pre-migration audit {expected_cycle}")
        _require(int(audit["cycle"]) == expected_cycle, "pre-migration audit cycles are discontinuous")
        _sha(audit["transcript_digest"], f"pre-migration transcript {expected_cycle}")
        _require(int(audit["transcript_entries"]) > 0, "pre-migration audit is empty")
        _require(int(audit["evidence_admitted_candidates"]) == 1, "pre-migration cycle must admit one candidate")
        _require(int(audit["exact_evaluations"]) == 1, "pre-migration cycle must have one exact evaluation")
        _require(
            int(audit["completed_candidates"])
            == int(audit["evidence_rejections"]) + int(audit["evidence_admitted_candidates"]),
            "pre-migration completed-candidate accounting is inconsistent",
        )


def _verify_scientific_fields(payload: Mapping[str, object]) -> None:
    for name in (
        "pre_migration_manifest_digest",
        "pre_migration_journal_head",
        "pre_migration_journal_records_digest",
        "packet_sha256",
        "task_digest",
        "journal_head",
        "journal_records_sha256",
    ):
        _sha(payload[name], name)
    _require(str(payload["protocol_commitment"]) != "", "protocol commitment is empty")
    _require(bool(payload["trans_substrate_continuity_supported"]), "continuity verdict is not supported")
    _require(bool(payload["post_migration_plasticity_supported"]), "plasticity verdict is not supported")
    _require(bool(payload["replay_supported"]), "seed-only replay is not supported")
    _require(bool(payload["rollback_restored_exactly"]), "rollback was not exact")
    _require(bool(payload["accepted_tool_was_pre_migration_owned"]), "accepted rewrite used no transported tool")

    migration = _mapping(payload["migration"], "migration")
    _require(bool(migration["exact"]), "parent migration was not exact")
    _require(int(migration["probe_calls"]) <= 120, "migration exceeded the probe budget")
    _require(int(migration["candidate_evaluations"]) <= 75_000, "migration exceeded candidate budget")
    _require(int(migration["native_components"]) <= 320, "migration exceeded native component budget")
    _require(int(migration["serialized_bytes"]) <= 16_777_216, "migration exceeded native byte budget")
    _sha(migration["source_body_digest"], "migrated source body")
    _sha(migration["native_body_sha256"], "migrated native body")

    task = _mapping(payload["task"], "task")
    _require(str(task["task_family"]) == "lineage_anchor", "result did not use the lineage-anchor family")
    _require(int(task["observation_count"]) == 127, "task observation count differs from the protocol")
    _require(int(task["observation_depth"]) == 6, "task observation depth differs from the protocol")
    _require(int(task["target_states"]) > 0, "task target has no states")
    _sha(task["parent_digest"], "task parent")
    _sha(task["target_digest"], "task target")
    _require(task["target_digest"] == payload["task_digest"] or _sha(payload["task_digest"], "task digest"), "")

    certificate = _mapping(payload["certificate"], "structural certificate")
    body_states = int(certificate["body_state_count"])
    lower_bound = int(certificate["certified_lower_bound"])
    _require(lower_bound > body_states, "certificate does not prove structural incapacity")
    _require(int(task["target_states"]) >= lower_bound, "target is smaller than the certified lower bound")

    arms = _mapping(payload["arms"], "arms")
    full = _mapping(arms["complete_migrated_lineage"], "complete arm")
    _require(bool(full["exact"]), "complete migrated lineage did not solve exactly")
    _require((int(full["quality_numerator"]), int(full["quality_denominator"])) == (127, 127), "complete quality is not exact")
    _require(full["accepted_body_digest"] == task["target_digest"], "accepted source body differs from target")
    _require(
        tuple(str(value) for value in _sequence(full["accepted_tool_ids"], "accepted tool IDs"))
        == tuple(str(value) for value in _sequence(task["generating_tool_ids"], "task tool IDs")),
        "accepted tool sequence differs from the hidden task generator",
    )
    full_nodes = int(_mapping(full["counters"], "complete counters")["symbolic_search_nodes"])
    _require(0 < full_nodes <= 4_096, "complete arm exceeded the equal search budget")

    for name in ("fresh_on_b", "learned_tool_ablated", "learning_state_ablated", "unchanged_parent_migrated"):
        arm = _mapping(arms[name], f"control {name}")
        _require(not bool(arm["exact"]), f"control {name} solved exactly")
        _require(int(arm["quality_numerator"]) < int(arm["quality_denominator"]), f"control {name} has exact quality")
        nodes = int(_mapping(arm["counters"], f"control counters {name}")["symbolic_search_nodes"])
        _require(nodes == 4_097, f"control {name} did not reach the same deterministic budget boundary")
        _require(full_nodes < nodes, f"complete arm is not cheaper than {name}")

    output = _mapping(arms["output_only"], "output-only control")
    _require(not bool(output["exact"]), "output-only control rewrote exactly")
    _require(str(output["reason"]) == "output_only_has_no_portable_rewrite_state", "output-only failure reason changed")
    _require(0 < int(output["quality_numerator"]) < int(output["quality_denominator"]), "output-only quality is not the real migrated behaviour")
    _require(int(_mapping(output["counters"], "output-only counters")["symbolic_search_nodes"]) == 0, "output-only control performed symbolic search")

    accepted_native = _mapping(payload["accepted_native"], "accepted native body")
    _require(accepted_native["source_digest"] == full["accepted_body_digest"], "native source digest differs from accepted body")
    _sha(accepted_native["native_body_sha256"], "accepted native body")
    _require(int(accepted_native["native_components"]) <= 320, "accepted native body exceeds component budget")
    _require(int(accepted_native["serialized_bytes"]) <= 16_777_216, "accepted native body exceeds byte budget")

    baselines = _mapping(payload["control_native_baselines"], "control native baselines")
    _require(set(baselines) == {"complete_parent_migrated", "output_only", "unchanged_parent_migrated"}, "native baseline set changed")
    for name, raw in baselines.items():
        baseline = _mapping(raw, f"native baseline {name}")
        _require(bool(baseline["exact"]), f"native baseline {name} is not exact")
        _sha(baseline["native_body_sha256"], f"native baseline {name}")
    _require(baselines["complete_parent_migrated"]["native_body_sha256"] == baselines["output_only"]["native_body_sha256"], "output-only body differs from migrated parent")


def _verify_event_cross_references(payload: Mapping[str, object], events: Sequence[Mapping[str, object]]) -> None:
    event_payloads = [
        _mapping(event["payload"], f"event payload {index}")
        for index, event in enumerate(events)
    ]
    pre = event_payloads[0]
    _require(pre["manifest_digest"] == payload["pre_migration_manifest_digest"], "pre-migration manifest event mismatch")
    _require(pre["journal_head"] == payload["pre_migration_journal_head"], "pre-migration head event mismatch")
    _require(pre["journal_records_digest"] == payload["pre_migration_journal_records_digest"], "pre-migration records event mismatch")

    migration = _mapping(payload["migration"], "migration")
    migrated = event_payloads[2]
    for field in ("source_body_digest", "native_body_sha256", "candidate_evaluations", "native_components", "serialized_bytes", "exact"):
        _require(migrated[field] == migration[field], f"ParentMigrated event disagrees on {field}")

    _require(event_payloads[3]["packet_sha256"] == payload["packet_sha256"], "PacketCommitted digest mismatch")
    _require(event_payloads[4]["packet_sha256"] == payload["packet_sha256"], "PacketRehydrated digest mismatch")
    task = _mapping(payload["task"], "task")
    _require(event_payloads[5]["task_digest"] == payload["task_digest"], "task-reveal digest mismatch")
    _require(event_payloads[5]["target_digest"] == task["target_digest"], "task-reveal target mismatch")
    _require(int(event_payloads[5]["target_states"]) == int(task["target_states"]), "task-reveal state count mismatch")

    arms = _mapping(payload["arms"], "arms")
    control_events = event_payloads[8:14]
    seen = {str(event["arm"]): event for event in control_events}
    _require(set(seen) == set(arms), "journal control events do not cover every arm")
    for name, arm in arms.items():
        _require(seen[name] == arm, f"journal ControlEvaluated event differs for {name}")

    full = _mapping(arms["complete_migrated_lineage"], "complete arm")
    adopted = event_payloads[15]
    _require(adopted["candidate_id"] == full["accepted_candidate_id"], "CandidateAdopted ID mismatch")
    _require(adopted["source_body_digest"] == full["accepted_body_digest"], "CandidateAdopted body mismatch")
    _require(tuple(adopted["tool_ids"]) == tuple(full["accepted_tool_ids"]), "CandidateAdopted tools mismatch")

    native = _mapping(payload["accepted_native"], "accepted native")
    _require(event_payloads[16] == native, "NativeBodySynthesised event mismatch")
    _require(bool(event_payloads[18]["exact"]), "RollbackCompleted event is not exact")
    completed = event_payloads[19]
    _require(bool(completed["trans_substrate_continuity_supported"]) == bool(payload["trans_substrate_continuity_supported"]), "lineage completion continuity mismatch")
    _require(bool(completed["post_migration_plasticity_supported"]) == bool(payload["post_migration_plasticity_supported"]), "lineage completion plasticity mismatch")


def verify_m040_result(
    payload: Mapping[str, object],
    *,
    raw_bytes: bytes | None = None,
    expected_sha256: str | None = None,
) -> None:
    """Raise when a persisted M040 result does not support its bounded claim."""

    if expected_sha256 is not None:
        _sha(expected_sha256, "expected artefact digest")
        _require(raw_bytes is not None, "raw bytes are required for external artefact verification")
        _require(hashlib.sha256(raw_bytes).hexdigest() == expected_sha256, "external artefact digest mismatch")
    _require(str(payload["schema"]) in {"m040-development-result/2", "m040-canonical-result/1"}, "unsupported M040 result schema")
    _verify_scientific_fields(payload)
    _verify_audits(payload)
    events = _decode_and_verify_journal(payload)
    _verify_event_cross_references(payload, events)
