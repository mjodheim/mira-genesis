# M030 — Untouched-seed component-uniform confirmation result

**Status: UNIFORM COMPONENT SIGNAL CONFIRMED IN DEVELOPMENT.**

M030 promoted M029's pre-declared component-uniform diagnostic to a primary comparison
on untouched seeds 64–127. Every pre-written confirmation gate passed without changing
either frozen policy path.

## Frozen identities and replay

- frozen implementation commit:
  `d53cc31d011339ec909db5756916eb3dd93cf74f`;
- protocol version: `M030-development-v1`;
- protocol SHA-256:
  `70dd76bc5efd4d28790527dd6da217cb4995050057a1a7203ebdf016a3f81d49`;
- raw development artifact SHA-256:
  `6d98836964f29297259afa0e6dc5e192fc4fa2abb2630670773b6a279b5ada96`;
- raw artifact size: 22,891,908 bytes;
- Python: 3.14.6;
- complete independent local replay: byte-identical size and SHA-256;
- complete repository suite before the run: 191 tests passed.

The ignored raw artifact is reproduced by:

```bash
python scripts/run_m030_unseen_component_confirmation.py \
  --workers 4 \
  --output results/M030_unseen_component_development.json
```

## Untouched confirmation boundary

- the primary seed set was exactly 64–127;
- M029 development, unit and smoke runs used only seeds 0–63;
- M030 unit and smoke validation used only seeds 128 and above;
- no confirmation seed was executed before commit `d53cc31`;
- M030 called the frozen M029 `development_adaptive` and `component_uniform` paths and
  introduced no evaluation or selection mechanism.

## Scale and controls

- 64 paired confirmation seeds;
- mismatch and aligned rigs;
- 256 total trajectories;
- 30,720 total expansions;
- 92,928 unique node/task evaluations;
- exact component-probe disjointness and structural controls;
- exact depth-three coverage in every trajectory;
- no repeated node/task evaluation;
- integer-only stochastic selections;
- no hidden field exposed to a public selector;
- exact visible/hidden equality in all aligned-control outcomes.

## Pre-written decision

| Gate | Required | Observed | Result |
|---|---:|---:|---|
| Exact confirmation seed range | 64–127 | 64–127 | pass |
| Probe disjointness and structural controls | exact | exact | pass |
| Component-uniform clade/exact-CMP concordance | at least 0 per mille | 662 per mille | pass |
| Concordance advantage over development adaptive | at least 167 per mille | 1,186 per mille | pass |
| Median paired final hidden advantage | at least 167 per mille | 1,000 per mille | pass |
| Component-uniform paired wins | at least 40 of 64 | 48 of 64 | pass |
| Coverage, uniqueness, isolation and aligned equality | all pass | all pass | pass |

The registered status is `uniform_component_signal_confirmed`. Estimator and policy
confirmation flags are both true.

## Confirmation outcome

| Mismatch metric, median | Development adaptive | Component uniform |
|---|---:|---:|
| weighted-clade/exact-CMP concordance | -524 | 662 |
| final development quality | 833 | 1,000 |
| final hidden quality | 0 | 1,000 |
| best hidden quality present in archive | 500 | 1,000 |

All values are per mille. Component uniform produced 48 wins, 16 ties and no losses.
The paired difference distribution was sixteen zeroes, thirteen +500 and thirty-five
+1,000 outcomes.

Final hidden quality under component uniform was zero in 13 seeds, 500 per mille in 13
and 1,000 per mille in 38. Development adaptive returned zero in 61 seeds and 1,000 in
three.

## Replication across seed blocks

The untouched block closely reproduced the pre-declared M029 diagnostic:

| Seed block | Component-uniform wins | Ties | Losses |
|---|---:|---:|---:|
| M029 diagnostic, 0–63 | 50 | 14 | 0 |
| M030 confirmation, 64–127 | 48 | 16 | 0 |

Both blocks had median paired final advantage 1,000 per mille and positive median
component clade/exact-CMP concordance.

## Interpretation and limits

M030 confirms the narrow information claim that survived M029: in this finite mismatch
rig, evenly distributed evidence about reusable components guides the observed clade
better than adaptively concentrated evidence about current development performance.
The effect reproduced on an untouched seed block using frozen code.

The result does not validate M029's failed component-adaptive policy, prove that
uniform allocation is generally optimal or establish a domain-independent potential
measure. The component suite uses the rig's known public task grammar, and M030 remains
development evidence rather than a sealed canonical evaluation.

The next scientific question is no longer whether the finite component signal exists.
It is whether that signal transports to a structurally different task generator, or
whether a resource-aware policy can improve on uniform allocation without overweighting
doomed mixed lineages. Either successor requires a new frozen protocol and must not
alter this confirmation.
