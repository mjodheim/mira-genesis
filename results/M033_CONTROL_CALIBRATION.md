# M033 pre-threshold control calibration

**Status: development control evidence only — primary seeds remain unobserved**

## Evaluated identity

- implementation commit: `1c4e7b59c9a846d1b16d09ae47ef1c5478450832`;
- focused workflow run: `30792247244`;
- retained artifact ID: `8847545755`;
- workflow artifact digest:
  `a63c07e1005b86908d9527b3be2ebbab6409eae0e4a4219d0bf0e9bbf69cd25f`;
- fixed-structure raw JSON SHA-256:
  `e189142ccbe1465caf76a30d22b8f294974c2c2dcce1e224f3e61748c7f8b5bb`;
- structural raw JSON SHA-256:
  `117de3c31b03afcdb4a7f20eb6b2a5877513045e7f1540a6e03a026d63bb0723`;
- focused tests: 27 passed;
- repository integrity audit: passed;
- static post-migration isolation audit: passed;
- both complete calibration replays: byte-identical.

The fixed-structure calibration used only seeds `1024–1031`. The structural calibration
used only seeds `2048–2063`. The reserved primary block `0–63` was not instantiated or
observed.

## Fixed-structure rig

Each of eight seeds produced two control tasks and six lineage rows:

- complete M032 lineage;
- fresh-B learner;
- unchanged pre-rewrite parent migrated to B;
- output-only control;
- learning-state ablation;
- learned-tool ablation.

The positive family required the transported two-edit component plus one still-missing
post-migration edit. Replaying the learned tool alone was therefore insufficient. The
negative family required an unrelated one-edit repair. A separate memory path compared
a relevant trace, the same trace in a misleading order and a canonical empty state.

The evaluator's product-automaton equivalence decision was exhaustively checked against
minimal canonical ground truth for every pair of binary two-state DFAs. A static audit
also proved that no pre-M033 module imports or reaches the M033 task generator, target
or held-out surfaces.

## Fixed-structure results

### Transported learned tool

All complete, fresh-B and unchanged-parent lineages reached exact equivalence on all
eight positive controls.

Median post-reveal rewrite candidate evaluations were:

| Lineage | Median candidates |
|---|---:|
| complete | **959** |
| learning-state ablated without memory routing | **959** |
| fresh-B | 976 |
| unchanged parent | 976 |
| learned-tool ablated | 976 |

The complete lineage used fewer candidates than fresh-B on **8/8** seeds and fewer than
the unchanged parent on **8/8** seeds. Removing learned tools erased the entire measured
advantage.

On the disjoint negative family, the complete lineage was better than fresh-B on
**0/8** seeds. Median candidate counts were 26 versus 25, exposing a small branching
cost rather than a false benefit.

### Functional transported memory

All relevant, permuted and empty-memory variants reached exact equivalence. Their median
total post-reveal candidate evaluations were:

| Memory surface | Median candidates |
|---|---:|
| relevant trace | **264** |
| canonical empty state | 959 |
| permuted trace | 960 |

The relevant trace was cheaper than both controls on **8/8** seeds. It did not contain a
complete answer: it selected one development-improving first exploration action, after
which the still-missing operations were discovered by bounded rewrite search. The
permuted trace selected an irrelevant first action and the public development gate
rejected it.

### Rollback and immobility

- output-only attempted zero rewrites across all fixed-structure tasks;
- a task-exact rewrite that failed an independent regression case restored body,
  learned tools, memory, uncertainty, exploration state and cost counters exactly;
- a successful transaction committed deterministically;
- identical transactions produced byte-identical records.

## Structural control rig

A separate control-only generator restricted to seeds `2048+` produced four source
scaffolds. Sixteen paired tasks covered each scaffold exactly four times. Every target
retained the transported learned core rewrite while requiring a scaffold-specific
post-migration operation. This block was designed to expose structural variation rather
than reproduce the single positive-control shape.

The complete, fresh-B, unchanged-parent, learned-tool-ablated and output-only variants
were evaluated under paired seeds. Exact DFA equivalence and held-out quality remained
the quality gates; deterministic candidate evaluations remained the post-reveal search
measure.

## Structural results

The complete and fresh-B lineages reached exact equivalence on **16/16** tasks. The
complete lineage also reached exact held-out quality on **16/16** tasks. Output-only
attempted zero rewrites.

The complete lineage used fewer candidate evaluations than fresh-B, the unchanged
parent and the learned-tool ablation on **12/16** tasks. The result was deliberately
mixed across scaffolds:

| Scaffold | Complete median | Fresh-B median | Complete wins |
|---|---:|---:|---:|
| 0 | **959** | 976 | 4/4 |
| 1 | **1910** | 1920 | 4/4 |
| 2 | 568 | **543** | 0/4 |
| 3 | **568** | 1879 | 4/4 |

The learned-tool ablation matched the fresh-B median on every scaffold. The unchanged
parent had the same directional pattern as fresh-B. Scaffold 2 is therefore a concrete
negative structural case: transported state remains exact but pays a 25-candidate median
branching cost.

This prevents a threshold freeze based on universal directional wins. It also prevents
pooling the strong scaffold-3 effect into one median and presenting it as a worst-case
bound. A valid primary rule must preserve paired exactness and declare how many
structural losses are admissible before any primary task is opened.

## Complete cost vectors

The artifact does not collapse unlike units into one synthetic score. Every row records
separately:

- pre-migration rewrite candidates and development-case evaluations;
- independent validation-case evaluations;
- opaque-substrate probes;
- native synthesis candidate evaluations and native components;
- serialised bytes and packet validations;
- post-migration rewrite candidates.

Fixed-control medians for the complete lineage's pre-migration path were 264 rewrite
candidates, 84 substrate probes and 321 native synthesis candidate evaluations. These
costs remain visible beside the post-reveal values; they are not subtracted from or
hidden behind the adaptation advantage.

## Interpretation

The pre-threshold controls support three narrow claims in this finite development rig:

1. a transported learned rewrite component reduces post-migration search on the
   designated positive family, and removing that component removes the reduction;
2. a relevant transported memory trace changes the first public-evidence exploration
   decision and substantially reduces later search relative to permuted and empty
   traces;
3. the benefit survives three of four structurally varied scaffolds but is not uniform,
   with one declared scaffold exposing a small causal branching cost.

They do **not** yet support the primary M033 claim. The structurally varied block provides
dynamic range for predeclaring the primary rule; it is not a substitute for the reserved
paired comparison.

## Gates still open

Before seeds `0–63` may be opened, M033 still requires:

1. a frozen primary generator committed without instantiating the reserved seeds;
2. a threshold-freeze amendment defining the primary statistic, directional rule,
   critical regressions, abstention limit and artifact identity;
3. complete Python 3.11 and Python 3.13 CI on the frozen pre-result implementation.

No result from seeds `0–63` exists, and no primary post-migration plasticity advantage
is claimed.
