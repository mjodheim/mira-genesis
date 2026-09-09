"""M121/H66 v3 apparatus: the v2 successor, redesigned so that it can return a negative.

v2 was correct and unfalsifiable. Every metric its verdict consulted was constant across 200
independently drawn salts, because its four corrections jointly removed every source of variance:
detection stopped depending on where a fault landed, when it landed, or on what else was damaged.
The finding is preserved at ``experiments/M121/V2_IMPLEMENTATION_NOTES.md`` and v2 is not edited.

v3 keeps all four of those corrections — they were right, and each removed a genuine
instrument-reason for failure — and adds the two things v2 lacked. **Fault position must decide
outcomes**, or the canonical salt decides nothing and the freeze-then-draw ceremony protects against
a threat that cannot materialise.

Inherited by import from v2 and forbidden to change here:

* the two-plane body, its guarded whole-plane read and its non-launderable deferred redundancy;
* the fault grammar and its application;
* replay on recovery.

Changed, deliberately, and each change is a source of variance rather than a correction:

1. **Coprime cadences.** v2 ran the monitor at every boundary and settled only at boundaries, so a
   monitor pass always separated a quiescent fault from the output that would reveal it. Here
   ``BOUNDARY_PERIOD`` and ``SETTLEMENT_PERIOD`` are coprime, so most settlements are not boundaries
   and a fault landing in the wrong window reaches an output first.
2. **Bounded monitor budget.** The monitor inspects ``MONITOR_SLOTS_PER_BOUNDARY`` of the deferred
   slots per boundary rather than all of them. Whether the corrupted slot is in the window depends on
   where the fault landed, and coverage accumulates with the number of boundary passes, so the
   horizon does real work instead of producing identical numbers at every length.
3. **A matched random-audit control.** ``random_audit`` spends exactly the same inspection budget on
   slots drawn from a salt-derived stream instead of the round-robin order. The claim that the
   structured audit is worth its budget can then be **false on a given schedule**, which is what the
   v2 arms could never be.

The monitor cursor is a pure function of the boundary index, not of arm history, so two
monitor-carrying arms inspect the same slots at the same boundaries. An ablation therefore cannot
differ for a scheduling reason, only for the capability it removed.

Nothing here draws a canonical salt or records a scientific observation.
"""
from __future__ import annotations

import hashlib
from typing import Any, Iterable, Mapping

from metamorphosis.m121_long_horizon_v2 import (
    ACTIVE_RECORDS,
    DEFERRED_SLOTS,
    FAULT_CLASSES,
    FAULT_SUBTYPES,
    QUARTILES,
    SALT_BYTES,
    ApparatusError,
    Body,
    GuardViolation,
    apply_fault,
    canonical_json,
    digest_of,
    sha256_hex,
)

GENERATOR_VERSION = "m121-v3-schedule-1"
APPARATUS_VERSION = "m121-v3-apparatus-1"
SCHEDULE_DOMAIN = b"M121-v3"
AUDIT_DOMAIN = b"M121-v3-random-audit"

HORIZONS: tuple[int, ...] = (32, 128, 512, 2048)
ARMS: tuple[str, ...] = (
    "full",
    "idle_floor",
    "no_checkpoint",
    "no_constraint_monitor",
    "random_audit",
)

#: Coprime, so only one settlement in five coincides with a boundary. This is the whole point: a
#: quiescent fault is seen before harm only when a boundary happens to fall between it and the next
#: settlement.
BOUNDARY_PERIOD = 5
SETTLEMENT_PERIOD = 8

#: Two of eight slots per boundary. A full sweep therefore takes four boundaries, so coverage is
#: genuinely partial and accumulates with horizon length. A budget equal to DEFERRED_SLOTS would
#: reproduce v2's guaranteed detection exactly.
MONITOR_SLOTS_PER_BOUNDARY = 2

#: The public development fixture. It may never become the canonical draw.
DEVELOPMENT_SALT = bytes.fromhex(
    "4d3132312d76332d646576656c6f706d656e742d6669787475726500000000ff"
)


def is_boundary(episode: int) -> bool:
    return (episode + 1) % BOUNDARY_PERIOD == 0


def is_settlement(episode: int) -> bool:
    return (episode + 1) % SETTLEMENT_PERIOD == 0


