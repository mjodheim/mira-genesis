# M033 pre-threshold control calibration

**Status: development control evidence only — primary seeds remain unobserved**

## Evaluated identity

- implementation commit: `5f8c389001384c932ad3cca9f1a2ed5c0f445fb0`;
- focused workflow run: `30786832967`;
- retained artifact ID: `8845544011`;
- raw JSON SHA-256: `e189142ccbe1465caf76a30d22b8f294974c2c2dcce1e224f3e61748c7f8b5bb`;
- workflow artifact digest: `645f1a6906c2cf99dcce1c9f0f22f2fb47d101fd01dd24d14d7c50f96b9e68d1`;
- focused tests: 23 passed;
- repository integrity audit: passed;
- static post-migration isolation audit: passed;
- independent complete replay: byte-identical.

The calibration used only seeds `1024–1031`. The reserved primary block `0–63` was not
instantiated or observed.

## Rig

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

## Results

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

- output-only attempted zero rewrites across all 16 tasks;
- a task-exact rewrite that failed an independent regression case restored body,
  learned tools, memory, uncertainty, exploration state and cost counters exactly;
- a successful transaction committed deterministically;
- identical transactions produced byte-identical records.

## Complete cost vectors

The artifact does not collapse unlike units into one synthetic score. Every row records
separately:

- pre-migration rewrite candidates and development-case evaluations;
- independent validation-case evaluations;
- opaque-substrate probes;
- native synthesis candidate evaluations and native components;
- serialised bytes and packet validations;
- post-migration rewrite candidates.

Control medians for the complete lineage's pre-migration path were 264 rewrite
candidates, 84 substrate probes and 321 native synthesis candidate evaluations. These
costs remain visible beside the post-reveal values; they are not subtracted from or
hidden behind the adaptation advantage.

## Interpretation

The pre-threshold controls support two narrow causal mechanism claims in this finite
control rig:

1. a transported learned rewrite component reduces post-migration search, and removing
   that component removes the reduction;
2. a relevant transported memory trace changes the first public-evidence exploration
   decision and substantially reduces later search relative to permuted and empty
   traces.

They do **not** yet support the primary M033 claim. Across seeds `1024–1031`, target
acceptance and held-out surfaces vary, but the positive control deliberately retains one
common rewrite structure. The 8/8 directional result therefore validates mechanism and
determinism, not structural generality or a primary decision threshold.

## Gates still open

Before seeds `0–63` may be opened, M033 still requires:

1. a structurally varied post-migration primary generator committed without observing
   the reserved seeds;
2. control-only calibration of that generator on a disjoint seed block;
3. a threshold-freeze amendment defining the primary statistic, directional rule,
   regressions, abstention limit and artifact identity;
4. complete Python 3.11 and Python 3.13 CI on the frozen pre-result implementation.

No result from seeds `0–63` exists, and no primary post-migration plasticity advantage
is claimed.
