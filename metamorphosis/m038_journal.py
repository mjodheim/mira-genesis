"""The M038 causal journal: typed serialisation, a hash chain, and a projected archive.

Implements the mechanisms accepted in `docs/adr/0001-causal-journal.md`. Nothing here
measures anything, reads a sealed block, or supports an M038 claim. It is the substrate the
experiment will later run on.

Three ideas carry the whole design, and each exists because the obvious alternative fails.

**Typed, length-prefixed encoding.** Joining fields with a separator is ambiguous whenever a
field contains the separator. Length prefixing removes that, but not type ambiguity: with
lengths alone the integer `1` and the string `"1"` share bytes. So every value carries a tag,
and — the part an earlier draft left open — the length itself has a fixed encoding, an
unsigned 64-bit big-endian integer, or a decoder cannot know where the length ends and the
payload begins.

**Two kinds of state.** An append-only journal and an exact rollback are compatible only if
`functional_state` (restored exactly) is separated from `audit_state` (which continues
across the rollback). Rollback is therefore three appends and no erasure, and a state digest
covers the functional half only — otherwise a digest would have to contain the hash of the
event containing it.

**One source of authority.** The lineage archive is a projection of the journal, never a
second persisted state. Two persisted truths diverge, and the divergence is invisible until
it matters.

A limit worth stating here, because it is easy to overclaim: a hash chain detects tampering
only *relative to a head committed elsewhere*. Someone who rewrites every event and
recomputes every hash obtains a chain that verifies — with a different head. ADR 0001 records
this for the rolling commitment; it holds identically for the causal journal, and
`test_a_wholly_rebuilt_chain_verifies_and_this_is_the_limit_of_the_mechanism` asserts it
rather than leaving it implicit.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import re
from typing import Any, Iterable, Mapping, Sequence

SCHEMA_VERSION = "m038-journal/1"

# Domain separators are a closed set of fixed byte constants. A domain supplied freely by the
# caller is not a separator: two call sites could pass the same value, or one could derive it
# from data being hashed.
DOMAIN_CAUSAL_EVENT = b"m038-causal-event-v1"
DOMAIN_FUNCTIONAL_STATE = b"m038-functional-state-v1"
DOMAIN_CHECKPOINT = b"m038-escalation-checkpoint-v1"
DOMAIN_COMPACT_TRACE = b"m038-compact-trace-v1"
DOMAIN_TOOL = b"m038-tool-v1"
DOMAIN_PROJECTED_ARCHIVE = b"m038-projected-archive-v1"

DOMAINS = frozenset({
    DOMAIN_CAUSAL_EVENT,
    DOMAIN_FUNCTIONAL_STATE,
    DOMAIN_CHECKPOINT,
    DOMAIN_COMPACT_TRACE,
    DOMAIN_TOOL,
    DOMAIN_PROJECTED_ARCHIVE,
})

# A fixed constant rather than a zero digest, so a chain truncated to nothing cannot
# masquerade as a valid root.
GENESIS_HASH = hashlib.sha256(b"m038-causal-journal-genesis-v1").digest()

# Exactly the events the M038 mechanism needs. `PopulationReduced` is absent because M038 is
# a single-organism lineage and has no population to reduce; the rollback pair is present
# because M038 forces a rollback.
EVENT_TYPES = (
    "EscalationCheckpointCreated",
    "StructuralIncapacityCertified",
    "CandidateProposed",
    "CandidateEvaluated",
    "CandidateRejected",
    "MutationProvisionallyAdopted",
    "MutationAdopted",
    "RollbackRequested",
    "RollbackCompleted",
    "ToolConstructed",
    "CycleCompleted",
)

TAG_ABSENT = b"N"
TAG_BOOL = b"B"
TAG_INT = b"I"
TAG_STRING = b"S"
TAG_BYTES = b"Y"
TAG_TUPLE = b"T"
TAG_LIST = b"L"
TAG_MAPPING = b"M"

_LENGTH_BYTES = 8
_CANONICAL_INT = re.compile(rb"^(0|-?[1-9][0-9]*)$")


class SerializationError(ValueError):
    """The bytes are not a canonical encoding, or the value cannot be encoded."""


class JournalIntegrityError(ValueError):
    """The chain, the state continuity, or a projection does not verify."""


# --------------------------------------------------------------------------------------
# Canonical typed serialisation
# --------------------------------------------------------------------------------------


def _length(count: int) -> bytes:
    if count < 0 or count >= 1 << (8 * _LENGTH_BYTES):
        raise SerializationError(f"length {count} does not fit in {_LENGTH_BYTES} bytes")
    return count.to_bytes(_LENGTH_BYTES, "big", signed=False)


def _frame(tag: bytes, payload: bytes) -> bytes:
    return tag + _length(len(payload)) + payload


def encode(value: Any) -> bytes:
    """Encode a value as `type_tag ‖ length ‖ payload`, canonically.

    The tag is one ASCII byte, the length an unsigned 64-bit big-endian integer, and the
    payload exactly that many bytes. Element counts use the same integer encoding.
    """
    if value is None:
        return _frame(TAG_ABSENT, b"")
    # bool before int: `isinstance(True, int)` is true, and conflating them would make
    # `True` and `1` share an encoding.
    if isinstance(value, bool):
        return _frame(TAG_BOOL, b"\x01" if value else b"\x00")
    if isinstance(value, int):
        return _frame(TAG_INT, str(value).encode("ascii"))
    if isinstance(value, str):
        return _frame(TAG_STRING, value.encode("utf-8"))
    if isinstance(value, (bytes, bytearray)):
        return _frame(TAG_BYTES, bytes(value))
    if isinstance(value, tuple):
        return _frame(TAG_TUPLE, _length(len(value)) + b"".join(encode(v) for v in value))
    if isinstance(value, list):
        return _frame(TAG_LIST, _length(len(value)) + b"".join(encode(v) for v in value))
    if isinstance(value, Mapping):
        names = list(value)
        if any(not isinstance(name, str) for name in names):
            raise SerializationError("mapping keys must be strings")
        encoded = sorted(name.encode("utf-8") for name in names)
        if len(set(encoded)) != len(encoded):
            raise SerializationError("mapping keys collide once encoded")
        body = _length(len(encoded))
        for name in encoded:
            body += _frame(TAG_STRING, name) + encode(value[name.decode("utf-8")])
        return _frame(TAG_MAPPING, body)
    raise SerializationError(f"no canonical encoding for {type(value).__name__}")


def _take(data: bytes, offset: int, count: int) -> tuple[bytes, int]:
    end = offset + count
    if end > len(data):
        raise SerializationError("truncated: declared length exceeds the available bytes")
    return data[offset:end], end


def _decode_at(data: bytes, offset: int) -> tuple[Any, int]:
    tag, offset = _take(data, offset, 1)
    raw_length, offset = _take(data, offset, _LENGTH_BYTES)
    size = int.from_bytes(raw_length, "big", signed=False)
    payload, offset = _take(data, offset, size)

    if tag == TAG_ABSENT:
        if payload:
            raise SerializationError("absent must carry no payload")
        return None, offset
    if tag == TAG_BOOL:
        if payload not in (b"\x00", b"\x01"):
            raise SerializationError("boolean payload must be exactly 0x00 or 0x01")
        return payload == b"\x01", offset
    if tag == TAG_INT:
        if not _CANONICAL_INT.match(payload):
            raise SerializationError(f"non-canonical integer {payload!r}")
        return int(payload), offset
    if tag == TAG_STRING:
        try:
            return payload.decode("utf-8"), offset
        except UnicodeDecodeError as error:
            raise SerializationError("string payload is not valid UTF-8") from error
    if tag == TAG_BYTES:
        return payload, offset
    if tag in (TAG_TUPLE, TAG_LIST, TAG_MAPPING):
        return _decode_container(tag, payload), offset
    raise SerializationError(f"unknown type tag {tag!r}")


def _decode_container(tag: bytes, payload: bytes) -> Any:
    if len(payload) < _LENGTH_BYTES:
        raise SerializationError("container payload is too short to hold its element count")
    count = int.from_bytes(payload[:_LENGTH_BYTES], "big", signed=False)
    inner = _LENGTH_BYTES

    if tag in (TAG_TUPLE, TAG_LIST):
        items = []
        for _ in range(count):
            item, inner = _decode_at(payload, inner)
            items.append(item)
        if inner != len(payload):
            raise SerializationError("container declares fewer elements than it contains")
        return tuple(items) if tag == TAG_TUPLE else items

    fields: dict[str, Any] = {}
    previous: bytes | None = None
    for _ in range(count):
        name, inner = _decode_at(payload, inner)
        if not isinstance(name, str):
            raise SerializationError("mapping field names must be strings")
        encoded_name = name.encode("utf-8")
        if previous is not None and encoded_name <= previous:
            raise SerializationError("mapping fields are not in canonical order")
        previous = encoded_name
        fields[name], inner = _decode_at(payload, inner)
    if inner != len(payload):
        raise SerializationError("mapping declares fewer fields than it contains")
    return fields


def decode(data: bytes) -> Any:
    """Decode one canonical value, requiring that it consumes every byte given."""
    value, offset = _decode_at(data, 0)
    if offset != len(data):
        raise SerializationError(f"{len(data) - offset} trailing bytes after the value")
    return value


def digest(domain: bytes, value: Any) -> bytes:
    """SHA-256 over a domain constant and the canonical encoding of a value."""
    if domain not in DOMAINS:
        raise SerializationError("domain separators come from the closed set in this module")
    return hashlib.sha256(domain + encode(value)).digest()


def functional_digest(state: Mapping[str, Any]) -> bytes:
    """Digest of a functional state. It never covers the journal producing it."""
    return digest(DOMAIN_FUNCTIONAL_STATE, state)


# --------------------------------------------------------------------------------------
# Counters
# --------------------------------------------------------------------------------------


@dataclass
class AuditCounters:
    """The audit half of the M038 measurement vector.

    Separated from the functional counters because only the functional half must be
    identical between arms B and C.
    """

    hash_operations: int = 0
    full_event_serializations: int = 0
    compact_event_serializations: int = 0
    journal_bytes: int = 0
    archive_projection_operations: int = 0
    audit_deterministic_operations: int = 0

    def as_mapping(self) -> dict[str, int]:
        return {
            "hash_operations": self.hash_operations,
            "full_event_serializations": self.full_event_serializations,
            "compact_event_serializations": self.compact_event_serializations,
            "journal_bytes": self.journal_bytes,
            "archive_projection_operations": self.archive_projection_operations,
            "audit_deterministic_operations": self.audit_deterministic_operations,
        }


# --------------------------------------------------------------------------------------
# The compact fast-path commitment
# --------------------------------------------------------------------------------------


class RollingCommitment:
    """A rolling hash over compact fast-path events, never over the body.

    It proves that the recorded compact trace has not been altered or reordered after the
    fact. It does not prove that every real event was recorded, nor that the fast path can
    be replayed — see ADR 0001.

    `batch_size` folds N events at a time. It must be fixed before any measurement.
    """

    def __init__(self, *, batch_size: int = 1, counters: AuditCounters | None = None) -> None:
        if batch_size < 1:
            raise ValueError("batch_size must be at least 1")
        self._head = GENESIS_HASH
        self._batch_size = batch_size
        self._pending: list[Any] = []
        self._count = 0
        self.counters = counters if counters is not None else AuditCounters()

    @property
    def head(self) -> bytes:
        return self._head

    @property
    def event_count(self) -> int:
        return self._count

    @property
    def batch_size(self) -> int:
        return self._batch_size

    @property
    def pending(self) -> int:
        return len(self._pending)

    def record(self, compact_event: Mapping[str, Any]) -> None:
        self._pending.append(dict(compact_event))
        self._count += 1
        self.counters.compact_event_serializations += 1
        self.counters.audit_deterministic_operations += 1
        if len(self._pending) >= self._batch_size:
            self.flush()

    def flush(self) -> bytes:
        """Fold any pending events into the head. Idempotent when nothing is pending."""
        if not self._pending:
            return self._head
        payload = encode(self._pending)
        self._head = hashlib.sha256(DOMAIN_COMPACT_TRACE + self._head + payload).digest()
        self.counters.hash_operations += 1
        self.counters.audit_deterministic_operations += 1
        self._pending.clear()
        return self._head


# --------------------------------------------------------------------------------------
# Events and the chain
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class JournalEvent:
    sequence: int
    event_type: str
    schema_version: str
    protocol_commitment: str
    previous_event_hash: bytes
    previous_state_digest: bytes
    immutable_input_digests: tuple[bytes, ...]
    operation_parameters: Mapping[str, Any]
    costs: Mapping[str, Any]
    result_state_digest: bytes
    event_hash: bytes

    def hashed_fields(self) -> dict[str, Any]:
        """Every field except `event_hash`, which cannot contain itself."""
        return {
            "sequence": self.sequence,
            "event_type": self.event_type,
            "schema_version": self.schema_version,
            "protocol_commitment": self.protocol_commitment,
            "previous_event_hash": self.previous_event_hash,
            "previous_state_digest": self.previous_state_digest,
            "immutable_input_digests": list(self.immutable_input_digests),
            "operation_parameters": dict(self.operation_parameters),
            "costs": dict(self.costs),
            "result_state_digest": self.result_state_digest,
        }

    def computed_hash(self) -> bytes:
        return digest(DOMAIN_CAUSAL_EVENT, self.hashed_fields())


class CausalJournal:
    """An append-only, hash-chained journal. The single source of authority.

    Nothing is ever erased or overwritten, including across a rollback: the functional state
    is restored while the audit state continues.
    """

    def __init__(
        self,
        *,
        protocol_commitment: str,
        initial_state_digest: bytes,
        schema_version: str = SCHEMA_VERSION,
        counters: AuditCounters | None = None,
    ) -> None:
        self._protocol_commitment = protocol_commitment
        self._schema_version = schema_version
        self._events: list[JournalEvent] = []
        self._head = GENESIS_HASH
        self._state_digest = initial_state_digest
        self.counters = counters if counters is not None else AuditCounters()

    @property
    def events(self) -> tuple[JournalEvent, ...]:
        return tuple(self._events)

    @property
    def head(self) -> bytes:
        return self._head

    @property
    def state_digest(self) -> bytes:
        return self._state_digest

    @property
    def protocol_commitment(self) -> str:
        return self._protocol_commitment

    def append(
        self,
        event_type: str,
        *,
        result_state_digest: bytes,
        operation_parameters: Mapping[str, Any] | None = None,
        costs: Mapping[str, Any] | None = None,
        immutable_input_digests: Sequence[bytes] = (),
    ) -> JournalEvent:
        if event_type not in EVENT_TYPES:
            raise JournalIntegrityError(f"unknown event type {event_type!r}")

        event = JournalEvent(
            sequence=len(self._events),
            event_type=event_type,
            schema_version=self._schema_version,
            protocol_commitment=self._protocol_commitment,
            previous_event_hash=self._head,
            previous_state_digest=self._state_digest,
            immutable_input_digests=tuple(immutable_input_digests),
            operation_parameters=dict(operation_parameters or {}),
            costs=dict(costs or {}),
            result_state_digest=result_state_digest,
            event_hash=b"",
        )
        payload = encode(event.hashed_fields())
        event_hash = hashlib.sha256(DOMAIN_CAUSAL_EVENT + payload).digest()
        stored = replace(event, event_hash=event_hash)

        self._events.append(stored)
        self._head = event_hash
        self._state_digest = result_state_digest
        self.counters.full_event_serializations += 1
        self.counters.hash_operations += 1
        self.counters.journal_bytes += len(payload)
        self.counters.audit_deterministic_operations += 2
        return stored

    def rollback(
        self,
        *,
        target_state_digest: bytes,
        reason: str,
        costs: Mapping[str, Any] | None = None,
    ) -> tuple[JournalEvent, JournalEvent]:
        """Restore a functional state additively: request, restore, attest.

        The journal and its counters continue across the rollback. "Exact rollback" is a
        claim about the functional state only.
        """
        requested = self.append(
            "RollbackRequested",
            result_state_digest=self._state_digest,
            operation_parameters={"reason": reason, "target": target_state_digest},
        )
        completed = self.append(
            "RollbackCompleted",
            result_state_digest=target_state_digest,
            operation_parameters={"reason": reason},
            costs=costs,
        )
        return requested, completed

    def verify(self, *, expected_schema_version: str | None = None) -> None:
        """Recompute the chain and the state continuity. Raises on any discrepancy."""
        verify_chain(
            self._events,
            protocol_commitment=self._protocol_commitment,
            expected_schema_version=expected_schema_version or self._schema_version,
            counters=self.counters,
        )
        if self._events and self._events[-1].event_hash != self._head:
            raise JournalIntegrityError("head does not match the last event")


def verify_chain(
    events: Sequence[JournalEvent],
    *,
    protocol_commitment: str,
    expected_schema_version: str,
    counters: AuditCounters | None = None,
) -> None:
    """Fail on a missing, altered or reordered event, or an unknown schema version.

    A deletion breaks both the sequence numbering and the hash chain; either alone is
    sufficient, and requiring both makes a silent renumbering detectable too.
    """
    previous_hash = GENESIS_HASH
    previous_state: bytes | None = None

    for position, event in enumerate(events):
        if event.schema_version != expected_schema_version:
            raise JournalIntegrityError(
                f"event {position} carries schema version {event.schema_version!r}, "
                f"expected {expected_schema_version!r}"
            )
        if event.protocol_commitment != protocol_commitment:
            raise JournalIntegrityError(f"event {position} belongs to another commitment")
        if event.sequence != position:
            raise JournalIntegrityError(
                f"event at position {position} declares sequence {event.sequence}"
            )
        if event.event_type not in EVENT_TYPES:
            raise JournalIntegrityError(f"event {position} has type {event.event_type!r}")
        if event.previous_event_hash != previous_hash:
            raise JournalIntegrityError(f"event {position} does not chain to its predecessor")
        if previous_state is not None and event.previous_state_digest != previous_state:
            raise JournalIntegrityError(f"event {position} breaks the state continuity")
        if event.computed_hash() != event.event_hash:
            raise JournalIntegrityError(f"event {position} has been altered")

        if counters is not None:
            counters.hash_operations += 1
            counters.audit_deterministic_operations += 1

        previous_hash = event.event_hash
        previous_state = event.result_state_digest


# --------------------------------------------------------------------------------------
# The escalation checkpoint
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class EscalationCheckpoint:
    """The immutable input of the full causal journal, serialised once at the boundary."""

    schema_version: str
    protocol_commitment: str
    fast_trace_head: bytes
    fast_event_count: int
    body: Any
    body_digest: bytes
    portable_learning_state: Mapping[str, Any]
    tool_registry: Sequence[Any]
    deterministic_counters: Mapping[str, int]
    rng_algorithm_and_state: Any
    admitted_observations: Sequence[Any]
    evidence_digest: bytes
    incapacity_certificate: Mapping[str, Any]
    escalation_reason: str

    def hashed_fields(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "protocol_commitment": self.protocol_commitment,
            "fast_trace_head": self.fast_trace_head,
            "fast_event_count": self.fast_event_count,
            "body": self.body,
            "body_digest": self.body_digest,
            "portable_learning_state": dict(self.portable_learning_state),
            "tool_registry": list(self.tool_registry),
            "deterministic_counters": dict(self.deterministic_counters),
            "rng_algorithm_and_state": self.rng_algorithm_and_state,
            "admitted_observations": list(self.admitted_observations),
            "evidence_digest": self.evidence_digest,
            "incapacity_certificate": dict(self.incapacity_certificate),
            "escalation_reason": self.escalation_reason,
        }

    def checkpoint_digest(self) -> bytes:
        return digest(DOMAIN_CHECKPOINT, self.hashed_fields())


# --------------------------------------------------------------------------------------
# The projected archive
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class ProjectedArchive:
    """A view derived from the journal, never a second persisted state."""

    adopted: tuple[Mapping[str, Any], ...] = ()
    provisionally_adopted: tuple[Mapping[str, Any], ...] = ()
    rejected: tuple[Mapping[str, Any], ...] = ()
    rollbacks: tuple[Mapping[str, Any], ...] = ()
    tools_constructed: tuple[Mapping[str, Any], ...] = ()
    final_state_digest: bytes = b""

    def archive_digest(self) -> bytes:
        return digest(
            DOMAIN_PROJECTED_ARCHIVE,
            {
                "adopted": [dict(item) for item in self.adopted],
                "provisionally_adopted": [dict(item) for item in self.provisionally_adopted],
                "rejected": [dict(item) for item in self.rejected],
                "rollbacks": [dict(item) for item in self.rollbacks],
                "tools_constructed": [dict(item) for item in self.tools_constructed],
                "final_state_digest": self.final_state_digest,
            },
        )


_PROJECTED = {
    "MutationAdopted": "adopted",
    "MutationProvisionallyAdopted": "provisionally_adopted",
    "CandidateRejected": "rejected",
    "RollbackCompleted": "rollbacks",
    "ToolConstructed": "tools_constructed",
}


def project_archive(
    events: Iterable[JournalEvent], *, counters: AuditCounters | None = None
) -> ProjectedArchive:
    """Rebuild the archive from the journal alone."""
    buckets: dict[str, list[Mapping[str, Any]]] = {name: [] for name in set(_PROJECTED.values())}
    final_state = b""

    for event in events:
        if counters is not None:
            counters.archive_projection_operations += 1
            counters.audit_deterministic_operations += 1
        final_state = event.result_state_digest
        bucket = _PROJECTED.get(event.event_type)
        if bucket is None:
            continue
        buckets[bucket].append({
            "sequence": event.sequence,
            "event_hash": event.event_hash,
            "operation_parameters": dict(event.operation_parameters),
            "result_state_digest": event.result_state_digest,
        })

    return ProjectedArchive(
        adopted=tuple(buckets["adopted"]),
        provisionally_adopted=tuple(buckets["provisionally_adopted"]),
        rejected=tuple(buckets["rejected"]),
        rollbacks=tuple(buckets["rollbacks"]),
        tools_constructed=tuple(buckets["tools_constructed"]),
        final_state_digest=final_state,
    )


def verify_projection(
    events: Iterable[JournalEvent],
    persisted_digest: bytes,
    *,
    counters: AuditCounters | None = None,
) -> ProjectedArchive:
    """Reconstruct the archive and compare it to a persisted copy.

    An archive modified without a corresponding event fails here. This is the check that
    keeps the journal the single authority rather than one of two truths.
    """
    archive = project_archive(events, counters=counters)
    if archive.archive_digest() != persisted_digest:
        raise JournalIntegrityError("the persisted archive diverges from the journal")
    return archive
