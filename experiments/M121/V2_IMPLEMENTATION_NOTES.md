# M121 / H66 — v2 apparatus implementation notes

**Status: DEVELOPMENT apparatus. Not a preregistration, not a protocol, not a scientific result.**

These notes record what was built for step two of the canonical chronology in
[`../../docs/audits/M121_V2_DESIGN_CANDIDATE_2026-09-05.md`](../../docs/audits/M121_V2_DESIGN_CANDIDATE_2026-09-05.md),
and — more importantly — **where the implementation departs from that candidate's text**. The
candidate is explicitly non-canonical, so closing its open degrees of freedom is the purpose of this
phase. Recording the departures is not optional: an apparatus that quietly diverged from its own
design contract would be exactly the defect the candidate was written to prevent.

Nothing here draws a canonical salt, records a scientific observation, or advances G7. P-025 resolves
publication governance only; the canonical salt, one-shot run, reveal and result acceptance remain
owner-gated.

## What exists

| Artifact | Role |
|---|---|
| `metamorphosis/m121_long_horizon_v2.py` | body, constraint monitor, checkpoints, schedule generator, evaluator, four arms |
| `scripts/run_m121_v2_development.py` | DEVELOPMENT runner on the public fixture salt; accepts no salt argument and draws no entropy |
| `scripts/check_m121_v2_result.py` | independent checker; reimplements the generator rather than importing it |
| `tests/test_m121_v2_harness.py` | 72 hostile offline tests |
| `V2_DEVELOPMENT_RESULT.json` | the fixture-salt campaign record, for reference and replay |

## Chronology position

1. v2 design contract frozen — done, in the audit document;
2. **apparatus implemented against neutral DEVELOPMENT fixtures — this work;**
3. **hostile tests pass — this work;**
4. complete apparatus source bytes frozen — *not done*;
5. canonical 32-byte salt drawn from OS entropy — *owner only, not done*;
6. salt provenance committed, exactly one schedule materialized — *not done*;
7. no apparatus edits after step 5.

Steps 4 onward are deliberately not reached. The apparatus is still editable, which is precisely why
no canonical salt may exist yet.

## Departures from the design candidate

Each of the four corrections below removes a way the apparatus could have returned `negative` for an
**instrument** reason rather than a scientific one — that is, a false refutation of H66. Each was
found by running the arms, not by reading the text. They are prospective: they are recorded here
before any canonical salt exists, and they are the owner's to accept or reverse.

### 1. The guarded read covers the operational plane

*Candidate:* "an operational fault mutates a guard or active value into a state that the next guarded
operation cannot legally consume."

*Implemented:* every work episode verifies all non-quarantined active records before doing its
update, so a corrupted record is refused by the very next operation.

*Why:* with a strict per-record reading, work reaches a given record once every `ACTIVE_RECORDS`
episodes, so an operational fault could lie dormant across a boundary. A rollback triggered by an
unrelated detection would then erase it before it was ever seen, costing an operational detection and
failing the positive-control condition. The candidate's phrase "the next guarded operation" already
implies immediacy; this makes it literal.

### 2. The quiescent redundancy is incremental, never recomputed

*Candidate:* the boundary invariant covers deferred state.

*Implemented:* work advances `deferred_tags[slot]` by the same increment it adds to
`deferred_values[slot]`, instead of recomputing the tag from the stored value.

*Why:* recomputing the tag from the value lets the next ordinary write to that slot launder a
corrupted slot clean — the invariant is restored over corrupt data, the monitor sees nothing, and the
settlement output diverges silently *in the `full` arm*. This was observed before the fix: `full`
reached 0/4 quiescent detections with 4 silent divergences at horizon 512. It is the single most
dangerous defect found, because it makes the instrument fail in the direction of a false negative
while looking healthy.

### 3. Recovery replays the episodes the rollback lost

*Candidate:* the phase order recovers from a checkpoint; replay is not specified.

*Implemented:* a restore replays episodes from the checkpoint to the current one, so a recovered arm
rejoins the fault-free trajectory.

*Why:* without replay, a recovered arm is permanently behind the evaluator's fault-free trajectory,
so *every* later settlement diverges from ground truth. Divergence would then measure the rollback
rather than the corruption, and `full` would record silent divergent outputs it did not cause.

### 4. Collision resolution covers targets, and rotation is confined to one slot

*Candidate:* "if that collides with an already selected fault, increment `counter` and hash again" —
collision is defined on the episode.

*Implemented:* a candidate fault is rejected if its episode **or** its `(class, target)` pair is
already used; the `deferred_slot_rotation` subtype rotates its own slot's value instead of swapping
with a neighbour.

*Why:* an arm that detects corruption but cannot repair it (the `no_checkpoint` ablation) must
quarantine the damaged record or slot. A second fault on the same target is then invisible, so the
checkpoint ablation loses a detection and the condition "checkpoint removal changes pre-harm
detection counts" fires for an instrument reason. Observed before the fix at horizons 32 and 128.
Four faults never exhaust eight targets, so the constraint is always satisfiable.

## A design consequence worth stating plainly

Detection is recorded **before** recovery on every path, and checkpoint validity is judged by what
each arm can actually see: every working arm verifies the operational plane, only a monitor-carrying
arm verifies the quiescent one. An arm without the monitor therefore checkpoints corrupt deferred
state and cannot repair it later. That asymmetry is the ablation itself, not an implementation
shortcut.

Detection without repair still prevents harm: an arm that has detected corruption it cannot repair
declines to emit a settlement output rather than committing one it knows was computed over corrupt
state. This is what separates the two mechanisms — the monitor buys **coverage before harm**, the
checkpoint buys **repair** — and it is why removing either does not degrade what the other supplies.

## DEVELOPMENT observations

On the public fixture salt, at all four horizons, with a constant eight-fault budget:

| arm | operational | quiescent | silent divergences | residual corruption |
|---|---|---|---|---|
| `full` | 4/4 | 4/4 | 0 | 0 |
| `no_constraint_monitor` | 4/4 | 0 | 2–4 | nonzero |
| `no_checkpoint` | 4/4 | 4/4 | 0 | nonzero, zero successful recoveries |
| `idle_floor` | — | — | — | zero work completed |

**These are fixture numbers and they are not a result.** They say the instrument dissociates as
designed on a salt that was visible while the apparatus was being written. They say nothing about
H66. The candidate is explicit that the public salt must never become the canonical draw, and the
runner enforces that by accepting no salt argument at all.

## What must happen before this can produce evidence

1. Independent hostile review of this apparatus — the project's internal reviewer may perform it, and
   the register must keep labelling that **self-audit**, not an external adversarial audit.
2. Conversion of the candidate into an actual amendment or protocol under the owner's authority.
3. Freezing the complete apparatus source bytes.
4. An owner-drawn canonical salt, after the freeze, with committed provenance.

Even a positive canonical result would be bounded evidence for constraint retention and recovery
across increasing **episode** horizons in one project-authored body. It would not establish
human-equivalent time horizons, real-environment autonomy, or closure of G7, and the episode counts
may not be reported as human-equivalent task horizons.
