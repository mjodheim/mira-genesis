# M029 — Hidden-disjoint component-probe development result

**Status: COMPONENT ESTIMATOR ALIGNED WITHOUT THE PRE-WRITTEN POLICY ADVANTAGE.**

M029 tested whether a hidden-disjoint compositional transfer probe could replace
current development performance as the signal for adaptive evaluation routing and
weighted clade guidance. The estimator aligned strongly with exact CMP, but the full
registered component-adaptive prediction was not supported.

## Frozen identities and replay

- frozen implementation commit:
  `7c3eaa210936afeb1640b9cfbf67924d67e6c679`;
- protocol version: `M029-development-v1`;
- protocol SHA-256:
  `989b909ebe2566aa5042f769e344511d2b3d93d4aa8423f6adb3e13ea1d46a07`;
- raw development artifact SHA-256:
  `8ef0d39adc8f26610468499f72a1227886d7d30691158d4078da216b91ea2e20`;
- raw artifact size: 34,330,797 bytes;
- Python: 3.14.6;
- complete independent local replay: byte-identical size and SHA-256;
- complete repository suite before the run: 179 tests passed.

The ignored raw artifact is reproduced by:

```bash
python scripts/run_m029_component_probe_comparison.py \
  --seeds 64 --workers 4 \
  --output results/M029_component_probe_development.json
```

## Scale and controls

- 64 paired seeds, numbered 0 through 63;
- mismatch and aligned rigs;
- frozen development-adaptive, component-uniform and component-adaptive policies;
- 384 total trajectories;
- 46,080 total expansions;
- 139,392 unique node/task evaluations;
- every component task exactly disjoint from development and hidden suites;
- shortcut/generic structural separation passed in every seed;
- exact depth-three coverage in every trajectory;
- no repeated node/task evaluation;
- integer-only stochastic selections;
- no hidden field exposed to a public selector;
- exact visible/hidden equality in all aligned-control outcomes.

## Pre-written decision

| Gate | Required | Observed | Result |
|---|---:|---:|---|
| Probe disjointness and structural controls | exact | exact | pass |
| High-potential allocation shift | at least 167 per mille | 92 per mille | fail |
| Component-adaptive clade/exact-CMP concordance | at least 0 per mille | 699 per mille | pass |
| Concordance advantage over development-adaptive | at least 167 per mille | 1,177 per mille | pass |
| Median paired final hidden advantage | at least 167 per mille | 0 per mille | fail |
| Component-adaptive paired wins | at least 40 of 64 | 31 of 64 | fail |
| Coverage, uniqueness, isolation and aligned equality | all pass | all pass | pass |

The registered status is `component_estimator_without_policy_advantage`. Component
estimator alignment is true; the allocation-shift, policy-advantage and complete-signal
claims are false.

## Primary comparison

| Mismatch metric, median | Development adaptive | Component uniform | Component adaptive |
|---|---:|---:|---:|
| weighted-clade/exact-CMP concordance | -478 | 668 | 699 |
| final development quality | 833 | 1,000 | 833 |
| final hidden quality | 0 | 1,000 | 500 |
| best hidden quality present in archive | 333 | 1,000 | 500 |
| high-potential observed-node allocation share | 34 | 60 | 126 |

All values are per mille except the final row's interpretation as a share, also per
mille. Component adaptive versus development adaptive produced 31 wins, 32 ties and
1 loss. The paired difference distribution was one -500, thirty-two zeroes, three +500
and twenty-eight +1,000 outcomes. Its median was therefore zero despite the higher
unpaired marginal median.

## Pre-declared diagnostic control

Component-uniform allocation was not a decision gate, so it cannot rescue the
registered hypothesis. It nevertheless supplies the result's most useful diagnostic:

- versus development adaptive: 50 wins, 14 ties and 0 losses;
- paired median hidden advantage: 1,000 per mille;
- final hidden distribution: 12 zero, 13 at 500 and 39 at 1,000 per mille;
- component adaptive versus component uniform: 9 wins, 28 ties and 27 losses.

This evidence was observed in the same run and is development evidence, not an
independent confirmation of a new uniform-component hypothesis.

## Interpretation

The component probe contains relevant information. It turned median clade/exact-CMP
concordance from -478 to at least 668 per mille without sharing any complete task with
the hidden suite. M028's information deficit was therefore real and locally repairable.

Adaptive concentration then introduced a different mismatch. The component probe
recognises generic motifs even inside mixed states that already consumed scarce depth
on shortcut edits. Those components are reusable, but their current lineage may no
longer have enough remaining edits to assemble the complete generic solution.

Post-hoc diagnostics, excluded from the decision rule, are consistent with this
explanation. Median policy expansions from shortcut-containing parents were 31 under
component adaptive versus 28 under component uniform. Expansions from pure generic
parents were 8 versus 12, and the median maximum generic count reached was 3 versus 4.

M029 therefore separates two requirements that the prior experiments conflated:

1. the evaluation signal must reveal reusable structure;
2. its weighting or parent policy must also respect remaining resource viability.

A clean successor must not relabel the observed component-uniform diagnostic as a
confirmed result on the same seeds. It may pre-register that policy on untouched seeds
64–127, or test a depth-aware viability correction under a separately frozen rule.
Neither option would establish a domain-independent potential measure or reproduce a
complete external system.
