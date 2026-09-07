# M121 / H66 — v3 apparatus: falsifiability restored, and what that exposed

**Status: DEVELOPMENT apparatus. Not a preregistration, not a protocol, not a scientific result.
NOT READY FOR A CANONICAL SALT.**

v2 could not return a negative. v3 was built to fix that, and it does. It also cannot currently
return a **positive**, and the reasons why are hypothesis questions rather than bugs. Both facts are
recorded here before any canonical salt exists. v2 is not edited; its finding is the record of what
went wrong and stays at [`V2_IMPLEMENTATION_NOTES.md`](V2_IMPLEMENTATION_NOTES.md).

## What v3 changes, and why

v3 keeps all four v2 corrections — they were right — and inherits the body, fault grammar and replay
by import. It adds the three things v2 lacked, each chosen to make **fault position decide
outcomes**:

| change | effect |
|---|---|
| coprime cadences (`BOUNDARY_PERIOD=5`, `SETTLEMENT_PERIOD=8`) | most settlements are not boundaries, so a fault landing in the wrong window reaches an output before any audit |
| bounded monitor budget (`MONITOR_SLOTS_PER_BOUNDARY=2` of 8 slots) | whether the corrupted slot is inspected depends on where the fault landed, and coverage accumulates with horizon |
| matched `random_audit` arm | the claim that the structured order is worth its budget can be false on a given schedule |

The monitor cursor is a pure function of the boundary index, so two monitor-carrying arms inspect
the same slots at the same boundaries and an ablation cannot differ for a scheduling reason.

## Falsifiability: restored

Measured over 300 independently drawn development salts at all four horizons.

**Controls are robust, as controls should be — they never failed:**

- `full`, `no_constraint_monitor` and `no_checkpoint` all detect 4/4 operational faults;
- monitor removal does not change operational detection;
- `no_checkpoint` never recovers and always ends with residual corruption;
- the idle floor always completes zero work.

**Treatment clauses genuinely vary with the salt:**

| quantity | v2 | v3 |
|---|---|---|
| `full` quiescent detections before harm | constant 4 | varies 0–4 |
| `full` residual corruption | constant 0 | varies 0–4 |
| `full` unrecovered silent divergences | constant 0 | varies 0–2 |
| horizon effect | none — identical at all four | real: at H=32 `full` detects nothing 18% of the time, at H=2048 1% |

The horizon now does work, in the direction the mechanism predicts: more boundary passes accumulate
more coverage. v2 produced identical numbers at every length and therefore tested nothing about
horizon.

## But it cannot currently pass either

Under the design candidate's clause set, **0 of 300 development salts pass every clause at every
horizon**. Three clauses are responsible, and none of them is an implementation defect.

### Clause 5 — `full` finishes with zero residual corruption — fails ~100%

This clause presupposes an audit that eventually sees everything in time. A **bounded** audit does
not provide that. Three successive apparatus changes were attempted and none made the clause
satisfiable:

1. a closing full sweep before the horizon is declared complete;
2. recovery triggered by that sweep;
3. checkpoints permitted only after a completed audit cycle, so a snapshot cannot carry corruption
   the monitor never inspected.

Each was defensible and each is retained. The clause still fails, which is the finding: **zero
residual corruption and a bounded audit are incompatible.** Either the hypothesis wants an unbounded
audit —
in which case v2's determinism returns — or the retention clause must be stated in terms of what the
audit covered rather than in absolutes.

### Clause 9 — removing the checkpoint does not change detection counts — fails ~99%

The design candidate asserts that removing checkpoints "changes recovery but not detection". In v3
that is **empirically false**, for a real mechanism reason rather than an artifact: a rollback in
`full` undoes corruption the monitor had not yet reached, so that fault is never detected, while
`no_checkpoint` keeps it and detects it later. Recovery and detection are coupled once recovery can
erase.

The apparatus tracks these separately as `erased_undetected`, so a corrected clause could compare
*resolved* faults (detected or erased) rather than detected ones. That is a change to the hypothesis
and is not made here.

### Clause 11 — the structured audit is at least as good as a matched random audit — fails ~78%

This clause is not in the design candidate; it was added in v3 as the equal-budget control the
coverage claim needed. The measured distributions of `full` and `random_audit` are close to
identical at every horizon.

