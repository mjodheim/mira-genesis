# M037 — a replayable lineage, and a tuning illusion

**Status: development result. Confirmed on untouched cases. No canonical claim.**

## What was missing

M035 showed a population reaching targets its founder provably cannot express. Each
organism recorded `parent_digest`, which names the previous body but cannot rebuild it, so
the lineage could be counted and not replayed.

Gate 9 requires that "the full lineage must remain replayable from the original seed and
immutable inputs".

## What was added

Every organism now carries its complete chain of `Mutation` steps — the operation itself,
not a pointer to its outcome. `replay(founder, ancestry)` rebuilds any descendant from the
founder body and the chain alone: no seed, no population, no search.

| Check | Result |
|---|---:|
| Lineages replayed byte-for-byte, development | 20 of 20 |
| Lineages replayed byte-for-byte, **untouched cases 12–23** | **12 of 12** |
| Deepest chain measured | 36 mutations |
| Winning lineage, deepest case | 47 generations, 21 mutations, 3 growths, 4→7 states |

A truncated chain provably does not rebuild the organism, so the record is load-bearing
rather than decorative.

## The selection rule was wrong, and the measurement said so

`minimal_criterion_survivors` sorted by score and cut at capacity. That is elitist
truncation wearing a minimal criterion's name, and M021 measured that rule as the most
destructive of the four it compared — 0 per mille against 750 for the minimal criterion.

The symptom was unmistakable once swept: **raising generations from 60 to 150 changed
nothing, on every configuration tested.** The population reached a fixed point and stopped
exploring.

Deduplicating by body before the cut restores exploration. Generations then matter again.

### One correction on the way, recorded because it was instructive

The first replacement ordered the distinct bodies by structural cost. It scored **0 of 12
on every configuration**. Cost rises with size, so a size-ordered cut discards precisely
the organisms that have grown: the diversity rule was selecting against the capacity
increase the experiment exists to measure.

Both errors share a shape. A minimal criterion **admits or rejects**; it does not rank.
Each time an order was slipped into it — by score, then by size — a pressure returned that
the mechanism cannot survive.

## The tuning was an illusion

A sweep over generations, population and growth margin found 9/12 on cases 0–11, against
6/12 for the delivered defaults. That looked like a 50 per cent improvement.

It was selection on the test set. Confirmed on cases 12–23, never previously run:

| Configuration | Cases 0–11 | **Untouched 12–23** |
|---|---:|---:|
| control, no growth | 0/12 | **0/12** |
| delivered defaults | 6–7/12 | **5/12** |
| swept "best" configuration | 9/12 | **3/12** |

The swept configuration is not merely no better — it is **worse** than the defaults on
fresh cases. The sweep did not improve the mechanism; it found the parameters that
flattered the twelve cases being watched.

The delivered defaults generalise: 5/12 on cases never used to choose anything, against a
control that remains at 0 by proved impossibility rather than by budget.

This is the sixth time in this session that a result turned out to be an artefact of its
own measurement. It is the first that was caught by protocol rather than by accident: the
untouched block exists precisely for this, as M030 used seeds 64–127 to confirm M029.

## Limits

Twelve confirmation cases, one generator, development only. The rate is 5/12, not a solved
problem. The selector remains the open question it has been since M014b — the correction
here fixed an implementation that contradicted M021's own measurement, and did not advance
the underlying problem.
