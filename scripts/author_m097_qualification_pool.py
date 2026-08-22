"""Author M097's fresh real-Python qualification worlds without acquiring an extension."""

from __future__ import annotations

import ast
import hashlib
import json
import tempfile
from pathlib import Path

from metamorphosis.m097_language import observe_requirement

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "experiments" / "M097" / "QUALIFICATION_POOL.json"
POOL_SCHEMA = "m097-qualification-pool-v1"
COMPONENT = "pkg/values.py"


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode("ascii")).hexdigest()


STRUCTURES = (
    {
        "id": "elapsed_window",
        "class": "Window",
        "key": "elapsed",
        "left_field": "closed",
        "right_field": "opened",
        "fields": [
            {"name": "opened", "annotation": "int"},
            {"name": "closed", "annotation": "int"},
            {"name": "label", "annotation": "str"},
        ],
        "cases": [
            {"opened": 2, "closed": 9, "label": "a"},
            {"opened": -4, "closed": 3, "label": "b"},
            {"opened": 10, "closed": 10, "label": "c"},
            {"opened": 7, "closed": 2, "label": "d"},
        ],
        "axes": ["reversed declaration order", "signed integers", "unrelated string field"],
    },
    {
        "id": "remaining_capacity",
        "class": "Capacity",
        "key": "remaining",
        "left_field": "maximum",
        "right_field": "occupied",
        "fields": [
            {"name": "maximum", "annotation": "int"},
            {"name": "occupied", "annotation": "int"},
            {"name": "reserved", "annotation": "int"},
        ],
        "cases": [
            {"maximum": 12, "occupied": 5, "reserved": 1},
            {"maximum": 0, "occupied": 0, "reserved": 0},
            {"maximum": 3, "occupied": 8, "reserved": 2},
            {"maximum": 101, "occupied": 44, "reserved": 9},
        ],
        "axes": ["different business meaning", "third numeric field", "negative result allowed"],
    },
    {
        "id": "floating_displacement",
        "class": "Movement",
        "key": "delta",
        "left_field": "finish",
        "right_field": "origin",
        "fields": [
            {"name": "origin", "annotation": "float"},
            {"name": "finish", "annotation": "float"},
            {"name": "axis", "annotation": "str"},
        ],
        "cases": [
            {"origin": 1.5, "finish": 4.75, "axis": "x"},
            {"origin": -2.0, "finish": 5.5, "axis": "y"},
            {"origin": 8.25, "finish": 3.0, "axis": "z"},
            {"origin": 0.0, "finish": 0.125, "axis": "t"},
        ],
        "axes": ["floating values", "renamed result key", "unrelated categorical field"],
    },
    {
        "id": "account_balance",
        "class": "AccountSlice",
        "key": "balance",
        "left_field": "credits",
        "right_field": "debits",
        "fields": [
            {"name": "owner", "annotation": "str"},
            {"name": "debits", "annotation": "int"},
            {"name": "credits", "annotation": "int"},
            {"name": "revision", "annotation": "int"},
        ],
        "cases": [
            {"owner": "a", "debits": 4, "credits": 11, "revision": 1},
            {"owner": "b", "debits": 9, "credits": 3, "revision": 2},
            {"owner": "c", "debits": 0, "credits": 0, "revision": 3},
            {"owner": "d", "debits": -2, "credits": 5, "revision": 4},
        ],
        "axes": ["four declared fields", "operands declared out of expression order", "financial interpretation"],
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
        "milestone": "M097",
        "status": status,
        "construction": "all four authored structures; no draw, exclusion, salt or reroll",
        "development_world_excluded": True,
        "qualification_was_not_run_during_development": True,
        "entries": entries,
        "population_size": len(entries),
        "preflight_boundary": (
            "construct and parse source, recover the unambiguous binary demand and cases, "
            "and check content addresses only; no candidate acquisition, registration, "
            "extended search or execution before freeze"
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
        raise ValueError("M097 qualification-pool digest mismatch")
    return value


def build_world(root: Path, entry: dict[str, object]) -> Path:
    package = root / "pkg"
    package.mkdir(parents=True, exist_ok=True)
    (package / "__init__.py").write_text("", encoding="utf-8", newline="\n")
    fields = list(entry["fields"])
    source = [
        '"""M097 qualification value object; no derived renderer at S0."""',
        "",
        "from dataclasses import dataclass",
        "",
        "",
        "@dataclass(frozen=True)",
        f"class {entry['class']}:",
        *[f"    {field['name']}: {field['annotation']}" for field in fields],
        "",
    ]
    (root / COMPONENT).write_text("\n".join(source), encoding="utf-8", newline="\n")
    for index in range(int(entry["caller_count"])):
        caller = [
            f"from pkg.values import {entry['class']}",
            "",
            "",
            f"def emit_{index}(value: {entry['class']}) -> dict:",
            "    return {",
            (
                f"        {entry['key']!r}: value.{entry['left_field']} "
                f"- value.{entry['right_field']},"
            ),
            "    }",
            "",
        ]
        (root / f"caller_{index}.py").write_text(
            "\n".join(caller), encoding="utf-8", newline="\n"
        )
    return root


def cases_for(entry: dict[str, object]) -> list[dict[str, object]]:
    return [{"arguments": dict(case)} for case in entry["cases"]]


def audit(pool: dict[str, object]) -> dict[str, object]:
    rows = []
    with tempfile.TemporaryDirectory(prefix="m097-pool-audit-") as temporary:
        base = Path(temporary)
        for entry in pool["entries"]:
            root = build_world(base / str(entry["id"]), entry)
            parsed = 0
            for path in root.rglob("*.py"):
                ast.parse(path.read_text(encoding="utf-8"))
                parsed += 1
            observed = observe_requirement(root, COMPONENT)
            expected = {
                "class": entry["class"],
                "key": entry["key"],
                "left_field": entry["left_field"],
                "operator": entry["operator"],
                "right_field": entry["right_field"],
                "demand": entry["caller_count"],
            }
            failures = []
            if observed.to_dict() != expected:
                failures.append("observed demand differs from the frozen recipe")
            if len(cases_for(entry)) < 4:
                failures.append("fewer than four execution cases")
            rows.append({
                "entry": entry["id"],
                "files_parsed": parsed,
                "observed_requirement": observed.to_dict(),
                "cases": len(cases_for(entry)),
                "passed": not failures,
                "failures": failures,
            })
    return {
        "schema": "m097-qualification-pool-audit-v1",
        "pool_digest": pool["pool_digest"],
        "entries_checked": len(rows),
        "acquisition_was_run": False,
        "extended_search_was_run": False,
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
