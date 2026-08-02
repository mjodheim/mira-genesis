# M031 — Structural transport of component guidance result

**Status: DEVELOPMENT — UNIFORM COMPONENT SIGNAL TRANSPORTED. Not canonical.**

## Result identity

| Item | Value |
|---|---|
| Frozen implementation commit | `4eb61e20418c8088487bbd5bbe806780d375d819` |
| Protocol version | `M031-development-v1` |
| Protocol SHA-256 | `15607402465f1a364d25672baf0d1dfc87c9b25dda0b8e90dee37d8636a22948` |
| Primary seeds | exactly 0–63 |
| Trajectories | 256 |
| Expansions | 65,792 |
| Unique evaluations | 198,144 |
| Raw artifact bytes | 48,018,205 |
| Raw artifact SHA-256 | `934d0a76eb7d6dbe60c1524b62f6a5e3ad4798e08d03eceaba106e1d3a1f61d0` |
| Independent replay | byte-identical |
| Pre-result repository tests | 202 passed |

The raw artifact is intentionally ignored by Git. It is reproduced with:

```bash
python scripts/run_m031_structural_transport.py --seed-start 0 --seeds 64 --workers 4
```

## Frozen question

Does M030's uniform component-guidance advantage transport to a composition generator
whose component size, task arity, incidence rule and dependency topology differ from
the generator on which the signal was discovered and confirmed?

M031 retained the frozen policy contrast, evaluation schedule, depth-three coverage,
weighted-clade parent selector and development-only final selector. It changed the
task generator before observing any primary M031 seed.

| Property | M029/M030 generator | M031 generator |
|---|---|---|
| Generic motif size | two atoms | three atoms |
| Task composition | six unordered pairs | eight cyclic/permuted triads |
| Hidden transformation | pair reversal | non-reversal triad permutation |
| Dependency topology | one platform | two independent scaffolds |
| Shortcut count | six | eight |
| Development/hidden cases | six each | eight each |
| Expression limit | two symbols | five symbols |

The five-symbol limit makes two reusable triad components observable while leaving one
component primitive. Any three generic motifs plus both scaffolds solve the complete
suite at depth five. Adding a shortcut consumes the depth required by that reusable
lineage.

## Pre-result boundary

Tests and smoke validation used only seeds 64 and above. The four-seed smoke on 64–67
was explicitly underpowered and reported `insufficient_paired_seeds`; it was used only
to verify execution, structural controls and dynamic range. The primary block 0–63 was
first executed after commit `4eb61e2` fixed the implementation and complete decision
rule.

## Registered gates

| Gate | Required | Observed | Result |
|---|---:|---:|---|
| Exact primary seed range | 0–63 | 0–63 | pass |
| Component-uniform clade/exact-CMP concordance | ≥ 0 | 737 | pass |
| Concordance advantage over development adaptive | ≥ 167 | 1,070 | pass |
| Median paired final hidden advantage | ≥ 167 | 500 | pass |
| Component-uniform wins | ≥ 40/64 | 43/64 | pass |
| Structural transport controls | all | all | pass |
| Probe disjointness | exact | exact | pass |
| Coverage and unique-task controls | exact | exact | pass |
| Hidden fields visible to selectors | false | false | pass |
| Aligned visible/hidden equality | exact | exact | pass |

All conjunctive gates passed. The registered comparison status is
`uniform_component_signal_transported`.

## Primary comparison

On the mismatch rig, component-uniform weighted-clade/exact-CMP concordance was
737 per mille. Development-adaptive concordance was -333 per mille, producing a
1,070-per-mille separation.

Median final hidden quality was 500 per mille under component uniform and zero under
development adaptive. Their paired difference had median 500 per mille, with 43 wins,
18 ties and 3 losses.

| Final hidden quality | Component uniform | Development adaptive |
|---:|---:|---:|
| 0 per mille | 4 | 40 |
| 500 per mille | 49 | 23 |
| 1,000 per mille | 11 | 1 |

The paired differences were -500 in 3 seeds, zero in 18, +500 in 37 and +1,000 in 6.
Final component-probe quality was zero in 4 component-uniform runs, 500 in 49 and 750
in 11. Under development adaptive it was zero in 40 runs, 500 in 23 and 750 in one.

The aligned control preserved exact visible/hidden equality for both policies. Median
final aligned quality was 500 per mille under each policy.

## Reproduction

The complete 256-trajectory command was executed twice from the frozen commit. Both
artifacts had exactly 48,018,205 bytes and the same SHA-256:

`934d0a76eb7d6dbe60c1524b62f6a5e3ad4798e08d03eceaba106e1d3a1f61d0`

The replay was therefore byte-identical, including every coverage, evaluation and
parent-selection trace.

## Interpretation and limits

The reusable-component information effect is not confined to M029/M030's pair-reversal
generator. Under the frozen uniform observation rule, it remained positively aligned
with exact rooted-clade potential and improved final hidden quality after transport to
a split-scaffold triad generator.

This is still internal finite development evidence. The component probes are derived
from a known public grammar, the structural intervention remains inside the M017 macro
language, and only two task generators have been tested. M031 does not establish a
domain-independent potential measure, prove uniform evaluation optimal, reproduce a
complete external metaproductivity system or demonstrate open-ended improvement.

The transport question opened by M030 is complete. A resource-aware adaptive policy is
now a separate optimisation successor: it may test whether non-uniform allocation can
retain the transported information benefit without overweighting shortcut-contaminated
lineages. The independent construction track remains the opaque-substrate migration of
M025's complete rewrite, memory and exploration state.
