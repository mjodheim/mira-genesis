# M034 — reachability as an exact capability measure

**Status: development measurement result — primary seeds remain unobserved**

## Why cost was the wrong measure

M033's body-anchored block returned the strongest number of the construction track: the
complete lineage beat its own unchanged parent 32/0/0, at a median of 26 candidates
against 264.5.

That number is confounded. The complete lineage begins from its migrated body, which is
the *product* of the pre-migration task. It wins partly because it starts closer, not
because it can do more. Deterministic search cost cannot separate those two things, and
Gate 8 exists precisely to separate them — it is the gate that "distinguishes transported
output from transported intelligence".

## The measure

For a lineage with body `B`, tool registry `R` and budget `k`:

    R(lineage, k) = { behaviours obtainable from B within k edits }

The set is finite and enumerable in this domain, so it is ground truth rather than an
estimate. It dissociates cleanly:

- a better **body** moves *where* the set sits;
- a genuine transported **capability** makes the set *larger* at a common body.

Held at a common body, any difference in size is attributable to retained machinery alone.

## Result 1 — a learned tool adds no capability

At a common body, with and without the learned tool, under the current budget rule:

| Budget | No learned tools | With learned tool |
|---|---:|---:|
| 1 | 2/16 | 2/16 |
| 2 | 5/16 | 5/16 |
| 3 | 7/16 | 7/16 |

The sets are not merely the same size, they are identical. Adding a second tool from an
earlier cycle — the D013 reactivation case — explores 906 sources instead of 895 and
arrives at the same 7 behaviours.

This is structural rather than empirical. A learned tool is a composition of primitive
operations, and its operations are charged individually against `max_edits`. Anything it
reaches is therefore a primitive composition already reachable within the same budget. It
can reorder search; it cannot extend reach.

That closes the question D013 left open. The learned-tool ablation was not inert because
of replay semantics alone, but because **a budget-neutral macro cannot carry capability**.
Repairing the kernel would not have changed this, and neither would any choice of task.

## Result 2 — charging a macro as one edit does add capability

The same tool, charged as a single edit:

| Budget | No tools | Per-operation (today) | Unit cost |
|---|---:|---:|---:|
| 1 | 2/16 | 2/16 | **4/16** |
| 2 | 5/16 | 5/16 | **6/16** |
| 3 | 7/16 | 7/16 | **10/16** |

The old set is a proper subset of the new one at every budget. Retained experience becomes
reachable capability rather than a bookmark.

This is D009 restated at the level of tools, in its minimal measurable form. It also gives
M017 a decidable success criterion it has never had: *does a self-extending language
increase reachability at constant budget?*

## What this does not settle

- **Memory is not covered.** It acts outside the rewrite search, selecting a starting point
  from current evidence, so a common-body reachability comparison cannot see it. A second
  measure is required, or reachability computed from the memory-selected start.
- **A unit-cost macro can cheat.** If a macro encodes a complete answer, unit cost makes it
  a lookup. The existing "no answer replay" control and requirement 6 of the M033 protocol
  already forbid this; both must be tightened before a unit-cost macro enters a primary
  comparison, not invented afterwards.
- **No claim is made about post-migration plasticity.** This is a measurement result about
  the instrument, not a result about a lineage.

## Kernel generation

Produced under kernel generation 2, after the D014 negative-constant repair. Generation-1
artifacts are retained and scoped rather than re-run, per D015. Cost figures are comparable
only within a generation; reachability sets are comparable across generations, which is a
further argument for preferring them.
