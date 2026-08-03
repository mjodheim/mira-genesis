# M033 status

**Status: COMBINED PRE-THRESHOLD CONTROLS PASSED — PRIMARY TASKS UNOBSERVED**

The protocol reserves primary seeds `0–63`. No implementation on this branch creates
or evaluates their post-migration tasks.

## Evaluated control identity

- implementation commit: `1c4e7b59c9a846d1b16d09ae47ef1c5478450832`;
- focused workflow run: `30792247244`;
- retained artifact ID: `8847545755`;
- workflow artifact digest:
  `a63c07e1005b86908d9527b3be2ebbab6409eae0e4a4219d0bf0e9bbf69cd25f`;
- fixed-structure raw calibration SHA-256:
  `e189142ccbe1465caf76a30d22b8f294974c2c2dcce1e224f3e61748c7f8b5bb`;
- structural raw calibration SHA-256:
  `117de3c31b03afcdb4a7f20eb6b2a5877513045e7f1540a6e03a026d63bb0723`;
- 27 focused tests passed;
- both fixed-structure and structural calibration replays were byte-identical;
- repository integrity and static task-isolation audits passed.

## Passed gates

- all six declared lineage constructors and ablations;
- exact unchanged-parent reconstruction from M025 archive and digest history;
- fresh-B creation after task reveal with no migrated state;
- deterministic fixed-structure controls restricted to seeds `1024+`;
- deterministic structurally varied controls restricted to seeds `2048+`;
- exact finite-state equivalence and held-out evaluator primitives;
- positive and negative learned-tool controls;
- relevant, permuted and empty-memory controls;
- no-answer replay control;
- output-only immobility;
- fail-closed post-migration regression and exact rollback;
- separate complete lifecycle cost vectors;
- byte-identical artifact replay for both calibration families.

## Fixed-structure control effect

On the positive learned-tool control, median post-reveal candidate evaluations were 959
for the complete lineage and 976 for fresh-B, the unchanged parent and the learned-tool
ablation. Complete was cheaper than fresh-B and parent on 8/8 seeds. On the disjoint
negative family, complete was better on 0/8 seeds and paid a small branching cost.

On the functional memory control, median candidate evaluations were 264 for the relevant
trace, 959 for empty memory and 960 for the permuted trace. Relevant memory was cheaper
than both controls on 8/8 seeds, while all three reached exact equivalence.

## Structural control effect

The structurally varied control block covered four source scaffolds with four seeds each.
The complete and fresh-B lineages reached exact equivalence on all 16 tasks, and the
complete lineage reached exact held-out quality on all 16 tasks.

The complete lineage used fewer post-reveal candidates than fresh-B, the unchanged
parent and the learned-tool ablation on 12/16 tasks. Directional results by scaffold
were 4/4, 4/4, 0/4 and 4/4. The third scaffold is therefore an explicit counterexample
to any predeclared rule requiring universal directional improvement.

Median complete-versus-fresh candidate counts by scaffold were:

- scaffold 0: 959 versus 976;
- scaffold 1: 1910 versus 1920;
- scaffold 2: 568 versus 543;
- scaffold 3: 568 versus 1879.

This mixed result supplies the dynamic range needed for threshold design without
opening or observing any primary task.

## Combined memory-and-tool control effect

A third block on seeds `3072–3103` ran the same four scaffolds through the memory-guided
path, measuring both transported mechanisms together. All five learning-capable variants
reached exact equivalence and exact held-out quality on all 32 tasks, so only
deterministic cost separates them.

The complete lineage beat fresh-B with 24 wins, no ties and 8 losses. Against every
control that retains transported state it did not win: 8/16/8 against the unchanged
parent, 8/16/8 against the learned-tool ablation and 16/0/16 against the learning-state
ablation.

Median candidate counts were 556.0 for the complete lineage, 1,427.5 for fresh-B, 763.5
for the learning-state ablation and 543.5 for both the unchanged parent and the
learned-tool ablation.

The mechanisms act on disjoint scaffolds:

- scaffolds 0 and 1: memory is accepted and carries the effect, 264 and 543 candidates
  against 959 and 1,910 for the learning-state ablation, while the learned-tool ablation
  and the unchanged parent reach identical values;
- scaffold 3: memory is rejected and learned tools carry the effect, 569 against 1,879
  for fresh-B, but the rejected probe costs one candidate and loses 569 to 568 against the
  learning-state ablation;
- scaffold 2: both are inert, the memory row is actively misleading and correctly
  rejected, and the complete lineage loses all four comparisons at 569 against 543.

Because the unchanged parent carries the same learning state without having adopted the
rewrite, the adopted rewrite buys nothing on three of the four scaffolds in this block.

Raw digest `0ef00f0f4168a95235f33050751b7871366ad1e2d2c08ed07bfb90b908423372`, 236
repository tests, byte-identical replay. See `results/M033_COMBINED_CALIBRATION.md`.

## Why thresholds are not frozen yet

The fixed-structure controls establish the causal learned-tool and memory mechanisms.
The structural block shows that their benefit is not uniform across source scaffolds.
A primary rule must therefore combine exactness, paired directional evidence and
predeclared regression limits rather than demand a win on every seed or rely on one
pooled median.

## Still missing before primary seeds may open

- a frozen primary generator for seeds `0–63`, committed without instantiating them;
- the threshold-freeze amendment defining the primary statistic, directional rule,
  regression limits, abstention limit and artifact identity;
- an explicit decision on whether beating the unchanged parent is a required gate or a
  secondary diagnostic, given that the combined block shows no such advantage;
- an explicit decision on whether a margin of one deterministic evaluation counts as a
  win or falls inside an abstention band, given that the rejected memory probe alone
  decides the scaffold-3 comparison;
- final complete Python 3.11 and 3.13 CI on that frozen pre-result implementation.

See `results/M033_CONTROL_CALIBRATION.md` for the complete evidence and limitations.
No result about primary post-migration plasticity is claimed.
