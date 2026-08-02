# M031 — Structural transport of component guidance protocol draft

**Status: FROZEN FOR THE M031 DEVELOPMENT COMPARISON. Not canonical.**

## Question

Does M030's uniform component-guidance advantage transport to a composition generator
whose component size, task arity, incidence rule and dependency topology all differ
from the generator on which the signal was discovered and confirmed?

## Structural intervention

M029/M030 used four length-two motifs, all unordered motif pairs, reversed hidden
pairs, one platform prerequisite and depth five. M031 replaces that generator with:

1. four length-three generic motifs;
2. eight development triads in two cyclic orders per starting component;
3. eight hidden triads using non-reversal permutations of the same components;
4. two independent scaffolds, each unlocking half of the generic motifs;
5. an MDL limit that permits two abstracted motifs plus one primitive motif inside a
   triad, making component quality observable before the complete solution;
6. depth five, exactly enough for both scaffolds and any three generic motifs;
7. one shortcut per development triad: eight shortcuts cannot fit within depth five,
   and one shortcut consumes the slot needed by a complete reusable lineage.

The aligned control uses separate fixed development and hidden contexts around the
same cyclic triads. Its exact visible and hidden quality must match for every reachable
state. Eight inert, depth-consuming decoys preserve the mismatch rig's action count and
ensure that both controls can execute the complete 40-expansion schedule.

## Frozen comparison

M031 transports the two policies promoted by M030 without adding an optimiser:

- `development_adaptive` allocates unique development-task observations by the frozen
  individual Thompson rule;
- `component_uniform` allocates unique hidden-disjoint single-component and repeated-
  component probes uniformly.

Both policies receive exact breadth coverage through depth three, one initial
observation per covered node, two warmup observations per covered node, the same 40
post-coverage expansions, two post-expansion observations, the same weighted-clade
parent selector and the same exact development final selector. Hidden cases and exact
rooted-clade quality remain evaluator-only.

## Seed boundary and scale

- exactly 64 paired primary seeds numbered 0 through 63;
- mismatch and aligned rigs;
- two frozen policies, for 256 total trajectories;
- four worker processes by default;
- tests and smoke execution use only seeds 64 and above before the pre-result commit.

Fewer than 64 paired seeds must report `insufficient_paired_seeds`. Any complete
64-seed set other than exactly 0–63 must report `development_seed_range_mismatch` and
cannot support transport.

## Pre-written prediction

Uniform component guidance transports only if all of the following pass:

1. the primary seed set is exactly 0–63;
2. every structural-distinction, probe-disjointness, shortcut, depth-viability and
   aligned-quality control passes;
3. component-uniform median weighted-clade/exact-CMP concordance is non-negative;
4. that concordance exceeds development-adaptive concordance by at least 167 per
   mille;
5. median paired final hidden quality exceeds development adaptive by at least
   167 per mille;
6. component uniform wins at least 40 of 64 paired mismatch seeds;
7. coverage, unique-task evaluation, integer-only selection, selector isolation and
   aligned visible/hidden equality all pass.

All gates are conjunctive. Estimator alignment without final policy advantage is
reported separately and does not count as transport.

## Prohibited conclusions

M031 is a finite internal development transport test, not a canonical sealed
evaluation. Its generator still exposes a known public grammar. A positive result
does not establish domain-independent potential measurement, software-scale recursive
improvement or optimality of uniform evaluation. A failed gate must not be repaired by
changing the generator, seed block, thresholds, schedule or policy after observation.
