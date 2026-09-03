"""A non-carrier stress schema that dominates the M122 candidate census *and* fits the route.

A stress schema has to satisfy two constraints at once, and M120's line only ever enforced one.

**It must be at least as demanding as the contract it certifies.** A stress easier than the
candidate schema proves nothing about the candidate schema. That is why M118's stress could not
speak for M120's contract and why M120 built its own.

**It must also be inside what the route enforces.** This is the constraint nobody was checking. The
M122 stress was first derived from M120's by substitution, and it inherited M120's defect exactly:
`armed_instruments` and `spare_instruments` duplicated the whole instrument subtree, putting the
stress at **eight** array-of-object levels -- the very depth the route had just been observed to
refuse. A stress the route cannot enforce certifies nothing either, and it would have failed for a
reason that says nothing about the contract.

So the duplication is removed here for the same reason it was removed from the contract: one
`instruments` array, five levels, and every other census dimension raised at the remaining levels
to keep dominance.

**It is deliberately not the candidate schema.** Sending the real carrier contract at scale during
DEVELOPMENT would hand the project a preview of what this generator produces under the very
contract H67 would be frozen on, and a preview is a forking path. M117 disclosed five apparatus
revisions, some following real endpoint observations; this line does not need to pay that twice.
The stress is a wholly unrelated domain -- survey stations and their instrument logs -- carrying no
cell, action, guard, effect or surface anywhere in it.

What it can establish is one thing: this route enforces a schema of this shape and emits a
conforming completion of this size. What it cannot establish, and is not asked to, is anything
about carriers.
"""

from __future__ import annotations

from typing import Any

STRESS_SCHEMA_NAME = "m122_survey_stations"
STATIONS = 24

_CODE = r"^[a-z][a-z0-9_]{1,11}$"
_TAG = r"^[a-z][a-z0-9]{1,7}$"

_BAND = ["low", "mid", "high", "peak"]
_STATE = ["idle", "armed", "logging", "faulted"]
_UNIT = ["metre", "second", "kelvin", "pascal"]
_GRADE = ["a", "b", "c", "d"]
_INDEX = [0, 1, 2, 3]
_SCALE = [2, 3, 4]


class StressError(RuntimeError):
    """The stress schema cannot certify the contract. Every path fails closed."""


def _reading() -> dict[str, Any]:
    return {
        "type": "object", "additionalProperties": False,
        "required": ["tag", "unit", "magnitude", "band"],
        "properties": {
            "tag": {"type": "string", "pattern": _TAG},
            "unit": {"type": "string", "enum": list(_UNIT)},
            "magnitude": {"type": "integer", "enum": list(_INDEX)},
            "band": {"type": "string", "enum": list(_BAND)},
        },
    }


def _channel() -> dict[str, Any]:
    return {
        "type": "object", "additionalProperties": False,
        "required": ["label", "scale", "grade", "heading", "readings"],
        "properties": {
            "label": {"type": "string", "pattern": _CODE},
            "scale": {"type": "integer", "enum": list(_SCALE)},
            "grade": {"type": "string", "enum": list(_GRADE)},
            "heading": {"type": "string", "enum": ["direct", "inverted"]},
            "readings": {"type": "array", "minItems": 1, "maxItems": 3, "items": _reading()},
        },
    }


def _calibration() -> dict[str, Any]:
    """A nested object rather than an array, so it raises the census without raising the depth."""
    return {
        "type": "object", "additionalProperties": False,
        "required": ["tag", "mode", "index"],
        "properties": {
            "tag": {"type": "string", "pattern": _TAG},
            "mode": {"type": "string", "enum": ["factory", "field", "bench"]},
            "index": {"type": "integer", "enum": list(_INDEX)},
        },
    }


def _instrument() -> dict[str, Any]:
    """One instrument array, not two.

    M120's contract and the first draft of this schema both duplicated a subtree to say something
    a single array could not, and both paid three array-of-object levels for it.
    """
    return {
        "type": "object", "additionalProperties": False,
        "required": ["serial", "state", "aperture", "calibration", "channels"],
        "properties": {
            "serial": {"type": "string", "pattern": _CODE},
            "state": {"type": "string", "enum": list(_STATE)},
            "aperture": {"type": "integer", "enum": [0, 2, 3, 4]},
            "calibration": _calibration(),
            "channels": {"type": "array", "minItems": 1, "maxItems": 3, "items": _channel()},
        },
    }


