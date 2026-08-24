"""Author the project-controlled M107 demand fixture.

Two demanded behaviours, each observed over every signal row with two nonces. Both are non-monotone
and therefore outside the complete image of the monotone fragment at every node bound.

Neither the operator, its arity, its truth table nor its identity appears anywhere in this fixture:
the lineage receives behaviour only and must find which single extension to its own interpreter
table brings both behaviours inside reach.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from metamorphosis import m107_runtime as runtime  # noqa: E402

# D1 and D2 are fixed here, before any protocol exists. Both are non-monotone.
TARGET_PRIMARY = [True, False, False, True]
TARGET_SECOND = [True, False, True, False]


def _observations(prefix: str, table: list[bool]) -> list[dict[str, object]]:
    return [
        {
            "case_id": "%s_%d_%d" % (prefix, index, nonce),
            "signals": list(row),
            "nonce": "m107-%s-%d-%d" % (prefix, index, nonce),
            "expected": table[index],
        }
        for index, row in enumerate(runtime.SIGNAL_ROWS)
        for nonce in range(2)
    ]


def build() -> dict[str, object]:
    payload: dict[str, object] = {
        "schema": "m107-demands-v1",
        "milestone": "M107",
        "authorship": "project_controlled_not_independent_task_evidence",
        "targets": [TARGET_PRIMARY, TARGET_SECOND],
        "primary": runtime.operator_demand(
            "m107_primary", _observations("primary", TARGET_PRIMARY)
        ),
        "joint": {
            "first": runtime.operator_demand(
                "m107_joint_first", _observations("joint_a", TARGET_PRIMARY)
            ),
            "second": runtime.operator_demand(
                "m107_joint_second", _observations("joint_b", TARGET_SECOND)
            ),
        },
    }
    payload["demands_digest"] = runtime.digest(payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="experiments/M107/DEMANDS.json")
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    raw = runtime.canonical_json(build()).encode("ascii")
    target = Path(arguments.out)
    if arguments.check:
        if not target.exists() or target.read_bytes() != raw:
            raise SystemExit("M107 demand fixture is stale")
        return 0
    if target.exists():
        raise SystemExit("M107 demand fixture already exists")
    target.write_bytes(raw)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
