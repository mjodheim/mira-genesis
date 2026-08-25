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

An acquisition can fail for structurally different reasons. Two extensible components are in the
registry from the start:

- the **operator table** the interpreter applies — the component M107 could extend;
- the **signal interface** — which inputs an expression is permitted to read.

M107's machinery can only ever blame the operator table. Faced with a signal-interface insufficiency
it exhausts the operator candidate space and refuses, which is *true* about the operator axis and
useless about the failure. Its attribution is hardwired.

M108's machinery holds its **attribution rule as lineage state**, expressed as a program in the very
expression language the interpreter runs, over failure features rather than task signals:

- `f0` — extending the operator table would strictly enlarge the reach of the lineage;
- `f1` — the demand behaves as a function of the signals the interface currently reads.

Neither feature names a component and neither is a relabelling of the answer. `f0` is a property of
the state and the candidate space alone and never inspects the demand; `f1` is a property of the
demand alone. `f0` is true in the lineage's own monotone phase and false once its operator table is
saturated, so it varies across the record without carrying the distinction on its own.

## Correction recorded before freeze

An earlier draft of this pre-registration asserted a single correct rule, `f0 AND NOT f1`, table
`0010`, and named `f0` "operator space exhausted". Building the instrument showed that claim false in
two ways, and both corrections are recorded here rather than repaired silently:

1. With that vocabulary the two features were **not independent** — a demand inconsistent with the
   readable signals always exhausts the operator space — so the feature row `(T,T)` was unreachable
   and the monotone rule `f0` was consistent with every realizable episode. The recursion argument
   would have been vacuous.
2. Determinacy cannot be judged against the observed rows alone; that would let a single episode
   determine a rule. It must be judged against the rows attribution can actually be asked about.

No protocol, population or result existed at any point during these corrections.

## The attribution domain

Attribution is consulted only on a demand the lineage could **not** construct. A complete census over
the state family of this world — every operator table reachable by one candidate addition, at every
interface width, against all 256 world functions, 14 303 unconstructible pairs — establishes:

| feature row | `(f0, f1)` | reachable while attributing |
|---|---|---|
| 0 | `(False, False)` | yes |
| 1 | `(False, True)` | **no** |
| 2 | `(True, False)` | yes |
| 3 | `(True, True)` | yes |

Row 1 is unreachable by a lemma, not by a failed search: a saturated operator table together with a
demand that *is* a function of the readable signals means the demand is already constructible, so no
failure exists to attribute. Two rules differing only on row 1 are the same machinery. Determinacy is
therefore required on rows `{0, 2, 3}` and no others.

## Why this is recursive rather than merely another extension

Every rule consistent with the blame record maps row 0 to "blame the signal interface". The complete
image of the monotone fragment `{AND, OR}` over the feature signals is `{f0, f1, f0 AND f1,
f0 OR f1}` — four functions, none of which is true at `(False, False)`, because no constant is
expressible from projections under `AND` and `OR`. The exclusion is the same monotonicity lemma M107
used, at every node bound, for any budget.

A lineage that has not acquired a negation-like operator therefore **cannot express its own corrected
attribution rule at all**. The machinery's rule is a program in the substrate the previous generation
extended, so generation 1's acquisition is a **precondition for generation 2's machinery
acquisition**, and that dependency is proved rather than asserted.

## H53

Starting from `M0` — a lineage whose interpreter already holds an acquired negation-like operator but
whose acquisition machinery attributes every failure to the operator table — the lineage acquires from
recorded attribution episodes a persistent, content-addressed **attribution rule A**, held as state
and expressed in its own language. `M1 = M0 + A` modifies the machinery: later acquisitions are
attributed by A rather than by the hardwired axis.

After complete producer death, a demand `B` is revealed for the first time. `B` is a three-signal
function that genuinely depends on signal 2 and is non-monotone.

- `B` is outside the reach of `M0` **for every operator set, arity, depth and budget**: every
  expression `M0` can build reads only signals 0 and 1, so its image is constant along axis 2. The
  census is complete — sixteen liftable images out of 256 world functions, intersection empty.
- `B` is *also* outside the complete image of the monotone fragment at full width, by the
  monotonicity lemma. `B` requires **both** generations; neither alone suffices.
- `M1` attributes the failure to the signal interface, extends that component, and constructs `B`.
- `M0` with the same later observations, the same runtime, the same machinery-step budget and an
  equal or larger node bound cannot construct `B`, for that structural reason rather than exhaustion.
- A fresh lineage holding only the monotone fragment cannot even **acquire A**.

## What A must not be

A is refused as evidence for H53 if it is a user-level operator, a consumer, a business rule, a lookup
keyed on `B`, or a definition directly required to build `B`. A is an attribution function over
failure features. It governs **every** later acquisition, contains no artefact of `B`, and is acquired
before `B` or any of its material exists.

The episodes are drawn from the lineage's own recorded history, including its monotone phase. Their
blame labels are **authored supervision** and are declared as such: M108 tests whether an acquired
attribution rule causally changes later acquisitions, not whether the lineage can invent the labels.

## Decisive conditions

- **P1** runtime and input preflight bind the canonical runtime and the exact fixtures.
- **P2** the registry holds both components from the start, `M0` attributes by the hardwired operator
  axis, and M108's enumerator is certified to denote exactly M107's image at M107's own width.
- **P3** `B` is outside every liftable image at the base interface width, by complete census, and the
  exclusion is recorded as operator-set- and budget-independent.
- **P4** `B` is outside the complete image of the monotone fragment at full width, by the monotonicity
  lemma, so generation 1 is necessary independently of the interface.
- **P5** the attribution domain is a complete census over the state family, and exactly one feature
  row is certified unreachable while attributing.
- **P6** no rule in the monotone fragment's image reproduces the blame record, at every node bound.
- **P7** an episode set leaving a domain row uncovered yields more than one attribution class and the
  lineage refuses.
- **P8** the full episode set yields exactly one attribution class, the rule space is exhausted, every
  consistent rule is non-monotone, and no episode carries `B`.
- **P9** A is adopted as content-addressed lineage state and attribution switches to the state-held
  rule.
- **P10** the producer process dies; a later isolated process receives only the serialized state.
- **P11** `B` is revealed only after producer death; `M1` attributes it to the signal interface and
  extends that component.
- **P12** `M1` constructs `B` and the witness executes to target under independent re-execution.
- **P13** `M0`, hardwired, exhausts the operator candidate space and refuses under an equal
  machinery-step budget, and still refuses at strictly larger node bounds.
- **P14** ablation of A is a byte-exact rollback to `M0` and removes the capability; mutation of A
  returns attribution to the operator axis and fails; corruption fails closed.
- **P15** every isolated process reports zero model, network and remote-execution calls.
- **P16** independent replay reproduces the stable evidence projection exactly.

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

The feature vocabulary, the component registry, the rule space, the episode blame labels, the demands
and the evaluator remain authored. `B`'s feature row is one the episode set already covers, so what is
tested is generalization to a **new demand with a recorded feature pattern**, not extrapolation into a
feature region never observed.

A positive M108 would license only this: *within a frozen bounded environment, a lineage-acquired
modification to the acquisition machinery causally expanded the set of later improvements the lineage
could construct under an equal budget.*

A positive M108 makes the next question whether `M1`'s improved machinery can itself acquire a
**further** machinery improvement that `M0` could not — the first true recursive depth.
