# M119 / H64 — preregistration

Written before the analysis plan, the generator spec, the bank nonce and the tested-system freeze,
and before any H64 observation exists. Nothing below may be revised after the seal is broken.

## Status at the time of writing

- H64 is **not frozen**. No carrier bank exists. Qualifying scientific invocations: **0**.
- M113, M114, M115, M116, M117 and M118 are closed. Nothing here reopens, reinterprets or repairs
  any of them, and no artifact of theirs is modified.
- M118 closed as **instrument design and audit**. H63 was never frozen, never generated a bank, and
  remains untested. That is not a result about the hypothesis, and it is not reported as one.

## The hypothesis

**H64.** A descendant carrying both pieces of acquired machinery — the attribution cascade and the
diagnostic policy — resolves demands on carriers it did not design more often than a comparator that
carries neither, on demands posed identically to both.

The hypothesis is about *acquired state*, so the design must be able to say **which** acquired state
did the work, or say plainly that it cannot. That is the whole reason there are four arms.

## The design, and why it is this small

M118 carried nine arms and still could not attribute an effect, because it lacked the one cell that
would have separated the two live explanations. M119 uses the 2×2 that does, and nothing else.

|                    | policy absent  | policy present |
|--------------------|----------------|----------------|
| **cascade absent** | `FRESH`        | `POLICY_ONLY`  |
| **cascade present**| `CASCADE_ONLY` | `FULL`         |

- `FULL` is the descendant. `FRESH` is the comparator. The primary comparison is fixed here, in
  code, as `DESCENDANT_ARM` and `COMPARATOR_ARM`, and no analysis may re-point it.
- `CASCADE_ONLY` and `POLICY_ONLY` exist to decompose a positive result. They cannot create one.
- There is no rollback, ablated, mutated or unregistered arm. None of them is needed to
  distinguish the two live causal explanations, and each is a way for the design to grow past the
  point where a one-shot instrument can be trusted.

One further arm, `FULL_BUDGET_PLUS`, sits **outside** that table and outside the primary
comparison. It holds exactly what `FULL` holds; only the observation budget differs, at M113's
multiplier of four, inherited rather than invented. It exists because pre-freeze review measured a
concrete ambiguity the 2×2 cannot resolve: on unreachable demands the policy-holding arms returned
`undetermined` 17 times in 25 against 2 in 25 for the comparator, and a probe that consumes
observations could be losing to its own cost rather than to its competence. The arm is fenced — it
is never the descendant or the comparator, no guard is evaluated on it, the decomposition never
sees it, and it can attribute a negative but can never create a positive. The reasoning and the
running arm count are recorded in `COMPLEXITY_BUDGET.md`.

### The comparator is symmetric, not merely balanced

M118's comparator dealt feature rows over a fixed component order, which short-changed the same
component in 400 of 400 seeds — a standing bias sold as a uniform prior. `FRESH` here draws each
feature row **independently and uniformly** over the three components, by rejection sampling from a
committed seed and the demand's opaque identity, so no component is favoured and none is
systematically the one expressed by the attributor's fallthrough. For every row and every component
the probability is exactly one third, which is a property that can be proven rather than estimated.

The draw consults the committed seed, the opaque carrier reference and the pair digest. It consults
no carrier semantics, no ground truth, and no M117 or M118 outcome. The seed is a digest of a fixed
public string, so its derivation is auditable rather than asserted, and the checker verifies the
recorded seed against that constant rather than against the record's own copy of it.

### What is held fixed, and what is not

External affordances are identical across arms: the same carrier, demand, channel, evaluator,
reference, observation budget and host primitives. Acquired state **may** enable different internal
actions, and that is stated rather than glossed: the policy gates the diagnostic probe, so an arm
holding the policy can take an action an arm without it cannot. That is the acquired state under
test, not a harness asymmetry, and the factorial cells exist to measure it.

## The primary endpoint

Each demand is posed identically to every arm, so outcomes are **paired per demand**:

- on a **reachable** demand, success is a correct construction;
- on an **unreachable** demand, success is a calibrated refusal;
- **everything else is failure**, including `undetermined`.

There is no disjunction and no second way to win. The demand classes are imported from the frozen
M113 evaluator rather than re-spelled, so an endpoint that names a class the evaluator does not
produce is a build error rather than a run-time surprise.

## The decision rule

`FULL` versus `FRESH`, on the paired per-demand outcomes:

1. **one-sided exact McNemar** over the discordant pairs, at **α = 0.05**; and
2. an absolute success-rate improvement of at least **ten percentage points**.

Both are required. The exact test is the sign test over discordant pairs: `P(X ≥ b)` for
`X ~ Binomial(b + c, ½)`, so at least **5** discordant pairs are needed for any significant result.

### Verdicts

Four states, fixed before the data:

