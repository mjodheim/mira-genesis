# M121 / H66 — v2 apparatus implementation notes

**Status: DEVELOPMENT apparatus. Not a preregistration, not a protocol, not a scientific result.**

**NOT READY FOR A CANONICAL SALT.** A falsifiability defect is recorded below: every metric the
verdict depends on is constant across every salt, so the instrument can only return `positive`. See
[BLOCKING FINDING](#blocking-finding-the-apparatus-cannot-currently-return-a-negative).

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

**They are also the same numbers on every other salt**, which is the blocking finding recorded
above. Read that section before reading this table as good news: a table that cannot change is a
description of the apparatus, not a measurement of anything.

## BLOCKING FINDING: the apparatus cannot currently return a negative

**Status: this apparatus must not receive a canonical salt.** The finding below was produced by the
same agent that wrote the apparatus, before any canonical draw existed, and it invalidates the
readiness of the instrument rather than any recorded result. Nothing has been spent.

### What was measured

The four arms were run over **200 independently drawn 32-byte salts** at all four horizons, and the
recorded metrics were then compared across **60 salts** to see which of them the salt moves at all.

Every metric the checker's negative conditions consult is **constant across every salt and every
horizon**:

| arm | operational | quiescent | silent divergences | residual | recoveries |
|---|---|---|---|---|---|
| `full` | 4 | 4 | 0 | 0 | varies (not consulted) |
| `no_constraint_monitor` | 4 | 0 | varies (not consulted) | varies (not consulted) | 4 |
| `no_checkpoint` | 4 | 4 | 0 | 8 | 0 |
| `idle_floor` | 0 | 0 | 0 | 0 | 0 |

The only quantities the salt moves — `full.recovery_successes`, `no_checkpoint.completed_work_items`
and `suppressed_outputs`, `no_constraint_monitor.silent_divergent_outputs` and
`residual_corruption` — are not consulted by any negative condition.

### Why this matters more than a passing test suite

The canonical chronology exists to stop the project choosing a favourable schedule: freeze the
apparatus, draw a salt afterwards, materialize exactly one schedule, never reroll. That protection
is real. It is also **vacuous here**, because no schedule is unfavourable. The instrument returns
`positive` for every input it can receive.

A result that could not have come out otherwise is not evidence. Spending a scarce, non-replayable
canonical draw on it would produce a `positive` that says nothing about H66, and the fact that it
was correctly frozen, correctly salted and correctly replayed would make it *look* like it did.

M077, the predecessor, returned a **valid negative** on its dissociation hypothesis. This apparatus
cannot. That is a regression in falsifiability, not an improvement in robustness.

### The cause is the four departures, jointly

Each correction above was defensible on its own and each removed a genuine instrument-reason for
failure. Together they removed the experiment's only sources of variance:

1. the whole-plane guarded read makes operational detection immediate **wherever** the fault lands,
   so position stops mattering;
2. the non-launderable redundancy makes quiescent corruption visible **whenever** it lands, so
   timing stops mattering;
3. replay on recovery makes `full` restore completely **always**, so residual corruption and silent
   divergence in `full` are structurally zero;
4. distinct targets remove the masking interference that made detection counts differ.

The honest reading is that the agent which found four ways the instrument could fail for the wrong
reason also removed every way it could fail for the right one, and did not notice until it went
looking for variance rather than for correctness.

### What would restore falsifiability

Directions only; none is chosen here, and the choice is not this agent's to make:

- make detection **latency** decisive by giving boundary and settlement cadences no common factor,
  so a quiescent fault landing in the wrong window reaches an output before the monitor runs;
- give the monitor a **bounded budget** — it inspects a limited number of slots per boundary — so
  where faults land decides coverage;
- allow two faults inside one inter-checkpoint window, so a single checkpoint cannot repair both;
- make the horizon do real work: at present the four horizons produce identical numbers, so the
  experiment does not test horizon robustness at all.

Any such change is an apparatus redesign that must precede a freeze, and it should be reviewed by
someone other than its author before implementation.

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
