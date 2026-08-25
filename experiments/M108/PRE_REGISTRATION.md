# M108 — endogenous modification of the acquisition machinery

**Hypothesis:** H53
**Decision slot:** D077 (reserved; unfilled until a canonical result exists)
**Track:** A — endogenous bounded lineage
**Pre-registration date:** 25 August 2026
**Status:** **PRE-REGISTERED QUESTION; NO PROTOCOL, POPULATION OR RESULT EXISTS**

## The ceiling M107 left

M107/H52 qualified the first endogenous extension of the **lower interpreter** (D076): an acquisition
changed what the interpreter could express, taking `complete_image` from four of sixteen to sixteen.
Recursive depth was **zero**. The search, the adoption rule, the candidate space, the diagnosis and
the evaluator were untouched and authored.

M107 changed *what the lineage can express*. M108 asks whether an acquisition can change **how the
lineage performs later acquisitions**.

## The machinery component under test: failure attribution

An acquisition can fail for structurally different reasons. Two extensible components exist in the
registry from the start:

- the **operator table** the interpreter applies;
- the **signal interface** — which inputs an expression is permitted to read.

M107's machinery can only ever blame the operator table. Faced with a signal-interface
insufficiency it exhausts the operator candidate space and refuses, which is *true* about the
operator axis and useless about the failure. Its attribution is hardwired.

M108's machinery holds its **attribution rule as lineage state**, expressed as a program in the very
expression language the interpreter runs, over failure features rather than task signals:

- `f0` — the operator candidate space is exhausted;
- `f1` — the demand is consistent with what the current signal interface can read.

The rule that blames the signal interface is `f0 AND NOT f1`, truth table `0010`.

## Why this is recursive rather than merely another extension

`0010` is **non-monotone**. It is therefore outside the complete image of the monotone fragment
`{AND, OR}` by the same monotonicity lemma M107 used — at every node bound, for any budget. A
lineage that has not acquired a negation-like operator **cannot express its own corrected attribution
rule at all**.

The machinery's rule is a program in the substrate the previous generation extended. Generation 1's
acquisition is therefore a **precondition for generation 2's machinery acquisition**, and that
dependency is provable rather than asserted.

## H53

Starting from `M0`, a lineage whose interpreter already holds an acquired negation-like operator but
whose acquisition machinery attributes every failure to the operator table, the lineage can acquire
from DEVELOPMENT attribution episodes a persistent, content-addressed **attribution rule A**, held as
state and expressed in its own language. `M1 = M0 + A` modifies the machinery: later acquisitions are
attributed by A rather than by the hardwired axis.

After complete producer death, a demand `B` is revealed for the first time. `B` is a three-signal
function that genuinely depends on signal 2.

- `B` is outside `complete_image(M0)` **for every operator set, arity, depth and budget**: every
  expression `M0` can build reads only signals 0 and 1, so its lifted image is constant along axis 2.
  The census is complete — sixteen liftable images, two hundred and forty signal-2-dependent targets,
  intersection empty.
- `M1` attributes the failure to the signal interface, extends that component, and constructs `B`.
- A fresh `M0` with the same later observations, the same runtime and an equal or larger budget
  cannot construct `B`, for that structural reason rather than exhaustion.
- A fresh lineage holding only the monotone fragment cannot even **acquire A**, because `0010` lies
  outside its complete image.

## What A must not be

A is refused as evidence for H53 if it is a user-level operator, a consumer, a business rule, a
lookup keyed on `B`, or a definition directly required to build `B`. A is an attribution function
over failure features. It governs **every** later acquisition, contains no artefact of `B`, and is
acquired before `B` or any of its material exists.

## Decisive conditions

- **P1** runtime and input preflight bind the canonical runtime and the exact fixtures.
- **P2** the registry contains both extensible components from the start, and `M0`'s attribution is
  the hardwired operator axis.
- **P3** a structural certificate shows `B` outside `complete_image(M0)` by complete census, and
  records the exclusion as budget-independent.
- **P4** the corrected attribution rule `0010` is certified outside the complete image of the
  monotone fragment by the monotonicity lemma, so a lineage without generation 1 cannot express it.
- **P5** a single DEVELOPMENT attribution episode leaves the rule underdetermined and the lineage
  refuses.
- **P6** the full episode set determines exactly one rule; the rule space is exhausted.
- **P7** A is adopted as content-addressed lineage state and the machinery's attribution now reads A.
- **P8** the producer process dies; a later isolated process receives only the serialized state.
- **P9** `B` is revealed only after producer death, and `M1` attributes it to the signal interface.
- **P10** `M1` extends the signal interface and constructs `B`, and the witness executes to target.
- **P11** `M0`, hardwired, exhausts the operator space on `B` and refuses.
- **P12** a fresh `M0` at a larger node bound also fails, so the difference is reach and not budget.
- **P13** a fresh lineage holding only the monotone fragment cannot express or acquire A.
- **P14** ablation of A restores the hardwired boundary; mutation of A changes attribution as
  predicted; building A without adopting it does not suffice; corruption fails closed.
- **P15** rollback to `M0` is byte-exact and inherited capabilities remain live.
- **P16** every isolated process reports zero model, network and remote-execution calls, and
  independent replay reproduces the stable evidence projection exactly.

**Verdict rule:** positive if and only if P1-P16 are all computed and true; negative otherwise. One
canonical attempt and one canonical checker replay are permitted. The first result is preserved even
if negative and may not be repaired.

## Instrument requirements

M103 and M105 were lost to checkers that could not start; M107's rehearsal caught four further
defects including M098's exact stable-projection failure. Before any M108 freeze the complete
`CANONICAL -> PRESERVE -> CHECK -> REPLAY` chain must be rehearsed end to end against a materialized
DEVELOPMENT result in a throwaway clean checkout, using exactly the frozen commands, exercising the
checker as a direct script through the replay branch, with exit codes asserted for result-present,
result-absent, corrupted-result and report-already-exists, with a tampered result carrying a
recomputed digest detected, and with every predicate computed. M108 must pin its bytes in
milestone-local attribute files and must not bind any file an earlier frozen protocol binds.

## What M108 cannot establish

Recursive depth of two or more; measured recursive acceleration; autonomous identification of the
bottleneck in worlds where the bottleneck varies; open-ended machinery growth; transfer to an
independently maintained domain; G1-G10 closure; general-agent evidence; self-hosting; AGI.

The feature vocabulary, the component registry, the rule space, the demands and the evaluator remain
authored. A positive M108 would license only this: *within a frozen bounded environment, a
lineage-acquired modification to the acquisition machinery causally expanded the set of later
improvements the lineage could construct under equal budget.*

A positive M108 makes the next question whether `M1`'s improved machinery can itself acquire a
**further** machinery improvement that `M0` could not — the first true recursive depth.
