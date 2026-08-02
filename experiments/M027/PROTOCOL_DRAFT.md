# M027 — Hidden-blind seeded clade guidance protocol draft

**Status: FROZEN FOR THE M027 DEVELOPMENT RUN. Not a canonical protocol.**

## Question

After a hidden-blind exploration phase has exposed every lineage through the minimum
reward-bearing depth, does observed clade guidance become a better estimator and a
better parent-selection policy than immediate-performance guidance?

## Relationship to M026

M026 established an exact performance/potential reversal but did not support its
HGM-inspired policy prediction. Its clade estimator could not value productive
descendants that the expansion process had rarely exposed.

M027 does not change the M026 task generators, sealed suites, exact scores, public
selector inputs, DGM-inspired equation, HGM-inspired clade aggregation, action order or
visible final-selection rule. It adds one common intervention before policy selection.

## Hidden-blind layered coverage

For parent depths zero, one and two in that order, the runner expands every publicly
expandable node until no unique child remains. This enumerates every reachable state
through depth three.

The scheduler reads only public node depth and expandability. It does not read action
names, macro states, development score magnitude, hidden cases, hidden scores or exact
potential. Exhaustiveness is checked against the finite evaluator after the phase, not
used to choose expansions.

Depth three is fixed structurally before the comparison: the positive rig's first
generic reward requires platform plus two generic edits. Shallower coverage cannot
guarantee an observed productive descendant under an arbitrary fixed action order.

Coverage requires exactly 97 expansions in the mismatch rig and 63 in the aligned rig.
Every compared strategy receives the identical archive for a paired rig and seed, then
receives 40 additional policy-selected expansions.

## Policies

1. `dgm_immediate` — M026's fixed-point adaptation of immediate-performance guidance;
2. `hgm_clade` — M026's clade-aggregated Thompson-sampling adaptation;
3. `uniform` — public archive baseline;
4. `oracle_guided` — evaluator-only positive control for parent selection.

These are narrow policy adaptations, not reproductions of their source systems.

## Pairing and scale

- 64 paired seeds numbered 0 through 63;
- both mismatch and aligned rigs;
- complete layered coverage followed by 40 policy expansions;
- deterministic common task families and per-state action orders;
- integer-only stochastic decisions;
- four worker processes by default.

Below 64 paired seeds, output must say `insufficient_paired_seeds`.

## Pre-written prediction

Layered coverage will expose at least one non-zero hidden-quality node in every mismatch
run. Once this evidence exists:

1. the clade estimate on HGM-guided archives will have non-negative median concordance
   with exact rooted-clade quality;
2. that concordance will exceed immediate-performance concordance by at least 167 per
   mille;
3. `hgm_clade` will exceed `dgm_immediate` by at least 167 per mille in median paired
   final hidden quality;
4. `hgm_clade` will win at least 40 of 64 paired mismatch seeds;
5. the aligned control will retain exact visible/hidden equality.

The seeded-clade prediction is supported only if all five conditions pass together
with exact coverage and selector isolation. Estimator alignment without policy
advantage is reported separately and does not count as support.

## Prohibited conclusions

M027 cannot establish general superiority of HGM or DGM, reproduce either system,
validate their scheduling stacks, establish software-scale recursive improvement or
support any canonical claim. A failed policy gate must not be repaired by changing the
threshold or coverage depth after observation.
