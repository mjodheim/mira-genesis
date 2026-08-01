# M021 — Selection measures against decidable ground truth

M021 turns the selection measure itself into the experimental variable.

- [`PROTOCOL_DRAFT.md`](PROTOCOL_DRAFT.md) — question, controls, predictions and
  invalidation conditions;
- [`STATUS.md`](STATUS.md) — current implementation and remaining work;
- `metamorphosis/m021_measures.py` — the four rankers;
- `scripts/run_m021_measure_comparison.py` — paired development comparison;
- `tests/test_m021.py` — ranker and audit guardrails;
- `.github/workflows/m021-development.yml` — non-canonical development workflow.

Nothing in this folder is frozen. Development results may reject the rig, but may not
be presented as a canonical scientific result.
