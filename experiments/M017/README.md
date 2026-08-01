# M017 — Self-extending language

## Why this experiment jumped the queue

The roadmap placed M017 sixth, behind memory (M015) and sensorimotor competence (M016).
**The order was wrong, not the names.**

M012b, M013e, M014b and M014c share a limit none of their criteria measured: the
organism can only express what was hand-written for it. In `m014c_meta.py`,
`MetaPlasticitySession.identify` enumerates exactly `passport.programs` — twelve
programs. All "learning" consists of reweighting group counters over that closed
catalogue. Facing a target that is not in it, the organism can only abstain: never
invent.

Adding memory or sensorimotor competence to that organism would have laterally extended
a paradigm whose core is not established. M017 attacks that core.

## The question

Can an organism whose starting vocabulary holds only atoms **absorb** the recurring
compositions of its environment, and gain from it an expressive power and a search cost
its twins do not have?

## The three organisms

| | Catalogue | Composes | Absorbs |
|---|---|---|---|
| `ClosedLibraryOrganism` | 12 frozen programs | no | no |
| `OpenSearchOrganism` | 36 atoms | up to 3 | no |
| `SelfExtendingOrganism` | 36 atoms, then more | up to 3 | **yes** |

The first reproduces M014c's capability exactly. Its incapacity is **structural**, not
slowness — and that is what gives M017 an effect size M014b could never obtain.

## What M017 corrects in the method

M014b compared 14 queries to 14 queries, over a window four queries wide. No criterion
there could separate signal from sampling noise.

M017 measures the **number of programs evaluated before finding one**, which ranges from
one to hundreds of thousands. The oracle cost is deliberately held constant across the
three organisms — same probing, same confirmation — so it cannot confound the
comparison.

## Status

Development. No canonical evaluation is permitted: see [`STATUS.md`](STATUS.md) and
[`PROTOCOL_DRAFT.md`](PROTOCOL_DRAFT.md).
