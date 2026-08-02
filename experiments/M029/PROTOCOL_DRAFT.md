# M029 — Hidden-disjoint component-probe protocol draft

**Status: FROZEN FOR THE M029 DEVELOPMENT RUN. Not canonical.**

## Question

When current development performance is an inverted proxy for hidden descendant
quality, can a public, hidden-disjoint compositional transfer probe supply the missing
information for evaluation routing and clade guidance?

## Relationship to M028

M028 changed observation weights without changing the information that produced those
weights. Individual-performance Thompson sampling allocated less evidence to
evaluator-identified high-potential observed nodes than uniform allocation did, and
the weighted clade estimate remained anti-aligned with exact CMP.

M029 changes the evaluation signal, not the coverage, evaluation schedule, adaptive
target algorithm, clade parent algorithm, expansion budget, task generator, hidden
suite or final selector. The frozen M028 adaptive policy is rerun as the development
signal baseline.

## Component transfer probe

For every reusable generic motif `g` already present in a rig definition, the evaluator
creates two probe tasks:

1. express `g` within one symbol;
2. express `g · g` within two symbols.

The mismatch rig therefore has eight component tasks and the aligned rig has twelve.
The complete sequence of every probe task must be absent from both the development and
hidden suites. A shortcut macro cannot pass either probe for any generic motif at the
fixed symbol limits. A state containing the platform and one generic macro passes both
probes for that motif and retains exact maximum hidden clade quality.

The probe is evaluator-defined before the run. Policies never receive motif identities,
rewrite states, action names, task sequences, hidden cases, hidden scores or exact CMP.
They receive only the same public structure and success/failure counts as M028.

This construction deliberately tests compositional transfer. It is not a general
definition of potential and it uses the finite rig's known public task grammar. Its
value must come from separation from the hidden suite, not from a claim that the probe
is domain-independent.

## Compared policies

1. `development_adaptive` — the frozen M028 adaptive policy and development suite;
2. `component_uniform` — the component probe with uniform evaluation targets;
3. `component_adaptive` — the component probe with individual-performance Thompson
   evaluation targets.

All policies receive M027's exhaustive hidden-blind coverage through depth three.
They use M028's fixed schedule: one initial unique evaluation per covered node, two
additional evaluations per covered node in aggregate, then 40 common
weighted-clade-selected expansions with one initial and two allocated evaluations per
new node. No node/task pair can repeat. Final selection uses the complete development
suite and node identifier tie-break exactly as in M027 and M028.

`component_uniform` is diagnostic. It determines whether the probe itself supplies
useful information even without adaptive concentration. The primary comparison is
`component_adaptive` against the frozen `development_adaptive` baseline.

## Pairing and scale

- 64 paired seeds numbered 0 through 63;
- mismatch and aligned rigs;
- three policies, for 384 total trajectories;
- exact common coverage and 40 post-coverage expansions;
- a total evaluation count equal to three times each final archive size;
- deterministic unique task orders and per-state action orders;
- integer-only stochastic decisions;
- four worker processes by default.

Below 64 paired seeds, output must say `insufficient_paired_seeds`.

## Pre-written prediction

The component signal is supported only if all of the following pass together:

1. every component task is disjoint from both development and hidden suites, and the
   shortcut/generic structural control passes in every seed;
2. `component_adaptive` allocates at least 167 per mille more non-initial evaluations
   to high-potential observed nodes than `development_adaptive` does;
3. `component_adaptive` median weighted-clade/exact-CMP concordance is non-negative;
4. that concordance exceeds `development_adaptive` by at least 167 per mille;
5. median paired final hidden quality exceeds `development_adaptive` by at least
   167 per mille;
6. `component_adaptive` wins at least 40 of 64 paired mismatch seeds;
7. exact coverage, unique-task evaluation, selector isolation and aligned
   visible/hidden equality all pass.

Component-estimator alignment without final policy advantage is reported separately
and does not count as support. Component adaptive versus component uniform outcomes are
reported diagnostically and are not gates for the signal hypothesis.

## Prohibited conclusions

M029 cannot establish a general measure of potential, reproduce HGM or DGM, validate
their full systems, establish software-scale recursive improvement or support a
canonical claim. A failed gate must not be repaired by exposing hidden cases, changing
the component definition, tuning thresholds or changing the evaluation schedule after
the full result is observed.
