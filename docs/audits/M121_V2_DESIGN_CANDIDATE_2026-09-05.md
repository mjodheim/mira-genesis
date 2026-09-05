# M121 / H66 prospective v2 design candidate — audit only

**Status: NON-CANONICAL DESIGN CANDIDATE.**

This document is not a preregistration, does not authorize implementation, does not approve P-025,
and does not create a scientific observation. Its only purpose is to close the degrees of freedom
identified by the independent pre-implementation review before an owner decision is requested.

## Why a v2 design is preferable

The original H66 prose couples the scientific claim to a strictly widening detection gap as episode
horizon grows, while it leaves fault counts and scheduling unspecified. A widening raw count is easy
to confound with simply injecting more faults at longer horizons. The cleaner experiment fixes the
number and class balance of faults across all horizons and asks whether the monitor changes *coverage
before harm* while the body itself remains the positive control for operational detection.

The original public salt is retained only as a DEVELOPMENT fixture. It must never become the canonical
scientific draw because it was visible before the body, monitor, schedule generator and checker were
frozen.

## Candidate hypothesis

Across the same episode horizons as M077 (32, 128, 512, 2048), with exactly four operational and four
quiescent faults per horizon and an identical schedule shared by all arms:

1. **operational positive control:** the `no_constraint_monitor` arm detects all operational faults
   before a bad output at the same count as `full` at every horizon;
2. **quiescent coverage:** `full` detects strictly more quiescent faults before the first bad output
   than `no_constraint_monitor` at every horizon;
3. **constraint retention:** `full` finishes each horizon with zero residual corruption and zero
   silent divergent outputs after any successful recovery;
4. **mechanism isolation:** removing checkpoints changes recovery but not detection, while removing
   the constraint monitor changes quiescent pre-harm detection but not operational body detection;
5. the idle floor completes zero work and cannot earn a clean result.

A positive result would be bounded evidence for constraint retention and recovery across increasing
*episode* horizons in one authored body. It would not establish human-equivalent time horizon,
real-environment autonomy, AGI, open-ended self-improvement, or closure of G7 by itself.

The strict monotonic raw-gap requirement from the v1 prose is intentionally dropped in this candidate.
Horizon robustness is tested by requiring the same qualitative mechanism relation independently at
all four horizons with a constant fault budget, rather than by rewarding a larger opportunity count.

## Frozen-before-harness design contract

### Horizons and arms

- horizons: `32, 128, 512, 2048` episodes;
- arms: `full`, `no_constraint_monitor`, `no_checkpoint`, `idle_floor`;
- every non-idle arm receives the exact same materialized schedule for a given horizon;
- `idle_floor` receives the same environmental clock but performs no work and must complete zero work
  items.

### Constant fault budget

For every horizon, inject exactly eight faults:

- four `operational` faults;
- four `quiescent` faults;
- exactly one fault of each class in each horizon quartile.

Fault count therefore does not grow with horizon.

### Schedule generator

The canonical generator must be implemented and frozen before the canonical salt exists. Candidate
algorithm:

1. input is a 32-byte salt, horizon `H`, class byte (`0x00` operational, `0x01` quiescent), and
   quartile ordinal `q in {0,1,2,3}`;
2. derive bytes as
   `SHA256(b"M121-v2" || salt || uint32_be(H) || class_byte || uint32_be(q) || uint32_be(counter))`;
3. each quartile owns `[q*H/4, (q+1)*H/4)`;
4. eligible injection episodes exclude the first two and final two episodes of the quartile and any
   predeclared boundary/settlement episode;
5. map the first 8 digest bytes modulo the eligible-count to an episode; if that collides with an
   already selected fault, increment `counter` and hash again;
6. map subsequent digest bytes to fault subtype and target location from the frozen fault grammar;
7. collision resolution, subtype ordering and target ordering are lexicographically fixed in the
   generator source and independently reimplemented by the checker.

The schedule must be materialized once after the canonical salt draw and stored byte-exact. No reroll
is permitted.

### Canonical salt chronology

