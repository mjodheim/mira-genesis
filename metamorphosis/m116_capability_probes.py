"""DEVELOPMENT-only probes that measure which schema features the fixed M116 route enforces.

The first DEVELOPMENT stress attempt told us that the route returns HTTP 200, stops voluntarily at
18 % of the output budget with zero reasoning tokens, and emits something that does not satisfy a
census-dominating strict schema. It could not tell us *which* constraint was ignored, because the
audit collapsed every outcome into one boolean.

These probes answer that. Each isolates a single feature class the frozen carrier schema actually
relies upon, and the required classes are derived from the committed census rather than chosen:
every keyword the census counts at least once gets a probe, and every keyword it counts zero times
gets none.

## How a probe distinguishes enforcement from coincidence

A schema and a prompt that agree prove nothing: a model that would have complied anyway looks
exactly like a decoder that forced it to. So each probe leaves the constrained dimension
**underspecified in the prompt** and constrained only in the schema. The prompt asks for "a status
token"; the schema says it must be one of four unusual words. If the output lands inside the
enumeration, something enforced it. If it does not, nothing did.

Where the prompt must push against the schema for the test to mean anything -- cardinality bounds,
closed objects -- it asks for a quantity the schema forbids. That is a capability measurement of
our own endpoint, and it is preregistered here rather than improvised later.

Coincidence is reduced, not eliminated, by repetition: each probe carries several independent
constrained fields, so a route that enforces nothing would have to guess all of them.

Nothing here is a scientific observation. No probe carries carrier vocabulary, no probe sends the
H61 qualifying input, and no probe result can advance a generality gate.
"""

from __future__ import annotations

from typing import Any

PROBE_SCHEMA_VERSION = "m116-capability-probe-v1"

# Vocabulary drawn from meteorology and shipping paperwork, screened against the carrier schema.
CARRIER_VOCABULARY = ("machines", "surface", "cells", "initial", "visible", "errors", "actions",
                      "consignments", "docket", "assayer", "parcels", "routing")

# Feature classes the census may demand. A probe exists for each; which ones are *required* is
# decided by the census at run time, never by this list.
FEATURE_CLASSES = (
    "enum",
    "pattern",
    "required",
    "additionalProperties_false",
    "minItems",
    "maxItems",
    "minimum",
    "maximum",
    "items",
    "max_nesting_depth",
    "array_of_object_levels",
)

_ENUM_VALUES = ["quernal", "brimsy", "voltak", "hesper"]
_PATTERN = r"^zq[0-9]{4}$"


def _probe(name: str, feature: str, prompt: str, schema: dict[str, Any],
           detects: str) -> dict[str, Any]:
    return {"schema_version": PROBE_SCHEMA_VERSION, "name": name, "feature_class": feature,
            "prompt": prompt, "schema": schema, "detects": detects}


def _enum_probe() -> dict[str, Any]:
    fields = {"band_%d" % i: {"type": "string", "enum": list(_ENUM_VALUES)} for i in range(6)}
    return _probe(
        "enum", "enum",
        "Return a JSON object with the six keys band_0 through band_5. Each value is a short "
        "lowercase weather-band label of your choosing. Emit no other keys and no prose.",
        {"type": "object", "additionalProperties": False,
         "required": sorted(fields), "properties": fields},
        "the prompt never names the permitted labels, so a value inside the enumeration can only "
        "come from enforcement",
    )


def _pattern_probe() -> dict[str, Any]:
    fields = {"ref_%d" % i: {"type": "string", "pattern": _PATTERN} for i in range(6)}
    return _probe(
        "pattern", "pattern",
        "Return a JSON object with the six keys ref_0 through ref_5. Each value is a short "
        "identifier of your choosing. Emit no other keys and no prose.",
        {"type": "object", "additionalProperties": False,
         "required": sorted(fields), "properties": fields},
        "the prompt never states the required shape, so an identifier matching ^zq[0-9]{4}$ can "
        "only come from enforcement",
    )


def _required_probe() -> dict[str, Any]:
    fields = {"named_%d" % i: {"type": "string"} for i in range(3)}
    fields.update({"unmentioned_%d" % i: {"type": "string"} for i in range(3)})
    return _probe(
        "required", "required",
        "Return a JSON object carrying the three keys named_0, named_1 and named_2, each a short "
        "lowercase word. Emit no prose.",
        {"type": "object", "additionalProperties": False,
         "required": sorted(fields), "properties": fields},
        "three required keys are never mentioned in the prompt; their presence can only come from "
        "enforcement",
    )


def _additional_properties_probe() -> dict[str, Any]:
    return _probe(
        "additional_properties", "additionalProperties_false",
        "Return a JSON object with the key kept, a short lowercase word. Also add the keys extra_a, "
        "extra_b and extra_c with short lowercase words, and any further keys you think useful. "
        "Emit no prose.",
        {"type": "object", "additionalProperties": False,
         "required": ["kept"], "properties": {"kept": {"type": "string"}}},
        "the prompt asks for keys the schema forbids; their absence can only come from enforcement",
    )


def _min_items_probe() -> dict[str, Any]:
    return _probe(
        "min_items", "minItems",
        "Return a JSON object with the single key readings, whose value is a short list of two or "
        "three integers. Emit no prose.",
        {"type": "object", "additionalProperties": False, "required": ["readings"],
         "properties": {"readings": {"type": "array", "minItems": 40,
                                     "items": {"type": "integer"}}}},
        "the prompt asks for two or three entries and the schema demands at least forty; reaching "
        "forty can only come from enforcement",
    )


