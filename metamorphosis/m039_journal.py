"""Append-only causal journal for the M039 three-cycle lineage.

M038's event vocabulary is frozen with its first canonical result.  M039 therefore uses a
new schema and domain separators rather than modifying the historical journal in place.
The authority remains canonical bytes, every event is hash chained, functional rollback is
additive, and anchored verification requires values supplied from outside the journal.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
from typing import Mapping, Sequence

from .m038_journal import decode, encode

SCHEMA_VERSION = "m039-lineage-journal/1"
DOMAIN_EVENT = b"m039-lineage-event-v1"
DOMAIN_STATE = b"m039-functional-state-v1"
DOMAIN_JOURNAL_ROOT = b"m039-lineage-journal-root-v1"
GENESIS_HASH = hashlib.sha256(DOMAIN_JOURNAL_ROOT).digest()

EVENT_TYPES = (
    "LineageStarted",
    "CycleEscalationCheckpointCreated",
    "StructuralIncapacityCertified",
    "CandidateProposed",
    "CandidateEvaluated",
    "CandidateRejected",
    "MutationProvisionallyAdopted",
    "MutationAdopted",
    "ToolConstructed",
    "ToolReused",
    "RollbackRequested",
    "RollbackCompleted",
    "CycleCompleted",
    "LineageCompleted",
)


class M039JournalError(ValueError):
    pass


def state_digest(state: Mapping[str, object]) -> bytes:
    return hashlib.sha256(DOMAIN_STATE + encode(dict(state))).digest()


@dataclass(frozen=True)
class LineageEvent:
    sequence: int
    event_type: str
    schema_version: str
    protocol_commitment: str
    lineage_id: str
    cycle: int
    previous_event_hash: bytes
    previous_state_digest: bytes
    immutable_input_digests: tuple[bytes, ...]
    operation_parameters: Mapping[str, object]
    costs: Mapping[str, int]
    result_state_digest: bytes
    event_hash: bytes

    def hashed_fields(self) -> dict[str, object]:
        return {
            "sequence": self.sequence,
            "event_type": self.event_type,
            "schema_version": self.schema_version,
            "protocol_commitment": self.protocol_commitment,
            "lineage_id": self.lineage_id,
            "cycle": self.cycle,
            "previous_event_hash": self.previous_event_hash,
            "previous_state_digest": self.previous_state_digest,
            "immutable_input_digests": list(self.immutable_input_digests),
            "operation_parameters": dict(self.operation_parameters),
            "costs": dict(self.costs),
            "result_state_digest": self.result_state_digest,
        }

    def persisted_fields(self) -> dict[str, object]:
        return {**self.hashed_fields(), "event_hash": self.event_hash}

    @classmethod
    def from_mapping(cls, fields: Mapping[str, object]) -> "LineageEvent":
        required = set(cls.__dataclass_fields__)
        if set(fields) != required:
            raise M039JournalError("event fields do not match the closed M039 schema")
        return cls(
            sequence=int(fields["sequence"]),
            event_type=str(fields["event_type"]),
            schema_version=str(fields["schema_version"]),
            protocol_commitment=str(fields["protocol_commitment"]),
            lineage_id=str(fields["lineage_id"]),
            cycle=int(fields["cycle"]),
            previous_event_hash=bytes(fields["previous_event_hash"]),
            previous_state_digest=bytes(fields["previous_state_digest"]),
            immutable_input_digests=tuple(fields["immutable_input_digests"]),
            operation_parameters=dict(fields["operation_parameters"]),
            costs={str(key): int(value) for key, value in dict(fields["costs"]).items()},
            result_state_digest=bytes(fields["result_state_digest"]),
            event_hash=bytes(fields["event_hash"]),
        )

    def computed_hash(self) -> bytes:
        return hashlib.sha256(DOMAIN_EVENT + encode(self.hashed_fields())).digest()


class LineageJournal:
    """One byte-authoritative chain spanning all three M039 cycles."""

    def __init__(
        self,
        *,
        protocol_commitment: str,
        lineage_id: str,
        initial_state_digest: bytes,
    ) -> None:
        if not protocol_commitment:
            raise ValueError("protocol commitment must be non-empty")
        if len(initial_state_digest) != 32:
            raise ValueError("initial state digest must be 32 bytes")
        self._protocol_commitment = protocol_commitment
        self._lineage_id = lineage_id
        self._initial_state_digest = initial_state_digest
        self._state_digest = initial_state_digest
        self._head = GENESIS_HASH
        self._records: list[bytes] = []
        self._open_cycle: int | None = None
        self._completed_cycles = 0
        self._completed = False
        self._persisted_bytes = 0
        self._hash_operations = 0
        self._serializations = 0

    @property
    def records(self) -> tuple[bytes, ...]:
        return tuple(self._records)

    @property
    def events(self) -> tuple[LineageEvent, ...]:
        events: list[LineageEvent] = []
        for raw in self._records:
            decoded = decode(raw)
            if not isinstance(decoded, Mapping):
                raise M039JournalError("persisted event is not a mapping")
            events.append(LineageEvent.from_mapping(decoded))
        return tuple(events)

    @property
    def head(self) -> bytes:
        return self._head

    @property
    def state_digest(self) -> bytes:
        return self._state_digest

    @property
    def initial_state_digest(self) -> bytes:
        return self._initial_state_digest

    @property
    def completed_cycles(self) -> int:
        return self._completed_cycles

    def counters(self) -> dict[str, int]:
        return {
            "events": len(self._records),
            "persisted_bytes": self._persisted_bytes,
            "hash_operations": self._hash_operations,
            "persisted_event_serializations": self._serializations,
        }

    def start(self, *, immutable_input_digests: Sequence[bytes] = ()) -> LineageEvent:
        if self._records:
            raise M039JournalError("the lineage has already started")
        return self._append(
            "LineageStarted",
            cycle=0,
            result_state_digest=self._initial_state_digest,
            immutable_input_digests=immutable_input_digests,
            operation_parameters={},
            costs={},
        )

    def open_cycle(
        self,
        cycle: int,
        *,
        result_state_digest: bytes,
        operation_parameters: Mapping[str, object],
        immutable_input_digests: Sequence[bytes],
        costs: Mapping[str, int] | None = None,
    ) -> LineageEvent:
        self._require_started()
        if self._completed:
            raise M039JournalError("a completed lineage cannot open another cycle")
        if self._open_cycle is not None:
            raise M039JournalError("the previous cycle is still open")
        expected = self._completed_cycles + 1
        if cycle != expected or cycle not in (1, 2, 3):
            raise M039JournalError(f"expected cycle {expected}, received {cycle}")
        self._open_cycle = cycle
        return self._append(
            "CycleEscalationCheckpointCreated",
            cycle=cycle,
            result_state_digest=result_state_digest,
            immutable_input_digests=immutable_input_digests,
            operation_parameters=operation_parameters,
            costs=costs or {},
        )

    def append(
        self,
        event_type: str,
        *,
        result_state_digest: bytes,
        operation_parameters: Mapping[str, object] | None = None,
        immutable_input_digests: Sequence[bytes] = (),
        costs: Mapping[str, int] | None = None,
    ) -> LineageEvent:
        self._require_started()
        if self._open_cycle is None:
            raise M039JournalError("cycle event appended while no cycle is open")
        if event_type in {
            "LineageStarted",
            "CycleEscalationCheckpointCreated",
            "CycleCompleted",
            "LineageCompleted",
        }:
            raise M039JournalError(f"{event_type} has a dedicated method")
        return self._append(
            event_type,
            cycle=self._open_cycle,
            result_state_digest=result_state_digest,
            immutable_input_digests=immutable_input_digests,
            operation_parameters=operation_parameters or {},
            costs=costs or {},
        )

    def rollback(
        self,
        *,
        target_state_digest: bytes,
        reason: str,
        costs: Mapping[str, int] | None = None,
    ) -> tuple[LineageEvent, LineageEvent]:
        requested = self.append(
            "RollbackRequested",
            result_state_digest=self._state_digest,
            operation_parameters={"reason": reason, "target": target_state_digest},
        )
        completed = self.append(
            "RollbackCompleted",
            result_state_digest=target_state_digest,
            operation_parameters={"reason": reason},
            costs=costs or {},
        )
        return requested, completed

    def complete_cycle(
        self,
        *,
        result_state_digest: bytes,
        operation_parameters: Mapping[str, object],
        costs: Mapping[str, int] | None = None,
    ) -> LineageEvent:
        if self._open_cycle is None:
            raise M039JournalError("no cycle is open")
        cycle = self._open_cycle
        event = self._append(
            "CycleCompleted",
            cycle=cycle,
            result_state_digest=result_state_digest,
            immutable_input_digests=(),
            operation_parameters=operation_parameters,
            costs=costs or {},
        )
        self._open_cycle = None
        self._completed_cycles += 1
        return event

    def complete_lineage(
        self,
        *,
        result_state_digest: bytes,
        operation_parameters: Mapping[str, object],
        immutable_input_digests: Sequence[bytes] = (),
    ) -> LineageEvent:
        if self._open_cycle is not None:
            raise M039JournalError("cannot complete a lineage while a cycle is open")
        if self._completed_cycles != 3:
            raise M039JournalError("M039 completes only after exactly three cycles")
        if self._completed:
            raise M039JournalError("the lineage is already complete")
        event = self._append(
            "LineageCompleted",
            cycle=0,
            result_state_digest=result_state_digest,
            immutable_input_digests=immutable_input_digests,
            operation_parameters=operation_parameters,
            costs={},
        )
        self._completed = True
        return event

    def verify_internal_consistency(self) -> None:
        verify_lineage_records(
            self.records,
            protocol_commitment=self._protocol_commitment,
            lineage_id=self._lineage_id,
            expected_initial_state_digest=self._initial_state_digest,
        )
        if self._records and self.events[-1].event_hash != self._head:
            raise M039JournalError("stored head does not match the final event")

    def verify_against(
        self,
        *,
        expected_initial_state_digest: bytes,
        expected_head: bytes,
        expected_final_state_digest: bytes,
    ) -> None:
        verify_lineage_records(
            self.records,
            protocol_commitment=self._protocol_commitment,
            lineage_id=self._lineage_id,
            expected_initial_state_digest=expected_initial_state_digest,
            expected_head=expected_head,
            expected_final_state_digest=expected_final_state_digest,
        )

    def _require_started(self) -> None:
        if not self._records:
            raise M039JournalError("call start() before appending lineage events")

    def _append(
        self,
        event_type: str,
        *,
        cycle: int,
        result_state_digest: bytes,
        immutable_input_digests: Sequence[bytes],
        operation_parameters: Mapping[str, object],
        costs: Mapping[str, int],
    ) -> LineageEvent:
        if event_type not in EVENT_TYPES:
            raise M039JournalError(f"unknown M039 event type {event_type!r}")
        if len(result_state_digest) != 32:
            raise M039JournalError("result state digest must be 32 bytes")
        if any(len(item) != 32 for item in immutable_input_digests):
            raise M039JournalError("immutable input digests must be 32 bytes")
        draft = LineageEvent(
            sequence=len(self._records),
            event_type=event_type,
            schema_version=SCHEMA_VERSION,
            protocol_commitment=self._protocol_commitment,
            lineage_id=self._lineage_id,
            cycle=cycle,
            previous_event_hash=self._head,
            previous_state_digest=self._state_digest,
            immutable_input_digests=tuple(immutable_input_digests),
            operation_parameters=dict(operation_parameters),
            costs={str(key): int(value) for key, value in costs.items()},
            result_state_digest=result_state_digest,
            event_hash=b"",
        )
        event_hash = hashlib.sha256(DOMAIN_EVENT + encode(draft.hashed_fields())).digest()
        self._hash_operations += 1
        stored = replace(draft, event_hash=event_hash)
        raw = encode(stored.persisted_fields())
        self._serializations += 1
        self._persisted_bytes += len(raw)
        self._records.append(raw)
        self._head = event_hash
        self._state_digest = result_state_digest
        return stored


def verify_lineage_records(
    records: Sequence[bytes],
    *,
    protocol_commitment: str,
    lineage_id: str,
    expected_initial_state_digest: bytes,
    expected_head: bytes | None = None,
    expected_final_state_digest: bytes | None = None,
) -> None:
    if not records:
        raise M039JournalError("lineage journal is empty")
    previous_head = GENESIS_HASH
    previous_state = expected_initial_state_digest
    open_cycle: int | None = None
    completed_cycles = 0
    completed = False

    for position, raw in enumerate(records):
        decoded = decode(raw)
        if not isinstance(decoded, Mapping):
            raise M039JournalError("persisted event is not a mapping")
        event = LineageEvent.from_mapping(decoded)
        if event.sequence != position:
            raise M039JournalError("event sequence is not contiguous")
        if event.schema_version != SCHEMA_VERSION:
            raise M039JournalError("unknown M039 journal schema")
        if event.protocol_commitment != protocol_commitment:
            raise M039JournalError("event protocol commitment diverged")
        if event.lineage_id != lineage_id:
            raise M039JournalError("event lineage identity diverged")
        if event.previous_event_hash != previous_head:
            raise M039JournalError("event hash chain is broken")
        if event.previous_state_digest != previous_state:
            raise M039JournalError("functional state continuity is broken")
        if event.computed_hash() != event.event_hash:
            raise M039JournalError("event bytes were altered")

        if position == 0:
            if event.event_type != "LineageStarted" or event.cycle != 0:
                raise M039JournalError("first event must be LineageStarted at cycle 0")
        elif event.event_type == "LineageStarted":
            raise M039JournalError("LineageStarted may occur only once")

        if event.event_type == "LineageStarted":
            # The root sentinel belongs to the lineage as a whole, not to cycle zero.
            pass
        elif event.event_type == "CycleEscalationCheckpointCreated":
            if open_cycle is not None:
                raise M039JournalError("a new cycle opened before the previous completed")
            expected_cycle = completed_cycles + 1
            if event.cycle != expected_cycle or event.cycle not in (1, 2, 3):
                raise M039JournalError("cycle checkpoints are not ordered 1, 2, 3")
            open_cycle = event.cycle
        elif event.event_type == "CycleCompleted":
            if open_cycle is None or event.cycle != open_cycle:
                raise M039JournalError("CycleCompleted does not close the active cycle")
            completed_cycles += 1
            open_cycle = None
        elif event.event_type == "LineageCompleted":
            if open_cycle is not None or completed_cycles != 3 or event.cycle != 0:
                raise M039JournalError("LineageCompleted requires three closed cycles")
            if position != len(records) - 1:
                raise M039JournalError("LineageCompleted must be the final event")
            completed = True
        else:
            # Every remaining event belongs to exactly one currently open cycle.  In
            # particular, cycle zero is not a harmless label: accepting it would allow a
            # causally load-bearing event to escape the cycle whose claim it supports.
            if open_cycle is None or event.cycle != open_cycle:
                raise M039JournalError("cycle event is outside its active cycle")

        previous_head = event.event_hash
        previous_state = event.result_state_digest

    if not completed:
        raise M039JournalError("lineage journal lacks its final completion event")
    if expected_head is not None and previous_head != expected_head:
        raise M039JournalError("journal head does not match the external anchor")
    if expected_final_state_digest is not None and previous_state != expected_final_state_digest:
        raise M039JournalError("final functional state does not match the external anchor")
