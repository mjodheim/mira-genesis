# M028 — Adaptive evaluation-weighting development result

**Status: PRE-WRITTEN DEVELOPMENT PREDICTION NOT SUPPORTED.**

M028 tested whether individual-performance Thompson sampling could allocate finite
evaluation evidence so that observed clade performance behaved more like exact maximum
descendant quality than uniform allocation did. It could not.

## Frozen identities and replay

- frozen implementation commit:
  `334eec2fa476c6a1d3b3f1431843d8d42e5ca883`;
- protocol version: `M028-development-v1`;
- protocol SHA-256:
  `bdbdb1c8a47fe0c047660f1f46959b608df1ce98828845fb03d574609ae4f2f5`;
- raw development artifact SHA-256:
  `a009c0c4f8ce3d2ab0f1af4fe0095f42fbf67183a3458ad4b667b88cf5dd7025`;
- raw artifact size: 22,820,822 bytes;
- Python: 3.14.6;
- complete independent local replay: byte-identical size and SHA-256;
- complete repository suite before the run: 156 tests passed.

The ignored raw artifact is reproduced by:

```bash
python scripts/run_m028_adaptive_evaluation_comparison.py \
  --seeds 64 --workers 4 \
  --output results/M028_adaptive_evaluation_development.json
```

## Scale and controls

- 64 paired seeds, numbered 0 through 63;
- mismatch and aligned rigs;
- uniform and adaptive evaluation policies;
- 256 total trajectories;
- 30,720 total expansions;
- 92,928 unique node/case evaluations;
- exact depth-three coverage in every trajectory;
- no repeated node/case evaluation;
- integer-only stochastic selections;
- no hidden field exposed to either public selector;
- exact visible/hidden equality in all aligned-control outcomes.

## Pre-written decision

| Gate | Required | Observed | Result |
|---|---:|---:|---|
| Adaptive weighted-clade/exact-CMP concordance | at least 0 per mille | -478 per mille | fail |
| Concordance advantage over uniform | at least 167 per mille | 40 per mille | fail |
| Median paired final hidden advantage | at least 167 per mille | 0 per mille | fail |
| Adaptive paired wins | at least 40 of 64 | 2 of 64 | fail |
| Aligned visible/hidden equality | exact | exact | pass |
| Coverage, uniqueness and selector isolation | all pass | all pass | pass |

The registered status is therefore
`adaptive_weighting_prediction_not_supported`. Estimator alignment and policy
advantage are both false.

## Primary comparison

| Mismatch metric, median | Uniform evaluation | Adaptive evaluation |
|---|---:|---:|
| weighted-clade/exact-CMP concordance | -518 per mille | -478 per mille |
| final development quality | 833 per mille | 833 per mille |
| final hidden quality | 0 per mille | 0 per mille |
| best hidden quality present in archive | 166 per mille | 333 per mille |
| high-potential observed-node allocation share | 51 per mille | 34 per mille |

Final hidden quality was zero in 62 seeds and 1,000 per mille in two seeds under each
policy. The successful seed identities differed: adaptive won seeds 23 and 36 and lost
seeds 28 and 45, producing 2 wins, 60 ties and 2 losses.

Adaptive allocation changed the archive even though it did not change the primary
result. Its best hidden quality distribution was 166/500/1,000 per mille in 32/30/2
seeds, compared with 41/21/2 under uniform allocation.

## Interpretation

The missing mechanism was not unequal weighting by itself. The adaptive evaluator used
the same immediate development proxy whose ordering is deliberately reversed from
hidden descendant potential. It consequently allocated *less* evidence to
evaluator-identified high-potential observed nodes than uniform sampling did: 34 versus
51 per mille. Weighting made the clade statistic slightly less anti-aligned, but it
remained a confident aggregate of the wrong evidence.

M028 therefore narrows the failure chain:

1. M026 showed that clade aggregation cannot value an unobserved lineage;
2. M027 showed that exhaustive breadth does not turn a clade mean into a maximum;
3. M028 shows that adaptive weighting by the misaligned individual proxy does not
   repair that mean and can route evidence away from high-potential lineages.

The result does not test full HGM, its asynchronous scheduler, its software tasks or
its complete evaluation stack. It rejects H10 only for this finite, isolated
adaptation. A scientifically distinct successor would need an evaluation allocation
signal other than current proxy performance—such as uncertainty, behavioural diversity
or a separately justified transfer proxy—or should return to M022's deferred cross-seed
adaptation controls.
