"""Author and source-audit M102's complete thirteen-record population.

The audit is deliberately non-executing.  It checks closed schemas, content addresses,
identifier freshness, public/hidden separation, and that raw input/expected SQLite
models can each be materialised and inspected.  It imports no Genesis runtime,
executor, acquisition function, definition checker, result checker, or runner.
"""

from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "experiments" / "M102" / "QUALIFICATION_POOL.json"
POOL_SCHEMA = "m102-qualification-pool-v1"

ROLE_COUNTS = {
    "policy_producer_trigger": 1,
    "record_retention": 3,
    "sqlite_c_trigger": 1,
    "sqlite_c_reuse": 3,
    "m101_a_conservation": 1,
    "m101_b_conservation": 1,
    "m100_conservation": 3,
}

DEVELOPMENT_DESCRIPTOR_DIGESTS = {
    # Digests bind all descriptors in tests/test_m102_runtime.py without copying the
    # development descriptor bodies into the qualification-only authoring source.
    "005a886dd39cd4b07c8303456cf5cb18fc312d292d552801db57a9137041d6a6",
    "04c6659cbc1a07d7a6d4813a1d3b819959a462239998cd62477a7ebe9f755de3",
    "2432109b7d753c693599a8ce1a0cef74c9f8f21262f9e5c50fbc605ed799d6a9",
    "454bc98a03325771a5d1c08bc608fa19b4a318670f6e331c1cbace3266b17a70",
    "9bbf316bd7b84b2a6f5c2909b18eeccc9bbfba52b1cd9424cc3071a4f4c01a13",
    "e2cf4b4f76b265c302f09b2e106e8b62f0ebc4d73d0962cf32969b480f47cfc8",
    "e873477c9a22a780d20cf204dd74d523008b7ca7d5fc0f3f1417d2e8033bfe94",
    "f8def88db3c43f63c072473b4cea09618eb5b21ca431aa71a487da076a6ed165",
}


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("ascii")).hexdigest()


def _case(case_id: str, value: Any, expected: Any) -> dict[str, Any]:
    return {"case_id": case_id, "input": copy.deepcopy(value), "expected": copy.deepcopy(expected)}