def eligible_episodes(horizon: int, quartile: int) -> tuple[int, ...]:
    """Episodes a fault may occupy in one quartile.

    Boundary and settlement episodes are both excluded, so every fault lands strictly between two
    predeclared events and its detectability is decided by the cadence rather than by landing on an
    event.
    """
    if horizon % 4:
        raise ApparatusError("horizon %d is not divisible into four quartiles" % horizon)
    span = horizon // 4
    if span < 6:
        raise ApparatusError("quartile of %d episodes cannot exclude four edge episodes" % span)
    low = quartile * span
    eligible = tuple(
        episode
        for episode in range(low + 2, low + span - 2)
        if not is_boundary(episode) and not is_settlement(episode)
    )
    if len(eligible) < len(FAULT_CLASSES):
        raise ApparatusError(
            "quartile %d of horizon %d offers %d eligible episodes for %d fault classes"
            % (quartile, horizon, len(eligible), len(FAULT_CLASSES))
        )
    return eligible


def _schedule_digest(salt: bytes, horizon: int, class_byte: int, quartile: int, counter: int) -> bytes:
    return hashlib.sha256(
        SCHEDULE_DOMAIN
        + salt
        + horizon.to_bytes(4, "big")
        + bytes([class_byte])
        + quartile.to_bytes(4, "big")
        + counter.to_bytes(4, "big")
    ).digest()


def build_schedule(salt: bytes, horizon: int) -> dict[str, Any]:
    """Materialize the fault schedule. The budget stays constant at eight faults per horizon."""
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
            span = ACTIVE_RECORDS if fault_class == "operational" else DEFERRED_SLOTS
            counter = 0
            while True:
                if counter > 1024:
                    raise ApparatusError(
                        "schedule generator exhausted quartile %d of horizon %d"
                        % (quartile, horizon)
                    )
                digest = _schedule_digest(salt, horizon, class_index, quartile, counter)
                episode = eligible[int.from_bytes(digest[:8], "big") % len(eligible)]
                target = digest[9] % span
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
        "monitor_slots_per_boundary": MONITOR_SLOTS_PER_BOUNDARY,
        "faults": faults,
    }
    schedule["schedule_sha256"] = digest_of(schedule)
    return schedule


def assert_schedule_taxonomy(schedule: Mapping[str, Any]) -> None:
    faults = list(schedule.get("faults") or ())
    horizon = int(schedule["horizon"])
    if len(faults) != len(QUARTILES) * len(FAULT_CLASSES):
        raise ApparatusError("horizon %r carries %d faults" % (horizon, len(faults)))
    episodes = [row["episode"] for row in faults]
    if len(set(episodes)) != len(episodes):
        raise ApparatusError("horizon %r reuses an injection episode" % (horizon,))
    for quartile in QUARTILES:
        allowed = set(eligible_episodes(horizon, quartile))
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
            if rows[0]["episode"] not in allowed:
                raise ApparatusError("fault %r falls outside its eligible window" % (rows[0],))


def monitor_window(boundary_index: int, *, arm: str, salt: bytes) -> tuple[int, ...]:
    """The slots this arm inspects at this boundary, at a budget identical across arms.

    The structured cursor is a pure function of the boundary index, so an ablation cannot inspect a
    different set for a reason unrelated to the capability it removed. The matched control spends the
    same budget on slots drawn from the salt, which is what makes "the structure is worth its budget"
    a claim that a schedule can refute.
    """
    budget = min(MONITOR_SLOTS_PER_BOUNDARY, DEFERRED_SLOTS)
    if arm == "random_audit":
        chosen: list[int] = []
        counter = 0
        while len(chosen) < budget:
            digest = hashlib.sha256(
                AUDIT_DOMAIN
                + bytes(salt)
                + boundary_index.to_bytes(4, "big")
                + counter.to_bytes(4, "big")
            ).digest()
            slot = digest[0] % DEFERRED_SLOTS
            if slot not in chosen:
                chosen.append(slot)
            counter += 1
            if counter > 1024:  # pragma: no cover - unreachable for budget < DEFERRED_SLOTS
                raise ApparatusError("random audit could not fill its budget")
        return tuple(sorted(chosen))
    start = (boundary_index * budget) % DEFERRED_SLOTS
    return tuple(sorted((start + offset) % DEFERRED_SLOTS for offset in range(budget)))


