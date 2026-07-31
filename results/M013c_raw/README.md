# M013c — Raw engineering results

> **Scientific status: `INCONCLUSIVE — NON REPRODUCIBLE AT ANNOUNCED COMMIT`.** The recorded metrics are retained as historical engineering evidence, but the validation claim is revoked.

The full local result contained 108 main executions, 108 oracle-ceiling executions, 36 no-probe baselines, 36 random-semantics baselines and 12 negative controls.

Full raw JSON SHA-256:

`62c80bc22d55644c3a4e8e315b286b250567197d58b8ab721fc8a27de93870f6`

## Known-broken original reproduction command

The original documentation instructed:

```bash
git checkout 40ac0f64a1fb9465e1c4cadf6c32c0cfde3b84dd
python scripts/run_m013c_evaluation_safe.py \
  --git-commit 40ac0f64a1fb9465e1c4cadf6c32c0cfde3b84dd \
  --output results/M013c.json
```

This command is **not a valid scientific reproduction procedure** because the announced commit does not contain `experiments/M013c/protocol.yaml` or the frozen protocol whose hash was reported. It is retained here only to document the defect.

Reported protocol SHA-256:

`082cb0ed7e91d486e3f78ea3ea627847453b66344872a7e63ff294efdd9f33e9`

`summary.json` preserves the original runner outcome under `recorded_run_status`, while its top-level status reflects the later audit. Canonical revocation details are recorded in `experiments/M013c/STATUS.md` and `FAILURE_LOG.md`.

The replacement experiment is M013d, which must be executed from a single self-contained immutable commit containing the frozen protocol, laboratory, evaluator and reproduction instructions before any reserved seed is opened.
