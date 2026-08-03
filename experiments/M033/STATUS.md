# M033 status

**Status: PRE-THRESHOLD CONTROLS PASSED — PRIMARY GENERATOR OPEN — PRIMARY TASKS UNOBSERVED**

The protocol reserves primary seeds `0–63`. No implementation on this branch creates
or evaluates their post-migration tasks.

## Evaluated control identity

- implementation commit: `5f8c389001384c932ad3cca9f1a2ed5c0f445fb0`;
- focused workflow run: `30786832967`;
- raw calibration SHA-256:
  `e189142ccbe1465caf76a30d22b8f294974c2c2dcce1e224f3e61748c7f8b5bb`;
- retained artifact ID: `8845544011`;
- artifact digest:
  `645f1a6906c2cf99dcce1c9f0f22f2fb47d101fd01dd24d14d7c50f96b9e68d1`;
- 23 focused tests passed;
- byte-identical independent calibration replay;
- repository integrity and static task-isolation audits passed.

## Passed gates

- all six declared lineage constructors and ablations;
- exact unchanged-parent reconstruction from M025 archive and digest history;
- fresh-B creation after task reveal with no migrated state;
- deterministic task generation restricted to seeds `1024+`;
- exact finite-state equivalence and held-out evaluator primitives;
- positive and negative learned-tool controls;
- relevant, permuted and empty-memory controls;
- no-answer replay control;
- output-only immobility;
- fail-closed post-migration regression and exact rollback;
- separate complete lifecycle cost vectors;
- byte-identical artifact replay.

## Control effect

On the positive learned-tool control, median post-reveal candidate evaluations were 959
for the complete lineage and 976 for fresh-B, the unchanged parent and the learned-tool
ablation. Complete was cheaper than fresh-B and parent on 8/8 seeds. On the disjoint
negative family, complete was better on 0/8 seeds and paid a small branching cost.

On the functional memory control, median candidate evaluations were 264 for the relevant
trace, 959 for empty memory and 960 for the permuted trace. Relevant memory was cheaper
than both controls on 8/8 seeds, while all three reached exact equivalence.

## Why thresholds are not frozen yet

The control seeds vary target acceptance and held-out surfaces, but the designated
positive control intentionally preserves one common rewrite structure. It validates the
causal mechanisms and their dynamic range, not structural generality. Treating its 8/8
direction or median magnitude as a primary threshold would repeat the typical-versus-
worst-case error prohibited by D010.

## Still missing before primary seeds may open

- a structurally varied post-migration primary generator;
- disjoint control-only calibration of that generator;
- the threshold-freeze amendment;
- final complete Python 3.11 and 3.13 CI on the frozen implementation.

See `results/M033_CONTROL_CALIBRATION.md` for the complete evidence and limitations.
No result about primary post-migration plasticity is claimed.
