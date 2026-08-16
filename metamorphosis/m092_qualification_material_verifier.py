"""Independent verifier for later M092 hidden qualification material.

The generator is deliberately not imported here.  Given the frozen protocol bytes, exact extended
runtime digests, and one already-materialized qualification artifact, this module independently
reconstructs the salt, both family-domain digests, every counter-mode rejection, and the exact
accepted draw order.  It therefore checks the generator rather than asking the generator to check
itself.

No candidate, canonical-search result, reproduction result, or hidden-world source is reachable from
this module.  It only verifies material supplied after the qualification chronology gates have been
satisfied elsewhere.
"""
from __future__ import annotations

import hashlib
import re
from typing import Mapping, Sequence

from metamorphosis.m092_runtime import canonical_bytes

MATERIAL_SCHEMA = "m092-hidden-qualification-material/1"
VERIFICATION_SCHEMA = "m092-verified-qualification-material/1"
FAMILIES = ("alternating_allocation", "complementary_protocol_phase")
DOMAIN_MIN = 3000
DOMAIN_MAX = 9999
INSTANCES_PER_FAMILY = 6
INSTANCES_PER_PARITY = 3
SALT_DERIVATION = "sha256(protocol_blob || substrate_digest_ascii || language_digest_ascii)"
_SHA64 = re.compile(r"\A[0-9a-f]{64}\Z")


class QualificationMaterialVerificationError(ValueError):
    """Material does not reproduce from the frozen independent draw algorithm."""


