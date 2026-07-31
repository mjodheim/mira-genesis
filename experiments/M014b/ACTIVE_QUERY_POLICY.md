# M014b active query policy

The inherited plasticity passport selects behavioral experiments with a deterministic two-stage objective:

1. minimize the largest remaining hypothesis branch by candidate count;
2. among equally robust splits, minimize posterior probability concentration and maximize learned-prior information gain;
3. use query length and lexical order only as deterministic tie-breakers.

This minimax-first ordering protects the learner from a development prior that does not exactly match the sealed target distribution. The random-query baseline uses the same hypothesis language, prior, repetition count and budgets, differing only in experiment selection.

The policy was introduced before the canonical PR was opened. The frozen requirement remains unchanged: median identification must be at least 20% better than both random querying and the no-learned-passport baseline.
