"""A non-carrier stress schema whose keyword census dominates the M120 candidate schema.

M118's readiness gate proved this route enforced eleven schema feature classes and served a 73,731
token conforming completion. That measurement was taken against M116's stress schema, and it does
not carry to M120: the M120 candidate schema uses the same eleven classes and far more of them --
22 `enum` occurrences against 5, eight array-of-object levels against five -- so the earlier census
does not dominate it. Readiness has to be re-measured, and this is the schema it is measured
against.

**It is deliberately not the candidate schema.** Sending the real carrier contract at scale during
DEVELOPMENT would hand the project a preview of what this generator produces under the very
contract H65 is about to be frozen on, and a preview is a forking path: M117 disclosed five
apparatus revisions, some following real endpoint observations, and that disclosure is a cost this
milestone does not need to pay again. So the stress is a wholly unrelated domain -- survey stations
and their instrument logs -- built to be at least as demanding as the candidate schema on every
census dimension, and carrying no cell, action, guard, effect or surface anywhere in it.

What the stress can therefore establish is exactly one thing: this route enforces a schema of this
shape and emits a conforming completion of this size. What it cannot establish, and is not asked
to, is anything about carriers.
"""

from __future__ import annotations

from typing import Any

STRESS_SCHEMA_NAME = "m120_survey_stations"
STATIONS = 24

_CODE = r"^[a-z][a-z0-9_]{1,11}$"
_TAG = r"^[a-z][a-z0-9]{1,7}$"

_BAND = ["low", "mid", "high", "peak"]
_STATE = ["idle", "armed", "logging", "faulted"]
_UNIT = ["metre", "second", "kelvin", "pascal"]
_GRADE = ["a", "b", "c", "d"]
_INDEX = [0, 1, 2, 3]
_SCALE = [2, 3, 4]


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


def _instrument(*, minimum_channels: int) -> dict[str, Any]:
    return {
        "type": "object", "additionalProperties": False,
        "required": ["serial", "state", "aperture", "channels", "calibration_index"],
        "properties": {
            "serial": {"type": "string", "pattern": _CODE},
            "state": {"type": "string", "enum": list(_STATE)},
            "aperture": {"type": "integer", "enum": [0, 2, 3, 4]},
            "channels": {"type": "array", "minItems": minimum_channels, "maxItems": 3,
                         "items": _channel()},
            "calibration_index": {"type": "integer", "enum": list(_INDEX)},
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


def _station() -> dict[str, Any]:
    return {
        "type": "object", "additionalProperties": False,
        "required": ["docket", "terrain", "masts", "offline", "fault_codes",
                     "armed_instruments", "spare_instruments"],
        "properties": {
            "terrain": {"type": "string", "enum": ["scree", "marsh", "ridge", "plain"]},
            "docket": {
                "type": "object", "additionalProperties": False,
                "required": ["reference", "operator", "shift"],
                "properties": {
                    "reference": {"type": "string", "pattern": _CODE},
                    "operator": {"type": "string", "pattern": _TAG},
                    "shift": {"type": "string", "enum": ["dawn", "noon", "dusk", "night"]},
                },
            },
            "masts": {"type": "array", "minItems": 3, "maxItems": 4, "items": _mast()},
            "offline": {"type": "array", "minItems": 0, "maxItems": 1,
                        "items": {"type": "integer", "enum": list(_INDEX)}},
            "fault_codes": {"type": "array", "minItems": 1, "maxItems": 4,
                            "items": {"type": "string", "pattern": _CODE}},
            "armed_instruments": {"type": "array", "minItems": 2, "maxItems": 3,
                                  "items": _instrument(minimum_channels=1)},
            "spare_instruments": {"type": "array", "minItems": 2, "maxItems": 3,
                                  "items": _instrument(minimum_channels=0)},
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


STRESS_PROMPT = (
    "Return a JSON object with exactly one key named stations. Its value must be a list of exactly "
    "%d survey stations. Every station records its docket, its terrain, its masts, which of them "
    "are offline, its fault codes, its armed instruments and its spare instruments. Every mast "
    "records its name, height, orientation and condition. Every instrument records its serial, "
    "state, aperture, calibration index and channels, and every channel records its label, scale, "
    "grade, heading and readings. Vary the values across stations. Emit no prose, no commentary "
    "and no keys beyond those the schema names."
) % STATIONS


__all__ = ["STATIONS", "STRESS_PROMPT", "STRESS_SCHEMA_NAME", "build_stress_schema"]