| verdict | meaning |
|---|---|
| `instrument_aborted` | the run cannot validly test H64 at all — **untested**, not refuted |
| `inconclusive` | a valid observation in which significance was not arithmetically attainable |
| `negative` | a valid, adequately powered test in which the criterion failed |
| `positive` | both criteria met and every mandatory guard held |

An underpowered bank is never a refutation. An instrument failure is never a scientific result.

### Guards

Three, one direction each, evaluated on `FULL` against `FRESH`: `invented_adapter` (at most),
`false_refusal` (at most), `attribution_agreement_rate` (at least). A guard can **veto** a positive
and can never **create** one. `attribution_agreement_rate` binds only where attribution was actually
examined: it has an outcome-dependent denominator, so an arm that constructs immediately examines
nothing, and vetoing on a rate that could not be formed would reject the best possible result.

### Interpretation

The strongest supportable statement is computed from the four arms by a preregistered mapping, not
written by whoever summarises the run. If `POLICY_ONLY` reproduces `FULL`'s advantage, the effect is
not attributable to the cascade; if `CASCADE_ONLY` does, no incremental contribution from the policy
is supported; if `FULL` exceeds both, a combined contribution is supported; otherwise the combined
effect is reported without attributing it to a component.

## The bank

- **36 carriers requested**, in one generation, from one blind generator.
- The prompt template and the output schema are M115's, inherited **byte for byte**. The generator
  is blind: one user message carrying the derived qualifying input and the frozen schema; no system
  message, no tools, no prior turns, no retrieval, no repository, no project vocabulary.
- The count is derived before any H64 observation exists, from the token envelope M118's readiness
  gate actually proved (73,731 conforming completion tokens, `finish_reason: stop`) and a
  DEVELOPMENT yield estimate over the M113 devkit emitter (0.2475 qualifying, mean 2.13 demand pairs
  per qualifying carrier). Expected paired demands ≈ 38, against 5 discordant needed.
- **That estimate is not a prediction.** It measures a devkit emitter, not the blind generator. M113
  recorded six per cent over project worlds against twenty-five per cent from M112's blind bank. The
  binding constraint is the admissibility minimum below, and the count is not revisable after the
  reveal.
- **Admissibility**, inherited from M115 unchanged: at least 3 qualifying carriers and at least 3
  distinct structural signatures. Below either, H64 is `instrument_aborted` — untested, not refuted.
- On the smallest admissible bank the frozen criterion can both pass and fail: 6 paired demands
  against 5 discordant needed, smallest attainable p = 0.015625. A criterion that could not be met
  by the smallest bank the plan admits would be a criterion discovered to be unsatisfiable after the
  reveal, so the plan refuses to freeze without this check.

## The route

Fixed in `metamorphosis/m118_route.py`, inherited **byte-unchanged** from M118: requested model
`deepseek/deepseek-v4-flash-0731`, provider `OpenInference`, canonical checkpoint
`deepseek/deepseek-v4-flash-20260731`. There is no second route and no fallback. **No provider
substitution.** If the route fails, H64 stops.

That module was fixed before H64 existed, which is a stronger prospective claim than M119 could
make by choosing a route now. M117 disclosed that five apparatus revisions occurred inside it and
that some followed real endpoint observations; M119 inherits a route, not a claim that route
selection was prospectively clean.

## Chronology

Each stage must prove its predecessors were **committed at HEAD, byte-identical to the working
tree**, before it may run. A file written seconds before a request is not a freeze. There is no
parameter through which a caller may supply a record it has just built.

    M118 closed, route fixed, readiness passed
      → this preregistration
      → plan, spec, qualifying input and nonce frozen
      → complete tested-system freeze committed
      → unique H64 qualifying generation
      → machine-only admission
      → seal, or terminal abort
      → reveal authorization → one reveal
      → frozen scoring → independent replay

The tested-system freeze binds the interpreting closure computed from the source, and separately
scans the disk for measurement entry points no root declares — a closure walks downward from its
roots, so a module nothing imports is invisible to it, and a runner is exactly such a module. It
also binds the plan, the spec, the exact request bytes and the nonce, and it is re-proved at every
phase after the generation.

The **bank nonce is committed before the generation** because the comparator's per-demand draw
consults the opaque carrier references derived from it. A nonce chosen after the bank existed would
be a degree of freedom over the comparator.

## The single generation

One qualifying request. Only an explicit pre-generation HTTP 429 carrying no completion and no
evidence of model execution may be retried, at most twice. Everything else is terminal: a scientific
outcome is never retried, no output is repaired, reparsed or regenerated, and there is no selection
among outputs.

Admission runs **before** anything is called a bank, on the bytes that arrived. It requires runtime
identity to be exactly the fixed route, `finish_reason: stop`, valid JSON, conformance to the frozen
output schema, and acceptance of the enveloped payload by the frozen carrier host. It is a pure
predicate: it may not repair, strip, extract, reformat, regenerate or choose. If it refuses, the
single generation opportunity is spent and H64 ends `instrument_aborted`.

## What a positive result would and would not mean

