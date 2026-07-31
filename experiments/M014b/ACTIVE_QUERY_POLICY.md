# M014b active query policy

The inherited plasticity passport selects behavioral experiments from a deterministic bounded pool containing every binary word of length 0 through 8. Candidate responses on that pool are precomputed once. If the bounded pool cannot distinguish the remaining hypotheses, the learner falls back to exact pairwise DFA witnesses, preserving completeness.

Within the available pool, the policy uses a deterministic multi-stage objective:

1. minimize the largest remaining hypothesis branch by candidate count;
2. among equally robust splits, minimize posterior probability concentration;
3. maximize learned-prior information gain;
4. use query length and lexical order only as deterministic tie-breakers.

This minimax-first ordering protects the learner from a development prior that does not exactly match the sealed target distribution. The random-query baseline receives the same bounded pool, hypothesis language, prior, repetition count and budgets, differing only in experiment selection.

The former development-only search over several length penalties was removed because every tested demonstration selected the neutral penalty. The serialized value remains explicit at `0.0`; the hypothesis language, schema prior and provenance hash remain learned from development demonstrations.

The policy was introduced before the canonical PR was opened. The frozen requirement remains unchanged: median identification must be at least 20% better than both random querying and the no-learned-passport baseline.
