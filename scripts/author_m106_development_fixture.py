"""Author M106 DEVELOPMENT-only feature observations.

M106 replicates H50 on a fresh population. The target semantic is fixed by the pre-registration
before implementation: truth table (True, False, False, True) over the ordered signal rows
(F,F), (F,T), (T,F), (T,T). M105 used (False, True, True, False); the two are distinct semantic
classes with distinct content addresses, so a mechanism tuned to M105's target cannot pass here.

The mechanism module metamorphosis/m105_runtime.py is imported unchanged. That is the point of the
replication and must never become a copy.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from metamorphosis import m105_runtime as runtime

TARGET_TRUTH_TABLE = (True, False, False, True)


def build() -> dict[str, object]:
    rows = ((False, False), (False, True), (True, False), (True, True))
    observations = [
        {
            "case_id": f"m106_development_{row_index}_{nonce_index}",
            "signals": list(signals),
            "nonce": f"m106-dev-{row_index}-{nonce_index}-only",
            "expected": TARGET_TRUTH_TABLE[row_index],
        }
        for row_index, signals in enumerate(rows)
        for nonce_index in range(2)
    ]
    return runtime.feature_demand("m106_development_feature", observations)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="experiments/M106/DEVELOPMENT_FIXTURE.json")
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    raw = runtime.canonical_json(build()).encode("ascii")
    target = Path(arguments.out)
    if arguments.check:
        if not target.exists() or target.read_bytes() != raw:
            raise SystemExit("M106 development fixture is stale")
        return 0
    if target.exists():
        raise SystemExit("M106 development fixture already exists")
    target.write_bytes(raw)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
