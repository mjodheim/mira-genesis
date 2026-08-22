"""Author M099's fresh successor worlds without invoking the persistence runtime."""

from __future__ import annotations

import ast
import json
import tempfile
from pathlib import Path

from scripts.author_m098_qualification_pool import (
    COMPONENT,
    build_world,
    canonical_json,
    digest,
    write_cases,
)

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "experiments" / "M099" / "QUALIFICATION_POOL.json"
POOL_SCHEMA = "m099-qualification-pool-v1"

STRUCTURES = (
    {
        "id": "storage_headroom",
        "class": "StorageWindow",
        "key": "headroom",
        "left_field": "allocated",
        "right_field": "used",
        "fields": [
            {"name": "pool", "annotation": "str"},
            {"name": "used", "annotation": "int"},
            {"name": "generation", "annotation": "int"},
            {"name": "allocated", "annotation": "int"},
        ],
        "cases": [
            {"pool": "a", "used": 3, "generation": 1, "allocated": 15},
            {"pool": "b", "used": 8, "generation": 2, "allocated": 8},
            {"pool": "c", "used": 21, "generation": 3, "allocated": 5},
            {"pool": "d", "used": -2, "generation": 4, "allocated": 6},
        ],
    },
    {
        "id": "pressure_drop",
        "class": "PressurePair",
        "key": "drop",
        "left_field": "inlet",
        "right_field": "outlet",
        "fields": [
            {"name": "outlet", "annotation": "float"},
            {"name": "inlet", "annotation": "float"},
            {"name": "station", "annotation": "str"},
        ],
        "cases": [
            {"outlet": 2.25, "inlet": 9.5, "station": "n"},
            {"outlet": 4.0, "inlet": 4.0, "station": "s"},
            {"outlet": 7.75, "inlet": 1.25, "station": "e"},
            {"outlet": -3.0, "inlet": 0.5, "station": "w"},
        ],
    },
    {
        "id": "inventory_delta",
        "class": "InventoryFrame",
        "key": "delta",
        "left_field": "counted",
        "right_field": "expected",
        "fields": [
            {"name": "sku", "annotation": "str"},
            {"name": "expected", "annotation": "int"},
            {"name": "warehouse", "annotation": "str"},
            {"name": "counted", "annotation": "int"},
            {"name": "cycle", "annotation": "int"},
        ],
        "cases": [
            {"sku": "q", "expected": 10, "warehouse": "a", "counted": 13, "cycle": 1},
            {"sku": "r", "expected": 5, "warehouse": "b", "counted": 5, "cycle": 2},
            {"sku": "s", "expected": 19, "warehouse": "c", "counted": 4, "cycle": 3},
            {"sku": "t", "expected": -2, "warehouse": "d", "counted": 7, "cycle": 4},
        ],
    },
)


def build_pool(*, status: str = "candidate") -> dict[str, object]:
    entries = []
    for spec in STRUCTURES:
        entry = dict(spec)
        entry["operator"] = "sub"
        entry["caller_count"] = 2
        entry["entry_digest"] = digest(entry)
        entries.append(entry)
    pool: dict[str, object] = {
        "schema": POOL_SCHEMA,
        "milestone": "M099",
        "status": status,
        "construction": "all three post-M098 successor structures; no draw, salt, exclusion or reroll",
        "m097_and_m098_worlds_excluded": True,
        "entries": entries,
        "population_size": len(entries),
        "preflight_boundary": (
            "construct and parse source and cases only; producer, persisted-state consumer, "
            "fault mutation, rollback and any capability execution are forbidden before freeze"
        ),
    }
    pool["pool_digest"] = digest(pool)
    return pool


def load_pool(path: Path = OUTPUT) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    recorded = value.pop("pool_digest", None)
    recomputed = digest(value)
    value["pool_digest"] = recorded
    if recorded != recomputed:
        raise ValueError("M099 pool digest mismatch")
    return value


def audit(pool: dict[str, object]) -> dict[str, object]:
    rows = []
    with tempfile.TemporaryDirectory(prefix="m099-pool-audit-") as temporary:
        base = Path(temporary)
        for entry in pool["entries"]:
            root = build_world(base / str(entry["id"]), entry)
            cases = write_cases(root / "cases.json", entry)
            parsed = 0
            for path in root.rglob("*.py"):
                ast.parse(path.read_text(encoding="utf-8"))
                parsed += 1
            loaded_cases = json.loads(cases.read_text(encoding="utf-8"))
            failures = []
            if parsed != int(entry["caller_count"]) + 2:
                failures.append("unexpected Python file census")
            if len(loaded_cases) != 4:
                failures.append("world does not contain four post-restart cases")
            rows.append({
                "entry": entry["id"], "python_files": parsed,
                "cases": len(loaded_cases), "passed": not failures, "failures": failures,
            })
    return {
        "schema": "m099-pool-audit-v1",
        "pool_digest": pool["pool_digest"],
        "entries_checked": len(rows),
        "producer_was_run": False,
        "fresh_runtime_was_run": False,
        "fault_was_injected": False,
        "passed": bool(rows) and all(row["passed"] for row in rows),
        "entries": rows,
    }


def main() -> int:
    pool = build_pool()
    report = audit(pool)
    print(json.dumps({"pool": pool, "audit": report}, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
