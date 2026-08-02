# M021 — 24-seed development result

**Status: DEVELOPMENT RESULT. Not frozen, not canonical, and not a claim about the full
quality-diversity or minimal-criterion families.**

## Run identity

- evaluated commit: `326f71534b9bee44b0c745211c27209f22ddff36`;
- GitHub Actions run: `30719097644`;
- paired seeds: `0..23`;
- trajectories: 96, four measures × 24 seeds;
- final artifact: `m021-development-30719097644`;
- artifact SHA-256: `872e831452ac2590dc0325176efba223da762c6aaca728ef707f44bceeaab78c`;
- versioned rows: [`M021_measure_comparison_development.csv`](M021_measure_comparison_development.csv).

Every shard, the aggregate job and all guardrails completed successfully. Ground truth
was computed by exact behavioural equivalence, remained unavailable to every ranker,
and was evaluated on deep copies rather than the selected population.

## Pre-registered development gate

The comparison required at least 24 paired seeds and a median adaptive held-out spread
of at least 100 per mille between the best and worst measure.

- paired seeds present: **24**;
- best median adaptive quality: **750 per mille**;
- worst median adaptive quality: **0 per mille**;
- spread: **750 per mille**;
- rig separates the implemented measures: **YES**.

The rig therefore passes its development separation gate.

## Primary result

| Implemented ranker | Adaptive median | Frozen median | Adaptive mean | Zero-quality seeds |
|---|---:|---:|---:|---:|
| Minimal criterion | **750‰** | **750‰** | 667‰ | 0 / 24 |
| Novelty | **416‰** | **416‰** | 434‰ | 2 / 24 |
| Niche-first quality-diversity approximation | **312‰** | **291‰** | 260‰ | 7 / 24 |
| Direct objective | **0‰** | **0‰** | 113‰ | 13 / 24 |

Pairwise adaptive seed outcomes, written as wins / ties / losses for the first row:

| Comparison | Wins / ties / losses | Median paired difference |
|---|---:|---:|
| Minimal criterion vs novelty | **18 / 5 / 1** | +167‰ |
| Minimal criterion vs quality-diversity approximation | **21 / 2 / 1** | +355‰ |
| Minimal criterion vs direct objective | **23 / 1 / 0** | +625‰ |
| Novelty vs quality-diversity approximation | **16 / 3 / 5** | +167‰ |
| Novelty vs direct objective | **19 / 3 / 2** | +334‰ |
| Quality-diversity approximation vs direct objective | **13 / 11 / 0** | +146‰ |

Exploratory paired bootstrap intervals, computed after the development run and therefore
not used as a frozen decision rule, keep the minimal-criterion advantage positive:

- minimal criterion minus novelty, median difference: 167‰, exploratory 95% interval
  84‰ to 333‰;
- minimal criterion minus quality-diversity approximation: 355‰, interval 333‰ to
  542‰;
- minimal criterion minus direct objective: 625‰, interval 458‰ to 667‰.

## Prediction audit

The prediction was written before the comparison:

1. quality-diversity approximation first;
2. minimal criterion close behind;
3. novelty preserves diversity without reliably moving quality;
4. direct objective degrades true quality.

The result does **not** support the first two positions.

- The minimal criterion is the clear development winner, not the runner-up.
- Novelty is second.
- The niche-first quality-diversity approximation is third.
- The direct objective is last, as predicted.

The prediction is retained as written. It is not rewritten to match the observation.

## Interpretation within the implemented algorithms

The direct objective optimises energy remaining after search. It therefore continues the
M019 failure mode: avoiding expensive learning is locally rewarded. Its median organism
holds zero macros, solves zero lifetime episodes, and obtains zero held-out quality.

Novelty preserves lineages that build different macro libraries, even when their current
energy is lower. It moves exact quality substantially above the direct objective, but it
has no viability requirement and can preserve difference without competence.

The minimal criterion combines the useful parts of both ideas. An organism must solve at
least one episode before novelty matters. That low viability floor prevents selection of
purely different non-solvers while avoiding a fine-grained objective that rewards cheap
non-learning. In this rig, that combination produces the strongest exact held-out
quality.

The quality-diversity row is a fixed-population, niche-first approximation whose niches
are `(macro-count bucket, forgetting kind)`. It is not a persistent MAP-Elites archive.
The declared descriptor is coarse, and the survivor budget may be smaller than the
number of represented niches. Its third-place result applies only to this implementation
and does not justify a claim against quality-diversity as a family.

## The adaptive/frozen warning

The primary metric was declared as adaptive held-out quality: one copied organism sees
the complete held-out sequence and may learn across it. Frozen quality resets to the
same pre-audit state for every episode.

The two metrics are identical on every seed for minimal criterion, novelty and direct
objective. They differ on only one quality-diversity seed, by 41 per mille. The median
adaptive advantage is therefore zero for all four measures.

This means the rig separates **what selection preserved before the audit**, but the
four-episode held-out sequence does not expose measurable new adaptation after
selection. The result must not be described as evidence that one measure produces more
adaptive organisms.

Before freezing M021, development must do one of two things without changing this
record:

1. create a new, explicitly named adaptation-stress rig with a longer or staged held-out
   sequence and a pre-written adaptive-versus-frozen gate; or
2. restrict M021's claim to frozen transferred quality and treat adaptive quality as an
   unsupported extension.

The second option would change the original primary question. The cleaner path is a new
development experiment rather than silently redefining this one after observation.

## Development conclusion

**Supported within this finite implementation:** selection measure strongly changes
exact hidden quality. A low viability floor followed by novelty outperforms novelty
alone, the niche-first quality-diversity approximation and immediate energy optimisation
across the 24 paired seeds.

**Not supported:** a claim that the winning measure improves post-selection adaptation,
a claim about persistent MAP-Elites, or any canonical/general conclusion.

M021 has completed its first valid development comparison. The next scientific step is
to preserve this result, build an adaptation-stress successor, and choose a frozen
paired decision rule before any canonical evaluation.
