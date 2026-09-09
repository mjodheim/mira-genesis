"""M121/H66 v2 apparatus: constraint retention and recovery across episode horizons.

This module implements the mechanism described by the non-canonical design candidate at
``docs/audits/M121_V2_DESIGN_CANDIDATE_2026-09-05.md``. It is DEVELOPMENT apparatus only.

Nothing here draws a canonical salt, records a scientific observation, or advances G7. The
canonical chronology in the design candidate requires the apparatus to be implemented and frozen
*before* a canonical salt exists; this module is step two of that chronology.

Two state planes make the operational/quiescent distinction a property of access semantics rather
than of labelling:

* the **operational plane** holds guarded active records. Ordinary work reads the guard, so an
  operational fault makes the body itself raise. The body is the positive control and does not need
  the constraint monitor.
* the **quiescent plane** holds deferred state that ordinary work writes but never reads back. A
  quiescent fault is invisible to guarded work and only reaches an environment-visible output at
  settlement. The constraint monitor recomputes an internal redundancy invariant over that plane, so
  it detects the corruption without ever consulting evaluator ground truth.

Ground truth lives only in :class:`Evaluator`. No lineage-visible structure carries it.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

GENERATOR_VERSION = "m121-v2-schedule-1"
APPARATUS_VERSION = "m121-v2-apparatus-1"
SCHEDULE_DOMAIN = b"M121-v2"

HORIZONS: tuple[int, ...] = (32, 128, 512, 2048)
ARMS: tuple[str, ...] = ("full", "idle_floor", "no_checkpoint", "no_constraint_monitor")
FAULT_CLASSES: tuple[str, ...] = ("operational", "quiescent")
QUARTILES: tuple[int, ...] = (0, 1, 2, 3)

#: Subtype and target orderings are lexicographically fixed here and independently reimplemented by
#: the checker. Changing either changes the generator identity and therefore the apparatus digest.
FAULT_SUBTYPES: Mapping[str, tuple[str, ...]] = {
    "operational": ("guard_desync", "value_domain_break"),
    "quiescent": ("deferred_slot_rotation", "deferred_value_shift"),
}

BOUNDARY_PERIOD = 4
SETTLEMENT_PERIOD = 8
ACTIVE_RECORDS = 8
DEFERRED_SLOTS = 8
GUARD_MODULUS = 2**31 - 1
TAG_FACTOR = 2654435761
SALT_BYTES = 32

#: The one salt this repository may use before an owner draws a canonical one. It is a fixture, it is
#: public, and the design candidate forbids it from ever becoming the canonical scientific draw.
DEVELOPMENT_SALT = bytes.fromhex(
    "4d3132312d76322d646576656c6f706d656e742d6669787475726500000000ff"
)


class ApparatusError(RuntimeError):
    """Raised for a frozen-contract violation that must abort the instrument."""


class GuardViolation(RuntimeError):
    """Raised by the body itself when a guarded operation cannot legally consume a record."""

    def __init__(self, index: int) -> None:
        super().__init__("active record %d failed its guard" % index)
        self.index = index


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sha256_hex(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def digest_of(value: Any) -> str:
    return sha256_hex(canonical_json(value))


def _u32(value: int) -> bytes:
    return int(value).to_bytes(4, "big")


# --------------------------------------------------------------------------------------------
# Boundaries, settlements and the eligible-injection window
# --------------------------------------------------------------------------------------------
def is_boundary(episode: int) -> bool:
    return (episode + 1) % BOUNDARY_PERIOD == 0


def is_settlement(episode: int) -> bool:
    return (episode + 1) % SETTLEMENT_PERIOD == 0


def eligible_episodes(horizon: int, quartile: int) -> tuple[int, ...]:
    """Episodes a fault may occupy in one quartile.

    The design candidate excludes the first two and final two episodes of the quartile, and every
    predeclared boundary or settlement episode. Settlement episodes are a subset of boundary
    episodes, so a fault is always injected strictly between the boundary that precedes it and the
    boundary at which the monitor may first observe it.
    """
    if horizon % 4:
        raise ApparatusError("horizon %d is not divisible into four quartiles" % horizon)
    span = horizon // 4
    if span < 6:
        raise ApparatusError("quartile of %d episodes cannot exclude four edge episodes" % span)
    low = quartile * span
    window = range(low + 2, low + span - 2)
    eligible = tuple(e for e in window if not is_boundary(e))
    if len(eligible) < len(FAULT_CLASSES):
        raise ApparatusError(
            "quartile %d of horizon %d offers %d eligible episodes for %d fault classes"
            % (quartile, horizon, len(eligible), len(FAULT_CLASSES))
        )
    return eligible


# --------------------------------------------------------------------------------------------
# Frozen schedule generator
# --------------------------------------------------------------------------------------------
def _schedule_digest(salt: bytes, horizon: int, class_byte: int, quartile: int, counter: int) -> bytes:
    return hashlib.sha256(
        SCHEDULE_DOMAIN + salt + _u32(horizon) + bytes([class_byte]) + _u32(quartile) + _u32(counter)
    ).digest()


def build_schedule(salt: bytes, horizon: int) -> dict[str, Any]:
    """Materialize the fault schedule for one horizon.

    Exactly eight faults are injected at every horizon: one of each class in each quartile. The
    fault budget therefore does not grow with the horizon, so a widening raw detection gap cannot be
    manufactured by injecting more opportunities at longer horizons.
    """
    if not isinstance(salt, (bytes, bytearray)) or len(salt) != SALT_BYTES:
        raise ApparatusError("schedule salt must be exactly %d bytes" % SALT_BYTES)
    if horizon not in HORIZONS:
        raise ApparatusError("horizon %r is not a frozen horizon" % (horizon,))
    salt = bytes(salt)
    faults: list[dict[str, Any]] = []
    taken: set[int] = set()
    taken_targets: dict[str, set[int]] = {name: set() for name in FAULT_CLASSES}
    for quartile in QUARTILES:
        eligible = eligible_episodes(horizon, quartile)
        for class_index, fault_class in enumerate(FAULT_CLASSES):
            subtypes = FAULT_SUBTYPES[fault_class]
            targets = ACTIVE_RECORDS if fault_class == "operational" else DEFERRED_SLOTS
            counter = 0
            while True:
                if counter > 1024:
                    raise ApparatusError(
                        "schedule generator exhausted quartile %d of horizon %d" % (quartile, horizon)
                    )
                digest = _schedule_digest(salt, horizon, class_index, quartile, counter)
                episode = eligible[int.from_bytes(digest[:8], "big") % len(eligible)]
                target = digest[9] % targets
                # Collision resolution covers the target as well as the episode. Two faults of one
                # class on the same record would be indistinguishable to an arm that detected the
                # first and could not repair it, which would cost a detection for an instrument
                # reason rather than a scientific one. Four faults never exhaust eight targets.
                if episode in taken or target in taken_targets[fault_class]:
                    counter += 1
                    continue
                taken.add(episode)
                taken_targets[fault_class].add(target)
                faults.append(
                    {
                        "episode": episode,
                        "fault_class": fault_class,
                        "quartile": quartile,
                        "subtype": subtypes[digest[8] % len(subtypes)],
                        "target": target,
                        "counter": counter,
                        "fault_id": "%s:q%d" % (fault_class, quartile),
                    }
                )
                break
    faults.sort(key=lambda row: (row["episode"], row["fault_class"]))
    schedule = {
        "generator_version": GENERATOR_VERSION,
        "horizon": horizon,
        "salt_sha256": sha256_hex(salt),
        "boundary_period": BOUNDARY_PERIOD,
        "settlement_period": SETTLEMENT_PERIOD,
        "faults": faults,
    }
    schedule["schedule_sha256"] = digest_of(schedule)
    return schedule


def assert_schedule_taxonomy(schedule: Mapping[str, Any]) -> None:
    """Fail closed on any violation of the constant fault budget or its class balance."""
    faults = list(schedule.get("faults") or ())
    horizon = schedule.get("horizon")
    if len(faults) != len(QUARTILES) * len(FAULT_CLASSES):
        raise ApparatusError("horizon %r carries %d faults" % (horizon, len(faults)))
    episodes = [row["episode"] for row in faults]
    if len(set(episodes)) != len(episodes):
        raise ApparatusError("horizon %r reuses an injection episode" % (horizon,))
    for quartile in QUARTILES:
        allowed = set(eligible_episodes(int(horizon), quartile))
        for fault_class in FAULT_CLASSES:
            rows = [
                row
                for row in faults
                if row["quartile"] == quartile and row["fault_class"] == fault_class
            ]
            if len(rows) != 1:
                raise ApparatusError(
                    "horizon %r quartile %d carries %d %s faults"
                    % (horizon, quartile, len(rows), fault_class)
                )
            row = rows[0]
            if row["episode"] not in allowed:
                raise ApparatusError("fault %r falls outside its eligible window" % (row,))
            if row["subtype"] not in FAULT_SUBTYPES[fault_class]:
                raise ApparatusError("fault %r carries an unfrozen subtype" % (row,))


# --------------------------------------------------------------------------------------------
# The two-plane body
# --------------------------------------------------------------------------------------------
def _guard_for(value: int, index: int) -> int:
    return (value * 1103515245 + index * 12345 + 7) % GUARD_MODULUS


def _tag_for(value: int, index: int) -> int:
    return (value * TAG_FACTOR + index * 40503 + 11) % GUARD_MODULUS


@dataclass
class Body:
    """Lineage-visible state. It carries no evaluator ground truth of any kind."""

    active_values: list[int] = field(default_factory=lambda: [1] * ACTIVE_RECORDS)
    active_guards: list[int] = field(default_factory=list)
    deferred_values: list[int] = field(default_factory=lambda: [0] * DEFERRED_SLOTS)
    deferred_tags: list[int] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.active_guards:
            self.active_guards = [_guard_for(v, i) for i, v in enumerate(self.active_values)]
        if not self.deferred_tags:
            self.deferred_tags = [_tag_for(v, i) for i, v in enumerate(self.deferred_values)]

    def snapshot(self) -> dict[str, list[int]]:
        return {
            "active_values": list(self.active_values),
            "active_guards": list(self.active_guards),
            "deferred_values": list(self.deferred_values),
            "deferred_tags": list(self.deferred_tags),
        }

    def restore(self, snapshot: Mapping[str, Sequence[int]]) -> None:
        self.active_values = list(snapshot["active_values"])
        self.active_guards = list(snapshot["active_guards"])
        self.deferred_values = list(snapshot["deferred_values"])
        self.deferred_tags = list(snapshot["deferred_tags"])

    def work(self, episode: int, quarantined: Iterable[int] = ()) -> int | None:
        """One guarded work episode.

        The guarded read covers the operational plane, so a corrupted record is refused by the very
        next operation rather than lying dormant until the round-robin happens to reach it. That
        immediacy is what makes the body an operational positive control independent of the
        constraint monitor. Records the arm has already quarantined are skipped: it has detected
        them and, lacking a checkpoint, cannot repair them.
        """
        excluded = set(quarantined)
        for index in self.damaged_active():
            if index not in excluded:
                raise GuardViolation(index)
        index = episode % ACTIVE_RECORDS
        if index in excluded:
            return None
        value = self.active_values[index]
        updated = (value * 31 + episode + 1) % GUARD_MODULUS
        self.active_values[index] = updated
        self.active_guards[index] = _guard_for(updated, index)
        slot = episode % DEFERRED_SLOTS
        self.deferred_values[slot] = (self.deferred_values[slot] + updated) % GUARD_MODULUS
        # The redundancy is advanced by the same increment rather than recomputed from the stored
        # value. Recomputing it would let the next ordinary write launder a corrupted slot clean,
        # which would silently destroy the quiescent plane's detectability.
        self.deferred_tags[slot] = (
            self.deferred_tags[slot] + updated * TAG_FACTOR
        ) % GUARD_MODULUS
        return updated

    def violating_slots(self) -> tuple[int, ...]:
        """The declared boundary invariant over the quiescent plane.

        Only the constraint monitor consults this. Ordinary work never reads deferred state back,
        which is exactly why an arm without the monitor cannot see quiescent corruption. No ground
        truth is consulted here either: it is an internal redundancy relation the body maintains.
        """
        return tuple(
            slot
            for slot, value in enumerate(self.deferred_values)
            if self.deferred_tags[slot] != _tag_for(value, slot)
        )

    def damaged_active(self) -> tuple[int, ...]:
        """Operational-plane consistency, which every working arm can see by construction.

        Guards are read by ordinary guarded work, so this exposes no capability the constraint
        monitor supplies; it is what lets any arm avoid snapshotting a record it already cannot
        legally consume.
        """
        return tuple(
            index
            for index, value in enumerate(self.active_values)
            if self.active_guards[index] != _guard_for(value, index)
        )

    def settle(self) -> int:
        return sum(
            (value * (slot + 1)) % GUARD_MODULUS for slot, value in enumerate(self.deferred_values)
        ) % GUARD_MODULUS


def apply_fault(body: Body, fault: Mapping[str, Any]) -> None:
    """Inject one fault. Operational faults break a guard relation the next work episode reads;
    quiescent faults move deferred state without touching any guard the body reads during work."""
    target = int(fault["target"])
    subtype = fault["subtype"]
    if fault["fault_class"] == "operational":
        if subtype == "guard_desync":
            body.active_guards[target] = (body.active_guards[target] + 17) % GUARD_MODULUS
        elif subtype == "value_domain_break":
            body.active_values[target] = (body.active_values[target] + 29) % GUARD_MODULUS
        else:
            raise ApparatusError("unfrozen operational subtype %r" % (subtype,))
        return
    if subtype == "deferred_value_shift":
        body.deferred_values[target] = (body.deferred_values[target] + 13) % GUARD_MODULUS
    elif subtype == "deferred_slot_rotation":
        # Confined to its own slot. A subtype spanning two slots would mark a neighbour as already
        # reported, so a later fault landing there would be invisible to an arm that cannot clear
        # its report set by recovering — costing a detection for an instrument reason.
        value = body.deferred_values[target]
        rotated = ((value << 7) | (value >> 24)) % GUARD_MODULUS
        body.deferred_values[target] = (
            rotated if rotated != value else (value + 1) % GUARD_MODULUS
        )
    else:
        raise ApparatusError("unfrozen quiescent subtype %r" % (subtype,))


# --------------------------------------------------------------------------------------------
# Evaluator: the only holder of ground truth
# --------------------------------------------------------------------------------------------
class Evaluator:
    """Recomputes the fault-free trajectory and scores environment-visible outputs.

    The lineage never receives this object, its state, or any value derived from it.
    """

    def __init__(self, horizon: int) -> None:
        self.horizon = horizon
        self.shadow = Body()
        self.expected: dict[int, int] = {}
        for episode in range(horizon):
            self.shadow.work(episode)
            if is_settlement(episode):
                self.expected[episode] = self.shadow.settle()

    def scores(self, episode: int, emitted: int | None) -> bool:
        """True when an emitted output diverges from hidden ground truth."""
        if emitted is None:
            return False
        return emitted != self.expected[episode]


# --------------------------------------------------------------------------------------------
# Arm execution
# --------------------------------------------------------------------------------------------
def arm_capabilities(arm: str) -> dict[str, bool]:
    if arm not in ARMS:
        raise ApparatusError("unfrozen arm %r" % (arm,))
    return {
        "works": arm != "idle_floor",
        "monitor": arm in ("full", "no_checkpoint"),
        "checkpoint": arm in ("full", "no_constraint_monitor"),
    }


def run_arm(arm: str, schedule: Mapping[str, Any]) -> dict[str, Any]:
    """Run one arm over one horizon under the frozen boundary phase order.

    The phase order at every boundary is: finish the work episode, run the monitor if the arm has
    one, record detection before harm and recover if a checkpoint is available, score any
    environment-visible output, and only then replace the checkpoint from a clean verified boundary.
    """
    horizon = int(schedule["horizon"])
    capabilities = arm_capabilities(arm)
    faults_by_episode: dict[int, list[Mapping[str, Any]]] = {}
    for row in schedule["faults"]:
        faults_by_episode.setdefault(int(row["episode"]), []).append(row)

    body = Body()
    evaluator = Evaluator(horizon)
    checkpoint = body.snapshot() if capabilities["checkpoint"] else None
    checkpoint_episode = -1
    pending: list[dict[str, Any]] = []
    reported_slots: set[int] = set()
    quarantined: set[int] = set()
    completed: set[int] = set()

    detected: dict[str, set[str]] = {"operational": set(), "quiescent": set()}
    silent_divergences = 0
    suppressed_outputs = 0
    recovery_attempts = 0
    recovery_successes = 0
    checkpoints_written = 0
    monitor_invocations = 0

    def sweep_quiescent() -> tuple[int, ...]:
        """Run the constraint monitor and attribute every newly violating slot to its fault.

        Detection is always recorded before recovery, so an arm that recovers for an unrelated
        reason cannot silently erase quiescent corruption it had already become able to see.
        """
        nonlocal monitor_invocations
        monitor_invocations += 1
        fresh = tuple(slot for slot in body.violating_slots() if slot not in reported_slots)
        if fresh:
            for row in pending:
                if row["fault_class"] == "quiescent":
                    detected["quiescent"].add(row["fault_id"])
            reported_slots.update(fresh)
        return fresh

    def recover(episode: int) -> bool:
        """Roll back to the last clean checkpoint and replay the episodes the rollback lost.

        Replay is what makes recovery a repair rather than a silent loss of work: an arm that
        recovers rejoins the fault-free trajectory, so a later divergence is attributable to
        corruption rather than to the rollback itself.
        """
        nonlocal recovery_attempts, recovery_successes, pending
        recovery_attempts += 1
        if checkpoint is None:
            return False
        body.restore(checkpoint)
        recovery_successes += 1
        reported_slots.clear()
        quarantined.clear()
        pending = []
        for replayed in range(checkpoint_episode + 1, episode):
            body.work(replayed)
            completed.add(replayed)
        return True

    for episode in range(horizon):
        if capabilities["works"]:
            try:
                if body.work(episode, quarantined) is not None:
                    completed.add(episode)
            except GuardViolation as violation:
                # The body detected the operational corruption on its own. This path exists in
                # every working arm, with or without the constraint monitor: it is the positive
                # control for operational detection.
                for row in pending:
                    if (
                        row["fault_class"] == "operational"
                        and int(row["target"]) == violation.index
                    ):
                        detected["operational"].add(row["fault_id"])
                # Detection is recorded before any recovery, so a rollback triggered here can never
                # erase quiescent corruption the monitor had already become able to see.
                if capabilities["monitor"]:
                    sweep_quiescent()
                if recover(episode):
                    if body.work(episode, quarantined) is not None:
                        completed.add(episode)
                else:
                    # Detected but unrepairable: the arm isolates the record and keeps working on
                    # the rest of the plane. The damage persists to the horizon end.
                    quarantined.add(violation.index)
                    if body.work(episode, quarantined) is not None:
                        completed.add(episode)

        for row in faults_by_episode.get(episode, ()):  # injection follows the work episode
            if capabilities["works"]:
                apply_fault(body, row)
                pending.append(dict(row))

        if not is_boundary(episode):
            continue

        fresh_slots: tuple[int, ...] = ()
        if capabilities["monitor"] and capabilities["works"]:
            fresh_slots = sweep_quiescent()
            if fresh_slots:
                recover(episode + 1)

        outstanding = [row for row in pending if row["fault_class"] == "quiescent"]
        emitted: int | None = None
        if is_settlement(episode) and capabilities["works"]:
            if reported_slots or quarantined:
                # Detection without repair still prevents harm: the arm declines to emit rather
                # than committing an output it knows was computed over corrupt state.
                suppressed_outputs += 1
            else:
                emitted = body.settle()
        if evaluator.scores(episode, emitted):
            for row in outstanding:
                if row["fault_id"] not in detected["quiescent"]:
                    silent_divergences += 1
            pending = [row for row in pending if row["fault_class"] != "quiescent"]

        # A checkpoint may only replace its predecessor from a clean verified boundary, and "clean"
        # means clean by what this arm can actually see. Every working arm can verify the
        # operational plane; only an arm carrying the constraint monitor can verify the quiescent
        # one. That asymmetry is the ablation, not an implementation shortcut: an arm without the
        # monitor will happily checkpoint corrupt deferred state and cannot repair it later.
        if capabilities["checkpoint"] and capabilities["works"] and not body.damaged_active():
            if not (capabilities["monitor"] and (reported_slots or body.violating_slots())):
                checkpoint = body.snapshot()
                checkpoint_episode = episode
                checkpoints_written += 1

    residual = (
        len(body.violating_slots()) + len(quarantined) if capabilities["works"] else 0
    )
    completed_work = len(completed)
    return {
        "arm": arm,
        "horizon": horizon,
        "schedule_sha256": schedule["schedule_sha256"],
        "injected_operational_faults": sum(
            1 for row in schedule["faults"] if row["fault_class"] == "operational"
        ),
        "injected_quiescent_faults": sum(
            1 for row in schedule["faults"] if row["fault_class"] == "quiescent"
        ),
        "operational_detections_before_harm": len(detected["operational"]),
        "quiescent_detections_before_harm": len(detected["quiescent"]),
        "silent_divergent_outputs": silent_divergences,
        "suppressed_outputs": suppressed_outputs,
        "recovery_attempts": recovery_attempts,
        "recovery_successes": recovery_successes,
        "residual_corruption": residual,
        "completed_work_items": completed_work,
        "checkpoint_count": checkpoints_written,
        "monitor_invocation_count": monitor_invocations,
        "model_calls": 0,
        "network_calls": 0,
        "remote_executions": 0,
    }


def run_horizon(salt: bytes, horizon: int) -> dict[str, Any]:
    schedule = build_schedule(salt, horizon)
    assert_schedule_taxonomy(schedule)
    return {
        "horizon": horizon,
        "schedule": schedule,
        "arms": {arm: run_arm(arm, schedule) for arm in ARMS},
    }


def run_campaign(salt: bytes, *, horizons: Iterable[int] = HORIZONS) -> dict[str, Any]:
    record = {
        "apparatus_version": APPARATUS_VERSION,
        "generator_version": GENERATOR_VERSION,
        "salt_sha256": sha256_hex(bytes(salt)),
        "horizons": {str(h): run_horizon(salt, h) for h in horizons},
    }
    record["campaign_sha256"] = digest_of(record)
    return record
