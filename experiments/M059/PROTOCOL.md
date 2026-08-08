# M059 — judging whether the substrate still suits

**Status: PROPOSED — unqualified.**

## Research question

Can the lineage determine, from evidence it gathered itself, that its current substrate cannot
express a capability it needs, that another one can, and move **for that reason** — while
refusing to move when the current substrate suffices?

## What every earlier migration had

An instruction. M048 was told to migrate, M056 to migrate again, M057 and M058 built the path and
discovered the instruction set — but the decision to cross was never the lineage's.

## Why this is not M049

M049 selected one strategy from four frozen candidates, and D016 closed that shape. A lineage
picking a substrate from a menu is the same thing with runtimes substituted.

The difference required here is that **no substrate is globally better**. If one always wins, the
answer is a fact to memorise once rather than a judgement about a situation.

## Two substrates, no ranking

Only the two signature **shapes** are declared, `f64` and `i32`. What either contains is
discovered by scanning the whole single-byte opcode space, as in M058. Nothing describes either
set, and nothing ranks them.

Measured, not assumed:

| | `f64` | `i32` |
|---|---:|---:|
| Operations discovered | 9 | 27 |
| Division | truncating? no — yields fractions | truncating |
| Bitwise, comparisons, shifts | absent | present |

`i32` cannot produce a fractional mean. `f64` has no bitwise operation. Each is inadequate for
something the other handles.

## A timing design was tried and rejected

The obvious first design has the lineage measure which substrate runs a workload faster. It does
not survive measurement, and the attempt is recorded so it is not proposed again.

JavaScript beats WebAssembly at every per-call workload from 1 to 100,000 operations, because
each wasm call crosses a boundary while V8 compiles the JavaScript to a single instruction. With
the loop moved inside the module wasm wins at 1,000 and 100,000 — then loses at 10,000,000,
because V8 eliminates the JavaScript loop entirely.

Past that point the comparison stops measuring substrates and starts measuring the optimiser. An
experiment resting on that crossover would report a property of V8.

## One mechanism, three outcomes

The judgement is a single procedure:

1. attempt synthesis in the **current** substrate;
2. if it succeeds — **stay**;
3. otherwise attempt the **alternative**; if it succeeds — **migrate**, and record what the
   current substrate returned as the reason;
4. otherwise — **insufficient evidence**.

The refusal is not a separate branch. It is what happens when the current substrate answers
first, and a permanent test reads the runtime source to assert that only two synthesis calls and
three decisions exist in that procedure.

## Task families

| Family | Expressible in |
|---|---|
| `bitwise_difference` | `i32` only |
| `fractional_mean` | `f64` only |
| `larger_of_two` | both |

The first two reverse which substrate is inadequate. The third is expressible where the lineage
already stands and must produce a refusal.

## The falsifiers

**The judgement must reverse.** If the same substrate wins both migrating families, the result is
a fact about the substrates and not about the situation.

**The refusal must occur.** A lineage that always migrates is executing rather than judging.

## Honesty about "cannot express"

Within a bounded search, *not found* is **insufficient evidence**, not proof of impossibility.

The two failures here have different causes and the record must distinguish them: `f64` exhausts
its entire admissible space on the bitwise family and returns `insufficient_evidence`, while
`i32` reaches the 200,000-candidate ceiling on the fractional mean and returns
`budget_exhausted`. The reasons quote the search outcome, and a permanent test asserts that no
reason claims impossibility.

## Declared parameters

| Parameter | Value |
|---|---:|
| Shapes | `f64`, `i32` |
| Opcode space scanned, per shape | 256 |
| Scan pairs | 3 |
| Maximum expression size | 7 nodes |
| Judgement budget | 200,000 |
| Starting substrate | `f64` |

## Anti-cheating

M059 does not pass if either instruction set is supplied rather than scanned, if any ranking
between substrates appears, if the refusal is produced by a branch the migrations do not share,
or if a capability is served from a lookup table.

## What this does not do

The decision is about **where a capability can live**, not a wholesale relocation of the body.
The inherited body computes in `f64`; a capability judged to belong in `i32` is hosted there. No
claim is made that the entire lineage moved, and the manifest records a journey of judgements
rather than a migration of everything.

## Qualification rule

M059 may pass in development only when the complete Python 3.11 and Python 3.13 matrices and the
repository-integrity job pass on the exact documented head. A run that fails before the
experiment's code executes is an infrastructure event under D017 and is not a verdict.

## Claim boundary

One lineage, two signature shapes, three task families. M059 does not establish arbitrary runtime
discovery, unrestricted code generation, open-ended evolution, general intelligence, consciousness
or production safety. Network, repository, credential, deployment and external-system authority
remain human-controlled.

M059 is noncanonical. M042 remains the only positive canonical continuous-lineage completion.