def _split_cases(
    prefix: str, pairs: list[tuple[Any, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if len(pairs) != 8:
        raise ValueError("every M102 authored world requires exactly eight cases")
    cases = [
        _case(f"{prefix}-{index:02d}", value, expected)
        for index, (value, expected) in enumerate(pairs, start=1)
    ]
    return cases[:4], cases[4:]


def _event(carrier: str, slot: str, descriptor: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "schema": "m102-registry-event-v1",
        "carrier": carrier,
        "slot": slot,
        "descriptor": copy.deepcopy(descriptor),
    }
    return {"event_id": f"registry-event-{digest(payload)[:16]}", **payload}


def _record_world(
    world_id: str,
    carrier: str,
    slots: list[str],
    events: list[dict[str, Any]],
    pairs: list[tuple[dict[str, Any], dict[str, Any]]],
) -> dict[str, Any]:
    public, hidden = _split_cases(world_id, pairs)
    return {
        "id": world_id,
        "role": "record_retention",
        "carrier": carrier,
        "slots": slots,
        "events": events,
        "public_cases": public,
        "hidden_cases": hidden,
    }


def _sqlite_model(rows: list[dict[str, Any]], *, transformed: bool) -> dict[str, Any]:
    if not transformed:
        return {
            "table": "qualified_objects",
            "columns": [
                {"name": "object_key", "type": "INTEGER"},
                {"name": "title_text", "type": "TEXT"},
            ],
            "rows": copy.deepcopy(rows),
            "indexes": [],
        }
    return {
        "table": "qualified_objects",
        "columns": [
            {"name": "object_key", "type": "INTEGER"},
            {"name": "caption_text", "type": "TEXT"},
            {"name": "caption_size", "type": "INTEGER"},
        ],
        "rows": [
            {
                "object_key": row["object_key"],
                "caption_text": row["title_text"],
                "caption_size": len(str(row["title_text"])),
            }
            for row in rows
        ],
        "indexes": [
            {
                "name": "idx_qualified_caption_size",
                "columns": ["caption_text", "caption_size"],
            }
        ],
    }


def _sqlite_pairs(prefix: str, names: list[list[str]]) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    pairs: list[tuple[dict[str, Any], dict[str, Any]]] = []
    offset = sum(ord(character) for character in prefix) * 10
    for index, values in enumerate(names, start=1):
        rows = [
            {"object_key": offset + index * 10 + row_index, "title_text": value}
            for row_index, value in enumerate(values, start=1)
        ]
        pairs.append((_sqlite_model(rows, transformed=False), _sqlite_model(rows, transformed=True)))
    return pairs


def _sqlite_world(
    world_id: str,
    role: str,
    names: list[list[str]],
    *,
    events: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    public, hidden = _split_cases(world_id, _sqlite_pairs(world_id, names))
    world: dict[str, Any] = {
        "id": world_id,
        "role": role,
        "carrier": "sqlite",
        "slots": ["alpha_prepare", "beta_finish", "gamma_prepare", "alpha_finish"],
        "public_cases": public,
        "hidden_cases": hidden,
    }
    if events is not None:
        world["events"] = events
    return world


def _source(name: str, argument: str, expression: str, document: str | None = None) -> str:
    lines = [f"def {name}({argument}):"]
    if document is not None:
        lines.append(f"    {document!r}")
    lines.append(f"    return {expression}")
    source = "\n".join(lines)
    ast.parse(source)
    return source


def _m101_a_world() -> dict[str, Any]:
    values = [
        "BASALT~RIDGE",
        "MICA~FIELD",
        "NICKEL~COVE",
        "FROST~GLASS",
        "CEDAR~CROWN",
        "LUNAR~STONE",
        "OCHRE~BRIDGE",
        "VELVET~ORE",
    ]
    public, hidden = _split_cases(
        "m102_m101_a_conserve_text",
        [(value, value.replace("~", " ").lower()) for value in values],
    )
    return {
        "id": "m102_m101_a_conserve_text",
        "role": "m101_a_conservation",
        "carrier": "text",
        "catalog": [
            {"kind": "suffix", "value": "!excluded"},
            {"kind": "replace", "old": "~", "new": " "},
            {"kind": "lower"},
        ],
        "public_cases": public,
        "hidden_cases": hidden,
    }


def _m101_b_world() -> dict[str, Any]:
    expressions = [
        "datum + 17",
        "datum - 19",
        "datum * 6",
        "-datum + 3",
        "datum // 7",
        "datum * datum + 2",
        "datum % 11",
        "datum + datum - 5",
    ]
    pairs = [
        (
            _source("raw_signal", "datum", expression),
            _source(
                "sealed_signal",
                "reading",
                expression.replace("datum", "reading"),
                "qualified conservation",
            ),
        )
        for expression in expressions
    ]
    public, hidden = _split_cases("m102_m101_b_conserve_syntax", pairs)
    return {
        "id": "m102_m101_b_conserve_syntax",
        "role": "m101_b_conservation",
        "carrier": "syntax",
        "catalog": [
            {
                "kind": "rename_argument",
                "function": "sealed_signal",
                "old": "datum",
                "new": "reading",
            },
            {"kind": "rename_function", "old": "raw_signal", "new": "sealed_signal"},
            {"kind": "add_docstring", "text": "qualified conservation"},
            {"kind": "wrap_return", "call": "repr"},
        ],
        "public_cases": public,
        "hidden_cases": hidden,
    }


def _m100_world(world_id: str, operation_index: int, signature: tuple[int, int]) -> dict[str, Any]:
    numeric = [
        (31, 12),
        (-17, 8),
        (44, -13),
        (9, 27),
        (-36, -14),
        (52, 7),
        (18, -29),
        (-41, 16),
    ]
    public, hidden = _split_cases(
        world_id,
        [
            (
                {"left": left, "right": right},
                signature[0] * left + signature[1] * right,
            )
            for left, right in numeric
        ],
    )
    return {
        "id": world_id,
        "role": "m100_conservation",
        "carrier": "m100",
        "operation_index": operation_index,
        "public_cases": public,
        "hidden_cases": hidden,
    }


def authored_worlds() -> list[dict[str, Any]]:
    alpha_events = [
        _event(
            "retention_alpha",
            "alpha_prepare",
            {"kind": "rename_key", "old": "payload_raw", "new": "payload_value"},
        ),
        _event("retention_alpha", "alpha_finish", {"kind": "sort_list", "key": "readings"}),
    ]
    beta_events = [
        _event("retention_beta", "beta_prepare", {"kind": "drop_key", "key": "obsolete_flag"}),
        _event(
            "retention_beta",
            "beta_finish",
            {"kind": "set_default", "key": "phase_name", "value": "queued"},
        ),
    ]
    gamma_events = [
        _event(
            "retention_gamma",
            "gamma_prepare",
            {"kind": "set_default", "key": "verified_flag", "value": True},
        ),
        _event(
            "retention_gamma",
            "gamma_finish",
            {"kind": "rename_key", "old": "entry_batch", "new": "sample_batch"},
        ),
    ]
    incoming = [
        _event(
            "collision_delta",
            "alpha_prepare",
            {"kind": "rename_key", "old": "source_fragment", "new": "text_fragment"},
        ),
        _event("collision_delta", "beta_finish", {"kind": "drop_key", "key": "scratch_note"}),
    ]

    record_worlds = [
        _record_world(
            "m102_record_retain_alpha",
            "retention_alpha",
            ["alpha_prepare", "alpha_finish"],
            alpha_events,
            [
                (
                    {"payload_raw": f"alpha-{index}", "readings": [index + 4, index, 2]},
                    {"payload_value": f"alpha-{index}", "readings": sorted([index + 4, index, 2])},
                )
                for index in range(21, 29)
            ],
        ),
        _record_world(
            "m102_record_retain_beta",
            "retention_beta",
            ["beta_prepare", "beta_finish"],
            beta_events,
            [
                (
                    {"token_id": 200 + index, "obsolete_flag": f"remove-{index}"},
                    {"token_id": 200 + index, "phase_name": "queued"},
                )
                for index in range(31, 39)
            ],
        ),
        _record_world(
            "m102_record_retain_gamma",
            "retention_gamma",
            ["gamma_prepare", "gamma_finish"],
            gamma_events,
            [
                (
                    {"entry_batch": [index * 2, index * 2 + 1], "series_id": f"g-{index}"},
                    {
                        "sample_batch": [index * 2, index * 2 + 1],
                        "series_id": f"g-{index}",
                        "verified_flag": True,
                    },
                )
                for index in range(41, 49)
            ],
        ),
    ]
    prior_events = [event for world in record_worlds for event in world["events"]]
    lookup_events = [
        alpha_events[0],
        incoming[0],
        beta_events[1],
        incoming[1],
        alpha_events[1],
        beta_events[0],
        gamma_events[0],
        gamma_events[1],
    ]
    lookups = [
        {
            "case_id": f"m102_policy_lookup-{index:02d}",
            "carrier": event["carrier"],
            "slot": event["slot"],
            "expected_descriptor": copy.deepcopy(event["descriptor"]),
        }
        for index, event in enumerate(lookup_events, start=1)
    ]
    policy_world = {
        "id": "m102_policy_collision_delta",
        "role": "policy_producer_trigger",
        "carrier": "registry",
        "incoming_events": incoming,
        "public_lookups": lookups[:4],
        "hidden_lookups": lookups[4:],
    }

    sqlite_events = [
        _event(
            "sqlite",
            "alpha_prepare",
            {
                "kind": "add_column",
                "table": "qualified_objects",
                "column": "caption_size",
                "type": "INTEGER",
                "default": -1,
            },
        ),
        _event(
            "sqlite",
            "beta_finish",
            {
                "kind": "backfill_length",
                "table": "qualified_objects",
                "source": "title_text",
                "target": "caption_size",
            },
        ),
        _event(
            "sqlite",
            "gamma_prepare",
            {
                "kind": "rename_column",
                "table": "qualified_objects",
                "old": "title_text",
                "new": "caption_text",
            },
        ),
        _event(
            "sqlite",
            "alpha_finish",
            {
                "kind": "create_index",
                "table": "qualified_objects",
                "name": "idx_qualified_caption_size",
                "columns": ["caption_text", "caption_size"],
            },
        ),
    ]
    sqlite_worlds = [
        _sqlite_world(
            "m102_sqlite_c_trigger",
            "sqlite_c_trigger",
            [
                ["AURORA-CROWN"],
                ["BRONZE-VAULT", "CINDER-LAKE"],
                ["DUSK-ORCHID"],
                ["EMBER-PASS", "FALLOW-MOON"],
                ["GARNET-HARBOR"],
                ["HELIUM-GROVE", "INDIGO-CLIFF"],
                ["JASPER-THREAD"],
                ["KELP-SPIRE", "LIMESTONE-ARC"],
            ],
            events=sqlite_events,
        ),
        _sqlite_world(
            "m102_sqlite_c_reuse_amber",
            "sqlite_c_reuse",
            [[f"AMBER-REUSE-{index}", f"BIRCH-REUSE-{index}"] for index in range(1, 9)],
        ),
        _sqlite_world(
            "m102_sqlite_c_reuse_cobalt",
            "sqlite_c_reuse",
            [[f"COBALT-REUSE-{index}"] for index in range(11, 19)],
        ),
        _sqlite_world(
            "m102_sqlite_c_reuse_fjord",
            "sqlite_c_reuse",
            [[f"FJORD-REUSE-{index}", f"GRANITE-REUSE-{index}"] for index in range(21, 29)],
        ),
    ]

    worlds: list[dict[str, Any]] = [policy_world, *record_worlds, *sqlite_worlds]
    worlds.extend([_m101_a_world(), _m101_b_world()])
    worlds.extend(
        [
            _m100_world("m102_m100_conserve_subtraction", 0, (1, -1)),
            _m100_world("m102_m100_conserve_addition", 1, (1, 1)),
            _m100_world("m102_m100_conserve_weighted", 2, (1, 2)),
        ]
    )
    if prior_events != [event for world in record_worlds for event in world["events"]]:
        raise AssertionError("record predecessor events changed during authorship")
    return worlds


def build_pool(*, status: str = "candidate") -> dict[str, Any]:
    entries = []
    for world in authored_worlds():
        entry: dict[str, Any] = {"world": world}
        entry["entry_digest"] = digest(entry)
        entries.append(entry)
    pool: dict[str, Any] = {
        "schema": POOL_SCHEMA,
        "milestone": "M102",
        "status": status,
        "construction": "complete authored 1/3/1/3/1/1/3 population; no draw, salt, replacement or reroll",
        "population_size": len(entries),
        "role_counts": ROLE_COUNTS,
        "requirements_per_source": {"public": 4, "hidden": 4},
        "development_fixture_excluded": True,
        "m101_qualification_worlds_excluded": True,
        "result_dependent_draw": False,
        "reroll": False,
        "scientifically_executed_before_freeze": False,
        "preflight_boundary": (
            "closed-schema construction, digest checks, AST parsing, and independent raw SQLite "
            "model materialisation only; K/C acquisition, registry migration, transfer, baseline, "
            "hidden scoring, mutation, ablation, rollback and replay are forbidden before freeze"
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
        raise ValueError("M102 qualification-pool digest mismatch")
    return value


def _quote(identifier: str) -> str:
    if not identifier.replace("_", "a").isalnum() or not identifier[0].isalpha():
        raise ValueError("unsafe SQLite identifier in authored pool")
    return f'"{identifier}"'


def _inspect_raw_sqlite_model(model: Any) -> dict[str, Any]:
    if not isinstance(model, dict) or set(model) != {"table", "columns", "rows", "indexes"}:
        raise ValueError("SQLite model is not closed")
    table = str(model["table"])
    columns = model["columns"]
    if not isinstance(columns, list) or not columns:
        raise ValueError("SQLite columns are missing")
    names = [str(item["name"]) for item in columns]
    connection = sqlite3.connect(":memory:")
    try:
        connection.execute(
            f"CREATE TABLE {_quote(table)} ("
            + ",".join(f"{_quote(str(item['name']))} {item['type']}" for item in columns)
            + ")"
        )
        for row in model["rows"]:
            connection.execute(
                f"INSERT INTO {_quote(table)} ({','.join(_quote(name) for name in names)}) "
                f"VALUES ({','.join('?' for _ in names)})",
                tuple(row[name] for name in names),
            )
        for index in model["indexes"]:
            connection.execute(
                f"CREATE INDEX {_quote(str(index['name']))} ON {_quote(table)} "
                f"({','.join(_quote(str(name)) for name in index['columns'])})"
            )
        connection.commit()
        info = connection.execute(f"PRAGMA table_info({_quote(table)})").fetchall()
        integrity = connection.execute("PRAGMA integrity_check").fetchone()
        if len(info) != len(columns) or integrity != ("ok",):
            raise ValueError("authored raw SQLite model cannot be independently inspected")
        return {"column_count": len(info), "row_count": len(model["rows"]), "integrity": "ok"}
    finally:
        connection.close()


def audit(pool: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    rows: list[dict[str, Any]] = []
    entries = pool.get("entries")
    if not isinstance(entries, list):
        entries = []
        failures.append("entries are not a list")
    ids: list[str] = []
    roles: Counter[str] = Counter()
    case_ids: list[str] = []
    descriptor_digests: list[str] = []
    raw_sqlite_models_inspected = 0
    policy_world: dict[str, Any] | None = None
    event_relation: list[dict[str, Any]] = []

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
        if not isinstance(world_id, str) or not world_id.startswith("m102_"):
            row_failures.append("world id is invalid")
        else:
            ids.append(world_id)
        if role not in ROLE_COUNTS:
            row_failures.append("world role is invalid")
        else:
            roles[str(role)] += 1

        if role == "policy_producer_trigger":
            expected_keys = {
                "id", "role", "carrier", "incoming_events", "public_lookups", "hidden_lookups"
            }
            splits = ("public_lookups", "hidden_lookups")
            policy_world = world
        elif role == "record_retention":
            expected_keys = {
                "id", "role", "carrier", "slots", "events", "public_cases", "hidden_cases"
            }
            splits = ("public_cases", "hidden_cases")
        elif role == "sqlite_c_trigger":
            expected_keys = {
                "id", "role", "carrier", "slots", "events", "public_cases", "hidden_cases"
            }
            splits = ("public_cases", "hidden_cases")
        elif role in {"sqlite_c_reuse", "m101_a_conservation", "m101_b_conservation"}:
            expected_keys = (
                {"id", "role", "carrier", "slots", "public_cases", "hidden_cases"}
                if role == "sqlite_c_reuse"
                else {"id", "role", "carrier", "catalog", "public_cases", "hidden_cases"}
            )
            splits = ("public_cases", "hidden_cases")
        else:
            expected_keys = {
                "id", "role", "carrier", "operation_index", "public_cases", "hidden_cases"
            }
            splits = ("public_cases", "hidden_cases")
        if set(world) != expected_keys:
            row_failures.append("world schema is not closed")

        for event in world.get("events", []) + world.get("incoming_events", []):
            if not isinstance(event, dict) or set(event) != {
                "schema", "event_id", "carrier", "slot", "descriptor"
            }:
                row_failures.append("registry event is not closed")
                continue
            payload = {key: value for key, value in event.items() if key != "event_id"}
            if event["event_id"] != f"registry-event-{digest(payload)[:16]}":
                row_failures.append("registry event digest mismatch")
            measured_descriptor = digest(event["descriptor"])
            descriptor_digests.append(measured_descriptor)
            if event["carrier"] != "sqlite":
                event_relation.append(event)

        for split in splits:
            cases = world.get(split)
            if not isinstance(cases, list) or len(cases) != 4:
                row_failures.append(f"{split} does not contain exactly four requirements")
                continue
            for case in cases:
                expected_case_keys = (
                    {"case_id", "carrier", "slot", "expected_descriptor"}
                    if role == "policy_producer_trigger"
                    else {"case_id", "input", "expected"}
                )
                if not isinstance(case, dict) or set(case) != expected_case_keys:
                    row_failures.append(f"{split} contains a non-closed requirement")
                    continue
                case_id = case.get("case_id")
                if not isinstance(case_id, str) or "development" in case_id.lower():
                    row_failures.append("case id is invalid or development-derived")
                else:
                    case_ids.append(case_id)
                if carrier == "sqlite":
                    try:
                        _inspect_raw_sqlite_model(case["input"])
                        _inspect_raw_sqlite_model(case["expected"])
                        raw_sqlite_models_inspected += 2
                    except (KeyError, TypeError, ValueError, sqlite3.Error) as error:
                        row_failures.append(f"raw SQLite model inspection failed: {error}")
                elif carrier == "syntax":
                    try:
                        ast.parse(str(case["input"]))
                        ast.parse(str(case["expected"]))
                    except SyntaxError as error:
                        row_failures.append(f"syntax case does not parse: {error}")
                elif carrier == "m100":
                    if not isinstance(case["input"], dict) or set(case["input"]) != {
                        "left", "right"
                    }:
                        row_failures.append("M100 case input is invalid")
        rows.append(
            {
                "entry": world_id,
                "role": role,
                "carrier": carrier,
                "passed": not row_failures,
                "failures": row_failures,
            }
        )

    if len(entries) != 13 or len(set(ids)) != 13:
        failures.append("population is not thirteen unique source records")
    if dict(roles) != ROLE_COUNTS:
        failures.append("population role census changed")
    if len(case_ids) != len(set(case_ids)):
        failures.append("public/hidden requirement ids overlap")
    if set(descriptor_digests) & DEVELOPMENT_DESCRIPTOR_DIGESTS:
        failures.append("a qualification descriptor equals a development descriptor")
    if len(descriptor_digests) != len(set(descriptor_digests)):
        failures.append("qualification registry descriptors are not all distinct")
    if policy_world is None:
        failures.append("policy producer is missing")
    else:
        lookups = policy_world.get("public_lookups", []) + policy_world.get("hidden_lookups", [])
        relation = {
            (event["carrier"], event["slot"], digest(event["descriptor"]))
            for event in event_relation
        }
        lookup_relation = {
            (item["carrier"], item["slot"], digest(item["expected_descriptor"]))
            for item in lookups
        }
        if lookup_relation != relation:
            failures.append("policy lookups do not close exactly over the authored event relation")
    if pool.get("population_size") != 13:
        failures.append("population metadata changed")
    if pool.get("requirements_per_source") != {"public": 4, "hidden": 4}:
        failures.append("requirement split metadata changed")
    if pool.get("development_fixture_excluded") is not True:
        failures.append("development fixture exclusion is absent")
    if pool.get("scientifically_executed_before_freeze") is not False:
        failures.append("pre-freeze execution marker changed")
    prior_pool = ROOT / "experiments" / "M101" / "QUALIFICATION_POOL.json"
    if prior_pool.exists():
        prior_text = prior_pool.read_text(encoding="utf-8")
        reused_ids = [world_id for world_id in ids if world_id in prior_text]
        if reused_ids:
            failures.append(f"world ids reused from M101: {reused_ids}")

    return {
        "schema": "m102-pool-preflight-v1",
        "scientific_verdict": False,
        "pool_digest": pool.get("pool_digest"),
        "entries_checked": len(rows),
        "source_only": True,
        "m102_runtime_imported": False,
        "acquisition_was_run": False,
        "registry_migration_was_run": False,
        "transfer_was_run": False,
        "baseline_was_run": False,
        "hidden_success_was_scored": False,
        "fault_was_injected": False,
        "rollback_was_run": False,
        "raw_sqlite_models_inspected": raw_sqlite_models_inspected,
        "passed": not failures and len(rows) == 13 and all(row["passed"] for row in rows),
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
    print(json.dumps({"pool_digest": pool["pool_digest"], "preflight": report}, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
