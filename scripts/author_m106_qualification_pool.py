"""Author the project-controlled M106 qualification population.

Fresh with respect to M105 in target semantic, identifiers, nonces, carrier keys, carrier values,
initial payloads and hidden cases. The mechanism module is imported unchanged.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Direct script execution puts scripts/ on sys.path, not the repository root, so
# ``from scripts import ...`` raises ModuleNotFoundError. That defect made M105's frozen checker
# exit before evaluating a single predicate and lost the milestone (D074). Every M106 entry point
# bootstraps the root explicitly and is exercised as a direct script before the freeze.
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import argparse
from pathlib import Path
from typing import Any

from metamorphosis import m105_runtime as runtime
from scripts.author_m106_development_fixture import TARGET_TRUTH_TABLE

SIGNAL_ROWS = ((False, False), (False, True), (True, False), (True, True))
TRUE_VALUE = "harbor"
FALSE_VALUE = "quartz"


def _context(signals: tuple[bool, bool], nonce: str) -> dict[str, Any]:
    return {"signals": list(signals), "nonce": nonce}


def _value_for(row_index: int) -> str:
    return TRUE_VALUE if TARGET_TRUTH_TABLE[row_index] else FALSE_VALUE


def _json_demand() -> dict[str, Any]:
    true_action = runtime.action_definition(
        {"kind": "set_field", "key": "channel", "value": TRUE_VALUE}
    )
    false_action = runtime.action_definition(
        {"kind": "set_field", "key": "channel", "value": FALSE_VALUE}
    )
    return runtime.consumer_demand(
        "m106_json_consumer",
        "json_document",
        [true_action, false_action],
        [
            {
                "case_id": "m106_json_public_00",
                "context": _context(SIGNAL_ROWS[0], "m106-json-public-thistle"),
                "initial": {"ledger": "open"},
                "expected": {"ledger": "open", "channel": _value_for(0)},
            },
            {
                "case_id": "m106_json_public_01",
                "context": _context(SIGNAL_ROWS[1], "m106-json-public-marram"),
                "initial": {"ledger": "open"},
                "expected": {"ledger": "open", "channel": _value_for(1)},
            },
        ],
        [
            {
                "probe_id": "m106_json_probe_10",
                "context": _context(SIGNAL_ROWS[2], "m106-json-probe-fennel"),
                "initial": {"probe": "row-two"},
            },
            {
                "probe_id": "m106_json_probe_11",
                "context": _context(SIGNAL_ROWS[3], "m106-json-probe-yarrow"),
                "initial": {"probe": "row-three"},
            },
        ],
        max_trace=1,
    )


def _sqlite_initial(value: str = "ledger") -> dict[str, Any]:
    return {"rows": [{"id": 1, "value": value, "status": "origin"}]}


def _sqlite_demand() -> dict[str, Any]:
    true_action = runtime.action_definition(
        {"kind": "set_status", "id": 1, "status": TRUE_VALUE}
    )
    false_action = runtime.action_definition(
        {"kind": "set_status", "id": 1, "status": FALSE_VALUE}
    )
    return runtime.consumer_demand(
        "m106_sqlite_consumer",
        "sqlite",
        [true_action, false_action],
        [
            {
                "case_id": "m106_sqlite_public_00",
                "context": _context(SIGNAL_ROWS[0], "m106-sqlite-public-basalt"),
                "initial": _sqlite_initial(),
                "expected": {
                    "rows": [{"id": 1, "value": "ledger", "status": _value_for(0)}]
                },
            },
            {
                "case_id": "m106_sqlite_public_01",
                "context": _context(SIGNAL_ROWS[1], "m106-sqlite-public-gypsum"),
                "initial": _sqlite_initial(),
                "expected": {
                    "rows": [{"id": 1, "value": "ledger", "status": _value_for(1)}]
                },
            },
        ],
        [
            {
                "probe_id": "m106_sqlite_probe_10",
                "context": _context(SIGNAL_ROWS[2], "m106-sqlite-probe-tallow"),
                "initial": _sqlite_initial("probe-row-two"),
            },
            {
                "probe_id": "m106_sqlite_probe_11",
                "context": _context(SIGNAL_ROWS[3], "m106-sqlite-probe-marlin"),
                "initial": _sqlite_initial("probe-row-three"),
            },
        ],
        max_trace=1,
    )


def _hidden_cases(family: str) -> list[dict[str, Any]]:
    hidden: list[dict[str, Any]] = []
    for index, signals in enumerate(SIGNAL_ROWS):
        value = _value_for(index)
        if family == "json_document":
            initial: Any = {"sealed": index, "retain": True}
            expected: Any = {"sealed": index, "retain": True, "channel": value}
        else:
            initial = _sqlite_initial(f"sealed-{index}")
            expected = {"rows": [{"id": 1, "value": f"sealed-{index}", "status": value}]}
        hidden.append(
            {
                "case_id": f"m106_{family}_hidden_{index}",
                "context": _context(signals, f"m106-{family}-sealed-nonce-{index}"),
                "initial": initial,
                "expected": expected,
            }
        )
    return hidden


def build() -> dict[str, Any]:
    pool: dict[str, Any] = {
        "schema": "m106-qualification-pool-v1",
        "milestone": "M106",
        "authorship": "project_controlled_not_independent_task_evidence",
        "target_truth_table": list(TARGET_TRUTH_TABLE),
        "json_demand": _json_demand(),
        "sqlite_demand": _sqlite_demand(),
        "hidden_json_cases": _hidden_cases("json_document"),
        "hidden_sqlite_cases": _hidden_cases("sqlite"),
    }
    pool["pool_digest"] = runtime.digest(pool)
    return pool


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="experiments/M106/QUALIFICATION_POOL.json")
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    raw = runtime.canonical_json(build()).encode("ascii")
    target = Path(arguments.out)
    if arguments.check:
        if not target.exists() or target.read_bytes() != raw:
            raise SystemExit("M106 qualification pool is stale")
        return 0
    if target.exists():
        raise SystemExit("M106 qualification pool already exists")
    target.write_bytes(raw)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
