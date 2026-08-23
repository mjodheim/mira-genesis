"""Author and source-audit M101's complete fifteen-world population.

The audit is deliberately non-executing.  It parses and instantiates the authored
records, checks schemas and case counts, and parses Python source, but it never imports
or invokes the M101 mechanism, acquisition runtime, execution capsule, or checker.
"""

from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "experiments" / "M101" / "QUALIFICATION_POOL.json"
POOL_SCHEMA = "m101-qualification-pool-v1"

ROLE_COUNTS = {
    "producer_trigger": 1,
    "text_holdout": 2,
    "record_transfer": 3,
    "syntax_transfer": 3,
    "b_reuse": 3,
    "m100_conservation": 3,
}


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("ascii")).hexdigest()


def _case(case_id: str, value: Any, expected: Any) -> dict[str, Any]:
    return {"case_id": case_id, "input": value, "expected": expected}


def _split_cases(prefix: str, pairs: list[tuple[Any, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    cases = [
        _case(f"{prefix}-{index:02d}", copy.deepcopy(value), copy.deepcopy(expected))
        for index, (value, expected) in enumerate(pairs, start=1)
    ]
    return cases[:4], cases[4:]


def _text_world(
    world_id: str,
    role: str,
    catalog: list[dict[str, Any]],
    inputs: list[str],
    expected: Callable[[str], str],
) -> dict[str, Any]:
    public, hidden = _split_cases(world_id, [(value, expected(value)) for value in inputs])
    return {
        "id": world_id,
        "role": role,
        "carrier": "text",
        "catalog": catalog,
        "public_cases": public,
        "hidden_cases": hidden,
    }


def _record_world(
    world_id: str,
    catalog: list[dict[str, Any]],
    pairs: list[tuple[dict[str, Any], dict[str, Any]]],
) -> dict[str, Any]:
    public, hidden = _split_cases(world_id, pairs)
    return {
        "id": world_id,
        "role": "record_transfer",
        "carrier": "record",
        "catalog": catalog,
        "public_cases": public,
        "hidden_cases": hidden,
    }


def _source(name: str, argument: str, expression: str, document: str | None = None) -> str:
    lines = [f"def {name}({argument}):"]
    if document is not None:
        lines.append(f"    {document!r}")
    lines.append(f"    return {expression}")
    source = "\n".join(lines)
    ast.parse(source)
    return source


def _syntax_world(
    world_id: str,
    role: str,
    catalog: list[dict[str, Any]],
    pairs: list[tuple[str, str]],
) -> dict[str, Any]:
    public, hidden = _split_cases(world_id, pairs)
    return {
        "id": world_id,
        "role": role,
        "carrier": "syntax",
        "catalog": catalog,
        "public_cases": public,
        "hidden_cases": hidden,
    }


def _m100_world(
    world_id: str,
    operation_index: int,
    pairs: list[tuple[tuple[int | float, int | float], int | float]],
) -> dict[str, Any]:
    public, hidden = _split_cases(
        world_id,
        [({"left": left, "right": right}, expected) for (left, right), expected in pairs],
    )
    return {
        "id": world_id,
        "role": "m100_conservation",
        "carrier": "m100",
        "operation_index": operation_index,
        "public_cases": public,
        "hidden_cases": hidden,
    }


def _syntax_pairs(
    old_name: str,
    old_argument: str,
    expressions: list[str],
    expected: Callable[[str], str],
) -> list[tuple[str, str]]:
    return [
        (_source(old_name, old_argument, expression), expected(expression))
        for expression in expressions
    ]


def authored_worlds() -> list[dict[str, Any]]:
    worlds: list[dict[str, Any]] = []
    worlds.append(
        _text_world(
            "m101_text_origin_trim_upper",
            "producer_trigger",
            [{"kind": "suffix", "value": "?"}, {"kind": "strip"}, {"kind": "upper"}],
            [
                "  birch  ", "\tslate\n", " copper", "opal ",
                "\nmarble ", " zinc\t", "  amber", "quartz  ",
            ],
            lambda value: value.strip().upper(),
        )
    )
    worlds.append(
        _text_world(
            "m101_text_transfer_delimiter_upper",
            "text_holdout",
            [
                {"kind": "upper"},
                {"kind": "prefix", "value": "!"},
                {"kind": "replace", "old": "_", "new": " "},
            ],
            [
                "north_gate", "red_fox", "deep_blue", "small_ore",
                "winter_ash", "quiet_bay", "iron_peak", "silver_road",
            ],
            lambda value: value.replace("_", " ").upper(),
        )
    )
    worlds.append(
        _text_world(
            "m101_text_transfer_lower_suffix",
            "text_holdout",
            [
                {"kind": "suffix", "value": "::ok"},
                {"kind": "replace", "old": "A", "new": "x"},
                {"kind": "lower"},
            ],
            [
                "ALPHA", "BrOnZe", "CEDAR", "DeLtA",
                "EMBER", "FjOrD", "GRANITE", "HaRbOr",
            ],
            lambda value: value.lower() + "::ok",
        )
    )

    raw_lists = [
        ([8, 2, 5], "a"), ([0, -4, 3], "b"), ([7, 7, 1], "c"), ([], "d"),
        ([12, 4], "e"), ([-1, -8, 2], "f"), ([6], "g"), ([9, 3, 9], "h"),
    ]
    worlds.append(
        _record_world(
            "m101_record_transfer_rename_sort",
            [
                {"kind": "drop_key", "key": "label"},
                {"kind": "sort_list", "key": "ordered"},
                {"kind": "rename_key", "old": "raw", "new": "ordered"},
            ],
            [
                (
                    {"raw": values, "label": label},
                    {"ordered": sorted(values), "label": label},
                )
                for values, label in raw_lists
            ],
        )
    )
    payloads = [
        ("red", 3), ("blue", 8), ("green", -2), ("amber", 0),
        ("white", 11), ("black", 4), ("violet", -7), ("silver", 6),
    ]
    worlds.append(
        _record_world(
            "m101_record_transfer_rename_drop",
            [
                {"kind": "drop_key", "key": "discarded"},
                {"kind": "rename_key", "old": "payload", "new": "discarded"},
                {"kind": "set_default", "key": "note", "value": "none"},
            ],
            [
                (
                    {"payload": amount, "colour": colour, "revision": index},
                    {"colour": colour, "revision": index},
                )
                for index, (colour, amount) in enumerate(payloads, start=1)
            ],
        )
    )
    statuses = ["ready", "held", "open", "closed", "warm", "cold", "new", "old"]
    worlds.append(
        _record_world(
            "m101_record_transfer_reset_default",
            [
                {"kind": "set_default", "key": "status", "value": "pending"},
                {"kind": "sort_list", "key": "values"},
                {"kind": "drop_key", "key": "status"},
            ],
            [
                (
                    {"status": status, "token": index, "values": [index, 0]},
                    {"status": "pending", "token": index, "values": [index, 0]},
                )
                for index, status in enumerate(statuses, start=1)
            ],
        )
    )

    expressions_x = ["x - 4", "x * 3", "-x", "x + 9", "x // 2", "x - 11", "x * x", "x + 1"]
    worlds.append(
        _syntax_world(
            "m101_syntax_transfer_function_argument",
            "syntax_transfer",
            [
                {"kind": "rename_argument", "function": "refine", "old": "x", "new": "datum"},
                {"kind": "add_docstring", "text": "distractor"},
                {"kind": "rename_function", "old": "sketch", "new": "refine"},
            ],
            _syntax_pairs(
                "sketch", "x", expressions_x,
                lambda expression: _source("refine", "datum", expression.replace("x", "datum")),
            ),
        )
    )
    expressions_value = [
        "value + 2", "value - 5", "value * 4", "-value",
        "value // 3", "value + 12", "value * value", "value - 1",
    ]
    worlds.append(
        _syntax_world(
            "m101_syntax_transfer_two_stage_name",
            "syntax_transfer",
            [
                {"kind": "rename_function", "old": "stage_calc", "new": "ready_calc"},
                {"kind": "rename_function", "old": "draft_calc", "new": "stage_calc"},
                {"kind": "wrap_return", "call": "repr"},
            ],
            _syntax_pairs(
                "draft_calc", "value", expressions_value,
                lambda expression: _source("ready_calc", "value", expression),
            ),
        )
    )
    expressions_item = [
        "item - 6", "item + 3", "item * 5", "-item",
        "item // 4", "item + 15", "item * item", "item - 2",
    ]
    worlds.append(
        _syntax_world(
            "m101_syntax_transfer_clean_sample",
            "syntax_transfer",
            [
                {"kind": "rename_function", "old": "rough_value", "new": "clean_value"},
                {"kind": "wrap_return", "call": "str"},
                {"kind": "rename_argument", "function": "clean_value", "old": "item", "new": "sample"},
            ],
            _syntax_pairs(
                "rough_value", "item", expressions_item,
                lambda expression: _source(
                    "clean_value", "sample", expression.replace("item", "sample")
                ),
            ),
        )
    )

    worlds.append(
        _syntax_world(
            "m101_syntax_b_publish_payload",
            "b_reuse",
            [
                {"kind": "rename_function", "old": "draft", "new": "stage"},
                {"kind": "rename_argument", "function": "stage", "old": "x", "new": "payload"},
                {"kind": "rename_function", "old": "stage", "new": "published"},
                {"kind": "add_docstring", "text": "unused"},
            ],
            _syntax_pairs(
                "draft", "x", expressions_x,
                lambda expression: _source("published", "payload", expression.replace("x", "payload")),
            ),
        )
    )
    worlds.append(
        _syntax_world(
            "m101_syntax_b_safe_absolute",
            "b_reuse",
            [
                {"kind": "rename_function", "old": "raw_metric", "new": "safe_metric"},
                {"kind": "rename_argument", "function": "safe_metric", "old": "value", "new": "measure"},
                {"kind": "wrap_return", "call": "abs"},
                {"kind": "add_docstring", "text": "unused"},
            ],
            _syntax_pairs(
                "raw_metric", "value", expressions_value,
                lambda expression: _source(
                    "safe_metric", "measure", f"abs({expression.replace('value', 'measure')})"
                ),
            ),
        )
    )
    worlds.append(
        _syntax_world(
            "m101_syntax_b_core_documented",
            "b_reuse",
            [
                {"kind": "rename_function", "old": "seed_label", "new": "core_label"},
                {"kind": "rename_argument", "function": "core_label", "old": "item", "new": "datum"},
                {"kind": "add_docstring", "text": "qualified label"},
                {"kind": "wrap_return", "call": "repr"},
            ],
            _syntax_pairs(
                "seed_label", "item", expressions_item,
                lambda expression: _source(
                    "core_label", "datum", expression.replace("item", "datum"), "qualified label"
                ),
            ),
        )
    )

    numeric_pairs = [
        (8, 3), (5, 5), (-2, 7), (0, -4), (13, 6), (-5, -9), (2, 11), (4, -3)
    ]
    for world_id, index, signature in (
        ("m101_m100_conserve_subtraction", 0, (1, -1)),
        ("m101_m100_conserve_addition", 1, (1, 1)),
        ("m101_m100_conserve_weighted", 2, (1, 2)),
    ):
        worlds.append(
            _m100_world(
                world_id,
                index,
                [
                    ((left, right), signature[0] * left + signature[1] * right)
                    for left, right in numeric_pairs
                ],
            )
        )
    return worlds


def build_pool(*, status: str = "candidate") -> dict[str, Any]:
    entries = []
    for world in authored_worlds():
        entry: dict[str, Any] = {"world": world}
        entry["entry_digest"] = digest(entry)
        entries.append(entry)
    pool: dict[str, Any] = {
        "schema": POOL_SCHEMA,
        "milestone": "M101",
        "status": status,
        "construction": "complete authored 1/2/3/3/3/3 population; no draw, salt, replacement or reroll",
        "population_size": len(entries),
        "role_counts": ROLE_COUNTS,
        "cases_per_world": {"public": 4, "hidden": 4},
        "development_fixture_excluded": True,
        "m097_through_m100_worlds_excluded": True,
        "result_dependent_draw": False,
        "reroll": False,
        "preflight_boundary": (
            "closed-schema construction, JSON instantiation and Python AST parsing only; M101 "
            "acquisition, registration, baseline, transfer, execution, mutation, ablation and "
            "rollback are forbidden before final freeze"
        ),
        "entries": entries,
    }
    pool["pool_digest"] = digest(pool)
    return pool


def load_pool(path: Path = OUTPUT) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    recorded = value.pop("pool_digest", None)
    measured = digest(value)
    value["pool_digest"] = recorded
    if recorded != measured:
        raise ValueError("M101 qualification-pool digest mismatch")
    return value


def audit(pool: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    rows = []
    entries = pool.get("entries")
    if not isinstance(entries, list):
        entries = []
        failures.append("entries are not a list")
    ids: list[str] = []
    roles: Counter[str] = Counter()
    for raw_entry in entries:
        row_failures: list[str] = []
        if not isinstance(raw_entry, dict) or set(raw_entry) != {"world", "entry_digest"}:
            rows.append({"passed": False, "failures": ["entry is not closed"]})
            continue
        if raw_entry["entry_digest"] != digest({"world": raw_entry["world"]}):
            row_failures.append("entry digest mismatch")
        world = raw_entry["world"]
        if not isinstance(world, dict):
            rows.append({"passed": False, "failures": ["world is not a record"]})
            continue
        world_id = world.get("id")
        role = world.get("role")
        carrier = world.get("carrier")
        if not isinstance(world_id, str) or not world_id.startswith("m101_"):
            row_failures.append("world id is invalid")
        else:
            ids.append(world_id)
        if role not in ROLE_COUNTS:
            row_failures.append("world role is invalid")
        else:
            roles[str(role)] += 1
        expected_keys = (
            {"id", "role", "carrier", "operation_index", "public_cases", "hidden_cases"}
            if carrier == "m100"
            else {"id", "role", "carrier", "catalog", "public_cases", "hidden_cases"}
        )
        if set(world) != expected_keys:
            row_failures.append("world schema is not closed")
        all_case_ids: list[str] = []
        for split in ("public_cases", "hidden_cases"):
            cases = world.get(split)
            if not isinstance(cases, list) or len(cases) != 4:
                row_failures.append(f"{split} does not contain exactly four cases")
                continue
            for case in cases:
                if not isinstance(case, dict) or set(case) != {"case_id", "input", "expected"}:
                    row_failures.append(f"{split} contains a non-closed case")
                    continue
                all_case_ids.append(str(case["case_id"]))
                json.loads(canonical_json(case))
                if carrier == "syntax":
                    try:
                        ast.parse(str(case["input"]))
                        ast.parse(str(case["expected"]))
                    except SyntaxError as error:
                        row_failures.append(f"syntax case does not parse: {error}")
                elif carrier == "record" and not isinstance(case["input"], dict):
                    row_failures.append("record case input is not a mapping")
                elif carrier == "text" and not isinstance(case["input"], str):
                    row_failures.append("text case input is not a string")
                elif carrier == "m100":
                    value = case["input"]
                    if not isinstance(value, dict) or set(value) != {"left", "right"}:
                        row_failures.append("M100 case input is invalid")
        if len(all_case_ids) != len(set(all_case_ids)):
            row_failures.append("case ids overlap")
        rows.append(
            {
                "entry": world_id,
                "role": role,
                "carrier": carrier,
                "public_cases": len(world.get("public_cases", [])),
                "hidden_cases": len(world.get("hidden_cases", [])),
                "passed": not row_failures,
                "failures": row_failures,
            }
        )
    if len(entries) != 15 or len(set(ids)) != 15:
        failures.append("population is not fifteen unique worlds")
    if dict(roles) != ROLE_COUNTS:
        failures.append("population role census changed")
    if pool.get("population_size") != 15 or pool.get("cases_per_world") != {"public": 4, "hidden": 4}:
        failures.append("population metadata changed")
    if pool.get("development_fixture_excluded") is not True:
        failures.append("development fixture is not excluded")
    if pool.get("m097_through_m100_worlds_excluded") is not True:
        failures.append("predecessor-world exclusion is absent")
    for milestone in range(97, 101):
        prior = ROOT / "experiments" / f"M{milestone}" / "QUALIFICATION_POOL.json"
        if prior.exists():
            prior_text = prior.read_text(encoding="utf-8")
            reused = [world_id for world_id in ids if world_id in prior_text]
            if reused:
                failures.append(f"world ids reused from M{milestone}: {reused}")
    return {
        "schema": "m101-pool-preflight-v1",
        "scientific_verdict": False,
        "pool_digest": pool.get("pool_digest"),
        "entries_checked": len(rows),
        "source_only": True,
        "m101_runtime_imported": False,
        "acquisition_was_run": False,
        "registration_was_run": False,
        "baseline_was_run": False,
        "transfer_was_run": False,
        "execution_was_run": False,
        "fault_was_injected": False,
        "rollback_was_run": False,
        "passed": not failures and len(rows) == 15 and all(row["passed"] for row in rows),
        "failures": failures,
        "entries": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--status", choices=("candidate", "frozen"), default="candidate")
    arguments = parser.parse_args()
    pool = build_pool(status=arguments.status)
    report = audit(pool)
    if arguments.write:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(json.dumps(pool, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"pool": pool, "preflight": report}, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
