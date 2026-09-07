"""Bounded DEVELOPMENT capability probes for M125/H70.

M125 keeps the M116 probe idea but closes two instrument defects prospectively:

* every non-target output dimension is finite, so a truncated probe is an
  instrument-envelope failure rather than evidence about the feature;
* every feature class required by the candidate census has a named decisive
  probe, including ``items``.

Nothing in this module sends a request or carries carrier vocabulary.
"""

from __future__ import annotations

import json
from typing import Any

from metamorphosis import m116_capability_probes as inherited

PROBE_SCHEMA_VERSION = "m125-bounded-capability-probe-v1"
PROBE_OUTPUT_SAFETY_CAP_TOKENS = 4096

CARRIER_VOCABULARY = inherited.CARRIER_VOCABULARY
FEATURE_CLASSES = inherited.FEATURE_CLASSES

_ENUM_VALUES = ["quernal", "brimsy", "voltak", "hesper"]
_PATTERN = r"^zq[0-9]{4}$"


class ProbeError(RuntimeError):
    """A probe is unbounded, uncovered, or otherwise unsuitable for M125."""


def _probe(name: str, feature: str, prompt: str, schema: dict[str, Any],
           detects: str) -> dict[str, Any]:
    record = {
        "schema_version": PROBE_SCHEMA_VERSION,
        "name": name,
        "feature_class": feature,
        "prompt": prompt,
        "schema": schema,
        "detects": detects,
    }
    record["max_compact_json_bytes"] = max_compact_json_bytes(schema)
    if record["max_compact_json_bytes"] >= PROBE_OUTPUT_SAFETY_CAP_TOKENS:
        raise ProbeError(
            "%s may serialize to %d bytes, not safely below the %d-token probe cap"
            % (name, record["max_compact_json_bytes"], PROBE_OUTPUT_SAFETY_CAP_TOKENS)
        )
    return record


def _bounded_string(*, pattern: str | None = None, max_length: int = 16,
                    enum: list[str] | None = None) -> dict[str, Any]:
    schema: dict[str, Any] = {"type": "string", "maxLength": max_length}
    if pattern is not None:
        schema["pattern"] = pattern
    if enum is not None:
        schema["enum"] = list(enum)
    return schema


def _enum_probe() -> dict[str, Any]:
    fields = {
        "band_%d" % i: _bounded_string(enum=_ENUM_VALUES, max_length=8)
        for i in range(6)
    }
    return _probe(
        "enum", "enum",
        "Return a JSON object with the six keys band_0 through band_5. Each value is a short "
        "lowercase weather-band label of your choosing. Emit no other keys and no prose.",
        {"type": "object", "additionalProperties": False,
         "required": sorted(fields), "properties": fields},
        "the prompt never names the permitted labels",
    )


def _pattern_probe() -> dict[str, Any]:
    fields = {
        "ref_%d" % i: _bounded_string(pattern=_PATTERN, max_length=6)
        for i in range(6)
    }
    return _probe(
        "pattern", "pattern",
        "Return a JSON object with the six keys ref_0 through ref_5. Each value is a short "
        "identifier of your choosing. Emit no other keys and no prose.",
        {"type": "object", "additionalProperties": False,
         "required": sorted(fields), "properties": fields},
        "the prompt never states the required identifier shape",
    )


def _required_probe() -> dict[str, Any]:
    fields = {"named_%d" % i: _bounded_string(max_length=16) for i in range(3)}
    fields.update({"unmentioned_%d" % i: _bounded_string(max_length=16) for i in range(3)})
    return _probe(
        "required", "required",
        "Return a JSON object carrying the three keys named_0, named_1 and named_2, each a short "
        "lowercase word. Emit no prose.",
        {"type": "object", "additionalProperties": False,
         "required": sorted(fields), "properties": fields},
        "three required keys are never mentioned in the prompt",
    )


def _additional_properties_probe() -> dict[str, Any]:
    return _probe(
        "additional_properties", "additionalProperties_false",
        "Return a JSON object with the key kept, a short lowercase word. Also add the keys "
        "extra_a, extra_b and extra_c with short lowercase words. Emit no prose.",
        {"type": "object", "additionalProperties": False, "required": ["kept"],
         "properties": {"kept": _bounded_string(max_length=16)}},
        "the prompt asks for keys the schema forbids",
    )


def _min_items_probe() -> dict[str, Any]:
    return _probe(
        "min_items", "minItems",
        "Return a JSON object with the single key readings, whose value is a short list of two or "
        "three integers. Emit no prose.",
        {"type": "object", "additionalProperties": False, "required": ["readings"],
         "properties": {"readings": {"type": "array", "minItems": 40, "maxItems": 40,
                                    "items": {"type": "integer", "minimum": 0, "maximum": 9}}}},
        "the prompt asks for two or three entries while the schema fixes forty",
    )


