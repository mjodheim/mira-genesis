# M012 — Raw engineering results

> **Scientific status: `INCONCLUSIVE — CONTAMINATED`.** The metrics are retained as historical engineering evidence. They do not constitute a clean held-out validation because evaluation seeds were exercised directly in the test suite during development.

`summary.json` is the current machine-readable decision record. It preserves the status emitted by the original runner in `recorded_run_status`, while its top-level `status` and `all_criteria_passed` fields reflect the later scientific audit.

`all_runs.json.gz.b64` contains the original 108 main executions, both sets of 108 baseline executions, and the 12 negative controls. This compressed payload is intentionally unchanged as historical raw evidence and may contain the original runner's pre-audit status metadata.

Reconstruction on Linux/macOS:

```bash
base64 -d all_runs.json.gz.b64 | gzip -d > M012.json
```

Portable Python reconstruction:

```bash
python - <<'PY'
import base64, gzip
from pathlib import Path
raw = base64.b64decode(Path('all_runs.json.gz.b64').read_bytes())
Path('M012.json').write_bytes(gzip.decompress(raw))
PY
```

Original evaluation code commit:

`5ebf244327b1fded84d5e3e648c9a078bd89d96b`

Protocol SHA-256:

`fde43b3c26cc9460b487aea6adbecd0cdc2f738a617ef6d213bd503a8e6ceb1f`

Heritage SHA-256:

`caf7fda6a1acda956954aeb11250787bf0f5731c9836d8ccfa9bfb369de9d08c`

Canonical revocation details are recorded in `experiments/M012/STATUS.md` and `FAILURE_LOG.md`. The replacement experiment is M012b.