def _digest(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _require_digest(value: object, label: str) -> str:
    if not isinstance(value, str) or _SHA64.fullmatch(value) is None:
        raise QualificationMaterialVerificationError(f"{label} must be lowercase SHA-256")
    return value


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


def _expected_family_draws(family_digest: bytes) -> tuple[list[str], list[dict[str, object]]]:
    span = DOMAIN_MAX - DOMAIN_MIN + 1
    rejection_limit = (1 << 256) - ((1 << 256) % span)
    parity_order = (0, 1) if family_digest[0] % 2 == 0 else (1, 0)
    used: set[int] = set()
    draws: list[dict[str, object]] = []

    for parity in parity_order:
        stratum = "even" if parity == 0 else "odd"
        accepted = 0
        counter = 0
        while accepted < INSTANCES_PER_PARITY:
            digest = _candidate_digest(family_digest, stratum, counter)
            current_counter = counter
            counter += 1
            integer = int.from_bytes(digest, "big")
            if integer >= rejection_limit:
                continue
            value = DOMAIN_MIN + (integer % span)
            if value % 2 != parity or value in used:
                continue
            used.add(value)
            draws.append({
                "value": value,
                "draw_digest": digest.hex(),
                "draw_counter": current_counter,
                "stratum": stratum,
            })
            accepted += 1

    return ["even" if item == 0 else "odd" for item in parity_order], draws


def _verify_family(
    item: Mapping[str, object],
    *,
    expected_family: str,
    salt: bytes,
) -> list[dict[str, object]]:
    if set(item) != {"family", "family_digest", "stratum_order", "draws"}:
        raise QualificationMaterialVerificationError("qualification family fields differ")
    if item.get("family") != expected_family:
        raise QualificationMaterialVerificationError("qualification family order or name differs")

    family_digest = _family_digest(salt, expected_family)
    if item.get("family_digest") != family_digest.hex():
        raise QualificationMaterialVerificationError("qualification family digest differs")
    expected_order, expected_draws = _expected_family_draws(family_digest)
    if item.get("stratum_order") != expected_order:
        raise QualificationMaterialVerificationError("qualification family stratum order differs")

    raw_draws = item.get("draws")
    if not isinstance(raw_draws, Sequence) or isinstance(raw_draws, (str, bytes, bytearray)):
        raise QualificationMaterialVerificationError("qualification family draws are malformed")
    actual_draws: list[dict[str, object]] = []
    for raw in raw_draws:
        if not isinstance(raw, Mapping):
            raise QualificationMaterialVerificationError("qualification draw is not an object")
        if set(raw) != {"value", "draw_digest", "draw_counter", "stratum"}:
            raise QualificationMaterialVerificationError("qualification draw fields differ")
        actual_draws.append(dict(raw))
    if actual_draws != expected_draws:
        raise QualificationMaterialVerificationError(
            "qualification draws differ from independent counter-mode reconstruction"
        )
    return actual_draws


def verify_qualification_material(
    material: Mapping[str, object],
    *,
    protocol_blob: bytes,
    extended_substrate_digest: str,
    extended_language_digest: str,
) -> dict[str, object]:
    """Reconstruct the complete 2x6 hidden-world draw and return a bound verification receipt."""

    substrate_digest = _require_digest(extended_substrate_digest, "extended substrate digest")
    language_digest = _require_digest(extended_language_digest, "extended language digest")
    expected_fields = {
        "schema", "protocol_sha256", "extended_substrate_digest", "extended_language_digest",
        "salt_derivation", "salt_digest", "domain", "instances_per_family",
        "instances_per_parity", "families", "materialized_after_adoption",
        "fresh_process_loaded_before_materialization", "materialization_digest",
    }
    if set(material) != expected_fields or material.get("schema") != MATERIAL_SCHEMA:
        raise QualificationMaterialVerificationError("qualification material schema or fields differ")

    payload = {key: value for key, value in material.items() if key != "materialization_digest"}
    if material.get("materialization_digest") != _digest(payload):
        raise QualificationMaterialVerificationError("qualification material digest differs")
    protocol_sha = hashlib.sha256(protocol_blob).hexdigest()
    if material.get("protocol_sha256") != protocol_sha:
        raise QualificationMaterialVerificationError("qualification material is bound to different protocol bytes")
    if material.get("extended_substrate_digest") != substrate_digest:
        raise QualificationMaterialVerificationError("qualification substrate digest differs")
    if material.get("extended_language_digest") != language_digest:
        raise QualificationMaterialVerificationError("qualification language digest differs")
    if material.get("salt_derivation") != SALT_DERIVATION:
        raise QualificationMaterialVerificationError("qualification salt derivation differs")
    if material.get("domain") != {"inclusive_minimum": DOMAIN_MIN, "inclusive_maximum": DOMAIN_MAX}:
        raise QualificationMaterialVerificationError("qualification domain differs")
    if material.get("instances_per_family") != INSTANCES_PER_FAMILY:
        raise QualificationMaterialVerificationError("qualification family size differs")
    if material.get("instances_per_parity") != INSTANCES_PER_PARITY:
        raise QualificationMaterialVerificationError("qualification parity size differs")
    if material.get("materialized_after_adoption") is not True:
        raise QualificationMaterialVerificationError("qualification material predates adoption")
    if material.get("fresh_process_loaded_before_materialization") is not True:
        raise QualificationMaterialVerificationError("qualification material predates fresh-process reload")

    salt = hashlib.sha256(
        protocol_blob + substrate_digest.encode("ascii") + language_digest.encode("ascii")
    ).digest()
    if material.get("salt_digest") != salt.hex():
        raise QualificationMaterialVerificationError("qualification salt digest differs")

    raw_families = material.get("families")
    if not isinstance(raw_families, Sequence) or isinstance(raw_families, (str, bytes, bytearray)):
        raise QualificationMaterialVerificationError("qualification families are malformed")
    if len(raw_families) != len(FAMILIES):
        raise QualificationMaterialVerificationError("qualification family count differs")

    worlds: list[dict[str, object]] = []
    for family_name, raw_family in zip(FAMILIES, raw_families, strict=True):
        if not isinstance(raw_family, Mapping):
            raise QualificationMaterialVerificationError("qualification family is not an object")
        draws = _verify_family(raw_family, expected_family=family_name, salt=salt)
        for ordinal, draw in enumerate(draws):
            worlds.append({
                "family": family_name,
                "family_ordinal": ordinal,
                "task_id": f"{family_name}:{draw['draw_digest']}",
                "value": draw["value"],
                "draw_digest": draw["draw_digest"],
                "draw_counter": draw["draw_counter"],
                "stratum": draw["stratum"],
            })

    if len(worlds) != len(FAMILIES) * INSTANCES_PER_FAMILY:
        raise QualificationMaterialVerificationError("verified qualification world count differs")
    task_ids = [str(world["task_id"]) for world in worlds]
    if len(task_ids) != len(set(task_ids)):
        raise QualificationMaterialVerificationError("verified qualification task identifiers collide")

    receipt: dict[str, object] = {
        "schema": VERIFICATION_SCHEMA,
        "protocol_sha256": protocol_sha,
        "extended_substrate_digest": substrate_digest,
        "extended_language_digest": language_digest,
        "materialization_digest": material["materialization_digest"],
        "salt_digest": salt.hex(),
        "draw_algorithm_recomputed_independently": True,
        "post_hoc_draw_reordering": False,
        "families": list(FAMILIES),
        "worlds": worlds,
    }
    receipt["verification_digest"] = _digest(receipt)
    return receipt


__all__ = [
    "DOMAIN_MAX", "DOMAIN_MIN", "FAMILIES", "INSTANCES_PER_FAMILY", "INSTANCES_PER_PARITY",
    "MATERIAL_SCHEMA", "QualificationMaterialVerificationError", "SALT_DERIVATION",
    "VERIFICATION_SCHEMA", "verify_qualification_material",
]