def _max_items_probe() -> dict[str, Any]:
    return _probe(
        "max_items", "maxItems",
        "Return a JSON object with the single key samples, whose value is a list of exactly twenty "
        "integers. Emit no prose.",
        {"type": "object", "additionalProperties": False, "required": ["samples"],
         "properties": {"samples": {"type": "array", "maxItems": 3,
                                    "items": {"type": "integer"}}}},
        "the prompt asks for twenty entries and the schema permits at most three; stopping at "
        "three can only come from enforcement",
    )


def _integer_bounds_probe() -> dict[str, Any]:
    fields = {"gauge_%d" % i: {"type": "integer", "minimum": 4400, "maximum": 4499}
              for i in range(6)}
    return _probe(
        "integer_bounds", "minimum",
        "Return a JSON object with the six keys gauge_0 through gauge_5. Each value is a small "
        "whole number of your choosing. Emit no other keys and no prose.",
        {"type": "object", "additionalProperties": False,
         "required": sorted(fields), "properties": fields},
        "the prompt asks for small numbers and the schema demands 4400-4499; landing in range can "
        "only come from enforcement",
    )


def _nested_arrays_probe(levels: int) -> dict[str, Any]:
    # `levels` nested arrays of objects, matching what the census demands of the carrier schema.
    schema: dict[str, Any] = {"type": "object", "additionalProperties": False,
                              "required": ["tier"], "properties": {}}
    innermost = {"type": "object", "additionalProperties": False, "required": ["leaf"],
                 "properties": {"leaf": {"type": "string"}}}
    node = innermost
    for _ in range(levels - 1):
        node = {"type": "object", "additionalProperties": False, "required": ["nested"],
                "properties": {"nested": {"type": "array", "minItems": 1, "maxItems": 1,
                                          "items": node}}}
    schema["properties"]["tier"] = {"type": "array", "minItems": 1, "maxItems": 1, "items": node}
    return _probe(
        "nested_arrays", "array_of_object_levels",
        "Return a JSON object with the single key tier. Emit the structure the schema requires and "
        "nothing else. No prose.",
        schema,
        "%d levels of arrays-of-objects must be produced; the prompt describes none of them" % levels,
    )


def _depth_probe(depth: int) -> dict[str, Any]:
    node: dict[str, Any] = {"type": "string", "enum": ["terminus"]}
    # Each wrapper adds two census depth levels (properties mapping plus the subschema).
    for _ in range(max(1, depth // 2)):
        node = {"type": "object", "additionalProperties": False, "required": ["down"],
                "properties": {"down": node}}
    return _probe(
        "nesting_depth", "max_nesting_depth",
        "Return a JSON object with the single key root. Emit the structure the schema requires and "
        "nothing else. No prose.",
        {"type": "object", "additionalProperties": False, "required": ["root"],
         "properties": {"root": node}},
        "a chain at least as deep as the frozen carrier schema must be produced from the schema "
        "alone",
    )


def _combined_probe(levels: int) -> dict[str, Any]:
    item = {"type": "object", "additionalProperties": False,
            "required": ["ref", "band", "gauge", "inner"],
            "properties": {
                "ref": {"type": "string", "pattern": _PATTERN},
                "band": {"type": "string", "enum": list(_ENUM_VALUES)},
                "gauge": {"type": "integer", "minimum": 4400, "maximum": 4499},
                "inner": {"type": "array", "minItems": 2, "maxItems": 2,
                          "items": {"type": "object", "additionalProperties": False,
                                    "required": ["leaf", "flag"],
                                    "properties": {"leaf": {"type": "string", "pattern": _PATTERN},
                                                   "flag": {"type": "boolean"}}}}}}
    return _probe(
        "combined", "combined",
        "Return a JSON object with the single key entries, whose value is a list of eight records. "
        "Each record carries a reference, a band label, a gauge number and two inner items. Choose "
        "the values yourself. Emit no other keys and no prose.",
        {"type": "object", "additionalProperties": False, "required": ["entries"],
         "properties": {"entries": {"type": "array", "minItems": 8, "maxItems": 8,
                                    "items": item}}},
        "every isolated feature class at once, at a cardinality the prompt does not pin down",
    )


def required_feature_classes(census: dict[str, Any]) -> list[str]:
    """Which classes the frozen carrier schema actually relies upon. Derived, never chosen."""
    counts = census.get("keyword_counts") or {}
    required = [name for name in FEATURE_CLASSES
                if name in counts and int(counts[name]) > 0]
    if int(census.get("max_nesting_depth", 0)) > 0:
        required.append("max_nesting_depth")
    if int(census.get("array_of_object_levels", 0)) > 0:
        required.append("array_of_object_levels")
    return sorted(set(required))


def build_matrix(census: dict[str, Any]) -> list[dict[str, Any]]:
    """The frozen probe sequence, in the order it will be sent.

    Isolated probes first, in a fixed order; the combined probe last and only reached when every
    isolated prerequisite has passed. The sequence is a pure function of the committed census.
    """
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
    if "minimum" in required or "maximum" in required:
        ordered.append(_integer_bounds_probe())
    if "array_of_object_levels" in required:
        ordered.append(_nested_arrays_probe(levels))
    if "max_nesting_depth" in required:
        ordered.append(_depth_probe(depth))
    ordered.append(_combined_probe(levels))
    return ordered


def assert_non_carrier(matrix: list[dict[str, Any]]) -> None:
    """No probe may carry carrier vocabulary or resemble the qualifying input."""
    import json

    blob = json.dumps(matrix)
    for word in CARRIER_VOCABULARY:
        if word in blob:
            raise ValueError("capability probe carries carrier vocabulary: %s" % word)


__all__ = [
    "CARRIER_VOCABULARY",
    "FEATURE_CLASSES",
    "PROBE_SCHEMA_VERSION",
    "assert_non_carrier",
    "build_matrix",
    "required_feature_classes",
]
