"""Immutable versioned lineage-state contracts for M043 Q4."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Sequence

from metamorphosis.m043_adoption_codec import (
    AdoptionError,
    SNAPSHOT_SCHEMA,
    _canonical_json,
    _digest,
    _domain_digest,
    _fields,
    _integer,
    _mapping,
    _parse_json,
    _sequence,
    _string,
)
from metamorphosis.m043_mealy import MealyMachine


@dataclass(frozen=True)
class ToolRecord:
    trace_digest: str
    task_id: str
    effect_kinds: tuple[str, ...]
    acquired_version: int
    validation_report_digest: str

    def to_dict(self) -> dict[str, object]:
        return {
            "trace_digest": self.trace_digest,
            "task_id": self.task_id,
            "effect_kinds": list(self.effect_kinds),
            "acquired_version": self.acquired_version,
            "validation_report_digest": self.validation_report_digest,
        }

    @staticmethod
    def from_dict(value: object) -> "ToolRecord":
        raw = _mapping(value, "tool record")
        _fields(
            raw,
            {
                "trace_digest",
                "task_id",
                "effect_kinds",
                "acquired_version",
                "validation_report_digest",
            },
            "tool record",
        )
        effects = tuple(
            _string(item, "effect_kind")
            for item in _sequence(raw["effect_kinds"], "effect_kinds")
        )
        if not effects:
            raise AdoptionError("tool record must contain at least one effect kind")
        return ToolRecord(
            trace_digest=_digest(raw["trace_digest"], "trace_digest"),
            task_id=_string(raw["task_id"], "task_id"),
            effect_kinds=effects,
            acquired_version=_integer(
                raw["acquired_version"], "acquired_version", minimum=1
            ),
            validation_report_digest=_digest(
                raw["validation_report_digest"], "validation_report_digest"
            ),
        )


@dataclass(frozen=True)
class LearningState:
    operation_priority: tuple[str, ...]
    successful_trace_digests: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "operation_priority": list(self.operation_priority),
            "successful_trace_digests": list(self.successful_trace_digests),
        }

    @staticmethod
    def from_dict(value: object) -> "LearningState":
        raw = _mapping(value, "learning state")
        _fields(
            raw,
            {"operation_priority", "successful_trace_digests"},
            "learning state",
        )
        priority = tuple(
            _string(item, "operation_priority")
            for item in _sequence(raw["operation_priority"], "operation_priority")
        )
        traces = tuple(
            _digest(item, "successful_trace_digest")
            for item in _sequence(
                raw["successful_trace_digests"], "successful_trace_digests"
            )
        )
        if not priority or len(set(priority)) != len(priority):
            raise AdoptionError("operation priority must be nonempty and unique")
        if len(set(traces)) != len(traces):
            raise AdoptionError("successful trace digests must be unique")
        return LearningState(priority, traces)


DEFAULT_LEARNING_STATE = LearningState(
    (
        "reachable_capacity_growth",
        "fixed_capacity_output_edit",
        "fixed_capacity_transition_edit",
        "unreachable_capacity_compaction",
    )
)


@dataclass(frozen=True)
class CausalJournalEntry:
    sequence: int
    event: str
    parent_snapshot_digest: str
    child_core_digest: str
    package_digest: str
    validation_report_digest: str
    accepted_body_digest: str
    tool_registry_digest: str
    learning_state_digest: str
    previous_entry_digest: str | None

    def to_dict(self) -> dict[str, object]:
        return {
            "sequence": self.sequence,
            "event": self.event,
            "parent_snapshot_digest": self.parent_snapshot_digest,
            "child_core_digest": self.child_core_digest,
            "package_digest": self.package_digest,
            "validation_report_digest": self.validation_report_digest,
            "accepted_body_digest": self.accepted_body_digest,
            "tool_registry_digest": self.tool_registry_digest,
            "learning_state_digest": self.learning_state_digest,
            "previous_entry_digest": self.previous_entry_digest,
        }

    def digest(self) -> str:
        return _domain_digest(b"m043-q4-journal-entry-v1\x00", self.to_dict())

    @staticmethod
    def from_dict(value: object) -> "CausalJournalEntry":
        raw = _mapping(value, "journal entry")
        expected = {
            "sequence",
            "event",
            "parent_snapshot_digest",
            "child_core_digest",
            "package_digest",
            "validation_report_digest",
            "accepted_body_digest",
            "tool_registry_digest",
            "learning_state_digest",
            "previous_entry_digest",
        }
        _fields(raw, expected, "journal entry")
        previous = raw["previous_entry_digest"]
        return CausalJournalEntry(
            sequence=_integer(raw["sequence"], "sequence", minimum=1),
            event=_string(raw["event"], "event"),
            parent_snapshot_digest=_digest(
                raw["parent_snapshot_digest"], "parent_snapshot_digest"
            ),
            child_core_digest=_digest(raw["child_core_digest"], "child_core_digest"),
            package_digest=_digest(raw["package_digest"], "package_digest"),
            validation_report_digest=_digest(
                raw["validation_report_digest"], "validation_report_digest"
            ),
            accepted_body_digest=_digest(
                raw["accepted_body_digest"], "accepted_body_digest"
            ),
            tool_registry_digest=_digest(
                raw["tool_registry_digest"], "tool_registry_digest"
            ),
            learning_state_digest=_digest(
                raw["learning_state_digest"], "learning_state_digest"
            ),
            previous_entry_digest=(
                None
                if previous is None
                else _digest(previous, "previous_entry_digest")
            ),
        )


def tool_registry_digest(registry: Sequence[ToolRecord]) -> str:
    return _domain_digest(
        b"m043-q4-tool-registry-v1\x00", [record.to_dict() for record in registry]
    )


def learning_state_digest(state: LearningState) -> str:
    return _domain_digest(b"m043-q4-learning-state-v1\x00", state.to_dict())


def journal_digest(journal: Sequence[CausalJournalEntry]) -> str:
    return _domain_digest(
        b"m043-q4-causal-journal-v1\x00", [entry.to_dict() for entry in journal]
    )


def _core_mapping(
    *,
    version: int,
    accepted_body: MealyMachine,
    tool_registry: Sequence[ToolRecord],
    learning_state: LearningState,
    accepted_task_commitments: Sequence[str],
) -> dict[str, object]:
    return {
        "version": version,
        "accepted_body": accepted_body.to_dict(),
        "tool_registry": [record.to_dict() for record in tool_registry],
        "learning_state": learning_state.to_dict(),
        "accepted_task_commitments": list(accepted_task_commitments),
    }


def _core_digest(**kwargs: object) -> str:
    return _domain_digest(b"m043-q4-lineage-core-v1\x00", _core_mapping(**kwargs))


@dataclass(frozen=True)
class LineageSnapshot:
    version: int
    accepted_body: MealyMachine
    tool_registry: tuple[ToolRecord, ...]
    learning_state: LearningState
    accepted_task_commitments: tuple[str, ...]
    causal_journal: tuple[CausalJournalEntry, ...]
    schema: str = SNAPSHOT_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != SNAPSHOT_SCHEMA:
            raise AdoptionError("unsupported lineage snapshot schema")
        _integer(self.version, "version", minimum=0)
        if len(self.causal_journal) != self.version:
            raise AdoptionError("journal length must equal the lineage version")
        if len(set(record.trace_digest for record in self.tool_registry)) != len(
            self.tool_registry
        ):
            raise AdoptionError("tool registry contains duplicate trace identities")
        if len(set(self.accepted_task_commitments)) != len(
            self.accepted_task_commitments
        ):
            raise AdoptionError("accepted task commitments must be unique")
        for digest in self.accepted_task_commitments:
            _digest(digest, "accepted_task_commitment")

    def core_mapping(self) -> dict[str, object]:
        return _core_mapping(
            version=self.version,
            accepted_body=self.accepted_body,
            tool_registry=self.tool_registry,
            learning_state=self.learning_state,
            accepted_task_commitments=self.accepted_task_commitments,
        )

    def core_digest(self) -> str:
        return _domain_digest(b"m043-q4-lineage-core-v1\x00", self.core_mapping())

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            **self.core_mapping(),
            "causal_journal": [entry.to_dict() for entry in self.causal_journal],
        }

    def to_bytes(self) -> bytes:
        return _canonical_json(self.to_dict())

    def digest(self) -> str:
        return hashlib.sha256(
            b"m043-q4-lineage-snapshot-v1\x00" + self.to_bytes()
        ).hexdigest()

    @staticmethod
    def from_bytes(
        payload: bytes | str, *, expected_digest: str | None = None
    ) -> "LineageSnapshot":
        raw = _parse_json(payload, "lineage snapshot")
        expected = {
            "schema",
            "version",
            "accepted_body",
            "tool_registry",
            "learning_state",
            "accepted_task_commitments",
            "causal_journal",
        }
        _fields(raw, expected, "lineage snapshot")
        if raw["schema"] != SNAPSHOT_SCHEMA:
            raise AdoptionError("unsupported lineage snapshot schema")
        try:
            body = MealyMachine.from_dict(_mapping(raw["accepted_body"], "accepted_body"))
        except ValueError as exc:
            raise AdoptionError("accepted body is malformed") from exc
        snapshot = LineageSnapshot(
            version=_integer(raw["version"], "version", minimum=0),
            accepted_body=body,
            tool_registry=tuple(
                ToolRecord.from_dict(item)
                for item in _sequence(raw["tool_registry"], "tool_registry")
            ),
            learning_state=LearningState.from_dict(raw["learning_state"]),
            accepted_task_commitments=tuple(
                _digest(item, "accepted_task_commitment")
                for item in _sequence(
                    raw["accepted_task_commitments"], "accepted_task_commitments"
                )
            ),
            causal_journal=tuple(
                CausalJournalEntry.from_dict(item)
                for item in _sequence(raw["causal_journal"], "causal_journal")
            ),
        )
        from metamorphosis.m043_adoption import audit_snapshot

        audit_snapshot(snapshot)
        if expected_digest is not None and snapshot.digest() != _digest(
            expected_digest, "expected_snapshot_digest"
        ):
            raise AdoptionError("lineage snapshot digest does not match its commitment")
        return snapshot


def initial_lineage(parent: MealyMachine) -> LineageSnapshot:
    return LineageSnapshot(0, parent, (), DEFAULT_LEARNING_STATE, (), ())


__all__ = [
    "CausalJournalEntry",
    "DEFAULT_LEARNING_STATE",
    "LearningState",
    "LineageSnapshot",
    "ToolRecord",
    "initial_lineage",
    "journal_digest",
    "learning_state_digest",
    "tool_registry_digest",
]
