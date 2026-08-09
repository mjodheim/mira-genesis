"""Deterministic tamper-evident memory with exact checkpoints and rollback."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Mapping, Sequence

from mira_core.contracts import JsonValue


GENESIS_DIGEST = "0" * 64


def _canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _event_digest(index: int, kind: str, payload: Mapping[str, JsonValue], previous: str) -> str:
    record = {"index": index, "kind": kind, "payload": dict(payload), "previous": previous}
    return hashlib.sha256(b"mira-memory-event-v1\0" + _canonical_json(record)).hexdigest()


@dataclass(frozen=True)
class MemoryEvent:
    index: int
    kind: str
    payload: Mapping[str, JsonValue]
    previous_digest: str
    digest: str

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "index": self.index,
            "kind": self.kind,
            "payload": dict(self.payload),
            "previous_digest": self.previous_digest,
            "digest": self.digest,
        }


class MemoryLedger:
    def __init__(self, events: Sequence[MemoryEvent] = ()) -> None:
        self._events = list(events)
        self.verify()

    @property
    def events(self) -> tuple[MemoryEvent, ...]:
        return tuple(self._events)

    @property
    def digest(self) -> str:
        return self._events[-1].digest if self._events else GENESIS_DIGEST

    def append(self, kind: str, payload: Mapping[str, JsonValue]) -> MemoryEvent:
        if not kind:
            raise ValueError("memory event kind cannot be empty")
        index = len(self._events)
        previous = self.digest
        digest = _event_digest(index, kind, payload, previous)
        event = MemoryEvent(index, kind, dict(payload), previous, digest)
        self._events.append(event)
        return event

    def checkpoint(self) -> bytes:
        return _canonical_json({
            "schema": "mira-memory-ledger-v1",
            "events": [event.to_dict() for event in self._events],
            "head_digest": self.digest,
        })

    @classmethod
    def restore(cls, checkpoint: bytes) -> "MemoryLedger":
        try:
            value = json.loads(checkpoint.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("memory checkpoint is malformed") from exc
        if not isinstance(value, dict) or value.get("schema") != "mira-memory-ledger-v1":
            raise ValueError("memory checkpoint schema mismatch")
        raw_events = value.get("events")
        if not isinstance(raw_events, list):
            raise ValueError("memory checkpoint events are absent")
        events: list[MemoryEvent] = []
        for raw in raw_events:
            if not isinstance(raw, dict) or not isinstance(raw.get("payload"), dict):
                raise ValueError("memory checkpoint carries a malformed event")
            events.append(MemoryEvent(
                int(raw["index"]), str(raw["kind"]), dict(raw["payload"]),
                str(raw["previous_digest"]), str(raw["digest"]),
            ))
        ledger = cls(events)
        if value.get("head_digest") != ledger.digest:
            raise ValueError("memory checkpoint head digest mismatch")
        return ledger

    def verify(self) -> None:
        previous = GENESIS_DIGEST
        for index, event in enumerate(self._events):
            if event.index != index or event.previous_digest != previous:
                raise ValueError("memory event chain is discontinuous")
            expected = _event_digest(index, event.kind, event.payload, previous)
            if event.digest != expected:
                raise ValueError("memory event digest mismatch")
            previous = event.digest

    def history(self) -> tuple[Mapping[str, JsonValue], ...]:
        return tuple(event.to_dict() for event in self._events)
