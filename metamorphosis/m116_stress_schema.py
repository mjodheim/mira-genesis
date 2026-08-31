"""A synthetic DEVELOPMENT stress schema that dominates the frozen carrier schema's census.

M116's original capacity gate proved one thing: that the route can emit more than M115's old
32,000-token ceiling. It proved it with 1,536 flat rows of eight integers -- a schema with no
regex constraint, no enumeration and a third of the carrier schema's nesting depth. A route whose
constrained decoder degrades on deep, pattern-constrained schemas would pass that gate and then
fail the qualifying request in exactly M115's way.

This schema is built to be at least as demanding as the frozen carrier schema on every structural
feature class the census counts, while describing a world with nothing whatever to do with
carriers: a mineral consignment manifest. Its vocabulary is screened against the carrier schema's
own, and it never travels with the qualifying input.

Being *structurally* dominating is the whole claim. It is not a carrier world, it is not a proxy
for one, and passing it is a permission to freeze -- never evidence for H61.
"""

from __future__ import annotations

from typing import Any

# Deliberately drawn from assaying and freight, and screened against the carrier vocabulary.
_CODE = r"^[a-z][a-z0-9_]{1,11}$"
_TAG = r"^[a-z][a-z0-9]{1,7}$"

STRESS_SCHEMA_NAME = "m116_consignment_manifest"

# How many top-level consignments the stress request asks for. Chosen so the schema-constrained
# output comfortably exceeds M115's old 32,000-token ceiling without approaching the candidate
# 131,072 budget, and fixed before the gate runs.
CONSIGNMENTS = 96


def _assay() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["element", "grade", "method", "replicates", "certified"],
        "properties": {
            "element": {"type": "string", "pattern": _TAG},
            "grade": {"type": "integer", "minimum": 0, "maximum": 9999},
            "method": {"type": "string", "enum": ["fire", "icp", "xrf", "titration"]},
            "replicates": {"type": "integer", "minimum": 1, "maximum": 6},
            "certified": {"type": "boolean"},
        },
    }


def _sample() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["label", "depth", "assays", "retained"],
        "properties": {
            "label": {"type": "string", "pattern": _CODE},
            "depth": {"type": "integer", "minimum": 1, "maximum": 400},
            "assays": {"type": "array", "minItems": 2, "maxItems": 2, "items": _assay()},
            "retained": {"type": "boolean"},
        },
    }


def _parcel() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["reference", "tonnes", "grade_band", "samples", "seals"],
        "properties": {
            "reference": {"type": "string", "pattern": _CODE},
            "tonnes": {"type": "integer", "minimum": 1, "maximum": 5000},
            "grade_band": {"type": "string", "enum": ["low", "medium", "high", "reject"]},
            "samples": {"type": "array", "minItems": 2, "maxItems": 2, "items": _sample()},
            "seals": {
                "type": "array", "minItems": 2, "maxItems": 2,
                "items": {"type": "string", "pattern": _TAG},
            },
        },
    }


def _leg() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["carrier_mode", "hours", "distance_km", "checkpoint"],
        "properties": {
            "carrier_mode": {"type": "string", "enum": ["rail", "barge", "road", "conveyor"]},
            "hours": {"type": "integer", "minimum": 1, "maximum": 240},
            "distance_km": {"type": "integer", "minimum": 1, "maximum": 9000},
            "checkpoint": {"type": "string", "pattern": _CODE},
        },
    }


def _routing() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["origin", "destination", "legs", "bonded"],
        "properties": {
            "origin": {"type": "string", "pattern": _CODE},
            "destination": {"type": "string", "pattern": _CODE},
            "legs": {"type": "array", "minItems": 2, "maxItems": 2, "items": _leg()},
            "bonded": {"type": "boolean"},
        },
    }


def build_stress_schema() -> dict[str, Any]:
    """Deterministically construct the stress schema. Same bytes on every call, forever."""
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["consignments"],
        "properties": {
            "consignments": {
                "type": "array",
                "minItems": CONSIGNMENTS,
                "maxItems": CONSIGNMENTS,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["docket", "assayer", "status", "parcels", "routing",
                                 "moisture", "priority", "net_masses", "insured",
                                 "tariff_codes"],
                    "properties": {
                        "docket": {"type": "string", "pattern": _CODE},
                        "assayer": {"type": "string", "pattern": _TAG},
                        "status": {"type": "string",
                                   "enum": ["held", "cleared", "quarantined", "released"]},
                        "moisture": {"type": "integer", "minimum": 0, "maximum": 100},
                        "priority": {"type": "string",
                                     "enum": ["routine", "expedited", "critical"]},
                        "net_masses": {
                            "type": "array", "minItems": 2, "maxItems": 2,
                            "items": {"type": "integer", "minimum": 0, "maximum": 50000},
                        },
                        "insured": {"type": "boolean"},
                        "tariff_codes": {
                            "type": "array", "minItems": 2, "maxItems": 2,
                            "items": {"type": "string", "pattern": _TAG},
                        },
                        "parcels": {"type": "array", "minItems": 2, "maxItems": 2,
                                    "items": _parcel()},
                        "routing": _routing(),
                    },
                },
            }
        },
    }


STRESS_PROMPT = (
    "Return a JSON object with exactly one key named consignments. Its value must be a list of "
    "exactly %d mineral consignment dockets. Every docket records its own assayer, clearance "
    "status, moisture percentage, priority, net masses, insurance flag, tariff "
    "codes, parcels and routing. Every parcel "
    "records its reference, tonnage, grade band, seals and samples, and every sample records its "
    "label, depth and assays. Vary the values across dockets. Emit no prose, no commentary and no "
    "keys beyond those the schema names."
) % CONSIGNMENTS


__all__ = ["CONSIGNMENTS", "STRESS_PROMPT", "STRESS_SCHEMA_NAME", "build_stress_schema"]
