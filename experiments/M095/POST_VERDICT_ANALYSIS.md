# M095 — post-verdict analysis of attempt 1

The frozen local qualification ran once on 22 August 2026 from clean source commit `951c7c2`.
Its preserved result is negative. This document analyses that result; it does not amend the
protocol, pool, mechanism, runner or checker, and it is not evidence for a retry.

## The result

- attempt 1, no prior or withdrawn result;
- zero model calls and zero network calls;
- all nine members of the exhaustive structural population ran;
- **0/6** demand-bearing entries demonstrated the enabling relation;
- **3/3** zero-inner-demand entries remained negative;
- the checker recomputed all eleven conditions: **8 passed, 3 failed**;
- failed conditions: P3, P5 and P6;
- result digest: `bdd35111220f256f86c19194428cb3ce60b8a04488c161109a1c92887a401e75`;
- checker digest: `bb24a484012d123d0336fb7c1974e58255222b6c91ce0bb22770f42e58d5d42f`.

P7 passed: every preserved entry replayed with the same evidence. The negative result is therefore
not an unreadable artifact or a one-off process failure. P8 and P9 also passed: the development
arrangement arm still demonstrates six demand-bearing points, four without descent, and the
exhaustive more-budget arm still cannot reach B from S0 while showing the searcher alive at S1.

## What the population exposed

A is reached in every one of the six positive entries and makes the nested operation structurally
applicable. B then has structural survivors, but **none is confirmed by execution**.

The renderers adopted for A reveal the common cause:

- `Coordinate` was required to produce `x_axis` and `y_axis`, but its adopted mapping also carries
  `x` and `y`, with unrelated wrappers;
- `Vector` was required to produce `x`, `y` and `z`, but its adopted mapping also carries
  `horizontal`;
- `Marker` was required to produce `code` and `confidence`, but its adopted mapping also carries
  `active`.

The local A requirement uses subset semantics: execution confirms that every required key has the
required value, but does not reject extra top-level keys. When B calls that renderer inside a nested
field, the caller's requirement compares the complete nested mapping. The extra keys then matter,
so every B candidate disagrees with the behaviour the caller wrote.

The development world did not expose this because its inner mapping's keys and declared fields
coincide exactly. The qualification varied precisely that assumption — re-keying, larger arity and
unrelated omitted fields — and all three structural families failed in both ranking regimes.

## Scientific interpretation

M095 demonstrated **structural applicability growth** in development, but did not qualify
**behaviourally compositional reach**. A capability accepted under a partial local contract cannot
automatically serve as a value inside a stricter nested contract. H40, as frozen, is refuted by
attempt 1.

This is not repaired after the verdict. Any change to acceptance, synthesis or the nested operation
requires a new hypothesis and frozen experiment. At least three successor mechanisms are now
separable and falsifiable:

1. require a renderer to be contract-exact, rejecting every extra key;
2. synthesise a minimal renderer whose output contains exactly the demanded bindings;
3. let the nested operation project a broader renderer onto the nested contract, while proving that
   the projection is derived from the observed demand rather than an authored target-specific patch.

The previously planned M096 jump to endogenous operation acquisition is therefore premature. The
next experiment should first establish contract-safe composition across the structural population;
only then is it meaningful to ask the lineage to acquire a new operation for the real-software line.
