# M022 — Adaptation-stress development protocol

**Status: DEVELOPMENT ONLY. Not frozen, hashed or canonical.**

## Question

M021 separated four selection measures on exact held-out quality, but adaptive and
frozen audits were nearly identical. M022 preserves that result and asks a separate
question: can a staged held-out sequence expose competence acquired after the audit
starts?

## Sequence

The evaluator creates three irreducible transformation motifs and selects four
noise-free episodes for each motif on different source automata. Episodes are
interleaved by round, producing twelve cases. Rounds 0 and 1 allow the abstraction
threshold to be reached; rounds 2 and 3 measure later reuse.

The builder rejects duplicate source automata across the complete sequence. The
development artifact records every paired episode, not only aggregate scores.

## Paired copies

Both copies start from the same deep-copied pre-audit state and receive identical cases,
oracles and search budgets.

- The adaptive copy persists across the complete sequence.
- The frozen copy is restored from the pre-audit template before every episode.

Every announced success is checked by exact behavioural equivalence. A false success is
fatal.

## Primary development signal

For late episodes solved by both copies:

`late_cost_ratio_per_mille = frozen_late_nodes * 1000 // adaptive_late_nodes`

A ratio of 1000 means no cost advantage. Solve counts are reported separately, and a
cost advantage cannot pass when the adaptive copy solves fewer late episodes.

## Controls written before execution

The self-extending positive control must have:

1. at least three common late solved episodes;
2. adaptive late solves not below frozen late solves;
3. late cost ratio at least 1500 per mille;
4. at least one macro after the adaptive sequence.

The open-search negative control must have:

1. equal adaptive and frozen solve counts;
2. late cost ratio exactly 1000 per mille;
3. zero macros after the adaptive sequence.

If either control fails, no selection-measure adaptation result may be interpreted.

## Information boundary

Motifs, target automata and exact verification belong to the evaluator. Organisms see
only source automata and behavioural query oracles. Selection rankers receive no M022
outcomes.

## Development order

1. pass the one-seed positive and negative controls;
2. repeat controls across paired seeds;
3. pre-write an adaptation decision rule;
4. only then evaluate populations selected by the M021 rankers.

M021 transferred-quality evidence and M022 adaptation evidence remain separate.
