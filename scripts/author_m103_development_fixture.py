"""Author the public DEVELOPMENT-only M103 constructor fixture deterministically."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from metamorphosis import m103_runtime as runtime  # noqa: E402


OUTPUT = ROOT / "experiments" / "M103" / "DEVELOPMENT_FIXTURE.json"


def _action(descriptor: dict[str, Any]) -> dict[str, Any]:
    return runtime.action_definition(descriptor)


def build_fixture() -> dict[str, Any]:
    amber = _action({"kind": "set_value", "key": "outcome", "value": "amber"})
    violet = _action({"kind": "set_value", "key": "outcome", "value": "violet"})
    producer = runtime.acquisition_demand(
        "development-constructor-trigger",
        "development_record",
        [amber, violet],
        [
            {
                "case_id": "development-left",
                "context": ["north"],
                "initial": {"seed": "same"},
                "expected": {"seed": "same", "outcome": "amber"},
            },
            {
                "case_id": "development-right",
                "context": ["south"],
                "initial": {"seed": "same"},
                "expected": {"seed": "same", "outcome": "violet"},
            },
        ],
        [
            {"probe_id": "development-probe-left", "context": ["north"], "initial": {}},
            {"probe_id": "development-probe-right", "context": ["south"], "initial": {}},
        ],
        max_trace=1,
    )

    set_flag = _action({"kind": "set_value", "key": "flag", "value": True})
    drop_missing = _action({"kind": "drop_value", "key": "missing"})
    ambiguous = runtime.acquisition_demand(
        "development-ambiguity-control",
        "development_record",
        [set_flag, drop_missing],
        [
            {
                "case_id": "ambiguity-fit",
                "context": ["single"],
                "initial": {"flag": True},
                "expected": {"flag": True},
            }
        ],
        [
            {
                "probe_id": "ambiguity-separator",
                "context": ["single"],
                "initial": {"flag": False, "missing": 1},
            }
        ],
        max_trace=1,
    )

    same = _action({"kind": "set_value", "key": "outcome", "value": "same"})
    non_discriminating = runtime.acquisition_demand(
        "development-no-limitation-control",
        "development_record",
        [same],
        [
            {
                "case_id": "no-limit-left",
                "context": ["north"],
                "initial": {},
                "expected": {"outcome": "same"},
            },
            {
                "case_id": "no-limit-right",
                "context": ["south"],
                "initial": {},
                "expected": {"outcome": "same"},
            },
        ],
        [
            {"probe_id": "no-limit-probe-left", "context": ["north"], "initial": {}},
            {"probe_id": "no-limit-probe-right", "context": ["south"], "initial": {}},
        ],
        max_trace=1,
    )
    payload = {
        "schema": "m103-development-fixture-v1",
        "milestone": "M103",
        "qualification": False,
        "producer": producer,
        "ambiguous_control": ambiguous,
        "non_discriminating_control": non_discriminating,
    }
    payload["fixture_digest"] = runtime.digest(payload)
    return payload


def main() -> int:
    expected = runtime.canonical_json(build_fixture()).encode("ascii")
    if OUTPUT.exists() and OUTPUT.read_bytes() != expected:
        raise SystemExit("existing M103 DEVELOPMENT fixture differs from deterministic authoring")
    OUTPUT.write_bytes(expected)
    fixture = json.loads(expected)
    print(json.dumps({"path": str(OUTPUT), "fixture_digest": fixture["fixture_digest"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
