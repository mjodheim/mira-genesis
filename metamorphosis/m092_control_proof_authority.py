"""Pre-result authority checker for the inherited-substrate impossibility proof M092-P.

The `fixed_substrate` and `more_budget_same_substrate` controls must not infer impossibility from a
failed or exhausted search.  Their reach authority is the separately derived eventual-polynomiality
invariant (M092-I) and its parity corollary (M092-P), whose design audit predates M092-B search.

This module binds the exact historical source/artifact bytes by Git blob SHA-1, recomputes the live
invariant manifest, and checks the load-bearing audit conclusions.  It intentionally does not rerun
the very large development audit during qualification; instead it proves that the preserved audit is
still bound to the exact source that produced the theorem implementation.  Later per-program control
evidence can use the corrected independent finite refutation certificate without changing this
unbounded authority.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Mapping

from metamorphosis.m092_invariant import invariant_manifest
from metamorphosis.m092_runtime import canonical_bytes

AUTHORITY_SCHEMA = "m092-control-proof-authority/1"

# Exact blobs observed and frozen before any terminal M092 canonical result existed.
PRE_RESULT_BLOB_BINDINGS = {
    "metamorphosis/m092_invariant.py": "a950008e83963fb8ae9e96b1fe864228a9988997",
    "scripts/audit_m092_design.py": "a98f0bd213e77a37c042263df802cedbadbd8027",
    "experiments/M092/DESIGN_AUDIT.json": "5f913472a3183c0a4ae4b529d0a9f2ef1a898d84",
}
EXPECTED_INVARIANT_DIGEST = "2b7aa8c08741a778b158577ed161cd381460d1ef52d6618a5b90bc505ac804d1"


class ControlProofAuthorityError(ValueError):
    """The pre-result M092-P proof authority is missing, drifted, or internally inconsistent."""


def _digest(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def git_blob_sha1(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def _load_json(path: Path) -> Mapping[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ControlProofAuthorityError(f"cannot read preserved proof artifact {path}") from error
    if not isinstance(value, Mapping):
        raise ControlProofAuthorityError(f"preserved proof artifact {path} is not an object")
    return value


def verify_m092p_authority(root: Path = Path(".")) -> dict[str, object]:
    """Recompute every binding needed to keep M092-P independent of search-budget outcomes."""

    observed_blobs: dict[str, str] = {}
    for relative, expected in PRE_RESULT_BLOB_BINDINGS.items():
        path = root / relative
        try:
            observed = git_blob_sha1(path.read_bytes())
        except OSError as error:
            raise ControlProofAuthorityError(f"bound proof source is missing: {relative}") from error
        observed_blobs[relative] = observed
        if observed != expected:
            raise ControlProofAuthorityError(f"pre-result proof source drifted: {relative}")

    audit = _load_json(root / "experiments/M092/DESIGN_AUDIT.json")
    live_manifest = invariant_manifest()
    if live_manifest.get("digest") != EXPECTED_INVARIANT_DIGEST:
        raise ControlProofAuthorityError("live M092-I invariant manifest digest drifted")
    if audit.get("invariant") != live_manifest:
        raise ControlProofAuthorityError("preserved design audit is bound to a different invariant manifest")
    if live_manifest.get("proposition") != "M092-I" or live_manifest.get("corollary") != "M092-P":
        raise ControlProofAuthorityError("invariant manifest no longer names M092-I/M092-P")
    if live_manifest.get("length_independent") is not True:
        raise ControlProofAuthorityError("M092-P authority became budget-dependent")
    if live_manifest.get("abstraction_is_exact") is not True or live_manifest.get("abstraction_is_a_widening") is not False:
        raise ControlProofAuthorityError("M092-I abstraction is no longer exact")

    soundness = audit.get("soundness")
    composition = audit.get("composition")
    parity = audit.get("parity_enumeration")
    axes = audit.get("insufficiency_axes")
    if not isinstance(soundness, Mapping) or not isinstance(composition, Mapping) or not isinstance(parity, Mapping):
        raise ControlProofAuthorityError("preserved design audit sections are malformed")
    if not isinstance(axes, list) or not axes:
        raise ControlProofAuthorityError("preserved insufficiency-axis audit is absent")

    if soundness.get("sound") is not True:
        raise ControlProofAuthorityError("eventual-polynomial interpreter soundness is not preserved")
    if soundness.get("mismatches") != 0 or soundness.get("refusal_disagreements") != 0:
        raise ControlProofAuthorityError("preserved soundness audit contains a disagreement")
    if composition.get("closed_under_composition") is not True or composition.get("mismatches") != 0:
        raise ControlProofAuthorityError("preserved composition audit does not support budget-independent closure")
    if parity.get("parity_matches") != 0:
        raise ControlProofAuthorityError("preserved finite corroboration contains a parity match")
    if "corroboration" not in str(parity.get("note", "")):
        raise ControlProofAuthorityError("finite parity enumeration is being presented as the impossibility proof")
    if any(
        not isinstance(item, Mapping) or item.get("blocked_by_the_same_invariant") is not True
        for item in axes
    ):
        raise ControlProofAuthorityError("an insufficiency axis is no longer blocked by the same invariant")

    receipt: dict[str, object] = {
        "schema": AUTHORITY_SCHEMA,
        "authority": "Corollary M092-P from Proposition M092-I",
        "search_failure_is_impossibility_proof": False,
        "length_independent": True,
        "exact_abstraction": True,
        "pre_result_blob_bindings": dict(PRE_RESULT_BLOB_BINDINGS),
        "observed_blob_bindings": observed_blobs,
        "invariant_digest": live_manifest["digest"],
        "soundness_exact_agreements": soundness.get("exact_agreements"),
        "soundness_mismatches": soundness.get("mismatches"),
        "composition_programs": composition.get("programs"),
        "composition_longest_program": composition.get("longest_program"),
        "composition_mismatches": composition.get("mismatches"),
        "finite_parity_enumeration_role": "corroboration_only",
        "finite_parity_matches": parity.get("parity_matches"),
        "control_uses_m092p_not_search_exhaustion": True,
    }
    receipt["authority_digest"] = _digest(receipt)
    return receipt


__all__ = [
    "AUTHORITY_SCHEMA", "ControlProofAuthorityError", "EXPECTED_INVARIANT_DIGEST",
    "PRE_RESULT_BLOB_BINDINGS", "git_blob_sha1", "verify_m092p_authority",
]