It would mean: on demands derived from carriers this project did not design, the descendant carrying
both pieces of acquired machinery resolved more of them than a symmetric comparator, by a margin
unlikely under the null and at least ten percentage points wide, without harming refusal calibration
or inventing adapters.

It would **not** mean, and will not be said to mean, any of the following:

- AGI, recursive self-improvement, open-ended intelligence, or the closing of any generality gate.
- Provider invariance. **One provider and one checkpoint were used, so provider is confounded with
  the effect.** Nothing here separates what the acquired machinery does from what this particular
  serving route does.
- Generality beyond the carrier family this project's meta-schema defines.
- Independence of the generator's training data. The generator is blind to the hypothesis; it is not
  independent of what it was trained on.
- Human independence, or external reproduction.

## Multiplicity across H60–H64

H64 is tested at α = 0.05 with no correction, and the reason is that **no statistical test has been
performed anywhere on this chain of hypotheses**. Checked against the committed records rather than
recalled:

| hypothesis | milestone | recorded verdict | statistical test performed |
|---|---|---|---|
| H59 | M114 | `instrument-aborted`, untested | none |
| H60 | M115 | `instrument-aborted`, untested | none |
| — | M116 | DEVELOPMENT capability matrix | none |
| H62 | M117 | instrument development / route calibration | none |
| H63 | M118 | closed as instrument design; never frozen, no bank | none |

H64 is therefore the **first** test of this target, and a first test is not a multiple comparison.
There is no family of prior p-values to correct against, because none was ever computed.

Two things follow, and both are binding:

- **This milestone spends the only uncorrected α on the chain.** If H64 also ends
  `instrument_aborted`, that consumes no α, because no test was performed. But if H64 returns a
  `negative` or a `positive`, a later milestone testing the same target must correct for having
  tested it twice, and must say so in its own preregistration.
- **The four arms do not create multiplicity here.** There is exactly one primary comparison, FULL
  versus FRESH, fixed in code before the data. The other cells enter only the decomposition of a
  result the primary comparison has already established, and the fenced diagnostic arm enters
  neither. No arm is tested against α, and no result is selected as the best of several contrasts.

## Stated limitations

1. Provider and model are confounded with the effect. No provider-invariance claim is available.
2. Readiness evidence for the fixed route is **inherited** from M118's committed DEVELOPMENT run
   rather than re-measured. It establishes that this route served the frozen request shape
   conformingly on that date; it does not establish that it still does. The live check is admission,
   where a failure is terminal and never redrawn.
3. `FRESH` is symmetric, not strong. Beating it is not evidence of beating a competent hand-written
   attributor.
7. The observation budget is 4000 per demand, inherited unchanged from M113. The endpoint is
   therefore *budget-constrained* resolution: an arm that spends observations on a diagnostic probe
   has fewer left. `FULL_BUDGET_PLUS` exists to say whether a negative is that cost or a competence
   cost; without it the two would be indistinguishable.
4. One bank, one generation, one model.
5. The carrier family is this project's.
6. M117's five disclosed apparatus revisions sit upstream of the route, and are not repaired here.

## Stop conditions

H64 stops, without a scientific verdict, if any of these holds:

- the fixed route cannot serve the frozen request, or runtime identity is not exactly that route;
- the one completion is not admissible;
- the bank falls below the admissibility minimum;
- the tested system does not match its freeze at any phase after the generation;
- the recovered plaintext is not the plaintext that was sealed.

In every one of those cases the outcome is recorded as `instrument_aborted`: H64 **untested**. It is
never converted into a negative result, and the design is never adjusted afterwards to rescue it.

## Amendment log

This document was written before the analysis plan, the generator spec, the bank nonce and the
tested-system freeze, and before any H64 observation existed. It was then amended three times, all
before the freeze and all before any model was called. They are listed rather than folded in
silently, because a preregistration that quietly changes is not a preregistration:

1. **One fenced diagnostic arm added.** `FULL_BUDGET_PLUS`, on the condition the complexity budget
   already stated, after pre-freeze review measured that the policy-holding arms returned
   `undetermined` on 17 of 25 unreachable demands. Reasoning and running arm count in
   `COMPLEXITY_BUDGET.md`. It cannot enter the primary comparison and cannot create a positive.
2. **The multiplicity position recorded**, checked against the committed records of H59, H60, H62
   and H63 rather than recalled.
3. **The observation budget stated as a limitation**, once it was established that the endpoint is
   budget-constrained resolution rather than resolution as such.

No amendment changed the arms of the 2×2, the endpoint, the statistical rule, α, the ten-point
effect floor, the guards, the verdict states, the bank size, or the admissibility minimums.

A DEVELOPMENT rehearsal of the whole pipeline was run before the freeze, and its outcome —
including its verdict, which was `negative` on a devkit bank — is recorded in
[`DEVELOPMENT_REHEARSAL.md`](DEVELOPMENT_REHEARSAL.md). Nothing in this document was changed in
response to it.
