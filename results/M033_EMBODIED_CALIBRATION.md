# M033 body-anchored control calibration

**Status: development control evidence only — primary seeds remain unobserved**

This block exists to repair a defect in the earlier M033 controls, not to add a
scaffold. The defect silently removed one of Gate 8's four required controls.

## The defect

Gate 8 of [`GENESIS_COMPLETION_CRITERIA.md`](../GENESIS_COMPLETION_CRITERIA.md) requires
the migrated lineage to beat a fresh organism, the unchanged parent migrated to B, **and**
the ablated variants.

The fixed, structural and combined blocks all start every lineage from the task's own
`baseline_source`. The migrated body is therefore never read. Since the unchanged parent
and the learned-tool ablation carry an identical tool registry (both empty, because the
passport holds exactly one learned tool) and an identical learning state, they present
**byte-identical surfaces** to every task under that anchor.

That is why the combined block returned exactly `8/16/8` for both comparisons: they were
not two controls, they were one control run twice.

A second consequence is worse. The task's baseline source *is* the pre-rewrite parent
source, so the complete lineage was made to discard its improved body at the start of
every post-migration task. The thing M032 exists to transport could not contribute.

## The repair

`TaskAnchor.LINEAGE_BODY` starts each lineage from the body it actually migrated.
`TaskAnchor.TASK_BASELINE` remains the default, so every previously recorded block stays
byte-reproducible and is not retroactively altered.

That non-interference was verified rather than assumed. All three previously recorded
blocks were re-run after the anchor change and reproduced their recorded digests exactly:

| Block | Seeds | Recorded digest | Reproduced |
|---|---|---|---|
| fixed-structure | `1024–1031` | `e189142ccbe1465caf76a30d22b8f294974c2c2dcce1e224f3e61748c7f8b5bb` | yes |
| structural | `2048–2063` | `117de3c31b03afcdb4a7f20eb6b2a5877513045e7f1540a6e03a026d63bb0723` | yes |
| combined | `3072–3103` | `0ef00f0f4168a95235f33050751b7871366ad1e2d2c08ed07bfb90b908423372` | yes |

Under the new anchor the two controls separate on **32 of 32** seeds.

## Evaluated identity

- seed block: `4096–4127`, disjoint from the fixed (`1024+`), structural (`2048–3071`)
  and combined (`3072–4095`) blocks and from the reserved primary block `0–63`;
- anchor: `lineage_body`;
- 32 seeds, 4 scaffolds, 8 seeds each, 32 unique task digests;
- raw JSON SHA-256:
  `394f9904b675ac2a8c9d143b8265022b32285efb0d56a01799f45e43b17571a8`;
- replay: byte-identical across two independent runs;
- isolation audit and repository integrity audit: passed.

The reserved primary block `0–63` was not instantiated or observed.

## Results

All five learning-capable variants reached exact equivalence and exact held-out quality
on all 32 tasks. Output-only attempted zero rewrites. Only deterministic cost separates
the lineages.

| Lineage | Median candidates |
|---|---:|
| complete | **26** |
| learned-tool ablated | **26** |
| learning-state ablated | 144 |
| unchanged parent | 264.5 |
| fresh-B | 1427.5 |

| Comparison | Wins | Ties | Losses |
|---|---:|---:|---:|
| versus fresh-B | **32** | 0 | 0 |
| versus unchanged parent | **32** | 0 | 0 |
| versus learning-state ablated | 16 | 0 | 16 |
| versus learned-tool ablated | 0 | **32** | 0 |

Per scaffold:

| Scaffold | Complete | Fresh-B | Parent | Learning-state abl. | Tool abl. |
|---|---:|---:|---:|---:|---:|
| 0 | **26** | 976 | 264 | 263 | 26 |
| 1 | **26** | 1920 | 264 | 263 | 26 |
| 2 | **2** | 543 | 265 | 1 | 2 |
| 3 | **26** | 1879 | 265 | 25 | 26 |

## What this establishes

**The migrated body carries the advantage.** Against a fresh organism the complete
lineage wins 32/32 (26 against 1,427.5 median), and against its own unchanged parent it
now wins 32/32 (26 against 264.5). Both comparisons were previously unmeasurable. This is
the first M033 evidence that transported competence — rather than transported tool
registry or memory — does real work after migration.

**The learned-tool control cannot act.** The tool ablation ties the complete lineage on all
32 seeds at an identical median of 26. The single learned tool is the trace that produced
the body, and replaying it there is a no-op, so the two lineages differ by nothing that can
fire. This is a statement about the rewrite language, not about transported plasticity;
see the correction under *Consequences for Gate 8* and D013.

**Memory helps only when relevant, and is charged when it is not.** It is accepted on
scaffolds 0 and 1, cutting 263 candidates to 26. It is rejected on scaffolds 2 and 3,
where the one-candidate probe is the entire margin against the learning-state ablation
(2 against 1, and 26 against 25).

## Consequences for Gate 8

Gate 8 is **not** satisfied by this block, and now for an interpretable reason rather
than a measurement artifact:

| Gate 8 control | Status |
|---|---|
| beats a fresh organism on B | **passes**, 32/0/0 |
| beats the unchanged parent migrated to B | **passes**, 32/0/0 |
| beats the learned-tool ablation | **structurally uninformative**, 0/32/0 |
| beats the learning-state ablation | **fails**, 16/0/16 — scaffold-dependent |

**Correction.** This document first recorded the tool-ablation tie as a generator defect
repairable by requiring a component the body does not encode. That was wrong, and the
requirement has been withdrawn. The tie cannot be repaired by any choice of target.

`PatchOperation` binds each edit to a positional AST index and `LearnedRewriteTool`
replays its operations verbatim, so a learned tool is a literal replay at fixed sites. The
tool a lineage carries after one improvement cycle is exactly the trace that produced its
body, and reapplying it to that body is a no-op — measured on 8/8 packets and pinned in
`tests/test_m020_learned_tool_replay_limit.py`. Under the correct body anchor the complete
lineage and its tool ablation therefore differ by something that cannot act.

The precondition is a property of the lineage, not the task: the registry must hold a tool
it is not already expressing. That arises from rollback, or from the repeated cycles Gate 9
requires. Gate 8's tool control should be evaluated on a multi-cycle lineage; until then a
tie there is not evidence about transported plasticity in either direction. Recorded as
D013.

The learning-state split is a genuine scaffold-dependence and belongs in the
threshold-freeze amendment as an abstention question: the deciding margin on scaffolds 2
and 3 is one deterministic evaluation.

## Limitations

Development control evidence on 32 seeds in one finite generator, under a corrected
anchor. It does not support the primary M033 claim, and no post-migration plasticity
advantage is claimed. Scaffold 2 resolves in two candidate evaluations for the complete
lineage, which is thin dynamic range; the primary generator should not inherit it
unchanged.

The earlier blocks remain valid evidence of what they measured under the default anchor.
They are not re-run, re-scored or withdrawn. See
[`M033_CONTROL_CALIBRATION.md`](M033_CONTROL_CALIBRATION.md) and
[`M033_COMBINED_CALIBRATION.md`](M033_COMBINED_CALIBRATION.md).
