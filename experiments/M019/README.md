# M019 — Selection pressure

## What was missing

Evolution is not a variation engine. It is a **filtering-under-constraint** engine.
Without the constraint, variation is drift.

Until M018, Genesis had no stake. An episode was posed, it solved or abstained, and
nothing followed. The search budget was 200,000 nodes, deliberately generous, and
exceeding it cost an abstention with no consequence.

That explains M018's negative result: the three forgetting mechanisms returned nothing
because **there was nothing to be efficient for**. An organism that cannot starve from
its own inefficiency has no reason to become efficient.

## Three absences, three additions

| | What evolution has | What Genesis had |
|---|---|---|
| **Scarcity** | starving to death | a generous budget, failure without consequence |
| **Population** | the lineage outlives the individual | a single organism |
| **Variation on the encoding** | gene duplication then divergence | absorption of recurring motifs only |

### Scarcity

Energy **is** the search budget. An impoverished organism searches less far, so solves
less, so grows poorer. The starvation spiral is deliberate: it is what makes efficiency a
matter of survival rather than of elegance.

Ranking is on **energy left**, that is on what remains after paying for one's searches.
Solving expensively is worth no more there than not solving.

### Population

The caterpillar dissolves once, and if that fails, that caterpillar dies — not the
species. M018's organism was alone, so a strategy ruinous nine times in ten and brilliant
the tenth was forbidden to it.

Read that way, M018's negative result does not say destroying is useless: it says
**destroying is untenable for an isolated individual**. That is not the same thing, and
the second reading opens a door the first closed.

### Duplication

Evolution copies a gene and lets the copy drift, producing a new structure without
destroying the old one. Genesis absorbed recurring motifs but never duplicated a symbol
in order to vary a version of it. `duplicate_and_diverge` fills that gap.

## The question this finally allows

> Does a population under selection discover what I failed to design?

M018 showed that three hand-written forgetting mechanisms did not pay off. Here nobody
chooses: all four sit in the starting population and selection settles it. If it
converges on a setting none of my heuristics reached, the project holds for the first
time **an improvement nobody wrote**.

## Our advantage over evolution

Evolution is slow for two reasons: its variation is **blind**, and its fitness is
measured in generations. Here variation can be directed, and fitness is computed exactly
and instantly since the domain is decidable.

It is the one place where the smallness of the domain is an asset rather than a ceiling.

## Status

Development, and the rig is **not valid** — see [`STATUS.md`](STATUS.md). No conclusion
is drawn on the hypothesis. See also [`PROTOCOL_DRAFT.md`](PROTOCOL_DRAFT.md).
