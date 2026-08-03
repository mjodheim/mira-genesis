# M033 control calibration

**Status: development control evidence only — primary seeds remain unobserved**

## Evaluated identity

- implementation commit: `8a1a4476f79f12a2a6b53b2421f698cbe2b08532`;
- focused workflow run: `30786188321`;
- retained artifact ID: `8845330147`;
- raw JSON SHA-256: `6eec1a2ef6063cabd40c36fe30fffb20a70c9da195016ce38a26457eab909d7a`;
- workflow artifact digest: `b440be4c3628012492c8c2a3e372458fc045920d6f1da5e49c24c321804af910`;
- focused tests: 14 passed;
- repository integrity audit: passed.

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

This yielded 16 tasks and 96 lineage-task rows. Every task was generated after the
migration/control checkpoint. The positive family required the transported two-edit
component plus one still-missing post-migration edit. Replaying the learned tool alone
was therefore insufficient. The negative family required an unrelated one-edit repair.

## Results

### Positive learned-tool family

All complete, fresh-B and unchanged-parent lineages reached exact equivalence on all
eight seeds.

Median post-reveal rewrite candidate evaluations were:

| Lineage | Median candidates |
|---|---:|
| complete | **959** |
| learning-state ablated | **959** |
| fresh-B | 976 |
| unchanged parent | 976 |
| learned-tool ablated | 976 |

The complete lineage used fewer candidates than fresh-B on **8/8** seeds and fewer than
the unchanged parent on **8/8** seeds. Removing learned tools erased the entire measured
advantage.

### Negative learned-tool family

Median candidate evaluations were 26 for the complete lineage and 25 for fresh-B. The
complete lineage was better on **0/8** seeds. The irrelevant transported tool therefore
did not create a false positive and exposed a small branching cost instead.

### Mechanism controls

- output-only attempted zero rewrites across all 16 tasks;
- fresh-B solved every positive control within the common finite budget;
- the unchanged parent was reconstructed from M025 archive/digest history and migrated
  independently;
- all packet-derived ablations remained isolated and deterministic;
- opaque native bodies matched their source DFAs on the bounded exhaustive audit.

## Interpretation

The control rig now supports a narrow causal tool claim: in this designated finite
family, a transported learned rewrite component reduces post-migration search cost, and
removing that component removes the reduction.

The observed difference is small in magnitude: 17 median candidate evaluations, about
1.7 percent of the fresh-B median. It is perfectly directional across these eight
control seeds, but it is not yet an admissible primary threshold. D010 forbids treating
this control-block median as a worst-case guarantee.

The learning-state ablation exactly matched the complete lineage. This is a useful
negative finding: the current search path does not functionally consume transported
memory, uncertainty or exploration state. M033 cannot claim transported plasticity as
a whole until the pre-written memory control is implemented and passes.

## Gates still open

Before a threshold-freeze amendment, M033 still requires:

1. a static task-isolation audit;
2. exhaustive evaluator/quality exactness controls;
3. a functional memory control with relevant, permuted and empty traces;
4. a forced bad post-migration rewrite with exact rollback;
5. complete lifecycle cost accounting rather than post-reveal candidate counts alone;
6. byte-identical independent calibration replay;
7. complete CI on Python 3.11 and Python 3.13.

No result from seeds `0–63` exists, and no post-migration plasticity advantage is
claimed.
