# M037 — adopted-mutation replay, a selector correction, and a tuning illusion

**Status: development result. No canonical claim. This establishes a Gate 9 *prerequisite*,
not Gate 9.**

## Three levels of replay, and which one this reaches

| Level | Meaning | Status |
|---|---|---|
| 1. body reconstruction | rebuild the final DFA | reached |
| 2. **adopted-mutation replay** | rebuild the chain of adopted transformations from a **supplied** founder | **reached** |
| 3. full lineage replay | reproduce the whole trajectory causally from the seed and committed inputs | **not reached** |

Gate 9 requires level 3: "the full lineage must remain replayable from the original seed
and immutable inputs". What follows is level 2, and the distinction is not cosmetic.

`replay(founder, ancestry)` takes a founder **DFA**, not a seed. It does not reconstruct
the founder's construction, the task families revealed, the observations received, the
candidates proposed or rejected, the evaluation costs, the admissible set, the capacity
reduction decision, or any migration, rollback or learned tool. Selection decisions are
**not recomputed** — only the winner's own transformations are stored, so a different
selection rule would yield a different lineage that this replay could not detect.

## What was missing

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

## The selector was misnamed, and its justification was false

Two separate errors, both recorded rather than quietly fixed.

**It ranked what it claimed to admit.** `minimal_criterion_survivors` sorted by score and
cut at capacity — and after the deduplication added here, it still sorted by
`(-score, structural_cost, digest)`. So it continued to favour high scores, favour small
bodies, and truncate. This document asserted that "a minimal criterion admits or rejects;
it does not rank" while the code ranked. **The documentation contradicted the
implementation**, which is the failure mode this repository exists to catch.

**Its justification was not what it cited.** The rule was described as chosen from M021's
measurement. `rank_by_minimal_criterion` in `m021_measures.py` filters on viability
(`ledger.solved > 0`), ranks the viable by **novelty**, ranks the rejected by energy, and
lets `Population.select` truncate. M021's 750 per mille belongs to *viability, then
novelty, then truncation*, in its own domain, and its report already says it is not a claim
about the general family. M035 implemented none of that.

### Three selectors, named apart

| Name | What it does | Whose result it owns |
|---|---|---|
| `thresholded_elitist_truncation` | threshold, rank by agreement, prefer small, truncate | M035's 6/12 |
| `viability_then_novelty` (M021) | viability bar, novelty rank, truncate | M021's 750 per mille |
| `minimal_admission_with_body_diversity` (M037) | threshold only, then uniform reduction over distinct bodies | its own, yet to be measured on a sealed block |

The third is a **new** development selector. It inherits nothing from M021.

### The unit of reduction is declared, not discovered

Reduction is uniform over **distinct bodies**, and that is an explicit diversity policy —
not neutrality between organisms. Ten clones present one candidacy.

Chosen on mechanism before any measurement: the property under test is *structural* drift,
and under per-individual reduction a heavily replicated clone crowds out rare structures by
multiplicity alone, which is a pressure toward whatever replicates best. Growth's cost stays
in `VariationBudget` and in the reported result, and is deliberately not reintroduced as a
survival pressure.

The reduction key is `SHA-256(domain || commitment || seed || generation || body_digest)`.
It receives no score, no size and no input position, and it draws from a separate hash
rather than the mutation generator — sharing that stream would make the number of admitted
organisms shift every later variation, coupling selection to variation.

## The old rule's symptom, which is what exposed it

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

## Both case blocks are now consumed

| Block | Role | Status |
|---|---|---|
| cases 0–11 | development and tuning | **consumed** |
| cases 12–23 | untouched confirmation | **consumed** |

Cases 12–23 did their work: they showed the swept configuration did not generalise. But
that outcome then informed the decision to keep the delivered defaults, so they are no
longer an intact block. They may support that specific conclusion and nothing further.

They may **not** be used to choose between per-individual and per-body reduction, to tune a
threshold or population, to decide between architectures, or to confirm any later
independent claim. The unit of reduction above was fixed on mechanism before measurement
precisely so that no consumed block could be asked to decide it.

A fresh block must be committed and guarded before the next experimental decision, with a
guard preventing unit tests, development scripts, ordinary workflows and parameter sweeps
from opening it.

## Limits

The 5/12 figure belongs to `thresholded_elitist_truncation`, the historical selector, on a
block that is now consumed. `minimal_admission_with_body_diversity` has **not** been
measured on a sealed block, and any rate obtained for it on consumed cases is descriptive
only — it can document the consequence of the correction, and cannot validate it.

A performance drop is possible and would be reported as such. The rule was chosen to match
its stated definition, not to improve a number.

The selector remains the open question it has been since M014b. Naming three selectors
apart does not solve it; it only stops one of them borrowing another's evidence.
