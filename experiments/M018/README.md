# M018 — Dissolution

## Why

M017 measured that accumulation alone eventually costs. A library inherited from an
environment with disjoint motifs gives **0.69×** — strictly worse than no library at
all, on four pairs out of four. Its macros never apply and still inflate the branching
factor on every episode.

The project had never given an organism the right to **destroy** what it had learned.
Since M012b everything ran one way: absorb, transport, accumulate. M018 opens the other
direction.

## What this is not

It is not a discovery of this project. The **utility problem** has been established
since the 1980s–90s on systems that learn macro-operators: as they accumulate, they
become slower than if they had learned nothing, and Markovitch and Scott showed that
selective forgetting was a necessity rather than a refinement. Loss of plasticity in
continual learning tells the same story, and its known remedy is to periodically
reinitialise the least useful units.

What M018 adds is not the idea but the **decidable domain**. Exact equivalence is
provable, explored nodes are countable, the effect is isolable. On the question "must one
destroy in order to keep improving", an exact result is possible where the literature
produces curves.

## The three mechanisms

| | What it does | What it costs |
|---|---|---|
| `UtilityForgetting` | discards symbols that never served, past a grace period | reactive: you must already have paid to know |
| `BudgetForgetting` | hard cap; admitting one forces evicting one | the trade is paid continuously |
| `DissolutionForgetting` | discards **every** macro, halves the pattern counts | the most radical, and the only one expected to cost |

The control is `NoForgetting` — M017's organism, which accumulates and never discards.

## The constraint that makes the problem hard

The organism **never reads what a macro does**. It knows only its use count and its age.
That is deliberate, and it is the exact constraint of an organism manipulating code
nobody understands: judge on use, never on semantics.

A symbol's cost is **uniform** — it multiplies the branching factor whatever its utility.
That is what makes the accounting honest and integral: a never-used symbol is pure cost,
with no weighting required.

## The caterpillar

Inside the chrysalis, most of the caterpillar's body is dissolved. What survives fits in
a few imaginal discs — and, experimentally, part of the learned memory.

`DissolutionForgetting` copies that structure: the macros — the body — all go; the
pattern counters — the plan — survive, halved. What still recurs will clear the threshold
again and be reborn; what no longer recurs will not return.

**Where the metaphor stops:** the butterfly's plan is in the genome, specified in
advance. The project has already done that — it is M012b, building a body from a given
contract. What M018 aims at is harder than biological metamorphosis: that the organism
choose the form nobody wrote.

## Status

Development. See [`PROTOCOL_DRAFT.md`](PROTOCOL_DRAFT.md) and [`STATUS.md`](STATUS.md).
