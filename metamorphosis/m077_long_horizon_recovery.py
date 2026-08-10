"""Unattended fault recovery and constraint retention across episode-count horizons.

The harness answers the recoverable half of G7: can one persistent lineage hold four declared
invariants and recover from injected faults with zero interventions as the horizon grows, and are
detection and restoration separable mechanisms?

Horizons are episode counts. Nothing here is a human-equivalent time horizon. No model is called, no
network is opened and every fault is a mutation of an in-memory pool.
"""
from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass, field
from typing import Mapping, Sequence


PROTOCOL_SCHEMA = "m077-long-horizon-recovery-protocol-v1"
GENERATOR_VERSION = 1

SLOT_COUNT = 16
RECORD_TYPES = ("alpha", "beta", "gamma", "delta")
CHECKPOINT_INTERVAL = 16
HORIZONS = (32, 128, 512, 2048)

ARMS = ("full", "no_checkpoint", "no_constraint_monitor", "idle_floor")

OPERATIONAL_FAULTS = ("journal_truncation", "capacity_spike")
SILENT_FAULTS = ("slot_type_corruption", "stale_checkpoint")
FAULT_KINDS = OPERATIONAL_FAULTS + SILENT_FAULTS

GENESIS_DIGEST = hashlib.sha256(b"m077-genesis").hexdigest()


class ShiftError(RuntimeError):
    """Raised when a protocol or body contract is violated."""


class OperationalFault(RuntimeError):
    """Raised by the body when a fault makes a legitimate operation impossible."""


def _digest(salt: bytes, horizon: int, index: int, tag: bytes = b"") -> bytes:
    return hashlib.sha256(
        salt + tag + horizon.to_bytes(4, "big") + index.to_bytes(4, "big"),
    ).digest()


@dataclass
class Pool:
    slot_types: tuple[str, ...]
    slots: list[tuple[str, int] | None]
    capacity: int

    @classmethod
    def build(cls, salt: bytes) -> "Pool":
        digest = hashlib.sha256(salt + b"slot-types").digest()
        slot_types = tuple(
            RECORD_TYPES[digest[index % len(digest)] % len(RECORD_TYPES)]
            for index in range(SLOT_COUNT)
        )
        return cls(slot_types=slot_types, slots=[None] * SLOT_COUNT, capacity=SLOT_COUNT)

    def occupancy(self) -> int:
        return sum(1 for slot in self.slots if slot is not None)


@dataclass
class Journal:
    digests: list[str] = field(default_factory=lambda: [GENESIS_DIGEST])

    def append(self, payload: str) -> None:
        self.digests.append(hashlib.sha256(
            (self.digests[-1] + payload).encode("utf-8"),
        ).hexdigest())

    @property
    def head(self) -> str:
        return self.digests[-1]

    def chain_is_unbroken(self) -> bool:
        return len(self.digests) >= 1 and self.digests[0] == GENESIS_DIGEST


@dataclass
class Checkpoint:
    pool: Pool
    journal_length: int
    head: str
    completed: int


@dataclass
class Body:
    """The environment. It owns state and raises on operations a fault made impossible."""

    pool: Pool
    journal: Journal
    completed: int = 0
    recorded_head: str = GENESIS_DIGEST

    @classmethod
    def build(cls, salt: bytes) -> "Body":
        return cls(pool=Pool.build(salt), journal=Journal())

    def apply_work(self, slot: int, record_type: str) -> None:
        if self.journal.head != self.recorded_head:
            raise OperationalFault("journal head does not match the recorded head")
        if self.pool.occupancy() > self.pool.capacity:
            raise OperationalFault("occupancy exceeds declared capacity")
        if record_type != self.pool.slot_types[slot]:
            raise ShiftError("the scheduler proposed a wrongly typed work item")
        self.pool.slots[slot] = (record_type, self.completed)
        self.journal.append(f"{slot}:{record_type}")
        self.recorded_head = self.journal.head
        self.completed += 1

    def audit(self) -> tuple[str, ...]:
        """Evaluator-owned invariant audit. Never used by an arm to make its own decisions."""

        broken: list[str] = []
        for index, slot in enumerate(self.pool.slots):
            if slot is not None and slot[0] != self.pool.slot_types[index]:
                broken.append("I1")
                break
        if not self.journal.chain_is_unbroken() or self.journal.head != self.recorded_head:
            broken.append("I2")
        if self.pool.occupancy() > self.pool.capacity:
            broken.append("I3")
        if self.completed < 0:
            broken.append("I4")
        return tuple(broken)

    def snapshot(self) -> Checkpoint:
        return Checkpoint(
            pool=copy.deepcopy(self.pool),
            journal_length=len(self.journal.digests),
            head=self.journal.head,
            completed=self.completed,
        )

    def restore(self, checkpoint: Checkpoint) -> None:
        self.pool = copy.deepcopy(checkpoint.pool)
        self.journal = Journal(digests=self.journal.digests[:checkpoint.journal_length])
        self.recorded_head = checkpoint.head
        self.completed = checkpoint.completed