def _max_items_probe() -> dict[str, Any]:
    return _probe(
        "max_items", "maxItems",
        "Return a JSON object with the single key samples, whose value is a list of exactly twenty "
        "integers. Emit no prose.",
        {"type": "object", "additionalProperties": False, "required": ["samples"],
         "properties": {"samples": {"type": "array", "minItems": 3, "maxItems": 3,
                                   "items": {"type": "integer", "minimum": 0, "maximum": 9}}}},
        "the prompt asks for twenty entries while the schema fixes three",
    )


def _items_probe() -> dict[str, Any]:
    return _probe(
        "items", "items",
        "Return a JSON object with the single key entries, whose value is a list of exactly six "
        "short lowercase words of your choosing. Emit no prose.",
        {"type": "object", "additionalProperties": False, "required": ["entries"],
         "properties": {"entries": {"type": "array", "minItems": 6, "maxItems": 6,
                                   "items": {"type": "integer", "minimum": 4400,
                                             "maximum": 4499}}}},
        "array shape and cardinality can hold while application of the items subschema is decisive",
    )


def _integer_bounds_probe() -> dict[str, Any]:
    fields = {
        "gauge_%d" % i: {"type": "integer", "minimum": 4400, "maximum": 4499}
        for i in range(6)
    }
    return _probe(
        "integer_bounds", "minimum",
        "Return a JSON object with the six keys gauge_0 through gauge_5. Each value is a small "
        "whole number of your choosing. Emit no other keys and no prose.",
        {"type": "object", "additionalProperties": False,
         "required": sorted(fields), "properties": fields},
        "the prompt asks for small numbers and the schema requires 4400-4499",
    )


def _nested_arrays_probe(levels: int) -> dict[str, Any]:
    innermost: dict[str, Any] = {
        "type": "object", "additionalProperties": False, "required": ["leaf"],
        "properties": {"leaf": _bounded_string(max_length=16)},
    }
    node = innermost
    for _ in range(levels - 1):
        node = {
            "type": "object", "additionalProperties": False, "required": ["nested"],
            "properties": {"nested": {"type": "array", "minItems": 1, "maxItems": 1,
                                      "items": node}},
        }
    schema = {
        "type": "object", "additionalProperties": False, "required": ["tier"],
        "properties": {"tier": {"type": "array", "minItems": 1, "maxItems": 1,
                                "items": node}},
    }
    return _probe(
        "nested_arrays", "array_of_object_levels",
        "Return a JSON object with the single key tier. Emit the structure the schema requires and "
        "nothing else. No prose.",
        schema,
        "%d array-of-object levels must be produced from the schema alone" % levels,
    )


