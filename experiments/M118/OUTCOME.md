# M118 — instrument design and audit: CLOSED

**M118 is an instrument-design and audit milestone, not a failed experiment.** It was stopped
deliberately, before any scientific generation, because pre-freeze hostile review showed the
measurement it inherited — and the correction built for it — were too complicated to trust as a
one-shot instrument.

| | |
|---|---|
| Milestone status | **instrument-design completed** |
| H63 | **untested** — never frozen |
| H63 carrier bank | **never generated** |
| H63 scientific statistic | **never computed** |
| Qualifying scientific invocations | **0** |
| Generality gates G1–G10 | **unchanged** |
| Successor | M119 / H64 |

## What succeeded

**Readiness calibration passed on the fixed OpenInference route.** Under a frozen gate the route
returned identity exact on every request, **0 of 9 required schema feature classes unenforced**, the
intended reasoning state with zero reasoning tokens, and a census-dominating stress at HTTP 200,
`finish_reason: stop`, **73,731 conforming completion tokens**.

That result stands and carries forward to M119. It is instrument evidence, not evidence for any
hypothesis.

## Why M118 stopped

Two independent hostile reviews, both before any scientific observation, found defects in the
measurement design. The first found three in the **inherited** M113 apparatus; the correction for
those introduced further defects of its own, which the second review found. The pattern —
design → review → Tier-1 defect → repair → review → Tier-1 defect — is itself the finding:

> **A measurement that needs this much repair to be trustworthy is too complicated to be trusted as
> a one-shot scientific instrument.**

M118 therefore ends in a simpler successor rather than a third repair.

## Design findings preserved

These are why the successor is smaller. None of them changes any closed milestone's recorded result.

### Inherited from M113

1. **P22 was too weak.** A `+1` improvement on **any one** of four correlated measures sufficed.
2. **Attribution was omitted from the no-worse guard**, so a descendant *worse* on attribution
   agreement could still pass on one extra calibrated refusal.
3. **T0 was a degenerate constant comparator** — with no acquired rules the attributor falls through
   to a hardwired `operator_table` on every feature row of every carrier.
4. **Action spaces differed across arms**, because policy state gates the diagnostic probe:
   `policy_fires` is `bool(policy) and …`, so an arm without a policy cannot probe **at any budget**.
5. **`budget_plus` could not probe**, so it did not isolate budget from capability — the very thing
   it existed for.

### Introduced by the first correction, found by the second review

6. **The correction itself introduced Tier-1 defects.** Replacing T0 with a stronger comparator left
   nothing requiring the descendant to beat T0 at all: a positive verdict with an affirmative causal
   statement was reproducible while the descendant scored **worse than both** the constant arm and
   the rules-only ablation.
7. **Plan prose and executable decision rules diverged.** The analysis plan that would have been
   frozen still declared `P22` and `only_the_genesis_state_differs_across_arms` — a predicate that
   had been replaced and a claim that had been withdrawn — while the new comparator, α and the seed
   appeared in no commitment at all.
8. **Scientific budget could fork through CLI state.** The runner took `--session-budget` from argv,
   unbound to any committed plan, so the analysis could be re-run at different budgets until one
   suited.
9. **Checker independence was incomplete.** Guards were evaluated on runner-supplied aggregates
   rather than recomputed from per-demand evidence, and the comparator seed was read from the record
   instead of compared to the frozen constant.
10. **A nominally information-free comparator carried fixed structural bias.** Eight rows do not
    divide by three, and dealing over a fixed component order short-changed `candidate_space` in
    **400 of 400 seeds**.
11. **Underpowered evidence was misreported as negative.** A bank too small for significance to be
    *arithmetically* attainable was classified as evidence against the hypothesis.
12. **Some acquired state and provenance sat outside the freeze** — the M109 and M111 result bytes
    the arms are restored from are read at run time and were not digest-bound.

## Corrigenda

Wrong intermediate interpretations, corrected explicitly rather than quietly amended:

- The readiness gate's first abort was attributed to a token overage. **Refuted**: capped at exactly
  the declared ceiling the same endpoints still returned 400, while probes sending twice the ceiling
  returned 200. Recorded in
  [`READINESS_ATTEMPT_01_INSTRUMENT_ABORT/`](READINESS_ATTEMPT_01_INSTRUMENT_ABORT/README.md).
- A claim that *"only the Genesis state differs across arms"* was made in this milestone and is
  **withdrawn**. It is literally true and misleading: the state itself determines whether the
  diagnostic probe can fire.
- A 129-seed majority-vote ensemble was built to remove single-seed luck and **rejected**:
  majority-of-uniform is not uniform, and it produced a 1/2/5 assignment — a worse prior than the
  3/3/2 it replaced.

## Claim boundary

M118 measured no hypothesis. It produced **no carrier bank, no scientific statistic and no
qualifying invocation**, and it is **not evidence for or against any Genesis proposition**. G1–G10
are unchanged. Its DEVELOPMENT observations came from devkit carriers and say nothing about H63.

**M118 designed and audited an instrument, and showed it was the wrong one. M119/H64 runs a smaller
one.**