Read carefully, this is a **substantive negative result about the mechanism**, not a defect: at this
budget, round-robin ordering buys nothing over random inspection. A hypothesis that the structure of
the audit matters is, on this evidence, not supported. That deserves to be stated rather than
designed away.

## The knob that must not be tuned

`MONITOR_SLOTS_PER_BOUNDARY` trades falsifiability against passability directly. At 8 of 8 the
audit is unbounded, the apparatus reduces to v2 and every clause passes by construction; at 1–2 of 8
it essentially always fails. Per-clause pass rates over 120 development salts at all four horizons:

| budget | clause 4 | clause 5 | clause 6 | clause 9 | clause 11 | **all** |
|---|---|---|---|---|---|---|
| 1 / 8 | 50% | 0% | 100% | 1% | 22% | **0%** |
| 2 / 8 | 90% | 1% | 100% | 1% | 22% | **0%** |
| 3 / 8 | 96% | 4% | 100% | 8% | 30% | **1%** |
| 4 / 8 | 99% | 0% | 100% | 8% | 27% | **0%** |
| 6 / 8 | 100% | 16% | 100% | 48% | 52% | **9%** |
| 8 / 8 | 100% | 100% | 100% | 100% | 100% | **100%** |

*(Measured before the closing-recovery correction described below, which restored variance to
clause 6; the clause-6 column therefore reads 100% throughout and should be re-measured. Every
other column is unaffected, because that correction only changed how a fault cleaned up after the
horizon ended is attributed.)*

**This table is the central result of the v3 work.** At 8 of 8 the audit is unbounded, the
apparatus is v2, and every clause passes by construction. At any bounded budget the experiment
essentially cannot pass. There is no intermediate setting where the hypothesis is both falsifiable
and has a fair chance of being confirmed: the best is 9% at 6 of 8, which is a coin weighted eleven
to one.

On this evidence the hypothesis as written is **trivially true with an unbounded audit and nearly
always false with a bounded one**, and no setting of *this* knob fixes it.

**That conclusion is drawn from a one-dimensional slice and must not be read as more.** Only
`MONITOR_SLOTS_PER_BOUNDARY` was varied, holding `BOUNDARY_PERIOD`, `SETTLEMENT_PERIOD`,
`DEFERRED_SLOTS`, the eight-fault budget and the injection-window rule fixed at their stated values.
A regime that is both falsifiable and fairly passable may exist elsewhere in that space — for
instance at a slower settlement cadence, which would give a bounded audit more chances per output
without making detection certain. Searching that space is legitimate apparatus design **only if it
is done on stated grounds and before a freeze**; searching it for the setting that makes the
experiment pass is the failure this apparatus exists to avoid, and the distinction is thin enough
that the search should not be run by the author alone.

## A correction found by the tests, recorded because it is the same mistake

The v3 suite contains a test asserting that verdict-bearing metrics vary across salts — written
specifically to catch v2's failure mode. It caught a fresh instance of it in v3.

The closing repair was marking still-undetected faults as *erased*, which is the bookkeeping used
for a rollback that undoes corruption before it mattered. A fault that reached an output and was
only cleaned up once the horizon ended did matter, so treating it as never having happened made
`unrecovered_silent_divergent_outputs` constant at zero — vacuous in exactly the way v2 was.

The closing repair no longer erases history. The lesson is not the fix: it is that an apparatus
author will reintroduce this defect while actively trying to avoid it, and only a test that asserts
*variance* rather than correctness catches it.

**Choosing this value by looking at which setting makes the experiment pass is precisely the failure
this apparatus exists to avoid**, and it is not done here. The value is set at 2 on the stated
ground that a full sweep should take several boundaries so coverage is genuinely partial. Whether
that is the right scientific choice is an owner and reviewer decision, and it must be made before a
freeze and without reference to any canonical outcome.

## What is being asked

1. Clause 5 needs restating, or the audit needs to be unbounded and the experiment loses its
   variance. Which?
2. Clause 9 encodes an assumption this apparatus falsifies. Should it compare resolved faults
   instead, or should the coupling itself become the reported result?
3. Clause 11's near-tie is a real finding. Should the structured-audit claim be dropped?
4. `MONITOR_SLOTS_PER_BOUNDARY` must be fixed on stated grounds before any freeze.

Until these are settled the apparatus stays unfrozen, no canonical salt may be drawn, and neither v2
nor v3 supports any claim about H66. G7 does not move.