def _mast() -> dict[str, Any]:
    return {
        "type": "object", "additionalProperties": False,
        "required": ["name", "height", "orientation", "condition"],
        "properties": {
            "name": {"type": "string", "pattern": _CODE},
            "height": {"type": "integer", "enum": list(_SCALE)},
            "orientation": {"type": "integer", "enum": list(_INDEX)},
            "condition": {"type": "string", "enum": ["sound", "worn", "damaged"]},
        },
    }


def _docket() -> dict[str, Any]:
    return {
        "type": "object", "additionalProperties": False,
        "required": ["reference", "operator", "shift"],
        "properties": {
            "reference": {"type": "string", "pattern": _CODE},
            "operator": {"type": "string", "pattern": _TAG},
            "shift": {"type": "string", "enum": ["dawn", "noon", "dusk", "night"]},
        },
    }


def _station() -> dict[str, Any]:
    return {
        "type": "object", "additionalProperties": False,
        "required": ["docket", "terrain", "masts", "offline", "fault_codes", "instruments"],
        "properties": {
            "docket": _docket(),
            "terrain": {"type": "string", "enum": ["scree", "marsh", "ridge", "plain"]},
            "masts": {"type": "array", "minItems": 3, "maxItems": 4, "items": _mast()},
            "offline": {"type": "array", "minItems": 0, "maxItems": 1,
                        "items": {"type": "integer", "enum": list(_INDEX)}},
            "fault_codes": {"type": "array", "minItems": 1, "maxItems": 4,
                            "items": {"type": "string", "pattern": _CODE}},
            "instruments": {"type": "array", "minItems": 2, "maxItems": 3,
                            "items": _instrument()},
        },
    }


def build_stress_schema() -> dict[str, Any]:
    """Deterministically construct the stress schema. Same bytes on every call, forever."""
    return {
        "type": "object", "additionalProperties": False,
        "required": ["stations"],
        "properties": {
            "stations": {"type": "array", "minItems": STATIONS, "maxItems": STATIONS,
                         "items": _station()},
        },
    }


def assert_certifies(candidate_schema: dict[str, Any], certified_levels: int) -> dict[str, Any]:
    """Both constraints, checked together, because satisfying one alone is worthless.

    Dominance without serviceability is a stress the route will refuse for reasons unrelated to the
    contract. Serviceability without dominance is a stress easier than the thing it certifies.
    """
    from metamorphosis import m116_schema as schema_tools  # noqa: PLC0415

    stressed = schema_tools.census(build_stress_schema())
    candidate = schema_tools.census(candidate_schema)
    dominates, shortfalls = schema_tools.census_dominates(stressed, candidate)
    if not dominates:
        raise StressError(
            "the stress schema does not dominate the candidate census, so it cannot certify it: %s"
            % ", ".join(shortfalls))
    levels = int(stressed["array_of_object_levels"])
    if levels > certified_levels:
        raise StressError(
            "the stress schema needs %d array-of-object levels and this route has been observed to "
            "enforce %d; it would fail for a reason that says nothing about the contract"
            % (levels, certified_levels))
    return {
        "stress_schema_census": stressed,
        "candidate_schema_census": candidate,
        "stress_dominates_the_candidate_schema": True,
        "stress_is_within_the_certified_nesting": True,
        "stress_schema_is_not_the_candidate_schema": True,
    }


STRESS_PROMPT = (
    "Return a JSON object with exactly one key named stations. Its value must be a list of exactly "
    "%d survey stations. Every station records its docket, its terrain, its masts, which of them "
    "are offline, its fault codes and its instruments. Every mast records its name, height, "
    "orientation and condition. Every instrument records its serial, state, aperture, calibration "
    "and channels, and every channel records its label, scale, grade, heading and readings. Vary "
    "the values across stations. Emit no prose, no commentary and no keys beyond those the schema "
    "names."
) % STATIONS


__all__ = ["STATIONS", "STRESS_PROMPT", "STRESS_SCHEMA_NAME", "StressError", "assert_certifies",
           "build_stress_schema"]
