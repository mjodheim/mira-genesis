"""Independently check the complete M105 Boolean semantic image and feature."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


MAX_NODES = 8
ROWS = ((False, False), (False, True), (True, False), (True, True))


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("ascii")).hexdigest()


def _closed(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError(f"{label} is not a closed record")
    return value


def _expression(raw: Any) -> tuple[dict[str, Any], int]:
    if not isinstance(raw, dict) or not isinstance(raw.get("op"), str):
        raise ValueError("M105 expression is invalid")
    op = raw["op"]
    if op == "CONST":
        item = _closed(raw, {"op", "value"}, "M105 constant")
        if not isinstance(item["value"], bool):
            raise ValueError("M105 constant is invalid")
        return item, 1
    if op == "INPUT":
        item = _closed(raw, {"op", "index"}, "M105 input")
        if item["index"] not in {0, 1}:
            raise ValueError("M105 input is invalid")
        return item, 1
    if op == "NOT":
        item = _closed(raw, {"op", "child"}, "M105 negation")
        _child, nodes = _expression(item["child"])
        return item, nodes + 1
    if op in {"AND", "OR"}:
        item = _closed(raw, {"op", "left", "right"}, "M105 binary")
        if canonical_json(item["left"]) > canonical_json(item["right"]):
            raise ValueError("M105 binary children are not canonical")
        _left, left_nodes = _expression(item["left"])
        _right, right_nodes = _expression(item["right"])
        return item, 1 + left_nodes + right_nodes
    raise ValueError("M105 expression operator is invalid")


def _execute(node: dict[str, Any], signals: tuple[bool, bool]) -> bool:
    op = node["op"]
    if op == "CONST":
        return node["value"]
    if op == "INPUT":
        return signals[node["index"]]
    if op == "NOT":
        return not _execute(node["child"], signals)
    if op == "AND":
        return _execute(node["left"], signals) and _execute(node["right"], signals)
    return _execute(node["left"], signals) or _execute(node["right"], signals)


def _independent_minimum_sizes() -> dict[int, int]:
    # Bit order follows ROWS.  The closure is computed over semantic masks,
    # independently of the runtime's tree enumerator.
    discovered = {0: 1, 15: 1, 12: 1, 10: 1}
    exact = {1: set(discovered)}
    for size in range(2, MAX_NODES + 1):
        current = {(~mask) & 15 for mask in exact.get(size - 1, set())}
        for left_size in range(1, size - 1):
            right_size = size - 1 - left_size
            for left in exact.get(left_size, set()):
                for right in exact.get(right_size, set()):
                    current.add(left & right)
                    current.add(left | right)
        new = {mask for mask in current if mask not in discovered}
        exact[size] = new
        for mask in new:
            discovered[mask] = size
    return discovered


def validate(census: dict[str, Any], feature: dict[str, Any] | None = None) -> dict[str, Any]:
    census = _closed(
        census,
        {
            "schema",
            "maximum_nodes",
            "semantic_count",
            "counts_by_shortest_size",
            "representatives",
            "complete_two_input_boolean_image",
            "census_digest",
        },
        "M105 census",
    )
    census_payload = {key: value for key, value in census.items() if key != "census_digest"}
    if census["schema"] != "m105-semantic-census-v1" or census["census_digest"] != digest(
        census_payload
    ):
        raise ValueError("M105 census schema or digest mismatch")
    minimum_sizes = _independent_minimum_sizes()
    if set(minimum_sizes) != set(range(16)):
        raise ValueError("Independent Boolean closure is incomplete")
    measured: dict[int, int] = {}
    representative_tables: set[tuple[bool, bool, bool, bool]] = set()
    for row in census["representatives"]:
        row = _closed(row, {"truth_table", "nodes", "body"}, "M105 census row")
        body, nodes = _expression(row["body"])
        table = tuple(_execute(body, signals) for signals in ROWS)
        if list(table) != row["truth_table"] or nodes != row["nodes"]:
            raise ValueError("M105 census representative semantics mismatch")
        mask = sum((1 << index) for index, value in enumerate(table) if value)
        if minimum_sizes[mask] != nodes:
            raise ValueError("M105 census representative is not shortest")
        representative_tables.add(table)  # type: ignore[arg-type]
        measured[nodes] = measured.get(nodes, 0) + 1
    if len(representative_tables) != 16 or measured != {
        int(size): count for size, count in census["counts_by_shortest_size"].items()
    }:
        raise ValueError("M105 census is not a complete unique semantic image")

    feature_report = None
    if feature is not None:
        feature = _closed(
            feature,
            {"schema", "feature_id", "body", "truth_table"},
            "M105 feature",
        )
        body, nodes = _expression(feature["body"])
        if nodes > MAX_NODES:
            raise ValueError("M105 feature exceeds independent node bound")
        table = tuple(_execute(body, signals) for signals in ROWS)
        payload = {
            "schema": "m105-constructor-feature-v1",
            "body": feature["body"],
            "truth_table": list(table),
        }
        if feature["schema"] != payload["schema"] or feature["truth_table"] != list(table):
            raise ValueError("M105 feature semantics mismatch")
        if feature["feature_id"] != f"feature-{digest(payload)[:16]}":
            raise ValueError("M105 feature content address mismatch")
        feature_report = {
            "feature_id": feature["feature_id"],
            "truth_table": list(table),
            "nodes": nodes,
            "content_address_valid": True,
        }

    report: dict[str, Any] = {
        "schema": "m105-independent-semantic-validation-v1",
        "scientific_verdict": False,
        "confirmed": True,
        "semantic_count": 16,
        "minimum_sizes": {str(mask): minimum_sizes[mask] for mask in sorted(minimum_sizes)},
        "feature": feature_report,
        "independent_of_m105_runtime_search_and_qualification": True,
    }
    report["report_digest"] = digest(report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--census", required=True)
    parser.add_argument("--feature")
    arguments = parser.parse_args()
    try:
        census = json.loads(Path(arguments.census).read_text(encoding="ascii"))
        feature = (
            json.loads(Path(arguments.feature).read_text(encoding="ascii"))
            if arguments.feature
            else None
        )
        report = validate(census, feature)
    except Exception as error:
        report = {
            "schema": "m105-independent-semantic-validation-v1",
            "scientific_verdict": False,
            "confirmed": False,
            "failed_closed": True,
            "error": f"{type(error).__name__}: {error}",
            "independent_of_m105_runtime_search_and_qualification": True,
        }
        report["report_digest"] = digest(report)
        print(json.dumps(report, sort_keys=True))
        return 3
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
