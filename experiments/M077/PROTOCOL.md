# M077 long-horizon recovery and constraint retention protocol

**FROZEN BEFORE IMPLEMENTING OR MATERIALIZING THE SHIFT HARNESS.**

## What this does and does not attempt

`MIRA_GENERALITY_CRITERIA.md` records G7 as open, and asks for two different things at once. It asks
for increasing **human-equivalent** task horizons — ten minutes, one hour, four hours, one day — and
it asks for a record containing intervention count, recovery after injected faults, constraint
retention, verification quality and cost.

This experiment addresses the second list and deliberately refuses the first. Calibrating a
human-equivalent horizon requires human baselines this project does not have, and inventing a
conversion from episodes to hours would be the kind of relabelling the whole register exists to
prevent. Horizons here are **episode counts**. Nothing in this experiment may be reported as a
fitted time horizon, and a positive result does not move the human-equivalent component of G7.

## Falsifiable claim

One persistent deterministic lineage runs a shift of work episodes over a sixteen-slot typed pool
with an append-only digest-chained journal. At every episode boundary four invariants must hold:
correct slot typing, unbroken journal chain, respected capacity, and monotone completed-work count.

Faults are injected at precommitted positions: slot-type corruption, journal truncation, capacity
spike and stale checkpoint. The lineage must detect each one, recover from its own checkpoint and
continue, with **zero interventions**.

At horizons of 32, 128, 512 and 2048 episodes the full arm must record zero unrecovered faults, zero
undetected violations, zero interventions, complete work and exact replay — and must not degrade as
the horizon grows. A retention result that holds at 32 and fails at 2048 is negative, not partial.

## The two ablations must each lose exactly one capability

This is the part that makes the result causal rather than descriptive.

- `no_checkpoint` removes recovery. It must show unrecovered faults, and its violation detection must
  stay **numerically identical** to the full arm.
- `no_constraint_monitor` removes detection. It must show undetected violations, and its fault
  recovery must stay **numerically identical** to the full arm.

An ablation that degrades both capabilities proves only that removing machinery hurts. The retained
half of each contrast is preregistered here, before the harness exists, precisely so it cannot be
inspected and then described afterwards.

## Why an idle floor arm exists

A lineage that emits no transition trivially violates nothing. The `idle_floor` arm measures that
degenerate strategy so a zero-violation score cannot be mistaken for competence. It must complete
zero work items.

## Schedule materialization

`PROTOCOL.json` holds one 32-byte salt drawn before any harness code existed. Work items, target
slots, record types, fault positions and fault kinds derive only from that salt, the horizon length
and a deterministic index. Every fault kind must appear at least once per horizon. The materialized
schedule is committed as a separate immutable artifact before any arm result is recorded.

## Safety boundary

The lineage receives compute and in-process memory only. No arm may reach a network, repository
write path, credential, deployment path, permission interface or physical actuator. Faults are
mutations of an in-memory pool, never of a real filesystem, process or device. No existing isolation
or safety policy is weakened.

## Claim boundary

A positive result establishes bounded unattended fault recovery and constraint retention across
increasing episode-count horizons, with each mechanism causally isolated. It establishes no
human-equivalent horizon, no real-environment autonomy, no Genesis Gate 2 or Gate 3 evidence and no
AGI claim, and it does **not close G7**. The pool, faults and invariants are project-authored, so
this is development evidence of the same kind as M072, M073 and M076, and it requires independent
reproduction before stronger language is used.
