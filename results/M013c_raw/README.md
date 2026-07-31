# M013c raw-result reproduction

The full local result contained 108 main executions, 108 oracle-ceiling executions, 36 no-probe baselines, 36 random-semantics baselines and 12 negative controls.

Full raw JSON SHA-256:

`62c80bc22d55644c3a4e8e315b286b250567197d58b8ab721fc8a27de93870f6`

Reproduce from the exact evaluation commit:

```bash
git checkout 40ac0f64a1fb9465e1c4cadf6c32c0cfde3b84dd
python scripts/run_m013c_evaluation_safe.py \
  --git-commit 40ac0f64a1fb9465e1c4cadf6c32c0cfde3b84dd \
  --output results/M013c.json
sha256sum results/M013c.json
```

Protocol SHA-256:

`082cb0ed7e91d486e3f78ea3ea627847453b66344872a7e63ff294efdd9f33e9`

The summary file records every acceptance decision. The complete raw file is deterministic from the committed laboratory, protocol and seeds; it was not transported through a fragmented bundle.
