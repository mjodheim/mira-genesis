# M121 / H66 — preregistration: does a boundary monitor earn coverage where corruption stays quiet?

**FROZEN BEFORE IMPLEMENTING OR MATERIALIZING THE SHIFT HARNESS.**

Written before any M121 harness code, any body, any schedule and any observation exists. The
schedule salt in `PROTOCOL.json` was drawn before this document was finished and before any
implementation was begun.

## Status at the time of writing

- H66 is **not frozen** in the sense of an owner-authorised protocol. No harness exists, no schedule
  is materialized, no arm has run.
- **No publication disposition is recorded for M121.** `docs/IP_REVIEWS/M121_PUBLICATION_REVIEW.md`
  is prepared for the owner and records no decision. Per `AGENTS.md` §2 and §3, enabling
  implementation stops here until that decision exists.
- M077 is closed as a valid negative under **D043** and is not reopened, repaired, rerun or
  relabelled by anything below.

## Why this milestone, and why now

`MIRA_GENERALITY_CRITERIA.md` records ten gates. Nine carry evidence of some kind. **G7 is the only
one recorded `open`** — no human-hour task-horizon evaluation exists, and the single milestone that
addressed any part of it returned a negative.

That negative is the reason this milestone has a shape at all. D043 did not merely record a failure;
it wrote the successor's constraint:

> A successor may not simply add horizons, faults or invariants to this body; it must introduce
> corruption that can stay quiescent indefinitely, or a body whose operations do not guard the
> corrupted state.

and M077's own result adds:

> A successor must not reuse this schedule or relabel the same body as new evidence.

Both are binding here. M121 is not a bigger M077.

## What M077 established, and the hole it left

M077 asked whether detection and restoration are separable mechanisms across increasing
episode-count horizons. Its `no_checkpoint` ablation behaved exactly as preregistered: restoration
dropped to 0.00 at every horizon while detection stayed numerically identical. Its
`no_constraint_monitor` ablation did not: it lost **one** fault out of 32, at the longest horizon
only, and nothing at the other three.

The reason is stated in its result and is the finding: a silently corrupted pool keeps being written
to, the corruption reaches an operation that cannot complete, and the body raises on its own.
**In that body the boundary monitor was redundant with operational failure.** It purchased detection
latency, not coverage.

That is a statement about a body in which every corruption eventually touches a guarded operation.
The complementary regime is untested, and it is the one that matters for long-horizon autonomy: an
agent running unattended does not mainly fail by crashing. It fails by **continuing, and being
wrong** — and nothing in the operation itself announces it.

## H66 — the falsifiable claim

**H66.** In a body where corruption can remain quiescent — where a corrupted region is not read by
any guarded operation, and where reading it produces a wrong result rather than an impossible one —
a periodic boundary monitor purchases **coverage** and not merely latency. Removing it leaves silent
corruption undetected, and the quantity of undetected corruption **grows with the horizon**.

Two sub-claims, and the design exists to make each able to fail independently.

## The 2×2, and why it is not a tautology

The obvious way to get a positive here is to build a body in which corruption is quiescent by
construction, and then observe that the monitor is necessary. That would be building the answer into
the apparatus, and it is exactly the move D043 warns about — a change shaped to make an arm comply.

So the fault schedule carries **both classes**, in proportions fixed by this document before the
body exists:

| class | definition | M077 analogue |
|---|---|---|
| **operational** | corrupts state that a guarded operation will read during the shift; reading it makes the operation impossible | slot-type corruption, journal truncation, capacity spike |
| **quiescent** | corrupts state no guarded operation reads during the shift; when it is eventually read, the operation **succeeds with a wrong result** | none — M077 had no such fault, which is why its monitor was redundant |

That gives two predictions, each falsifiable, and the hypothesis is their **conjunction**:

1. **On operational faults**, `no_constraint_monitor` detects at parity with `full` at every horizon.
   This reproduces M077 inside the new body and is the internal positive control. If it fails, the
   body is not comparable to M077's and the run is **uninterpretable**, not positive.
2. **On quiescent faults**, `no_constraint_monitor` detects strictly fewer than `full`, and the gap
   **widens monotonically with horizon**.

If (2) fails, the monitor buys latency here too, D043's teaching generalises beyond its body, and
M121 is a second valid negative. That is a real finding and it will be reported as one.

## The primary endpoint: divergence, measured from state and never from self-report

The lineage completes work items and records what it completed. A quiescent fault does not stop it;
it makes a later operation **succeed with a wrong result**.

