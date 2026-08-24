"""Author the pre-freeze M103 behavioral predecessor-conservation fixture."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "experiments" / "M102" / "QUALIFICATION_POOL.json"
TARGET = ROOT / "experiments" / "M103" / "PREDECESSOR_CONSERVATION.json"


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("ascii")).hexdigest()


def _case(case_id: str, input_value: Any, expected: Any) -> dict[str, Any]:
    return {"case_id": case_id, "input": input_value, "expected": expected}


def _source_worlds() -> dict[str, dict[str, Any]]:
    pool = json.loads(SOURCE.read_text(encoding="ascii"))
    return {entry["world"]["id"]: entry["world"] for entry in pool["entries"]}


def _record_world(source: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "m102-record-execution-world-v1",
        "world_id": "m103_predecessor_record_fresh",
        "carrier": source["carrier"],
        "slots": source["slots"],
        "cases": [
            _case(
                "m103-predecessor-record-01",
                {"payload_raw": "fresh-onyx", "readings": [41, -3, 17]},
                {"payload_value": "fresh-onyx", "readings": [-3, 17, 41]},
            ),
            _case(
                "m103-predecessor-record-02",
                {"payload_raw": "fresh-quartz", "readings": [8, 8, -12]},
                {"payload_value": "fresh-quartz", "readings": [-12, 8, 8]},
            ),
        ],
    }


def _sqlite_model(rows: list[tuple[int, str]], *, transformed: bool) -> dict[str, Any]:
    if not transformed:
        return {
            "table": "qualified_objects",
            "columns": [
                {"name": "object_key", "type": "INTEGER"},
                {"name": "title_text", "type": "TEXT"},
            ],
            "rows": [
                {"object_key": key, "title_text": text} for key, text in rows
            ],
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
                "object_key": key,
                "caption_text": text,
                "caption_size": len(text),
            }
            for key, text in rows
        ],
        "indexes": [
            {
                "name": "idx_qualified_caption_size",
                "columns": ["caption_text", "caption_size"],
            }
        ],
    }


def _sqlite_world(source: dict[str, Any]) -> dict[str, Any]:
    rows_a = [(31901, "M103-FRESH-ONYX"), (31902, "M103-FRESH-QUARTZ")]
    rows_b = [(31911, "M103-FRESH-CEDAR"), (31912, "M103-FRESH-EMBER")]
    return {
        "schema": "m102-sqlite-execution-world-v1",
        "world_id": "m103_predecessor_sqlite_fresh",
        "slots": source["slots"],
        "cases": [
            _case(
                "m103-predecessor-sqlite-01",
                _sqlite_model(rows_a, transformed=False),
                _sqlite_model(rows_a, transformed=True),
            ),
            _case(
                "m103-predecessor-sqlite-02",
                _sqlite_model(rows_b, transformed=False),
                _sqlite_model(rows_b, transformed=True),
            ),
        ],
    }


def _m101_world(
    source: dict[str, Any], public_cases: list[dict[str, Any]], hidden_cases: list[dict[str, Any]]
) -> dict[str, Any]:
    world = copy.deepcopy(source)
    world["id"] = f"m103_{source['id']}_fresh"
    world["public_cases"] = public_cases
    world["hidden_cases"] = hidden_cases
    return world


def _m100_world(source: dict[str, Any], pairs: list[tuple[int, int]]) -> dict[str, Any]:
    operation_index = source["operation_index"]

    def expected(left: int, right: int) -> int:
        if operation_index == 0:
            return left - right
        if operation_index == 1:
            return left + right
        return left + 2 * right

    cases = [
        _case(
            f"m103-predecessor-m100-{operation_index}-{index:02d}",
            {"left": left, "right": right},
            expected(left, right),
        )
        for index, (left, right) in enumerate(pairs, start=1)
    ]
    world = copy.deepcopy(source)
    world["id"] = f"m103_{source['id']}_fresh"
    world["public_cases"] = cases[:2]
    world["hidden_cases"] = cases[2:]
    return world


def build_fixture() -> dict[str, Any]:
    source = _source_worlds()
    a_world = _m101_world(
        source["m102_m101_a_conserve_text"],
        [
            _case("m103-predecessor-a-01", "ONYX~HARBOR", "onyx harbor"),
            _case("m103-predecessor-a-02", "QUARTZ~VALE", "quartz vale"),
        ],
        [
            _case("m103-predecessor-a-03", "CEDAR~EMBER", "cedar ember"),
            _case("m103-predecessor-a-04", "SILVER~BASIN", "silver basin"),
        ],
    )
    b_world = _m101_world(
        source["m102_m101_b_conserve_syntax"],
        [
            _case(
                "m103-predecessor-b-01",
                "def raw_signal(datum):\n    return datum * 9 - 4",
                "def sealed_signal(reading):\n    return abs(reading * 9 - 4)",
            ),
            _case(
                "m103-predecessor-b-02",
                "def raw_signal(datum):\n    return -datum // 3",
                "def sealed_signal(reading):\n    return abs(-reading // 3)",
            ),
        ],
        [
            _case(
                "m103-predecessor-b-03",
                "def raw_signal(datum):\n    return datum % 13 + 2",
                "def sealed_signal(reading):\n    return abs(reading % 13 + 2)",
            ),
            _case(
                "m103-predecessor-b-04",
                "def raw_signal(datum):\n    return datum + datum + 7",
                "def sealed_signal(reading):\n    return abs(reading + reading + 7)",
            ),
        ],
    )
    pairs = [(73, 18), (-22, 31), (9, -17), (-44, -6)]
    entries = [
        {"action": "execute-record", "world": _record_world(source["m102_record_retain_alpha"])},
        {"action": "execute-sqlite", "world": _sqlite_world(source["m102_sqlite_c_reuse_amber"])},
        {"action": "execute-m101-a", "world": a_world},
        {"action": "execute-m101-b", "world": b_world},
        *[
            {
                "action": "execute-m100",
                "world": _m100_world(source[source_id], pairs),
            }
            for source_id in (
                "m102_m100_conserve_subtraction",
                "m102_m100_conserve_addition",
                "m102_m100_conserve_weighted",
            )
        ],
    ]
    payload = {
        "schema": "m103-predecessor-conservation-fixture-v1",
        "status": "pre-freeze",
        "source": "fresh M103 cases over frozen M102 execution interfaces",
        "entry_count": len(entries),
        "entries": entries,
    }
    return {**payload, "fixture_digest": digest(payload)}


def main() -> int:
    value = build_fixture()
    TARGET.write_bytes(canonical_json(value).encode("ascii"))
    print(value["fixture_digest"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
