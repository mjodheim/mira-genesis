# M077 status

**NEGATIVE RESULT — PRESERVED WITHOUT RETRY. TRACK A, MODEL-FREE.**

- Target: the intervention-count, fault-recovery and constraint-retention components of **G7**.
  The human-equivalent horizon component is explicitly refused, not attempted.
- Horizon unit: episode counts (32, 128, 512, 2048). Never reported as fitted time.
- Preregistered dissociation: **refuted.** `no_constraint_monitor` was required to lose detection at
  every horizon; it loses one fault of 32 at h2048 and nothing elsewhere.
- Cause: silent corruption eventually breaks a guarded operation, so the operational path detects it
  without any boundary audit. The monitor buys latency, not coverage, in this body.
- Sub-result 1 (positive): full arm holds all four invariants, recovers every fault, zero
  interventions, zero residual violations at all four horizons — **no degradation with horizon**.
- Sub-result 2 (positive): `no_checkpoint` drops restoration to exactly 0.00 while detection stays
  numerically identical to the full arm — checkpoint recovery is causally isolated.
- Floor: `idle_floor` completes zero work and still ends with residual violations.
- Schedule commitment `80e92af4…a9d13`; first result `93ecd2d0…d983d9`, attempt 1, no retry.
- Local regressions: 25 passed. Independent checker: `failures: []`. Integrity: clean.
- Gate advance: **none.** G7 stays open.

## Frozen ordering

1. `31b2778` froze `PROTOCOL.json` and `PROTOCOL.md` before any harness code existed; the salt was
   drawn first and schedule content was absent from the freeze.
2. `720bad4` added the harness and recorded both instrument corrections before materialization.
3. The schedule was bound and the result preserved in one pass, attempt 1, with no retry and no
   fault repositioned after an outcome was observed.

## Why this was not iterated into a pass

The first instrument correction moved the failing arm rather than fixing a threshold, which is the
signature of a genuine refutation rather than a defect. A third correction shaped to make
`no_constraint_monitor` comply would have been tuning against an observed outcome, which D041
forbids in spirit and the protocol forbids in text. `check_m077_result.py` fails closed if the
preserved negative is ever silently converted to positive.

## What a successor would need

Not more horizons, more faults or more invariants in this body — that repeats the instrument. A
successor must introduce corruptions that can stay quiescent indefinitely, so that a boundary
monitor has coverage an operational path cannot reach, or move to a body where operations do not
guard the corrupted state. Reusing this schedule is forbidden.