def inject(body: Body, kind: str, salt: bytes, ordinal: int) -> None:
    digest = hashlib.sha256(salt + b"fault" + ordinal.to_bytes(4, "big")).digest()
    if kind == "slot_type_corruption":
        slot = digest[0] % SLOT_COUNT
        wrong = next(t for t in RECORD_TYPES if t != body.pool.slot_types[slot])
        body.pool.slots[slot] = (wrong, -1)
    elif kind == "journal_truncation":
        if len(body.journal.digests) > 1:
            body.journal.digests.pop()
    elif kind == "capacity_spike":
        body.pool.capacity = SLOT_COUNT - 1
        for index in range(SLOT_COUNT):
            if body.pool.slots[index] is None:
                body.pool.slots[index] = (body.pool.slot_types[index], -1)
        body.pool.capacity = SLOT_COUNT - 1
    elif kind == "stale_checkpoint":
        body.recorded_head = GENESIS_DIGEST
    else:
        raise ShiftError(f"unknown fault kind {kind!r}")


def build_schedule(salt: bytes, horizon: int) -> dict[int, str]:
    """Deterministic fault positions; every kind appears at least once per horizon."""

    count = max(4, horizon // 64)
    schedule: dict[int, str] = {}
    ordinal = 0
    while len(schedule) < count:
        digest = _digest(salt, horizon, ordinal, b"schedule")
        index = 1 + digest[0] % max(1, horizon - 2)
        kind = (
            FAULT_KINDS[len(schedule) % len(FAULT_KINDS)]
            if len(schedule) < len(FAULT_KINDS)
            else FAULT_KINDS[digest[1] % len(FAULT_KINDS)]
        )
        ordinal += 1
        if index not in schedule:
            schedule[index] = kind
        if ordinal > horizon * 8:
            raise ShiftError("fault schedule failed to converge")
    missing = set(FAULT_KINDS) - set(schedule.values())
    if missing:
        raise ShiftError(f"schedule omitted fault kinds {sorted(missing)}")
    return dict(sorted(schedule.items()))


def work_item(salt: bytes, horizon: int, index: int, pool: Pool) -> tuple[int, str]:
    digest = _digest(salt, horizon, index, b"work")
    slot = digest[0] % SLOT_COUNT
    return slot, pool.slot_types[slot]


@dataclass
class ShiftRecord:
    arm: str
    horizon: int
    faults_injected: int
    detections: int
    restorations: int
    interventions: int
    work_items_completed: int
    residual_violations: int
    replay_digest: str

    @property
    def restoration_rate_on_detected(self) -> float:
        return 1.0 if self.detections == 0 else self.restorations / self.detections


def run_shift(salt: bytes, horizon: int, arm: str) -> ShiftRecord:
    if arm not in ARMS:
        raise ShiftError(f"unknown arm {arm!r}")
    monitor_enabled = arm != "no_constraint_monitor"
    checkpoint_enabled = arm != "no_checkpoint"

    body = Body.build(salt)
    schedule = build_schedule(salt, horizon)
    checkpoint = body.snapshot()
    detections = 0
    restorations = 0
    completed_before_faults = 0
    transitions: list[str] = []
    # Unique-fault accounting. Counting raw detection events made detections exceed injected
    # faults, because an unrepaired fault re-triggers on every later episode.
    # Faults can land on adjacent episodes, so several may be outstanding at once. A single slot
    # silently dropped the earlier one; overlapping faults compound into one corrupt state, and
    # repairing that state resolves every fault still outstanding.
    outstanding: set[int] = set()
    detected_ids: set[int] = set()
    restored_ids: set[int] = set()

    for index in range(horizon):
        if index in schedule:
            inject(body, schedule[index], salt, index)
            outstanding.add(index)

        if arm == "idle_floor":
            continue

        detected = False
        slot, record_type = work_item(salt, horizon, index, body.pool)
        try:
            body.apply_work(slot, record_type)
            completed_before_faults += 1
        except OperationalFault:
            # The body itself signalled; this path exists independently of the monitor.
            detected = True

        if monitor_enabled and not detected and body.audit():
            detected = True

        if detected:
            detected_ids.update(outstanding)
        if detected:
            if checkpoint_enabled:
                if checkpoint.head != body.journal.digests[
                    min(checkpoint.journal_length, len(body.journal.digests)) - 1
                ]:
                    # The checkpoint itself was staled; rebuild from a verified live state.
                    body.recorded_head = body.journal.head
                    body.pool.capacity = SLOT_COUNT
                    for position, slot_value in enumerate(body.pool.slots):
                        if slot_value is not None and slot_value[0] != body.pool.slot_types[
                            position
                        ]:
                            body.pool.slots[position] = None
                    checkpoint = body.snapshot()
                else:
                    body.restore(checkpoint)
                if outstanding and not body.audit():
                    restored_ids.update(outstanding)
                    outstanding.clear()

        if checkpoint_enabled and index % CHECKPOINT_INTERVAL == 0 and not body.audit():
            checkpoint = body.snapshot()
        transitions.append(f"{index}:{body.completed}:{body.journal.head[:8]}")

    detections = len(detected_ids)
    restorations = len(restored_ids)
    residual = len(body.audit())
    return ShiftRecord(
        arm=arm,
        horizon=horizon,
        faults_injected=len(schedule),
        detections=detections,
        restorations=restorations,
        interventions=0,
        work_items_completed=completed_before_faults,
        residual_violations=residual,
        replay_digest=hashlib.sha256(
            "|".join(transitions).encode("utf-8"),
        ).hexdigest(),
    )


def run_arm(salt: bytes, arm: str) -> dict[str, object]:
    records = {horizon: run_shift(salt, horizon, arm) for horizon in HORIZONS}
    return {
        "arm": arm,
        "horizons": {
            str(horizon): {
                "faults_injected": record.faults_injected,
                "detections": record.detections,
                "restorations": record.restorations,
                "unrecovered_faults": record.detections - record.restorations,
                "undetected_faults": record.faults_injected - record.detections,
                "interventions": record.interventions,
                "work_items_completed": record.work_items_completed,
                "residual_violations": record.residual_violations,
                "restoration_rate_on_detected": record.restoration_rate_on_detected,
                "replay_digest": record.replay_digest,
            }
            for horizon, record in records.items()
        },
    }


@dataclass(frozen=True)
class RecoveryVerdict:
    positive: bool
    reasons: tuple[str, ...] = field(default=())


def evaluate(arms: Mapping[str, Mapping[str, object]]) -> RecoveryVerdict:
    """Check the preregistered thresholds and the single-capability-loss dissociation."""

    reasons: list[str] = []
    full = arms["full"]["horizons"]
    assert isinstance(full, dict)

    for horizon in HORIZONS:
        row = full[str(horizon)]
        if row["unrecovered_faults"] != 0:
            reasons.append(f"full arm left {row['unrecovered_faults']} unrecovered at {horizon}")
        if row["undetected_faults"] != 0:
            reasons.append(f"full arm missed {row['undetected_faults']} faults at {horizon}")
        if row["residual_violations"] != 0:
            reasons.append(f"full arm ended with violations at {horizon}")
        if row["interventions"] != 0:
            reasons.append(f"full arm required intervention at {horizon}")

    no_checkpoint = arms["no_checkpoint"]["horizons"]
    no_monitor = arms["no_constraint_monitor"]["horizons"]
    assert isinstance(no_checkpoint, dict) and isinstance(no_monitor, dict)

    for horizon in HORIZONS:
        key = str(horizon)
        if no_checkpoint[key]["unrecovered_faults"] < 1:
            reasons.append(f"no_checkpoint recovered everything at {horizon}")
        if no_checkpoint[key]["detections"] != full[key]["detections"]:
            reasons.append(
                f"no_checkpoint changed detection at {horizon}: "
                f"{no_checkpoint[key]['detections']} vs {full[key]['detections']}"
            )
        if no_monitor[key]["undetected_faults"] < 1:
            reasons.append(f"no_constraint_monitor detected everything at {horizon}")
        if no_monitor[key]["restoration_rate_on_detected"] != full[key][
            "restoration_rate_on_detected"
        ]:
            reasons.append(
                f"no_constraint_monitor changed restoration rate at {horizon}"
            )

    idle = arms["idle_floor"]["horizons"]
    assert isinstance(idle, dict)
    for horizon in HORIZONS:
        if idle[str(horizon)]["work_items_completed"] != 0:
            reasons.append(f"idle floor completed work at {horizon}")

    return RecoveryVerdict(positive=not reasons, reasons=tuple(reasons))


def canonical_json(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")
