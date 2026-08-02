# M021 — Status

**FIRST VALID DEVELOPMENT COMPARISON COMPLETE**

M021 asks whether four implemented selection measures move an exact, hidden ground
truth rather than merely improving their own scores.

## Rig and controls

- four rankers: direct objective, novelty, niche-first quality-diversity approximation
  and minimal criterion;
- M019's longer selection-horizon correction;
- common random numbers for every measure at each paired seed;
- exact behavioural-equivalence verification on held-out episodes;
- non-mutating deep-copy audits;
- separate adaptive and frozen held-out quality;
- 24 paired seeds required before comparison;
- a pre-written 100-per-mille development separation floor;
- targeted unit tests, exact shard aggregation and a guarded development workflow.

## Discarded pilot

An earlier three-seed run was underpowered and made no ranking claim. Its original
separation guard passed even though the widest within-measure spread was 584 per mille
against a 750-per-mille between-measure spread. Five of twelve populations never solved
an episode during life and eight learned no macro.

That failure is retained as **R007** in [`../../MEASURES.md`](../../MEASURES.md). It led
to the 24-paired-seed minimum and the explicit restriction of the separation floor to a
development gate rather than a statistical or canonical decision rule.

## First 24-seed result

The complete paired run evaluated 96 trajectories at commit
`326f71534b9bee44b0c745211c27209f22ddff36`.

Median adaptive held-out quality:

1. minimal criterion — **750 per mille**;
2. novelty — **416 per mille**;
3. niche-first quality-diversity approximation — **312 per mille**;
4. direct objective — **0 per mille**.

The best-to-worst spread is 750 per mille, above the pre-written 100-per-mille floor.
The rig therefore separates the implemented measures in development.

The pre-run ordering prediction was wrong. Quality-diversity was predicted first and
minimal criterion close behind; the observed order places minimal criterion clearly
first and quality-diversity third. The original prediction remains recorded unchanged.

See [`../../results/M021_DEVELOPMENT_RESULT.md`](../../results/M021_DEVELOPMENT_RESULT.md)
and [`../../results/M021_measure_comparison_development.csv`](../../results/M021_measure_comparison_development.csv).

## Adaptive-quality warning

The adaptive and frozen held-out scores are identical on every seed for minimal
criterion, novelty and direct objective. They differ on only one quality-diversity seed.
The median adaptive advantage is zero for all four measures.

The current rig therefore separates **what selection preserved before the audit**. It
does not demonstrate that one measure produces stronger post-selection adaptation.
M021 must not be described as evidence for adaptive improvement.

## What remains before freeze consideration

- decide whether M021's eventual claim is frozen transferred quality only;
- repeat M022's now-passing seed-0 adaptation controls across paired seeds;
- pre-write an M022 selection-population decision rule before applying it to M021
  survivors;
- choose and freeze a paired uncertainty and decision rule before any sealed run;
- retain the exact four implementations or rename claims that refer to broader method
  families;
- keep the quality-diversity limitation explicit: this row is not persistent
  MAP-Elites;
- freeze and hash a protocol before authorising any canonical workflow.

## Scientific status

**DEVELOPMENT RESULT SUPPORTED:** selection measure strongly changes exact hidden
quality in this bounded implementation, and minimal criterion is the strongest of the
four implemented rankers across the 24 paired seeds.

**NOT YET SUPPORTED:** post-selection adaptive advantage, a conclusion about persistent
MAP-Elites or quality-diversity as a family, or any canonical/general claim.
