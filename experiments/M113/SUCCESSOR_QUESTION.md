# The successor question, recorded before M113 runs

**Status: a question, not a milestone. Nothing here is implemented, frozen or claimed.**

M113 has not run. This document exists because the evidence that points at the *next* ceiling is
already in hand and is independent of M113's bank, and recording it now is stronger than deriving it
afterwards from a result. Nothing below presupposes what M113 will return.

## What the pre-freeze evidence already says

`experiments/M113/DEVKIT_SURVEY.json` applies the frozen qualification rule and the frozen census to
1 200 carriers under `mira-blind-carrier-v1`. On the 276 that qualify, the inherited three-feature
vocabulary maps its occupied rows like this:

| row | components the census assigns across carriers | M111's own pooled record |
|---|---|---|
| 1 | `operator_table` | `operator_table`, determined |
| 2 | `candidate_space`, `signal_interface` | not seen |
| 3 | `candidate_space`, `signal_interface` | undetermined |
| 5 | `operator_table` | `operator_table`, determined |
| 6 | `candidate_space`, `signal_interface` | not seen |
| **7** | **`candidate_space`, `signal_interface`** | **`signal_interface`, determined** |

**Four of the six occupied rows carry more than one limiting component**, and one of them — row 7 —
is a row M111 recorded as *determined*. On a family of carriers drawn from this meta-schema, no
function of `(g0, g1, g2)` is right on all of them. The lineage's diagnostic vocabulary does not
determine these carriers, and its own record says otherwise about row 7.

That is a fact about the **feature vocabulary**, measured on development data, and it does not depend
on the blind bank at all. Whether it survives on carriers a blind generator emits is one of the
things M113 measures.

## Which space is inadequate

The candidate ceilings worth naming were: interface representation, feature vocabulary, component
registry, probe vocabulary, search language, evaluator coupling. The measurement above singles out
one of them.

- **Interface representation** is not the binding constraint. The learner reads four wire surfaces
  with emitter-chosen tokens and recovers the observation on all of them; nothing in the development
  run fails for want of a representation.
- **Component registry** is not obviously binding either. Three components suffice to make every
  demand in the census determined-or-not; what fails is telling *which* one from the features.
- **The feature vocabulary is binding.** Three booleans cannot separate `candidate_space` from
  `signal_interface` on four of six rows, and adding no rule over those three booleans can.

## The question, and the shape a successor must have

The wrong successor is a wider hard-coded vocabulary. Adding `g3` by hand would remove the ambiguity
and establish nothing: the project would have supplied exactly the discrimination the lineage failed
to have, which is the authored-supervision defect M108 already recorded about its blame labels.

The right question is the one the ceiling actually poses:

> Can the lineage **establish that its own feature vocabulary is insufficient**, acquire an
> extension to it from lineage-owned machinery, register that extension as state, and use it to
> attribute correctly on a row the inherited three features cannot separate — while an otherwise
> identical lineage without the acquired feature cannot?

That is M107's move — *establish the insufficiency, then extend the language* — applied to the
observation vocabulary rather than to the operator table. Its precedents are exact: M097 acquired an
operation when the operation language could not express a requirement; M107 acquired an operator when
the interpreter held no operator semantics; M108 modified the attribution rule; M109 produced the
machinery that produces the machinery. A vocabulary extension is the next member of that series and
not a new kind of thing.

Four conditions such a successor would have to meet, stated now so they cannot be relaxed later:

1. **The insufficiency must be proved, not observed.** A census showing one row with two components
   is evidence; the proof is that the rule space over the inherited features contains **zero**
   programs consistent with the episode set, the way M108 and M109 proved theirs by enumeration.
2. **The new feature must be computed by the lineage, from what it can observe.** A feature the
   project defines and the lineage merely switches on is authored supervision wearing an
   acquisition's clothes.
3. **The extension must be state, and must survive producer death.** M098 and M099 recorded what
   separates a capability from a live Python process.
4. **The ablation must bite.** A lineage handed the same episodes without the acquired feature must
   be refused with zero consistent rules, by enumeration rather than by budget.

## Ordering, and what is not being claimed

This question is **not** scheduled ahead of M113's result. M113 measures whether the ambiguity
transports to carriers the project did not design, and that measurement is worth having before a
successor is built on the assumption that it does. If M113's bank shows the inherited vocabulary
*is* a function on blind carriers, this question is weaker than it currently looks and the successor
should be re-derived rather than executed as written.

Nothing here advances a generality gate, and none of it may be cited as evidence. It is a question
with its motivation recorded before the bank that will test it exists.