The primary measure is therefore the count of work items whose **recorded outcome diverges from
ground truth the lineage cannot read**. G6 states the rule this follows: task completion is measured
from environment state, never from the agent's self-report. G7's `verification_quality` component is
exactly this quantity, and M077 could not measure it because every one of its faults eventually
announced itself.

A lineage that reports success on a corrupted item has failed that item, however clean its journal
looks.

## Arms

M077's arm structure is inherited because it worked, and because reusing a structure whose
dissociation logic is already validated is cheaper than inventing one.

| arm | holds | must lose |
|---|---|---|
| `full` | checkpoint + boundary monitor | — |
| `no_checkpoint` | monitor only | restoration; detection must stay **numerically identical** to `full` |
| `no_constraint_monitor` | checkpoint only | the audit; fault recovery must stay **numerically identical** to `full` on operational faults |
| `idle_floor` | neither, and emits no transition | must complete **zero** work items |

An ablation that degrades both capabilities proves only that removing machinery hurts. The retained
half of each contrast is fixed here, before the harness exists, so it cannot be inspected and then
described afterwards. `idle_floor` exists because a lineage that does nothing trivially corrupts
nothing, and a zero-divergence score must not be earnable by inactivity.

## Horizons

32, 128, 512 and 2048 episodes — **the same ladder as M077**, deliberately, so the operational
control is comparable across the two milestones.

Everything else about the schedule is fresh. The salt in `PROTOCOL.json` was drawn for this
milestone; M077's salt, schedule and body are not reused, and the M077 artifacts are read only as a
closed record.

The long-horizon prediction is specifically that the **quiescent** gap grows: at 32 episodes a
monitor and no monitor may look similar, and by 2048 they must not. A result that is flat across
horizons does not support H66 even if the gap is non-zero, because the claim is about horizon.

## Human-equivalent horizons: refused, and this time mechanically

M077 refused the human-equivalent component of G7 in prose, correctly, and its claim boundary held.
M121 refuses it in **code**.

The result schema carries no field that can express wall-clock duration, human-equivalent time or a
fitted horizon, its field list is an enforced allowlist, and the checker fails closed if such a
field ever appears — the same discipline M120's pre-seal adequacy gate uses for its information
boundary. Calibrating a human-equivalent horizon requires human baselines this project does not
have, and `MIRA_GENERALITY_CRITERIA.md` records that requirement as an **external blocker** rather
than a pending task.

Horizons here are **episode counts**. Nothing in this experiment may be reported as a fitted time
horizon, and no positive result moves the human-equivalent component of G7.

## Instrument-abort conditions

The run stops without a scientific verdict, recorded as `instrument_aborted`, if any of these holds:

- the operational positive control fails — `no_constraint_monitor` does not detect at parity with
  `full` on operational faults, which would mean the new body is not comparable to M077's;
- `no_checkpoint` loses detection as well as restoration, or `no_constraint_monitor` loses
  restoration as well as detection, which would mean neither ablation isolates one capability;
- `idle_floor` completes work, which would mean the degenerate strategy is not degenerate;
- a quiescent fault is observed to raise on its own, which would mean it was not quiescent and the
  fault taxonomy is wrong;
- the schedule does not rebuild byte-identically from the committed salt.

An instrument abort is **not** a negative result and may never be reported as one.

## Safety boundary

Inherited from M077 unchanged. The lineage receives compute and in-process memory only. No arm may
reach a network, repository write path, credential, deployment path, permission interface or
physical actuator. Faults are mutations of an in-memory pool, never of a real filesystem, process or
device. No existing isolation or safety policy is weakened. Track A: no external model, no network,
no external task, no third-party attestation.

## Claim boundary

A fully positive result would establish, **within one project-authored in-memory body**, that a
periodic boundary audit purchases coverage against corruption that does not announce itself, and
that the coverage it purchases grows in value with the horizon.

It would establish none of the following, and will not be reported as any of them:

- a human-equivalent task horizon, or any fitted time horizon;
- long-horizon autonomy in a real environment;
- a cost model in money, energy or human-equivalent labour;
- Genesis Gate 2 or Gate 3 evidence;
- closure of G7, which requires the human-equivalent ladder this milestone explicitly refuses;
- any AGI evidence.

**G7 would remain open.** The most this milestone can do is move G7's evidence line from `open` to a
bounded partial entry, and say precisely what is still missing.

## What this milestone does not touch

The three requirements `MIRA_GENERALITY_CRITERIA.md` records as **external blockers** — a
human-maintained sealed bank, independent reproduction, and external adversarial audit — are not
addressed, reduced or approached by anything here. Each requires a person outside the project. No
internal result, including a fully positive M121, may be read as progress toward them.

## Amendment log

Amendments will be listed here rather than folded in silently.

*No amendments.*