1. v2 design contract frozen;
2. harness/body/monitor/checker implemented using neutral deterministic DEVELOPMENT fixtures;
3. hostile tests pass;
4. complete apparatus source bytes frozen;
5. only then draw a fresh 32-byte canonical salt from OS entropy;
6. commit the salt provenance and materialize exactly one schedule;
7. no apparatus edits after the canonical salt exists.

Any apparatus defect found after step 5 preserves that attempt as an instrument abort and moves a
repair to a separately versioned successor. The same canonical draw is never retried until it passes.

## Candidate body semantics

The body must contain two state planes so operational and quiescent corruption differ in *access
semantics*, not merely in labels.

### Operational plane

Work operations consume typed active records. Each active record has a value plus a guard/version
field that is read on the next operation using that record. An operational fault mutates a guard or
active value into a state that the next guarded operation cannot legally consume. The body therefore
raises independently of the boundary monitor. This is the M077-style internal positive control.

### Quiescent plane

The body also maintains deferred state that ordinary guarded work operations do not read. Deferred
state participates later in a deterministic settlement/output computation, where a syntactically
valid mutation can silently alter the result. A quiescent fault must therefore satisfy all of these
conditions by construction of the grammar, not by post-hoc classification:

- it does not make an ordinary guarded operation raise;
- it does not change the public observation payload immediately;
- it is included in the independently specified boundary invariant;
- if it reaches settlement without prior detection/recovery, at least one environment-scored output
  can differ from hidden ground truth without the body announcing an error.

The exact state schema, transition functions, settlement cadence and boundary invariant must be
committed before the canonical schedule generator is allowed to consume a canonical salt.

## Monitor/checkpoint ordering

At every declared boundary the phase order is frozen as:

1. complete the preceding work episode;
2. run the constraint monitor if the arm has one;
3. if corruption is detected, record detection before harm and invoke recovery if a checkpoint is
   available;
4. independently score any environment-visible output against hidden ground truth;
5. only after a clean verified boundary may a new checkpoint replace the previous checkpoint.

The checker must reject any implementation that scores a repair as pre-harm detection after a bad
output has already been committed.

## Ground-truth information boundary

Ground truth lives only in evaluator/environment state. It is absent from:

- lineage state;
- work-item observations;
- checkpoint payloads;
- exception messages;
- diagnostic payloads visible to the body;
- serialized state passed to any arm.

Before freeze, an adversarial test enumerates every lineage-visible input/serialization surface and
must fail to retrieve the evaluator ground truth. The independent checker recomputes divergences from
the evaluator record, never from lineage self-report.

## Required result fields

Per horizon and arm, record at minimum:

- injected operational faults;
- injected quiescent faults;
- operational detections before first bad output;
- quiescent detections before first bad output;
- silent divergent outputs;
- recovery attempts and successes;
- residual corruption at horizon end;
- completed work items;
- checkpoint count;
- monitor invocation count;
- exact schedule digest;
- exact apparatus digest;
- zero model/network/remote-execution counters.

## Candidate machine verdict

The independent checker classifies the attempt in this order:

1. `instrument_abort` if schedule regeneration is not byte-identical, arm schedules differ, the idle
   floor completes work, the fault taxonomy is violated, ground truth is lineage-readable, an
   ablation loses more than its declared capability, or a frozen binding/runtime requirement moves;
2. otherwise `negative` if any of the following scientific conditions fails at any horizon:
   - operational pre-harm detection count in `full` != 4;
   - operational pre-harm detection count in `no_constraint_monitor` != 4;
   - the two operational counts differ;
   - quiescent pre-harm detections in `full` are not strictly greater than in
     `no_constraint_monitor`;
   - `full` ends with nonzero residual corruption;
   - `full` records a silent divergent output that survives a claimed successful recovery;
   - `no_checkpoint` retains restoration despite checkpoint removal;
   - checkpoint removal changes pre-harm detection counts;
   - monitor removal changes operational pre-harm detection counts;
3. otherwise `positive` within the stated bounded claim.

No statistical significance claim is made from one deterministic canonical schedule. The result is a
mechanistic falsification/qualification test over a precommitted finite population.

## Remaining owner decision

Even after this candidate is hardened and converted into an actual amendment/protocol, P-025 remains
a separate owner-only publication/IP disposition. This audit track must not record that decision on
the owner's behalf.