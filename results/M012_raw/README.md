# M012 — Raw results

`summary.json` contains the complete aggregate decision record and every pre-registered acceptance criterion.

`all_runs.json.gz.b64` contains all 108 main executions, both sets of 108 baseline executions, and the 12 negative controls. It is gzip-compressed JSON encoded as Base64 so it remains a normal auditable Git text file.

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

Evaluation code commit:

`5ebf244327b1fded84d5e3e648c9a078bd89d96b`

Protocol SHA-256:

`fde43b3c26cc9460b487aea6adbecd0cdc2f738a617ef6d213bd503a8e6ceb1f`

Heritage SHA-256:

`caf7fda6a1acda956954aeb11250787bf0f5731c9836d8ccfa9bfb369de9d08c`
