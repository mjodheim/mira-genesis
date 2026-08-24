"""Author the project-controlled M105 qualification pool after implementation."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from metamorphosis import m105_runtime as runtime


def _context(signals: tuple[bool, bool], nonce: str) -> dict[str, Any]:
    return {"signals": list(signals), "nonce": nonce}


def _json_demand() -> dict[str, Any]:
    amber = runtime.action_definition(
        {"kind": "set_field", "key": "route", "value": "amber"}
    )
    violet = runtime.action_definition(
        {"kind": "set_field", "key": "route", "value": "violet"}
    )
    return runtime.consumer_demand(
        "json_consumer",
        "json_document",
        [amber, violet],
        [
            {
                "case_id": "json_public_00",
                "context": _context((False, False), "json-public-cinder"),
                "initial": {"seed": "same"},
                "expected": {"seed": "same", "route": "amber"},
            },
            {
                "case_id": "json_public_01",
                "context": _context((False, True), "json-public-lilac"),
                "initial": {"seed": "same"},
                "expected": {"seed": "same", "route": "violet"},
            },
        ],
        [
            {
                "probe_id": "json_probe_10",
                "context": _context((True, False), "json-probe-cedar"),
                "initial": {"probe": "ten"},
            },
            {
                "probe_id": "json_probe_11",
                "context": _context((True, True), "json-probe-slate"),
                "initial": {"probe": "eleven"},
            },
        ],
        max_trace=1,
    )


def _sqlite_initial(value: str = "seed") -> dict[str, Any]:
    return {"rows": [{"id": 1, "value": value, "status": "base"}]}


def _sqlite_demand() -> dict[str, Any]:
    amber = runtime.action_definition(
        {"kind": "set_status", "id": 1, "status": "amber"}
    )
    violet = runtime.action_definition(
        {"kind": "set_status", "id": 1, "status": "violet"}
    )
    return runtime.consumer_demand(
        "sqlite_consumer",
        "sqlite",
        [amber, violet],
        [
            {
                "case_id": "sqlite_public_00",
                "context": _context((False, False), "sqlite-public-ochre"),
                "initial": _sqlite_initial(),
                "expected": {
                    "rows": [{"id": 1, "value": "seed", "status": "amber"}]
                },
            },
            {
                "case_id": "sqlite_public_01",
                "context": _context((False, True), "sqlite-public-violet"),
                "initial": _sqlite_initial(),
                "expected": {
                    "rows": [{"id": 1, "value": "seed", "status": "violet"}]
                },
            },
        ],
        [
            {
                "probe_id": "sqlite_probe_10",
                "context": _context((True, False), "sqlite-probe-cobalt"),
                "initial": _sqlite_initial("probe-ten"),
            },
            {
                "probe_id": "sqlite_probe_11",
                "context": _context((True, True), "sqlite-probe-ivory"),
                "initial": _sqlite_initial("probe-eleven"),
            },
        ],
        max_trace=1,
    )


def _hidden_cases(family: str) -> list[dict[str, Any]]:
    rows = (
        ((False, False), "amber"),
        ((False, True), "violet"),
        ((True, False), "violet"),
        ((True, True), "amber"),
    )
    hidden: list[dict[str, Any]] = []
    for index, (signals, route) in enumerate(rows):
        if family == "json_document":
            initial: Any = {"hidden": index, "preserve": True}
            expected: Any = {"hidden": index, "preserve": True, "route": route}
        else:
            initial = _sqlite_initial(f"hidden-{index}")
            expected = {
                "rows": [{"id": 1, "value": f"hidden-{index}", "status": route}]
            }
        hidden.append(
            {
                "case_id": f"{family}_hidden_{index}",
                "context": _context(signals, f"{family}-hidden-nonce-{index}"),
                "initial": initial,
                "expected": expected,
            }
        )
    return hidden


def build() -> dict[str, Any]:
    pool: dict[str, Any] = {
        "schema": "m105-qualification-pool-v1",
        "milestone": "M105",
        "authorship": "project_controlled_not_independent_task_evidence",
        "json_demand": _json_demand(),
        "sqlite_demand": _sqlite_demand(),
        "hidden_json_cases": _hidden_cases("json_document"),
        "hidden_sqlite_cases": _hidden_cases("sqlite"),
    }
    pool["pool_digest"] = runtime.digest(pool)
    return pool


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="experiments/M105/QUALIFICATION_POOL.json")
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    raw = runtime.canonical_json(build()).encode("ascii")
    target = Path(arguments.out)
    if arguments.check:
        if not target.exists() or target.read_bytes() != raw:
            raise SystemExit("M105 qualification pool is stale")
        return 0
    if target.exists():
        raise SystemExit("M105 qualification pool already exists")
    target.write_bytes(raw)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
