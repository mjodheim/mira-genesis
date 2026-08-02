# M027 — Hidden-blind seeded clade guidance development result

**Status: DEVELOPMENT — PRE-WRITTEN SEEDED-CLADE PREDICTION NOT SUPPORTED**

This is a development result, not a canonical validation and not a reproduction of
DGM or HGM.

## Identity

- evaluated implementation commit:
  `83e2aed02b49e1439ede08d42d15a378dbd46642`;
- protocol version: `M027-development-v1`;
- frozen protocol SHA-256:
  `f83e057586508a70c6095b9e9bf7472f67d1d11b0827b3ba6ede1f5f0805ce4a`;
- result artifact SHA-256:
  `57530237d7dcb1a4efbf04ed16e129802a9ab01350941ff941df32fad84f9d44`;
- 64 paired seeds, 512 trajectories and 61,440 completed expansions;
- local runtime: Python 3.14.6, four worker processes;
- a second complete four-worker run produced the identical artifact hash;
- the complete repository suite passes: 144 tests.

## Pre-written decision

The seeded-clade prediction required all of the following:

1. exact breadth coverage through depth three;
2. a non-zero hidden signal exposed before policy selection in every mismatch run;
3. non-negative median concordance between the clade estimate and exact rooted-clade
   quality on HGM-guided archives;
4. at least 167 per mille more concordance than immediate performance;
5. at least 167 per mille median paired final hidden advantage over DGM-inspired
   guidance and at least 40 wins among 64 seeds;
6. exact visible/hidden equality in the aligned control and complete selector
   isolation.

Conditions 1, 2 and 6 passed. Conditions 3, 4 and 5 failed.

## Primary result

| Mismatch metric | DGM immediate | HGM clade | Uniform | Oracle-guided control |
|---|---:|---:|---:|---:|
| Median hidden quality after coverage | 166 | 166 | 166 | 166 |
| Median final development quality | 833 | 833 | 833 | 1000 |
| Median final hidden exact quality | **0** | **0** | **0** | 1000 |
| Median best hidden quality found | 166 | 166 | 500 | 1000 |
| Median immediate/exact-CMP concordance | -1000 | -1000 | -975 | -598 |
| Median clade/exact-CMP concordance | -903 | -907 | -872 | -355 |

The paired HGM-minus-DGM final hidden difference was exactly 0 per mille in all 64
seeds: 0 wins, 64 ties and 0 losses. The pre-written rule required a median difference
of at least 167 and 40 wins.

On HGM-guided archives, clade aggregation improved concordance over immediate
performance by only 93 per mille, below the 167-per-mille gate, and remained strongly
negative at -907 per mille rather than reaching the required non-negative value.

The final hidden distributions were:

| Policy | 0 | 500 | 1000 |
|---|---:|---:|---:|
| DGM immediate | 64 | 0 | 0 |
| HGM clade | 64 | 0 | 0 |
| Uniform | 63 | 0 | 1 |
| Oracle-guided control | 0 | 4 | 60 |

Search discovery and visible final selection also diverged. DGM found a 500-per-mille
hidden node in 8/64 runs, HGM never exceeded the 166-per-mille coverage signal, and
uniform search found at least 500 in 46/64 runs. Except for one uniform run, the visible
shortcut score still selected a final node with zero hidden quality.

## Controls

The mismatch rig enumerated every reachable state through depth three in exactly 97
coverage expansions. The aligned rig did so in exactly 63. These counts and the state
sets were exact in every row before policy selection.

Coverage exposed at least one 166-per-mille hidden node in every mismatch row. The
aligned control preserved exact visible/hidden equality in all 256 aligned rows. Public
selectors received no hidden or exact field, and every stochastic decision remained
integer-only.

Each mismatch trajectory completed 97 coverage plus 40 policy expansions. Each aligned
trajectory completed 63 plus 40. No trajectory stopped early.

## Interpretation

M027 rejects the hypothesis that hidden-blind breadth exploration alone repairs M026's
failure. Productive descendants were present and observed before policy selection, but
the clade statistic still tracked the wrong ordering.

The local cause is decidable. Exact CMP is a maximum over reachable hidden utility,
whereas M027's fixed full evaluation gives every observed clade node equal task weight.
Numerous shortcut descendants contribute visible successes without hidden utility, so
their average dominates the rare generic lineage that determines the exact maximum.
Coverage supplies evidence, but undifferentiated averaging dilutes it.

Full HGM couples clade aggregation to an adaptive evaluation policy intended to weight
higher-utility agents more heavily and approximate a soft maximum. M027 deliberately
held that scheduler fixed to isolate exploration. The result therefore identifies the
evaluation-weighting mechanism as the next separable question; it does not evaluate or
contradict full HGM.

## Conclusion

The second literature-facing benchmark is complete as a reproducible negative
development result. M026 showed that sparse exploration can withhold long-horizon
evidence. M027 shows that exposing the evidence is still insufficient when the
estimator averages a clade whose common proxy-successful descendants are not the nodes
that determine exact hidden potential.
