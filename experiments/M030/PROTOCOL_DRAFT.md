# M030 — Untouched-seed component-uniform confirmation protocol draft

**Status: FROZEN FOR THE M030 DEVELOPMENT CONFIRMATION. Not canonical.**

## Question

Does the component-uniform diagnostic observed in M029 reproduce on an untouched block
of structural and stochastic seeds when promoted to a primary comparison before those
seeds are evaluated?

## Why a separate experiment is required

M029 registered `component_adaptive` against `development_adaptive` as its primary
comparison. `component_uniform` was explicitly diagnostic. It produced 50 wins,
14 ties and no losses on seeds 0–63, but that observation cannot be converted into a
confirmed M029 claim after the fact.

M030 performs the clean successor: the exact frozen M029 code paths are compared on
seeds 64–127, which were not executed by M029's unit tests, smoke run or complete
comparison. M030 unit tests and smoke execution use seeds 128 and above. No M030
development command may execute a seed in 64–127 before the pre-result commit exists.

## Frozen mechanisms

M030 adds no evaluation or selection mechanism. It calls M029's frozen implementations:

1. `development_adaptive` — M028's development-performance adaptive evaluator;
2. `component_uniform` — M029's hidden-disjoint component probe with uniform
   evaluation targets.

Coverage, component tasks, unique task orders, evaluation schedule, clade parent
selector, 40-expansion budget, development final selector, exact hidden evaluator and
all isolation boundaries are unchanged.

## Pairing and scale

- exactly 64 paired confirmation seeds numbered 64 through 127;
- mismatch and aligned rigs;
- two frozen policies, for 256 total trajectories;
- exact common coverage and 40 post-coverage expansions;
- deterministic unique task orders and per-state action orders;
- integer-only stochastic decisions;
- four worker processes by default.

Fewer than 64 paired seeds must report `insufficient_paired_seeds`. Any complete
64-seed set other than exactly 64–127 must report `confirmation_seed_range_mismatch`
and cannot support the prediction.

## Pre-written prediction

The component-uniform diagnostic is confirmed only if all of the following pass:

1. the confirmation seed set is exactly 64–127;
2. component-probe disjointness and shortcut/generic structural controls pass;
3. component-uniform median weighted-clade/exact-CMP concordance is non-negative;
4. that concordance exceeds development-adaptive concordance by at least 167 per
   mille;
5. median paired final hidden quality exceeds development adaptive by at least
   167 per mille;
6. component uniform wins at least 40 of 64 paired mismatch seeds;
7. exact coverage, unique-task evaluation, selector isolation and aligned
   visible/hidden equality all pass.

All gates are conjunctive. Estimator alignment without final policy advantage is
reported separately and does not count as confirmation.

## Prohibited conclusions

M030 is an internal untouched-seed development confirmation, not a canonical sealed
evaluation. It cannot establish a domain-independent potential measure, reproduce a
complete external system or establish software-scale recursive improvement. A failed
gate must not be repaired by changing the seed block, threshold, component tasks,
evaluation schedule or frozen policy code after observation.
