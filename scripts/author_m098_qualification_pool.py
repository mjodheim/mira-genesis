"""Author M098 post-restart worlds without invoking persistence or the fresh runtime."""

from __future__ import annotations

import ast
import hashlib
import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "experiments" / "M098" / "QUALIFICATION_POOL.json"
COMPONENT = "pkg/values.py"
POOL_SCHEMA = "m098-qualification-pool-v1"


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode("ascii")).hexdigest()


STRUCTURES = (
    {
        "id": "thermal_spread",
        "class": "ThermalBand",
        "key": "spread",
        "left_field": "high",
        "right_field": "low",
        "fields": [
            {"name": "sensor", "annotation": "str"},
            {"name": "low", "annotation": "float"},
            {"name": "high", "annotation": "float"},
        ],
        "cases": [
            {"sensor": "a", "low": -2.5, "high": 7.0},
            {"sensor": "b", "low": 5.0, "high": 5.0},
            {"sensor": "c", "low": 9.5, "high": 3.25},
            {"sensor": "d", "low": 0.125, "high": 1.0},
        ],
    },
    {
        "id": "version_span",
        "class": "VersionRange",
        "key": "span",
        "left_field": "ceiling",
        "right_field": "floor",
        "fields": [
            {"name": "floor", "annotation": "int"},
            {"name": "ceiling", "annotation": "int"},
            {"name": "channel", "annotation": "str"},
            {"name": "epoch", "annotation": "int"},
        ],
        "cases": [
            {"floor": 1, "ceiling": 8, "channel": "a", "epoch": 2},
            {"floor": -4, "ceiling": 4, "channel": "b", "epoch": 3},
            {"floor": 9, "ceiling": 2, "channel": "c", "epoch": 4},
            {"floor": 0, "ceiling": 0, "channel": "d", "epoch": 5},
        ],
    },
    {
        "id": "quota_unused",
        "class": "QuotaSlice",
        "key": "unused",
        "left_field": "granted",
        "right_field": "consumed",
        "fields": [
            {"name": "consumed", "annotation": "int"},
            {"name": "account", "annotation": "str"},
            {"name": "granted", "annotation": "int"},
        ],
        "cases": [
            {"consumed": 4, "account": "x", "granted": 12},
            {"consumed": 0, "account": "y", "granted": 0},
            {"consumed": 17, "account": "z", "granted": 6},
            {"consumed": -3, "account": "w", "granted": 2},
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
        "milestone": "M098",
        "status": status,
        "construction": "all three post-M097 structures; no draw, salt, exclusion or reroll",
        "m097_development_and_qualification_worlds_excluded": True,
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
        raise ValueError("M098 pool digest mismatch")
    return value


def build_world(root: Path, entry: dict[str, object]) -> Path:
    package = root / "pkg"
    package.mkdir(parents=True, exist_ok=True)
    (package / "__init__.py").write_text("", encoding="utf-8", newline="\n")
    source = [
        '"""M098 post-restart world; no renderer is present at S0."""',
        "",
        "from dataclasses import dataclass",
        "",
        "",
        "@dataclass(frozen=True)",
        f"class {entry['class']}:",
        *[f"    {field['name']}: {field['annotation']}" for field in entry["fields"]],
        "",
    ]
    (root / COMPONENT).write_text("\n".join(source), encoding="utf-8", newline="\n")
    for index in range(int(entry["caller_count"])):
        caller = [
            f"from pkg.values import {entry['class']}", "", "",
            f"def emit_{index}(value: {entry['class']}) -> dict:",
            "    return {",
            (
                f"        {entry['key']!r}: value.{entry['left_field']} "
                f"- value.{entry['right_field']},"
            ),
            "    }", "",
        ]
        (root / f"caller_{index}.py").write_text(
            "\n".join(caller), encoding="utf-8", newline="\n"
        )
    return root


def write_cases(path: Path, entry: dict[str, object]) -> Path:
    cases = [{"arguments": dict(case)} for case in entry["cases"]]
    path.write_text(canonical_json(cases) + "\n", encoding="utf-8", newline="\n")
    return path


def audit(pool: dict[str, object]) -> dict[str, object]:
    rows = []
    with tempfile.TemporaryDirectory(prefix="m098-pool-audit-") as temporary:
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
            if any("arguments" not in case for case in loaded_cases):
                failures.append("case lacks constructor arguments")
            rows.append({
                "entry": entry["id"], "python_files": parsed,
                "cases": len(loaded_cases), "passed": not failures, "failures": failures,
            })
    return {
        "schema": "m098-pool-audit-v1",
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
