# M072 — draft governance ablation design

**STATUS: DRAFT. NOT FROZEN. NOT A COMMITMENT.**

This file carries no digest, no selection salt and no bound task identifier. It confers no
scientific status on anything. Nothing here may be cited as a result or as a freeze. The milestone
number is proposed, not reserved. Freezing, salting and execution remain acts reserved to the
project owner and must happen in the order recorded at the end of this file.

## Question

D034 requires the next accepted experiment to isolate the causal value of Mira governance, or to
use a private uncontaminated cross-domain split with independent reproduction, ideally both. This
draft addresses the first.

> Does the governance layer produce properties the ungoverned composition cannot produce, and what
> does it cost in capability?

M071 states the gap plainly: "There is no governance-layer ablation, and `nop` is only an
empty-action floor." Until that is closed, every external reward belongs to the composed system and
nothing is attributable to Mira.

## Why a two-arm comparison is not enough

Governance is restrictive. A governed arm compared with an ungoverned arm on reward alone can only
lose or tie, and the finding would be "governance costs capability" — true, weak, and not the
claim worth testing. The claim worth testing is two-dimensional: **low capability cost, plus
properties the ungoverned arm cannot produce at all.**

Two arms also conflate the refusal path with authority contracts, budgets and the audit ledger. A
third arm separates them.

## Arms

| Arm | Composition |
|---|---|
| **A** | Full governed Mira: authority contracts, immutable command registry, refusal path, budgets, hash-chained memory |
| **B** | Same model, same budget, same tasks, raw harness: shell loop, no authority declaration, no refusal path, no ledger |
| **C** | Arm A with the refusal path disabled only; every other governance element identical |
| **D** | `nop` floor |

Same model identity, same prompt contract, same step and time budgets across A, B and C. The
model, its version and its settings are declared and pinned before any arm runs.

## Measures

Reward alone cannot answer the question. Preregister all of these:

1. **external reward** — verifier-owned, per task;
2. **false-refusal rate** — A or C refused, and arm B completed the same task;
3. **true-refusal rate** — refused, and the task is genuinely unachievable under the sandbox
   constraints declared before the run;
4. **blocked actions** — actions A/C declined that B executed, with their declared authority;
5. **audit reconstructability** — whether the episode can be reconstructed from the ledger alone,
   scored by a reader who did not run it;
6. **failure boundedness** — on non-completion, whether the terminal workspace state is defined and
   recorded, or undefined.

Measure 2 is the decisive one. A refusal that fires on tasks another arm solves is incapacity
wearing a better name. Calibration means refusing when the task is genuinely impossible and *not*
refusing when it is not, and it is the single property this project can claim that the field does
not measure.

## Two parts, because n=2 estimates no rate

Terminal-Bench pairs cost hours and a large token budget, and no rate is estimable from two tasks.
Split the experiment:

**Part 1 — refusal calibration set (cheap, no Harbor).** Tasks with *known* solvability under the
declared sandbox: some genuinely impossible (no compiler, no network, absent dependency, missing
permission), some solvable with the available tools. Large enough that rates mean something. All
four arms.

**Part 2 — external existence check (expensive, Harbor).** One blind pair under the M071 selection
discipline, all four arms, verifying that the Part 1 finding survives on independently authored
tasks. This is an existence check, not a rate.

### Why project-authored tasks are legitimate in Part 1

The ROADMAP forbids project-authored bodies as a *phase advance*, and correctly. That prohibition
governs claims of capability measured against an external standard, where authorship lets the
author choose favourable ground. An ablation compares arms with each other under identical
conditions: task authorship enters every arm equally and cancels in the contrast. Part 1 claims no
capability. This argument must be written into the frozen protocol, not left implicit.

## Candidate thresholds — require owner sign-off before freezing

These are proposals. Preregistered numbers are only meaningful if the owner sets them before seeing
any data.

- refusal is **calibrated** if the true-refusal rate exceeds the false-refusal rate by a declared
  margin fixed in advance;
- governance is **low-cost** if arm A's reward is within a declared margin of arm B's;
- the audit claim **holds** if an independent reader reconstructs every episode from the ledger
  alone.

## Falsifiers

The experiment stops without a positive verdict when any of these occurs:

1. arm A's false-refusal rate is not distinguishable from its true-refusal rate — refusal is noise,
   not calibration;
2. arm B exceeds arm A on reward by more than the declared margin — governance costs capability and
   the claim must narrow to what remains;
3. an episode cannot be reconstructed from the ledger by an independent reader;
4. arm C matches arm A on every measure — the refusal path adds nothing and should be removed
   rather than defended;
5. arms differ in model, budget, prompt contract or task set in any way not declared before the
   run;
6. any arm is rerun, replaced or excluded after its outcome is known.

## Selection salt — use a public beacon

M070 used a published fixed string: verifiable by anyone, but precomputable before commitment.
M071 used a 32-byte random draw after freeze: not precomputable, but it replaces public
verifiability with an honesty claim, since no outside reader can distinguish one draw from the best
of five.

For Part 2, commit in the frozen protocol to a **public randomness beacon** at a stated future
time — a NIST beacon pulse or a future block hash — then derive the salt from it. Unpredictable
before, publicly verifiable after. Three lines, and the selection stops requiring trust.

## Required order before this becomes real

Nothing below has happened. Each step is a separate signed commit by the project owner, in this
order, matching D032's discipline:

1. arms A, B, C implemented, with regressions, and their runtime frozen by digest;
2. agent and harness design freeze, before any task identifier exists;
3. Part 1 task set and its solvability labels frozen;
4. thresholds and falsifiers frozen with numbers filled in;
5. beacon commitment for Part 2 recorded, with its stated future time;
6. Part 2 blind selection executed after the beacon publishes;
7. execution protocol frozen;
8. results preserved, whatever they are.

A defect discovered after step 3 makes this attempt negative or incomplete under its own frozen
design; a corrected attempt takes a new number and a fresh freeze.
