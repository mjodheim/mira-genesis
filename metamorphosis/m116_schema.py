"""Structural JSON-schema machinery for M116, written to leak nothing about what it validates.

Two jobs live here, and they share a keyword vocabulary so that neither can drift from the other:

* **Validation.** A strict, dependency-free validator for the subset of JSON Schema the frozen
  M115 carrier output schema actually uses. Every rejection names a *schema location* and the
  keyword that failed. It never names, echoes, quotes or summarizes the offending value, because
  the caller runs before reveal and a violation message is the one channel through which carrier
  content could reach a human.
* **Census.** A mechanical count of the structural feature classes a schema relies upon, so that a
  DEVELOPMENT stress schema can be proved at least as demanding as the frozen carrier schema
  without anyone choosing the thresholds by hand.

Nothing here parses model output, seals, reveals or decides a scientific question.
"""

from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

CENSUS_SCHEMA = "m116-schema-complexity-census-v1"

# The keywords the census counts. Adding one changes the census digest, which is the point: a
# stress schema certified against an older vocabulary must not silently pass a newer rule.
CENSUS_KEYWORDS = (
    "additionalProperties_false",
    "enum",
    "exclusiveMaximum",
    "exclusiveMinimum",
    "items",
    "maxItems",
    "maxLength",
    "maximum",
    "minItems",
    "minLength",
    "minimum",
    "pattern",
    "properties",
    "required",
    "uniqueItems",
)

# Composition constructs. The frozen carrier schema uses none of them; the census still reports
# them so that a successor schema which does cannot be certified against a census that ignored it.
COMPOSITION_KEYWORDS = ("allOf", "anyOf", "oneOf", "not", "if", "then", "else", "$ref")

SUPPORTED_TYPES = ("array", "boolean", "integer", "null", "number", "object", "string")


class SchemaError(RuntimeError):
    """A schema is malformed, or uses a keyword this validator refuses to guess about."""


class InstanceError(RuntimeError):
    """An instance failed validation. Carries a schema location and a keyword, never a value."""

    def __init__(self, location: str, keyword: str) -> None:
        super().__init__("%s failed %s" % (location or "<root>", keyword))
        self.location = location or "<root>"
        self.keyword = keyword


# --------------------------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------------------------

def _is_integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _type_matches(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, Mapping)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return _is_integer(value)
    if expected == "number":
        return _is_integer(value) or (isinstance(value, float) and not isinstance(value, bool))
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "null":
        return value is None
    raise SchemaError("unsupported type %r" % expected)


def _reject_unknown(schema: Mapping[str, Any], location: str) -> None:
    known = set(CENSUS_KEYWORDS) | {"type", "additionalProperties", "$schema", "title",
                                    "description", "$comment"}
    for keyword in schema:
        if keyword in COMPOSITION_KEYWORDS:
            raise SchemaError(
                "%s uses composition keyword %s, which this validator refuses to guess about"
                % (location or "<root>", keyword)
            )
        if keyword not in known and keyword != "additionalProperties_false":
            raise SchemaError("%s uses unsupported keyword %s" % (location or "<root>", keyword))


def validate_instance(instance: Any, schema: Mapping[str, Any], *, location: str = "") -> None:
    """Raise `InstanceError` if `instance` does not satisfy `schema`.

    The raised error names where in the *schema* the failure happened and which keyword rejected
    it. It never carries any part of the instance.
    """
    if not isinstance(schema, Mapping):
        raise SchemaError("%s is not a schema object" % (location or "<root>"))
    _reject_unknown(schema, location)

    declared = schema.get("type")
    if declared is not None:
        expected = [declared] if isinstance(declared, str) else list(declared)
        if not any(_type_matches(instance, str(item)) for item in expected):
            raise InstanceError(location, "type")

    if "enum" in schema:
        allowed = schema["enum"]
        if not isinstance(allowed, Sequence) or isinstance(allowed, (str, bytes)):
            raise SchemaError("%s enum is not a list" % (location or "<root>"))
        if not any(instance == candidate and type(instance) is type(candidate)
                   for candidate in allowed):
            raise InstanceError(location, "enum")

    if isinstance(instance, str):
        pattern = schema.get("pattern")
        if pattern is not None and re.search(str(pattern), instance) is None:
            raise InstanceError(location, "pattern")
        if "minLength" in schema and len(instance) < int(schema["minLength"]):
            raise InstanceError(location, "minLength")
        if "maxLength" in schema and len(instance) > int(schema["maxLength"]):
            raise InstanceError(location, "maxLength")

    if _is_integer(instance) or (isinstance(instance, float) and not isinstance(instance, bool)):
        if "minimum" in schema and instance < schema["minimum"]:
            raise InstanceError(location, "minimum")
        if "maximum" in schema and instance > schema["maximum"]:
            raise InstanceError(location, "maximum")
        if "exclusiveMinimum" in schema and instance <= schema["exclusiveMinimum"]:
            raise InstanceError(location, "exclusiveMinimum")
        if "exclusiveMaximum" in schema and instance >= schema["exclusiveMaximum"]:
            raise InstanceError(location, "exclusiveMaximum")

    if isinstance(instance, Mapping):
        properties = schema.get("properties")
        properties = properties if isinstance(properties, Mapping) else {}
        for name in schema.get("required") or ():
            if name not in instance:
                raise InstanceError("%s/properties/%s" % (location, name), "required")
        if schema.get("additionalProperties") is False:
            for name in instance:
                if name not in properties:
                    raise InstanceError(location, "additionalProperties")
        for name, value in instance.items():
            subschema = properties.get(name)
            if isinstance(subschema, Mapping):
                validate_instance(value, subschema,
                                  location="%s/properties/%s" % (location, name))

    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < int(schema["minItems"]):
            raise InstanceError(location, "minItems")
        if "maxItems" in schema and len(instance) > int(schema["maxItems"]):
            raise InstanceError(location, "maxItems")
        if schema.get("uniqueItems") is True:
            seen: list[Any] = []
            for item in instance:
                if item in seen:
                    raise InstanceError(location, "uniqueItems")
                seen.append(item)
        items = schema.get("items")
        if isinstance(items, Mapping):
            for item in instance:
                validate_instance(item, items, location="%s/items" % location)


