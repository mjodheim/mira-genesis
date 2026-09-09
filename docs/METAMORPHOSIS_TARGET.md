# The metamorphosis target

**Prospective, authoritative for direction. 8 September 2026.**

This document states what Mira Genesis is now building. It changes no frozen definition, reinterprets
no recorded result, and creates no evidence. It is a statement of **objective**, and objectives are
prospective by nature: `GENESIS_COMPLETION_CRITERIA.md`, `MIRA_GENERALITY_CRITERIA.md`, every frozen
protocol and every recorded verdict keep exactly the meaning they already have.

## The objective

> Build a program capable of **empirical metamorphosis**: a persistent software lineage able to
> diagnose its own limitations, modify its body and progressively its own acquisition machinery,
> evaluate its descendants experimentally, adopt or reject transformations on evidence, retain what
> it has acquired, and continue the same process after a change of body or substrate.

That is the directing goal. It is not a label to be awarded; it is a program that either runs or
does not.

## Three levels that are routinely confused

The repository holds three distinct things. Collapsing them is the most common way to misread this
project, and until now the navigation made it easy to do.

### 1. Phase-one bounded Genesis — **already achieved, and closed**

M042 satisfies the ten frozen Genesis completion gates in the deterministic binary-DFA laboratory.
M066 confirms the same gate structure on the CPython → Node ESM → whole-WebAssembly path, with
independent reproduction across Python 3.11 and 3.13.

This is a real, recorded, bounded result. It is finished. Nothing in the present objective reopens,
widens or re-derives it, and no later work may cite it as more than it is.

### 2. Empirical metamorphosis — **the current objective**

The mechanisms qualified since M107 are no longer isolated curiosities; they are the **primitives**
of the program described above:

| milestone | mechanism | recursive depth |
|---|---|---|
| M107 | endogenous extension of the lower interpreter | 0 — the acquisition machinery is untouched |
| M108 | endogenous modification of the acquisition machinery itself | 1 |
| M109 | a modified machinery producing the next modification, on the lineage's own blame findings | 2 |
| M110 | transfer of an acquired machinery modification into a materially different consumer family | — |
| M111 | self-directed diagnosis: spending a scarce probe where the lineage's own record shows its vocabulary undetermined | 3 |
| M112 | the worlds themselves produced by a blind generator with no repository mount | — |

What is missing is not another mechanism. It is that **these have never run as one program.** Each
was demonstrated inside its own experiment harness, against its own authored population, and then
stopped. There is no lineage that carries all of them, no loop that continues after a candidate is
rejected, and no runtime in which a rejection becomes an observation rather than the end of a run.

Building that runtime is the current frontier.

### 3. Generality validation — **a later evidence level, not the purpose**

`MIRA_GENERALITY_CRITERIA.md` and its G1–G10 gates remain exactly as binding as they were, and the
three external blockers — a human-maintained sealed bank, independent reproduction, an external
adversarial audit — remain unliftable from inside this repository.

But they answer a **different question**. They ask how general the resulting system is. They do not
tell you what to build, and the AGI-candidate tier was never the project's purpose. Treating it as
the purpose has a specific cost: it makes the architectural path look blocked by recruitment, when
the actual blocker on the *program* is that the runtime does not exist yet.

`COMPLETION_PATH.md` remains accurate about the generality tier and about what only external people
can supply. It is a validation roadmap, and it should be read as one.

## What the objective requires that the repository does not yet have

An integrated Genesis runtime, separate from the frozen experiment modules and reusing their
validated invariants without editing their sources, providing at minimum:

- a versioned, persistent `LineageState`;
- a current executable body;
- a transformation and tool registry;
- a registry of modifiable components;
- a memory of observations, failures, experiments and acquisitions;
- diagnosis machinery;
- transformation generation and search;
- an isolated candidate execution environment;
- parent / candidate / control comparison;
- an adoption-or-rollback transaction;
- a complete descent journal;
- restoration after process death.

And a loop that runs without human architectural intervention:

```text
observe -> diagnose -> hypothesize -> construct candidates -> isolate -> test
       -> compare -> adopt/reject -> persist -> continue
```

A rejected candidate must not end the program. It becomes an observation the lineage holds, and the
loop continues within its budget. (A *scientific* negative stays frozen under the repository's
existing rules — that is a separate thing from the program learning that a candidate does not work.)

## The invariant that must never bend

The architecture splits strictly in two:

- **mutable Genesis**, which may evolve;
- **an immutable trust root**, holding at minimum isolation, budget, provenance and the final
  accept/reject decision.

**Genesis must never be able to become better by modifying the measure that decides it is better.**
Every other design question in this program is negotiable. This one is not.

## Causality between generations is a property of the runtime, not of a milestone

"Version 1 better, version 2 better, version 3 better" is not the claim. At least one later
improvement must be impossible, or materially less reachable, without an earlier acquisition —
demonstrated by real ablation: remove the earlier acquisition, retry the later generation at the same
budget, show the loss of reach, diagnosis or efficiency.

M107–M111 established this pattern experiment by experiment. In the runtime it becomes a permanent
property that every generation is measured against, not a control written once per milestone.

## What success would and would not mean

Success would establish a **bounded but real** form of empirical self-evolution and software
metamorphosis: one continuous lineage that measures itself, diagnoses itself, transforms itself,
verifies the transformation experimentally, adopts or rejects it, retains what it learned,
progressively modifies the machinery that enables later transformations, changes form, and then goes
on evolving in that new form.

It would **not** demonstrate AGI, human-level general intelligence, consciousness, or open-ended
unbounded evolution. G1–G10, the independent human banks, external reproduction, human baselines and
outside audit continue afterwards as validation of the system obtained — not as a condition for
building it.

## The stopping criterion

Not green tests. Not a positive milestone. Not a publishable paper.

The work reaches its objective when the repository contains an **executable integrated Genesis
program** and a **reproducible experiment** showing one lineage that measures itself, diagnoses
itself, transforms itself, verifies the transformation experimentally, adopts or rejects it on that
evidence, retains what it learned, progressively modifies the machinery enabling later
transformations, changes form, and continues to evolve in the new form.

Work that does not directly increase the credibility or the capability of that loop is secondary:
support, external validation, or technical debt. It is not the frontier.