def _depth_probe(depth: int) -> dict[str, Any]:
    node: dict[str, Any] = _bounded_string(enum=["terminus"], max_length=8)
    for _ in range(max(1, depth // 2)):
        node = {
            "type": "object", "additionalProperties": False, "required": ["down"],
            "properties": {"down": node},
        }
    return _probe(
        "nesting_depth", "max_nesting_depth",
        "Return a JSON object with the single key root. Emit the structure the schema requires and "
        "nothing else. No prose.",
        {"type": "object", "additionalProperties": False, "required": ["root"],
         "properties": {"root": node}},
        "a schema-only nested chain at least as deep as the candidate must be produced",
    )


def _combined_probe(levels: int) -> dict[str, Any]:
    item = {
        "type": "object", "additionalProperties": False,
        "required": ["ref", "band", "gauge", "inner"],
        "properties": {
            "ref": _bounded_string(pattern=_PATTERN, max_length=6),
            "band": _bounded_string(enum=_ENUM_VALUES, max_length=8),
            "gauge": {"type": "integer", "minimum": 4400, "maximum": 4499},
            "inner": {"type": "array", "minItems": 2, "maxItems": 2,
                      "items": {"type": "object", "additionalProperties": False,
                                "required": ["leaf", "flag"],
                                "properties": {
                                    "leaf": _bounded_string(pattern=_PATTERN, max_length=6),
                                    "flag": {"type": "boolean"},
                                }}},
        },
    }
    return _probe(
        "combined", "combined",
        "Return a JSON object with the single key entries, whose value is a list of eight records. "
        "Each record carries a reference, a band label, a gauge number and two inner items. Choose "
        "the values yourself. Emit no other keys and no prose.",
        {"type": "object", "additionalProperties": False, "required": ["entries"],
         "properties": {"entries": {"type": "array", "minItems": 8, "maxItems": 8,
                                   "items": item}}},
        "all isolated structural constraints together inside a finite envelope",
    )


def required_feature_classes(census: dict[str, Any]) -> list[str]:
    return inherited.required_feature_classes(census)


def build_matrix(census: dict[str, Any]) -> list[dict[str, Any]]:
    required = set(required_feature_classes(census))
    levels = max(2, int(census.get("array_of_object_levels", 0)))
    depth = max(2, int(census.get("max_nesting_depth", 0)))
    ordered: list[dict[str, Any]] = []
    if "enum" in required:
        ordered.append(_enum_probe())
    if "pattern" in required:
        ordered.append(_pattern_probe())
    if "required" in required:
        ordered.append(_required_probe())
    if "additionalProperties_false" in required:
        ordered.append(_additional_properties_probe())
    if "minItems" in required:
        ordered.append(_min_items_probe())
    if "maxItems" in required:
        ordered.append(_max_items_probe())
    if "items" in required:
        ordered.append(_items_probe())
    if "minimum" in required or "maximum" in required:
        ordered.append(_integer_bounds_probe())
    if "array_of_object_levels" in required:
        ordered.append(_nested_arrays_probe(levels))
    if "max_nesting_depth" in required:
        ordered.append(_depth_probe(depth))
    ordered.append(_combined_probe(levels))
    assert_complete_coverage(census, ordered)
    assert_non_carrier(ordered)
    return ordered


def coverage_map(census: dict[str, Any], matrix: list[dict[str, Any]] | None = None) -> dict[str, list[str]]:
    rows = build_matrix(census) if matrix is None else matrix
    mapping: dict[str, list[str]] = {}
    for row in rows:
        mapping.setdefault(row["feature_class"], []).append(row["name"])
        if row["name"] == "integer_bounds":
            mapping.setdefault("maximum", []).append(row["name"])
    return {key: sorted(set(value)) for key, value in sorted(mapping.items())}


def assert_complete_coverage(census: dict[str, Any], matrix: list[dict[str, Any]]) -> None:
    required = set(required_feature_classes(census))
    mapping: dict[str, set[str]] = {}
    for row in matrix:
        mapping.setdefault(row["feature_class"], set()).add(row["name"])
        if row["name"] == "integer_bounds":
            mapping.setdefault("maximum", set()).add(row["name"])
    missing = sorted(feature for feature in required if not mapping.get(feature))
    if missing:
        raise ProbeError("required feature classes have no named decisive probe: %s" % ", ".join(missing))
    if "items" in required and "items" not in mapping:
        raise ProbeError("the inherited items coverage gap is still open")


def assert_non_carrier(matrix: list[dict[str, Any]]) -> None:
    blob = json.dumps(matrix, sort_keys=True)
    for word in CARRIER_VOCABULARY:
        if word in blob:
            raise ProbeError("capability probe carries carrier vocabulary: %s" % word)


def max_compact_json_bytes(schema: dict[str, Any]) -> int:
    """A conservative finite upper bound for compact UTF-8 JSON under this probe schema.

    String bounds reserve six bytes per character, covering JSON ``\\uXXXX`` escaping. Objects
    require ``additionalProperties: false`` and arrays require ``maxItems``; otherwise the probe is
    rejected as unbounded.
    """
    if "enum" in schema:
        return max(len(json.dumps(value, ensure_ascii=True, separators=(",", ":")).encode("utf-8"))
                   for value in schema["enum"])
    kind = schema.get("type")
    if kind == "string":
        if "maxLength" not in schema:
            raise ProbeError("string schema lacks maxLength")
        return 2 + 6 * int(schema["maxLength"])
    if kind in ("integer", "number"):
        candidates = [schema.get("minimum"), schema.get("maximum"), 0]
        return max(len(str(value)) for value in candidates if value is not None) + 2
    if kind == "boolean":
        return 5
    if kind == "null":
        return 4
    if kind == "array":
        if "maxItems" not in schema:
            raise ProbeError("array schema lacks maxItems")
        item = schema.get("items")
        if not isinstance(item, dict):
            raise ProbeError("array schema lacks a bounded items schema")
        count = int(schema["maxItems"])
        child = max_compact_json_bytes(item)
        return 2 + count * child + max(0, count - 1)
    if kind == "object":
        if schema.get("additionalProperties") is not False:
            raise ProbeError("object schema is not closed")
        properties = schema.get("properties")
        if not isinstance(properties, dict):
            properties = {}
        total = 2
        first = True
        for name, child_schema in sorted(properties.items()):
            if not isinstance(child_schema, dict):
                raise ProbeError("property %s has no schema" % name)
            if not first:
                total += 1
            first = False
            total += len(json.dumps(name, ensure_ascii=True).encode("utf-8")) + 1
            total += max_compact_json_bytes(child_schema)
        return total
    raise ProbeError("unsupported or unbounded probe schema type %r" % kind)


__all__ = [
    "CARRIER_VOCABULARY", "FEATURE_CLASSES", "PROBE_OUTPUT_SAFETY_CAP_TOKENS",
    "PROBE_SCHEMA_VERSION", "ProbeError", "assert_complete_coverage", "assert_non_carrier",
    "build_matrix", "coverage_map", "max_compact_json_bytes", "required_feature_classes",
]
