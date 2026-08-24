"""Author M105 DEVELOPMENT-only feature observations."""

from __future__ import annotations

import argparse
from pathlib import Path

from metamorphosis import m105_runtime as runtime


def build() -> dict[str, object]:
    labels = (
        ((False, False), False),
        ((False, True), True),
        ((True, False), True),
        ((True, True), False),
    )
    observations = [
        {
            "case_id": f"development_{row_index}_{nonce_index}",
            "signals": list(signals),
            "nonce": f"development-{row_index}-{nonce_index}-only",
            "expected": expected,
        }
        for row_index, (signals, expected) in enumerate(labels)
        for nonce_index in range(2)
    ]
    return runtime.feature_demand("development_feature", observations)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="experiments/M105/DEVELOPMENT_FIXTURE.json")
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    raw = runtime.canonical_json(build()).encode("ascii")
    target = Path(arguments.out)
    if arguments.check:
        if not target.exists() or target.read_bytes() != raw:
            raise SystemExit("M105 development fixture is stale")
        return 0
    if target.exists():
        raise SystemExit("M105 development fixture already exists")
    target.write_bytes(raw)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