def instance_is_valid(instance: Any, schema: Mapping[str, Any]) -> tuple[bool, str, str]:
    """Return `(ok, location, keyword)` without raising. Never returns instance content."""
    try:
        validate_instance(instance, schema)
    except InstanceError as exc:
        return False, exc.location, exc.keyword
    return True, "", ""


# --------------------------------------------------------------------------------------------
# Census
# --------------------------------------------------------------------------------------------

def _walk(node: Any, depth: int, counts: dict[str, int], state: dict[str, int]) -> None:
    state["max_depth"] = max(state["max_depth"], depth)
    if isinstance(node, Mapping):
        for keyword, value in node.items():
            if keyword == "additionalProperties" and value is False:
                counts["additionalProperties_false"] += 1
            elif keyword in counts:
                counts[keyword] += 1
            if keyword in COMPOSITION_KEYWORDS:
                state["composition_constructs"] += 1
            if keyword == "type":
                for name in ([value] if isinstance(value, str) else list(value or ())):
                    state.setdefault("types", set()).add(str(name))  # type: ignore[arg-type]
            if keyword == "items":
                state["array_of_object_levels"] += (
                    1 if isinstance(value, Mapping) and value.get("type") == "object" else 0
                )
            _walk(value, depth + 1, counts, state)
    elif isinstance(node, list):
        for item in node:
            _walk(item, depth + 1, counts, state)


def census(schema: Mapping[str, Any]) -> dict[str, Any]:
    """Mechanically derive the structural feature census of `schema`.

    The census is a pure function of the schema document. Nothing about any instance, completion
    or carrier enters it.
    """
    if not isinstance(schema, Mapping):
        raise SchemaError("census input is not a schema object")
    counts = {keyword: 0 for keyword in CENSUS_KEYWORDS}
    state: dict[str, Any] = {"max_depth": 0, "composition_constructs": 0,
                             "array_of_object_levels": 0, "types": set()}
    _walk(schema, 0, counts, state)
    return {
        "schema": CENSUS_SCHEMA,
        "max_nesting_depth": int(state["max_depth"]),
        "array_of_object_levels": int(state["array_of_object_levels"]),
        "composition_constructs": int(state["composition_constructs"]),
        "distinct_types": sorted(str(name) for name in state["types"]),
        "keyword_counts": dict(sorted(counts.items())),
    }


# Census fields on which a stress schema must be at least as demanding as the frozen carrier
# schema. `composition_constructs` is deliberately absent: the frozen schema uses none, so
# requiring more would force an unrelated construct into the stress schema for no reason.
DOMINANCE_FIELDS = ("max_nesting_depth", "array_of_object_levels")


def census_dominates(
    candidate: Mapping[str, Any], frozen: Mapping[str, Any]
) -> tuple[bool, list[str]]:
    """Is `candidate` structurally at least as demanding as `frozen` on every censused class?"""
    failures: list[str] = []
    for field in DOMINANCE_FIELDS:
        if int(candidate.get(field, 0)) < int(frozen.get(field, 0)):
            failures.append(
                "%s: %d < required %d" % (field, int(candidate.get(field, 0)),
                                          int(frozen.get(field, 0)))
            )
    candidate_counts = candidate.get("keyword_counts") or {}
    frozen_counts = frozen.get("keyword_counts") or {}
    for keyword in sorted(frozen_counts):
        required = int(frozen_counts[keyword])
        observed = int(candidate_counts.get(keyword, 0))
        if observed < required:
            failures.append("keyword %s: %d < required %d" % (keyword, observed, required))
    missing = sorted(set(frozen.get("distinct_types") or ()) - set(candidate.get("distinct_types") or ()))
    if missing:
        failures.append("missing types: %s" % ", ".join(missing))
    return (not failures), failures


__all__ = [
    "CENSUS_KEYWORDS",
    "CENSUS_SCHEMA",
    "COMPOSITION_KEYWORDS",
    "DOMINANCE_FIELDS",
    "InstanceError",
    "SchemaError",
    "census",
    "census_dominates",
    "instance_is_valid",
    "validate_instance",
]
