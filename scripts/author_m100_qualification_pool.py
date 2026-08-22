"""Author M100's complete fresh-world population without running acquisition."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "experiments" / "M100" / "QUALIFICATION_POOL.json"
COMPONENT = "pkg/values.py"
POOL_SCHEMA = "m100-qualification-pool-v1"


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode("ascii")).hexdigest()


STRUCTURES = (
    {
        "id": "signal_margin", "cycle": "A", "class": "SignalFrame",
        "key": "margin", "left_field": "observed", "right_field": "baseline",
        "signature": [1, -1],
        "fields": [
            {"name": "channel", "annotation": "str"},
            {"name": "baseline", "annotation": "int"},
            {"name": "observed", "annotation": "int"},
        ],
        "cases": [
            {"channel": "a", "baseline": 3, "observed": 11},
            {"channel": "b", "baseline": 7, "observed": 7},
            {"channel": "c", "baseline": 14, "observed": 2},
            {"channel": "d", "baseline": -5, "observed": 4},
        ],
    },
    {
        "id": "route_slack", "cycle": "A", "class": "RouteBudget",
        "key": "slack", "left_field": "available", "right_field": "reserved",
        "signature": [1, -1],
        "fields": [
            {"name": "reserved", "annotation": "float"},
            {"name": "route", "annotation": "str"},
            {"name": "available", "annotation": "float"},
            {"name": "revision", "annotation": "int"},
        ],
        "cases": [
            {"reserved": 2.5, "route": "n", "available": 8.0, "revision": 1},
            {"reserved": 5.0, "route": "s", "available": 5.0, "revision": 2},
            {"reserved": 9.25, "route": "e", "available": 1.5, "revision": 3},
            {"reserved": -1.0, "route": "w", "available": 3.25, "revision": 4},
        ],
    },
    {
        "id": "thermal_offset", "cycle": "A", "class": "CalibrationRead",
        "key": "offset", "left_field": "measured", "right_field": "reference",
        "signature": [1, -1],
        "fields": [
            {"name": "probe", "annotation": "str"},
            {"name": "measured", "annotation": "float"},
            {"name": "epoch", "annotation": "int"},
            {"name": "reference", "annotation": "float"},
        ],
        "cases": [
            {"probe": "p", "measured": 10.5, "epoch": 1, "reference": 2.0},
            {"probe": "q", "measured": 4.0, "epoch": 2, "reference": 4.0},
            {"probe": "r", "measured": -3.5, "epoch": 3, "reference": 1.0},
            {"probe": "s", "measured": 0.25, "epoch": 4, "reference": -2.5},
        ],
    },
    {
        "id": "combined_load", "cycle": "B", "class": "LoadPair",
        "key": "combined", "left_field": "primary", "right_field": "secondary",
        "signature": [1, 1],
        "fields": [
            {"name": "secondary", "annotation": "int"},
            {"name": "primary", "annotation": "int"},
            {"name": "node", "annotation": "str"},
        ],
        "cases": [
            {"secondary": 4, "primary": 9, "node": "a"},
            {"secondary": -3, "primary": 3, "node": "b"},
            {"secondary": 8, "primary": -2, "node": "c"},
            {"secondary": -5, "primary": -7, "node": "d"},
        ],
    },
    {
        "id": "total_credit", "cycle": "B", "class": "CreditPair",
        "key": "total", "left_field": "earned", "right_field": "carried",
        "signature": [1, 1],
        "fields": [
            {"name": "account", "annotation": "str"},
            {"name": "earned", "annotation": "float"},
            {"name": "period", "annotation": "int"},
            {"name": "carried", "annotation": "float"},
        ],
        "cases": [
            {"account": "x", "earned": 4.5, "period": 1, "carried": 1.25},
            {"account": "y", "earned": 0.0, "period": 2, "carried": 0.0},
            {"account": "z", "earned": -2.0, "period": 3, "carried": 9.5},
            {"account": "w", "earned": -1.5, "period": 4, "carried": -3.0},
        ],
    },
    {
        "id": "merged_distance", "cycle": "B", "class": "RouteLegs",
        "key": "distance", "left_field": "outbound", "right_field": "returning",
        "signature": [1, 1],
        "fields": [
            {"name": "route", "annotation": "str"},
            {"name": "returning", "annotation": "int"},
            {"name": "outbound", "annotation": "int"},
            {"name": "version", "annotation": "int"},
        ],
        "cases": [
            {"route": "m", "returning": 5, "outbound": 12, "version": 1},
            {"route": "n", "returning": 0, "outbound": 7, "version": 2},
            {"route": "o", "returning": -4, "outbound": 6, "version": 3},
            {"route": "p", "returning": -9, "outbound": -2, "version": 4},
        ],
    },
    {
        "id": "reinforced_score", "cycle": "C", "class": "ScorePair",
        "key": "reinforced", "left_field": "base", "right_field": "bonus",
        "signature": [1, 2],
        "fields": [
            {"name": "base", "annotation": "int"},
            {"name": "label", "annotation": "str"},
            {"name": "bonus", "annotation": "int"},
        ],
        "cases": [
            {"base": 10, "label": "a", "bonus": 3},
            {"base": 4, "label": "b", "bonus": 0},
            {"base": -2, "label": "c", "bonus": 5},
            {"base": 7, "label": "d", "bonus": -4},
        ],
    },
    {
        "id": "replicated_cost", "cycle": "C", "class": "CostFrame",
        "key": "replicated", "left_field": "setup", "right_field": "unit",
        "signature": [1, 2],
        "fields": [
            {"name": "unit", "annotation": "float"},
            {"name": "setup", "annotation": "float"},
            {"name": "currency", "annotation": "str"},
            {"name": "batch", "annotation": "int"},
        ],
        "cases": [
            {"unit": 2.5, "setup": 8.0, "currency": "e", "batch": 1},
            {"unit": 0.0, "setup": 3.0, "currency": "f", "batch": 2},
            {"unit": -1.5, "setup": 2.0, "currency": "g", "batch": 3},
            {"unit": 4.25, "setup": -2.5, "currency": "h", "batch": 4},
        ],
    },
    {
        "id": "duplicated_mass", "cycle": "C", "class": "MassBlend",
        "key": "loaded", "left_field": "core", "right_field": "shell",
        "signature": [1, 2],
        "fields": [
            {"name": "serial", "annotation": "str"},
            {"name": "shell", "annotation": "int"},
            {"name": "core", "annotation": "int"},
            {"name": "generation", "annotation": "int"},
        ],
        "cases": [
            {"serial": "u", "shell": 3, "core": 20, "generation": 1},
            {"serial": "v", "shell": 0, "core": 6, "generation": 2},
            {"serial": "w", "shell": -4, "core": 9, "generation": 3},
            {"serial": "x", "shell": 7, "core": -5, "generation": 4},
        ],
    },
)


def build_pool(*, status: str = "candidate") -> dict[str, object]:
    entries = []
    for specification in STRUCTURES:
        entry = dict(specification)
        entry["caller_count"] = 2
        entry["entry_digest"] = digest(entry)
        entries.append(entry)
    pool: dict[str, object] = {
        "schema": POOL_SCHEMA,
        "milestone": "M100",
        "status": status,
        "construction": (
            "all nine authored post-M099 structures, three per conserved operation; "
            "no draw, exclusion, salt or reroll"
        ),
        "m097_through_m099_worlds_excluded": True,
        "entries": entries,
        "population_size": len(entries),
        "cycle_counts": {"A": 3, "B": 3, "C": 3},
        "preflight_boundary": (
            "construct and parse source and cases only; migration, acquisition, registration, "
            "isolated execution, mutation, ablation and rollback are forbidden before freeze"
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
        raise ValueError("M100 pool digest mismatch")
    return value


def _expression(entry: dict[str, object]) -> str:
    left = f"value.{entry['left_field']}"
    right = f"value.{entry['right_field']}"
    signature = entry["signature"]
    if signature == [1, -1]:
        return f"{left} - {right}"
    if signature == [1, 1]:
        return f"{left} + {right}"
    if signature == [1, 2]:
        return f"{left} + {right} + {right}"
    raise ValueError("unsupported authored signature")


def build_world(root: Path, entry: dict[str, object]) -> Path:
    package = root / "pkg"
    package.mkdir(parents=True, exist_ok=True)
    (package / "__init__.py").write_text("", encoding="utf-8", newline="\n")
    source = [
        '"""M100 fresh world; the required renderer is absent at S0."""',
        "", "from dataclasses import dataclass", "", "", "@dataclass(frozen=True)",
        f"class {entry['class']}:",
        *[f"    {field['name']}: {field['annotation']}" for field in entry["fields"]],
        "",
    ]
    (root / COMPONENT).write_text("\n".join(source), encoding="utf-8", newline="\n")
    for index in range(int(entry["caller_count"])):
        caller = [
            f"from pkg.values import {entry['class']}", "", "",
            f"def emit_{index}(value: {entry['class']}) -> dict:",
            "    return {", f"        {entry['key']!r}: {_expression(entry)},", "    }", "",
        ]
        (root / f"caller_{index}.py").write_text(
            "\n".join(caller), encoding="utf-8", newline="\n"
        )
    return root


def write_cases(path: Path, entry: dict[str, object]) -> Path:
    left_coefficient, right_coefficient = entry["signature"]
    cases = []
    for raw in entry["cases"]:
        arguments = dict(raw)
        expected = (
            left_coefficient * arguments[str(entry["left_field"])]
            + right_coefficient * arguments[str(entry["right_field"])]
        )
        cases.append({"arguments": arguments, "expected": expected})
    path.write_text(canonical_json(cases), encoding="utf-8", newline="\n")
    return path


def audit(pool: dict[str, object]) -> dict[str, object]:
    rows = []
    with tempfile.TemporaryDirectory(prefix="m100-pool-audit-") as temporary:
        base = Path(temporary)
        for entry in pool["entries"]:
            root = build_world(base / str(entry["id"]), entry)
            cases_path = write_cases(root / "cases.json", entry)
            parsed = 0
            for path in root.rglob("*.py"):
                ast.parse(path.read_text(encoding="utf-8"))
                parsed += 1
            cases = json.loads(cases_path.read_text(encoding="utf-8"))
            failures = []
            if parsed != int(entry["caller_count"]) + 2:
                failures.append("unexpected Python file census")
            if len(cases) != 4 or any(set(item) != {"arguments", "expected"} for item in cases):
                failures.append("world does not contain four closed execution cases")
            rows.append({
                "entry": entry["id"], "cycle": entry["cycle"], "python_files": parsed,
                "cases": len(cases), "passed": not failures, "failures": failures,
            })
    return {
        "schema": "m100-pool-audit-v1",
        "pool_digest": pool["pool_digest"],
        "entries_checked": len(rows),
        "migration_was_run": False,
        "acquisition_was_run": False,
        "fresh_runtime_was_run": False,
        "fault_was_injected": False,
        "passed": len(rows) == 9 and all(row["passed"] for row in rows),
        "entries": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--status", choices=("candidate", "frozen"), default="candidate")
    args = parser.parse_args()
    pool = build_pool(status=args.status)
    report = audit(pool)
    if args.write:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(json.dumps(pool, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"pool": pool, "audit": report}, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
