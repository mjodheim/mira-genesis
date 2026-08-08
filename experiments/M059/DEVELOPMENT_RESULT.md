# M059 — development result

## Status

**POSITIVE ON ITS CENTRAL QUESTION — PENDING QUALIFICATION.**

The lineage judged its substrate inadequate twice, in opposite directions, and refused to move a
third time. This is a bounded, noncanonical development result.

## What was observed

Starting in `f64`, the journey is **`f64 → i32 → f64`**.

| Family | Decision | Current substrate returned |
|---|---|---|
| `bitwise_difference` | **migrate** to `i32` | `insufficient_evidence`, 22,503 candidates |
| `fractional_mean` | **migrate** to `f64` | `budget_exhausted`, 200,000 candidates |
| `larger_of_two` | **stay** | `synthesized`, 20 candidates |

| | `f64` | `i32` |
|---|---:|---:|
| Operations discovered | **9** | **27** |
| Candidates refused by the validator | 247 | 229 |

Every accepted body was verified on arguments the judgement never saw.

## Why this is a judgement and not an instruction

**It reverses.** Two migrations, two distinct targets — `f64` and `i32`. Neither substrate is
globally better; each is inadequate for something the other handles. Had one won both families,
the result would have been a fact about the substrates rather than about the situation, and that
is exactly the M049 shape D016 closed.

**It can refuse.** `larger_of_two` is expressible where the lineage already stands, and the
decision is `stay`. A lineage that always migrates is executing, not judging.

**The refusal shares the mechanism.** `stay` is what happens when the current substrate answers
first — not a separate branch. A permanent test reads the runtime source and asserts that the
judgement contains exactly two synthesis calls and three decisions.

## The two failures are not the same failure

`f64` exhausted its **entire** admissible space on the bitwise family in 22,503 candidates and
returned `insufficient_evidence`. `i32` reached the 200,000-candidate ceiling on the fractional
mean and returned `budget_exhausted`.

Both are honest forms of *not found*, and they are not interchangeable. One means the search
looked everywhere it was allowed to look; the other means it ran out of room. The manifest
records which, and a permanent test asserts that no recorded reason claims impossibility.

Within a bounded search, *not found* is insufficient evidence. The lineage's basis for moving is
what the search returned, never a claim about what a substrate can express.

## A design that measurement rejected

The first design would have had the lineage time both substrates and move to the faster one. It
does not survive contact with the numbers.

JavaScript beats WebAssembly at every per-call workload from 1 to 100,000 operations, because
each call crosses a boundary while V8 compiles the JavaScript to a single instruction. With the
loop moved inside the module, WebAssembly wins at 1,000 and 100,000 — and then loses at
10,000,000, because V8 eliminates the JavaScript loop altogether.

Past that point the comparison measures the optimiser, not the substrate. The design was
abandoned before anything was built on it, and it is recorded here so it is not proposed again.

## Something the substrates did not share

`i32.div_s` **traps** on a zero divisor; `f64` division yields infinity. An uncaught trap aborted
the search during development. The difference had to be handled rather than assumed away, and it
is a small reminder that two substrates differ in more than their operation lists.

## Claim boundary

The decision is about **where a capability can live**, not a wholesale relocation. The inherited
body computes in `f64`; a capability judged to belong in `i32` is hosted there. No claim is made
that the entire lineage moved.

The signature shapes are still authored, as in M058. The lineage discovers what each substrate
contains, not that the shapes exist.

M059 does not establish arbitrary runtime discovery, unrestricted code generation, open-ended
evolution, general intelligence, consciousness or production safety. Network, repository,
credential, deployment and external-system authority remain human-controlled.

M059 is noncanonical. **M042 remains the only positive canonical continuous-lineage
completion.**

## The line this completes

| Experiment | Given | Had to find |
|---|---|---|
| M048 | a compiler, a target runtime, an instruction to migrate | nothing about the crossing |
| M056 | a compiler, a target substrate | that its acquisitions survive a second crossing |
| M057 | six named operations | what they do, how to compose them |
| M058 | a signature shape | which operations exist |
| M059 | two shapes, no ranking | **whether to move at all, and where** |

What remains handed is the shape of the question and the tasks that arrive. The lineage does not
choose what it is asked to do.
