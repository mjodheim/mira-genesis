# M033 status

**Status: TOOL CONTROL CALIBRATED — MEMORY CONTROL OPEN — PRIMARY TASKS UNOBSERVED**

The protocol reserves primary seeds `0–63`. No implementation on this branch creates
or evaluates their post-migration tasks.

## Passed controls

Focused workflow run `30786188321` passed 14 M032/M033 tests, the repository integrity
audit and the primary-seed guard. It also retained the eight-seed calibration artifact
`8845330147`.

Implemented and verified:

- independent complete, output-only, learning-state-ablated and learned-tool-ablated
  rehydrations from one validated M032 packet;
- exact reconstruction of the unchanged pre-rewrite parent from M025 archive and
  digest history, followed by independent migration to B;
- fresh-B construction after task reveal with no packet, memory or learned tools;
- deterministic control-task generation restricted to seeds `1024+`;
- exact finite-state task evaluation and bounded post-migration rewrite execution;
- deterministic probe, native-synthesis and rewrite-candidate cost fields;
- output-only immobility, mutable-state isolation and no-answer-replay controls.

## Calibration result

On seeds `1024–1031`, the positive learned-tool family produced exact solutions for the
complete, fresh-B and unchanged-parent lineages on all eight seeds.

Median post-reveal candidate evaluations were:

- complete: **959**;
- learning-state ablated: **959**;
- fresh-B: **976**;
- unchanged parent: **976**;
- learned-tool ablated: **976**.

The complete lineage beat fresh-B and the parent on 8/8 seeds. Removing learned tools
erased the measured advantage. On the disjoint negative family, complete was never
better than fresh-B and paid a small branching cost: median 26 versus 25 candidates.

The raw artifact SHA-256 is
`6eec1a2ef6063cabd40c36fe30fffb20a70c9da195016ce38a26457eab909d7a`.
See `results/M033_CONTROL_CALIBRATION.md`.

## Important negative finding

The learning-state ablation exactly matched the complete lineage. The current search
path therefore does not functionally consume transported memory, uncertainty or
exploration state. This prevents a whole-plasticity claim and blocks threshold freeze
until the pre-written memory control exists and passes.

## Still missing before threshold freeze

- static task-isolation audit;
- exhaustive evaluator and held-out-quality exactness audit;
- functional relevant/permuted/empty memory control;
- forced bad post-migration rewrite with exact rollback;
- complete lifecycle cost accounting;
- byte-identical independent calibration replay;
- complete Python 3.11 and 3.13 CI on the final control implementation;
- frozen numerical gates before seeds `0–63` may be opened.

No result about primary post-migration plasticity is claimed.