class Evaluator:
    """The only holder of ground truth, recomputed under the v3 cadence."""

    def __init__(self, horizon: int) -> None:
        self.horizon = horizon
        shadow = Body()
        self.expected: dict[int, int] = {}
        for episode in range(horizon):
            shadow.work(episode)
            if is_settlement(episode):
                self.expected[episode] = shadow.settle()

    def diverges(self, episode: int, emitted: int | None) -> bool:
        if emitted is None:
            return False
        return emitted != self.expected[episode]


def arm_capabilities(arm: str) -> dict[str, bool]:
    if arm not in ARMS:
        raise ApparatusError("unfrozen arm %r" % (arm,))
    return {
        "works": arm != "idle_floor",
        "monitor": arm in ("full", "no_checkpoint", "random_audit"),
        "checkpoint": arm in ("full", "no_constraint_monitor", "random_audit"),
    }


def run_arm(arm: str, schedule: Mapping[str, Any], salt: bytes) -> dict[str, Any]:
    """Run one arm. Detection is always recorded before recovery."""
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
    covered_since_checkpoint: set[int] = set()
    completed: set[int] = set()
    boundary_index = 0

    detected: dict[str, set[str]] = {"operational": set(), "quiescent": set()}
    erased_undetected: set[str] = set()
    injected_quiescent: set[str] = set()
    divergences: list[frozenset[str]] = []
    silent_divergences = 0
    suppressed_outputs = 0
    emitted_outputs = 0
    recovery_attempts = 0
    recovery_successes = 0
    checkpoints_written = 0
    monitor_invocations = 0
    slots_inspected = 0

    def sweep(window: Iterable[int]) -> tuple[int, ...]:
        """Inspect only the budgeted slots and attribute what is newly visible."""
        nonlocal monitor_invocations, slots_inspected
        monitor_invocations += 1
        window = tuple(window)
        slots_inspected += len(window)
        covered_since_checkpoint.update(window)
        violating = set(body.violating_slots())
        fresh = tuple(slot for slot in window if slot in violating and slot not in reported_slots)
        if fresh:
            for row in pending:
                if row["fault_class"] == "quiescent" and int(row["target"]) in fresh:
                    detected["quiescent"].add(row["fault_id"])
            reported_slots.update(fresh)
        return fresh

    def recover(episode: int, *, closing: bool = False) -> bool:
        nonlocal recovery_attempts, recovery_successes, pending
        recovery_attempts += 1
        if checkpoint is None:
            return False
        # A rollback undoes corruption the arm never saw as well as corruption it did. Those faults
        # were neither detected nor harmful, so counting them against coverage would understate the
        # monitor and counting them for it would overstate it. They are tracked separately.
        # A closing repair is not an erasure. A fault that reached an output and was only
        # cleaned up once the horizon ended did matter, and counting it as never having happened
        # would make the retention metric vacuous -- which is how v2 stopped being able to fail.
        if not closing:
            for row in pending:
                if (
                    row["fault_class"] == "quiescent"
                    and row["fault_id"] not in detected["quiescent"]
                ):
                    erased_undetected.add(row["fault_id"])
        body.restore(checkpoint)
        recovery_successes += 1
        reported_slots.clear()
        quarantined.clear()
        covered_since_checkpoint.clear()
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
                for row in pending:
                    if (
                        row["fault_class"] == "operational"
                        and int(row["target"]) == violation.index
                    ):
                        detected["operational"].add(row["fault_id"])
                if capabilities["monitor"]:
                    sweep(monitor_window(boundary_index, arm=arm, salt=salt))
                if recover(episode):
                    if body.work(episode, quarantined) is not None:
                        completed.add(episode)
                else:
                    quarantined.add(violation.index)
                    if body.work(episode, quarantined) is not None:
                        completed.add(episode)

        for row in faults_by_episode.get(episode, ()):
            if capabilities["works"]:
                apply_fault(body, row)
                pending.append(dict(row))
                if row["fault_class"] == "quiescent":
                    injected_quiescent.add(row["fault_id"])

        boundary = is_boundary(episode)
        settlement = is_settlement(episode)
        fresh: tuple[int, ...] = ()

        if boundary and capabilities["works"]:
            if capabilities["monitor"]:
                fresh = sweep(monitor_window(boundary_index, arm=arm, salt=salt))
                if fresh:
                    recover(episode + 1)
            boundary_index += 1

        if settlement and capabilities["works"]:
            if reported_slots or quarantined:
                suppressed_outputs += 1
            else:
                emitted = body.settle()
                emitted_outputs += 1
                if evaluator.diverges(episode, emitted):
                    silent_divergences += 1
                    divergences.append(
                        frozenset(
                            row["fault_id"]
                            for row in pending
                            if row["fault_class"] == "quiescent"
                            and row["fault_id"] not in detected["quiescent"]
                        )
                    )

        # An arm may only checkpoint what it can verify. Every working arm verifies the operational
        # plane; a monitor-carrying arm has seen at most its budgeted window of the quiescent one, so
        # it can and will snapshot corruption it has not looked at. That is a real failure mode of a
        # bounded audit, not an implementation shortcut, and it is one of the ways v3 can lose.
        if boundary and capabilities["checkpoint"] and capabilities["works"]:
            verified = (
                not capabilities["monitor"]
                or covered_since_checkpoint >= set(range(DEFERRED_SLOTS))
            )
            if not body.damaged_active() and not reported_slots and verified:
                checkpoint = body.snapshot()
                checkpoint_episode = episode
                checkpoints_written += 1
                covered_since_checkpoint.clear()

    # Closing audit. A bounded monitor never guarantees it has looked everywhere, so without a full
    # sweep before the horizon is declared complete, residual corruption is nonzero by construction
    # and the retention clause is unsatisfiable rather than tested. A real system audits everything
    # before declaring done; what survives that sweep is what "retention" should mean.
    closing_detections = 0
    if capabilities["works"] and capabilities["monitor"]:
        # A fault found only by the closing sweep was not found before harm, so pre-harm counts are
        # restored afterwards. The sweep may repair; it may not flatter coverage.
        before = set(detected["quiescent"])
        closing = sweep(range(DEFERRED_SLOTS))
        closing_detections = len(detected["quiescent"] - before)
        detected["quiescent"] = before
        if closing:
            recover(horizon, closing=True)

    never_detected = injected_quiescent - detected["quiescent"] - erased_undetected
    # A divergence counts as unrecovered when a fault that was live and unseen when the output was
    # emitted was still never seen by the horizon's end. A divergence caused by a fault the monitor
    # went on to find and repair is a latency cost, not a retention failure.
    unrecovered_silent_divergences = sum(
        1 for live in divergences if live & never_detected
    )

    residual = (
        len(body.violating_slots()) + len(quarantined) if capabilities["works"] else 0
    )
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
        "quiescent_faults_never_detected": len(never_detected),
        "closing_audit_detections": closing_detections,
        "silent_divergent_outputs": silent_divergences,
        "unrecovered_silent_divergent_outputs": unrecovered_silent_divergences,
        "emitted_outputs": emitted_outputs,
        "suppressed_outputs": suppressed_outputs,
        "recovery_attempts": recovery_attempts,
        "recovery_successes": recovery_successes,
        "residual_corruption": residual,
        "completed_work_items": len(completed),
        "checkpoint_count": checkpoints_written,
        "monitor_invocation_count": monitor_invocations,
        "slots_inspected": slots_inspected,
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
        "arms": {arm: run_arm(arm, schedule, salt) for arm in ARMS},
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


__all__ = [
    "APPARATUS_VERSION",
    "ARMS",
    "BOUNDARY_PERIOD",
    "DEVELOPMENT_SALT",
    "GENERATOR_VERSION",
    "HORIZONS",
    "MONITOR_SLOTS_PER_BOUNDARY",
    "SETTLEMENT_PERIOD",
    "Evaluator",
    "arm_capabilities",
    "assert_schedule_taxonomy",
    "build_schedule",
    "canonical_json",
    "digest_of",
    "eligible_episodes",
    "is_boundary",
    "is_settlement",
    "monitor_window",
    "run_arm",
    "run_campaign",
    "run_horizon",
]
