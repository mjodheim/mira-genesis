"""Frozen post-adoption hidden-world generator for M092 qualification.

The module contains no selected-candidate, theorem, search-result, or qualification values.  Hidden
values are derived only when the caller proves that the extended runtime is durably committed and has
already been loaded in a fresh process.  The raw protocol blob is part of the salt, so any protocol
byte drift changes every world.

Sampling implements the precommitted contract:
* two named families from PROTOCOL.json;
* six hidden values per family in [3000, 9999];
* exactly three even and three odd values per family;
* family-domain-separated counter-mode SHA-256 rejection sampling without replacement;
* stratum order selected by a family-domain-separated digest.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Mapping

from metamorphosis.m092_runtime import canonical_bytes

QUALIFICATION_MATERIAL_SCHEMA = "m092-hidden-qualification-material/1"
FAMILIES = ("alternating_allocation", "complementary_protocol_phase")
DOMAIN_MIN = 3000
DOMAIN_MAX = 9999
INSTANCES_PER_FAMILY = 6
INSTANCES_PER_PARITY = 3
_SHA64 = re.compile(r"\A[0-9a-f]{64}\Z")


class QualificationGenerationError(ValueError):
    """The frozen hidden-world materialization boundary was violated."""


def _digest(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _require_digest(value: str, label: str) -> None:
    if _SHA64.fullmatch(value) is None:
        raise QualificationGenerationError(f"{label} must be lowercase SHA-256")


def _protocol_qualification(protocol: Mapping[str, object]) -> Mapping[str, object]:
    if protocol.get("schema") != "m092-endogenous-substrate-extension-protocol-v1":
        raise QualificationGenerationError("M092 protocol schema differs")
    qualification = protocol.get("qualification")
    if not isinstance(qualification, Mapping):
        raise QualificationGenerationError("M092 protocol qualification section is absent")
    families = qualification.get("family_schemas")
    hidden_domain = qualification.get("hidden_value_domain")
    if not isinstance(families, Mapping) or set(families) != set(FAMILIES):
        raise QualificationGenerationError("qualification family set differs from the frozen protocol")
    if qualification.get("hidden_instances_per_family") != INSTANCES_PER_FAMILY:
        raise QualificationGenerationError("hidden instance count differs from the frozen protocol")
    if not isinstance(hidden_domain, Mapping):
        raise QualificationGenerationError("hidden qualification domain is malformed")
    if hidden_domain.get("inclusive_minimum") != DOMAIN_MIN or hidden_domain.get("inclusive_maximum") != DOMAIN_MAX:
        raise QualificationGenerationError("hidden qualification domain differs")
    if "three even and three odd" not in str(hidden_domain.get("stratification", "")):
        raise QualificationGenerationError("hidden qualification parity stratification differs")
    if "counter-mode SHA-256 rejection sampling without replacement" not in str(
        qualification.get("draw_algorithm", "")
    ):
        raise QualificationGenerationError("hidden qualification draw algorithm differs")
    return qualification


def _salt(protocol_blob: bytes, substrate_digest: str, language_digest: str) -> bytes:
    # Literal concatenation in protocol order, frozen before result reveal.  Digests are lowercase
    # ASCII hexadecimal; the raw protocol bytes are used unchanged.
    return hashlib.sha256(
        protocol_blob + substrate_digest.encode("ascii") + language_digest.encode("ascii")
    ).digest()


def _family_digest(salt: bytes, family: str) -> bytes:
    return hashlib.sha256(
        b"M092-qualification-family-v1\0" + salt + b"\0" + family.encode("utf-8")
    ).digest()


def _candidate_digest(family_digest: bytes, stratum: str, counter: int) -> bytes:
    return hashlib.sha256(
        b"M092-qualification-draw-v1\0"
        + family_digest
        + b"\0"
        + stratum.encode("ascii")
        + b"\0"
        + counter.to_bytes(8, "big", signed=False)
    ).digest()


def _draw_stratum(
    family_digest: bytes,
    *,
    parity: int,
    already_used: set[int],
) -> list[dict[str, object]]:
    span = DOMAIN_MAX - DOMAIN_MIN + 1
    limit = (1 << 256) - ((1 << 256) % span)
    stratum = "even" if parity == 0 else "odd"
    accepted: list[dict[str, object]] = []
    counter = 0
    while len(accepted) < INSTANCES_PER_PARITY:
        digest = _candidate_digest(family_digest, stratum, counter)
        counter += 1
        integer = int.from_bytes(digest, "big")
        if integer >= limit:
            continue
        value = DOMAIN_MIN + (integer % span)
        if value % 2 != parity or value in already_used:
            continue
        already_used.add(value)
        accepted.append({
            "value": value,
            "draw_digest": digest.hex(),
            "draw_counter": counter - 1,
            "stratum": stratum,
        })
    return accepted


def materialize_hidden_qualification(
    protocol_blob: bytes,
    *,
    extended_substrate_digest: str,
    extended_language_digest: str,
    adoption_committed: bool,
    fresh_process_loaded: bool,
) -> dict[str, object]:
    """Materialize the hidden 2x6 worlds only after durable adoption and fresh-process reload."""

    if not adoption_committed or not fresh_process_loaded:
        raise QualificationGenerationError(
            "hidden qualification cannot materialize before committed adoption and fresh reload"
        )
    _require_digest(extended_substrate_digest, "extended substrate digest")
    _require_digest(extended_language_digest, "extended language digest")
    try:
        protocol = json.loads(protocol_blob.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise QualificationGenerationError("protocol blob is not canonical UTF-8 JSON") from error
    if not isinstance(protocol, Mapping):
        raise QualificationGenerationError("protocol blob must decode to an object")
    _protocol_qualification(protocol)

    salt = _salt(protocol_blob, extended_substrate_digest, extended_language_digest)
    families: list[dict[str, object]] = []
    for family in FAMILIES:
        family_digest = _family_digest(salt, family)
        parity_order = (0, 1) if family_digest[0] % 2 == 0 else (1, 0)
        used: set[int] = set()
        draws: list[dict[str, object]] = []
        for parity in parity_order:
            draws.extend(_draw_stratum(family_digest, parity=parity, already_used=used))
        if len(draws) != INSTANCES_PER_FAMILY:
            raise QualificationGenerationError("hidden family did not materialize exactly six worlds")
        values = [int(item["value"]) for item in draws]
        if len(values) != len(set(values)):
            raise QualificationGenerationError("hidden family contains duplicate values")
        if sum(value % 2 == 0 for value in values) != INSTANCES_PER_PARITY:
            raise QualificationGenerationError("hidden family does not contain exactly three even values")
        if sum(value % 2 == 1 for value in values) != INSTANCES_PER_PARITY:
            raise QualificationGenerationError("hidden family does not contain exactly three odd values")
        families.append({
            "family": family,
            "family_digest": family_digest.hex(),
            "stratum_order": ["even" if parity == 0 else "odd" for parity in parity_order],
            "draws": draws,
        })

    material: dict[str, object] = {
        "schema": QUALIFICATION_MATERIAL_SCHEMA,
        "protocol_sha256": hashlib.sha256(protocol_blob).hexdigest(),
        "extended_substrate_digest": extended_substrate_digest,
        "extended_language_digest": extended_language_digest,
        "salt_derivation": "sha256(protocol_blob || substrate_digest_ascii || language_digest_ascii)",
        "salt_digest": salt.hex(),
        "domain": {"inclusive_minimum": DOMAIN_MIN, "inclusive_maximum": DOMAIN_MAX},
        "instances_per_family": INSTANCES_PER_FAMILY,
        "instances_per_parity": INSTANCES_PER_PARITY,
        "families": families,
        "materialized_after_adoption": True,
        "fresh_process_loaded_before_materialization": True,
    }
    material["materialization_digest"] = _digest(material)
    return material


__all__ = [
    "DOMAIN_MAX", "DOMAIN_MIN", "FAMILIES", "INSTANCES_PER_FAMILY", "INSTANCES_PER_PARITY",
    "QUALIFICATION_MATERIAL_SCHEMA", "QualificationGenerationError",
    "materialize_hidden_qualification",
]
