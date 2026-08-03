# M033 combined memory-and-tool control calibration

**Status: development control evidence only — primary seeds remain unobserved**

This block closes the one cross-term the earlier M033 controls left open. The
fixed-structure block tested transported memory on a single task shape, and the
structural block tested transported learned tools across four scaffolds. Neither
measured both mechanisms together under structural variation. This calibration runs the
same four scaffolds through the memory-guided execution path, on a disjoint seed block.

Its headline finding is negative for the strong reading of M033: **the complete lineage
has no advantage over its own unchanged parent on this block.**

## Evaluated identity

- seed block: `3072–3103`, disjoint from the fixed (`1024+`) and structural (`2048–3071`)
  blocks and from the reserved primary block `0–63`;
- 32 seeds, 4 scaffolds, 8 seeds each, 32 unique task digests;
- raw JSON SHA-256:
  `0ef00f0f4168a95235f33050751b7871366ad1e2d2c08ed07bfb90b908423372`;
- repository tests: 236 passed on Python 3.11.15;
- isolation audit, repository integrity audit and attribution policy: passed;
- replay: byte-identical across two independent runs.

The digest above is the canonical raw-JSON SHA-256 reported by the runner, which is
newline-normalised and therefore platform-independent. It was produced locally on
Python 3.11.15; the workflow re-derives it on Python 3.11 and 3.13 and fails closed if
the two runs differ.

The reserved primary block `0–63` was not instantiated or observed.

## Rig

Each seed instantiates one scaffold-specific post-migration task and six lineages. Five
are learning-capable and run through `execute_memory_guided_task`; the output-only
control runs through `execute_control_task` and may not rewrite.

The memory mechanism is deliberately oracle-free. The first decodable memory row is
turned into one bounded patch operation, applied to the baseline, and retained **only if
public development evidence strictly improves**. Acceptance consumes one edit from the
budget. Attempting the probe always costs exactly one candidate evaluation, whether or
not it is accepted. That cost is charged, not hidden.

## Aggregate results

All five learning-capable variants reached exact equivalence and exact held-out quality
on all 32 tasks. Output-only attempted zero rewrites. Quality therefore never separates
the lineages on this block; only deterministic search cost does.

| Lineage | Median candidates | Memory accepted |
|---|---:|---:|
| unchanged parent | **543.5** | 16/32 |
| learned-tool ablated | **543.5** | 16/32 |
| complete | 556.0 | 16/32 |
| learning-state ablated | 763.5 | 0/32 |
| fresh-B | 1427.5 | 0/32 |

Paired outcomes for the complete lineage:

| Comparison | Wins | Ties | Losses |
|---|---:|---:|---:|
| versus fresh-B | **24** | 0 | 8 |
| versus unchanged parent | 8 | 16 | 8 |
| versus learning-state ablated | 16 | 0 | 16 |
| versus learned-tool ablated | 8 | 16 | 8 |

Against a genuinely fresh organism the complete lineage wins 24/32. Against every
control that retains some transported state, it does not win.

## Per-scaffold results

| Scaffold | Complete | Fresh-B | Parent | Learning-state abl. | Tool abl. | Memory accepted |
|---|---:|---:|---:|---:|---:|---:|
| 0 | **264** | 976 | 264 | 959 | 264 | 8/8 |
| 1 | **543** | 1920 | 543 | 1910 | 543 | 8/8 |
| 2 | 569 | **543** | 544 | 568 | 544 | 0/8 |
| 3 | **569** | 1879 | 1880 | 568 | 1880 | 0/8 |

Complete-lineage outcomes by scaffold:

| Scaffold | vs fresh-B | vs parent | vs learning-state abl. | vs tool abl. |
|---|---|---|---|---|
| 0 | 8/0/0 | 0/8/0 | 8/0/0 | 0/8/0 |
| 1 | 8/0/0 | 0/8/0 | 8/0/0 | 0/8/0 |
| 2 | 0/0/8 | 0/0/8 | 0/0/8 | 0/0/8 |
| 3 | 8/0/0 | 8/0/0 | 0/0/8 | 8/0/0 |

## What the mechanisms actually do

The two transported mechanisms are real, but they act on **disjoint scaffolds** and
neither is attributable to the adopted rewrite.

**Scaffolds 0 and 1 — memory carries the effect, tools contribute nothing.** The memory
row decodes to an operation that strictly improves development evidence (0 to 5 cases
passed at seed 3072) and is accepted. Complete falls to 264 candidates against 959 for
the learning-state ablation and 976 for fresh-B. The learned-tool ablation and the
unchanged parent reach *exactly the same* 264, so removing learned tools changes nothing
here.

**Scaffold 3 — tools carry the effect, memory is a pure tax.** The memory probe is
attempted and rejected (0 to 0). The learned tool cuts rewrite search from 1879 to 568,
so complete beats fresh-B, the parent and the tool ablation. But it *loses* to the
learning-state ablation by exactly one candidate, 569 against 568 — the rejected probe.

**Scaffold 2 — both mechanisms are inert and the complete lineage pays.** The memory row
is actively misleading: it takes development evidence from 1 case passed to 0, and the
public gate correctly rejects it, costing one candidate. The learned tool also raises
rewrite search from 543 to 568, a 25-candidate branching cost. Complete therefore loses
all four comparisons, 569 against 543.

## The parent result

The most consequential number is `complete versus unchanged parent = 8/16/8`.

The unchanged parent never adopted the M032 rewrite, yet it carries the same learning
state and therefore routes memory identically. It matches the complete lineage exactly on
scaffolds 0 and 1, beats it on scaffold 2, and loses only on scaffold 3. On this block the
adopted rewrite buys nothing on three of four scaffolds.

This does not contradict the fixed-structure block, which measured the learned-tool
mechanism on a family built to require it. It does show that the mechanism's benefit is
scaffold-selective, and that a primary rule requiring the complete lineage to beat its own
parent would currently fail on this control evidence.

## Consequences for the threshold-freeze amendment

1. Quality cannot be the primary discriminator here — all learning-capable variants are
   exactly equivalent on all 32 tasks. The statistic must be deterministic cost.
2. A rule demanding universal directional wins is refuted twice over: scaffold 2 loses
   against every control, and scaffold 3 loses against the learning-state ablation by a
   single candidate.
3. Single-candidate margins decide paired outcomes. The amendment must state whether a
   margin of one deterministic evaluation counts as a win or falls inside an abstention
   band, otherwise the probe cost alone can flip a scaffold.
4. Ablation controls are not interchangeable. Memory and tools dominate different
   scaffolds, so pooling them into one "ablated" control would hide both effects.
5. The unchanged-parent comparison is the strictest control and currently shows no
   advantage. The amendment must declare it either as a required gate or as a
   secondary diagnostic, before any primary seed is opened.

## Limitations

This is development control evidence on 32 seeds in one finite generator. It does not
support the primary M033 claim, and no primary post-migration plasticity advantage is
claimed. The block was designed to expose interaction between the two transported
mechanisms and to supply dynamic range for threshold design; it is not a substitute for
the reserved paired comparison on seeds `0–63`, which remain uninstantiated and
unobserved.

See [`M033_CONTROL_CALIBRATION.md`](M033_CONTROL_CALIBRATION.md) for the fixed-structure
and structural blocks that precede this one.
