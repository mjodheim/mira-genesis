"""Verify the preserved M066 canonical result, reproduction, seal and audit."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Mapping


ROOT = Path(__file__).resolve().parents[1]
RESULT_PATH = Path("results/artifacts/M066_CANONICAL_RESULT.json")
REPRODUCTION_PATH = Path("results/artifacts/M066_INDEPENDENT_REPRODUCTION.json")
SEAL_PATH = Path("results/artifacts/M066_CANONICAL_FIRST_RESULT_SEAL.json")
AUDIT_PATH = Path("results/artifacts/M066_CANONICAL_AUDIT.json")

HEAD_SHA = "2cf454ca4e393a319f89ae5afbcd5e3f9250182c"
PARENT_SHA = "4a4b4a1a1e4831a4e1f8a40f896e3b2921cdc6e5"
PROTOCOL_SHA256 = "f66ab480dfa0631e730753b7e45e3b83da7e2938d3e28e4aa2f497a6e383d66b"
MANIFEST_DIGEST = "b7d4c39c4c89c85346f4b0b2ebbf390e9f8818d4369a6ed4e21fb8d0580a62b1"
RESULT_SHA256 = "eaf6fee975bddaae583e0f739d0a5ad050209b303d304eddc81bb6320c642ace"
REPRODUCTION_SHA256 = "b990efa4c85c808349de046b7b7ed7477138b77c5111f7385e913f7583ab77cc"
SEAL_SHA256 = "0468dbccbe95d0185579b8e46500c0c9518e4912821aed1ab6a63b16b61c198a"
AUDIT_SHA256 = "9923a385a8a73eda87c80cfa90e8841f9cb6aa9bac3d9004914ed44c49360d23"


class CanonicalEvidenceError(ValueError):
    """Raised when preserved M066 evidence is absent, altered or inconsistent."""


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _load(root: Path, relative: Path, expected_sha256: str) -> tuple[bytes, Mapping[str, object]]:
    path = root / relative
    try:
        payload = path.read_bytes()
        value = json.loads(payload)
    except (OSError, json.JSONDecodeError) as exc:
        raise CanonicalEvidenceError(f"canonical evidence is absent or malformed: {relative}") from exc
    if _sha256(payload) != expected_sha256:
        raise CanonicalEvidenceError(f"canonical evidence bytes drifted: {relative}")
    if not isinstance(value, Mapping):
        raise CanonicalEvidenceError(f"canonical evidence is not a mapping: {relative}")
    return payload, value


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise CanonicalEvidenceError(message)


def validate_canonical_evidence(root: Path = ROOT) -> dict[str, object]:
    result_bytes, result = _load(root, RESULT_PATH, RESULT_SHA256)
    _reproduction_bytes, reproduction = _load(
        root, REPRODUCTION_PATH, REPRODUCTION_SHA256
    )
    _seal_bytes, seal = _load(root, SEAL_PATH, SEAL_SHA256)
    _audit_bytes, audit = _load(root, AUDIT_PATH, AUDIT_SHA256)

    _require(result.get("schema") == "m066-canonical-result-v1", "raw result schema drifted")
    _require(result.get("marker_parent_sha") == PARENT_SHA, "raw result parent drifted")
    _require(result.get("manifest_digest") == MANIFEST_DIGEST, "recorded manifest digest drifted")
    manifest = result.get("manifest")
    _require(isinstance(manifest, Mapping), "canonical manifest is absent")
    observed_manifest_digest = _sha256(
        b"m066-manifest-v1\x00"
        + json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )
    _require(observed_manifest_digest == MANIFEST_DIGEST, "canonical manifest bytes drifted")
    _require(manifest.get("protocol_sha256") == PROTOCOL_SHA256, "protocol digest drifted")
    _require(manifest.get("selected_bank_index") == 0, "canonical bank selection drifted")
    _require(
        manifest.get("selection_mode") == "m066_marker_parent_commitment",
        "canonical selection provenance drifted",
    )
    _require(manifest.get("marker_parent_sha") == PARENT_SHA, "manifest parent drifted")
    _require(manifest.get("canonical_workflow_authorised") is True, "M066 workflow was not authorised")
    _require(
        manifest.get("repository_write_authority_granted_to_lineage") is False,
        "lineage authority boundary drifted",
    )

    m065 = manifest.get("base_m065_manifest")
    _require(isinstance(m065, Mapping), "frozen M065 manifest is absent")
    _require(m065.get("canonical_workflow_authorised") is False, "M065 was reauthorised")
    base = m065.get("base_manifest")
    _require(isinstance(base, Mapping), "whole-WebAssembly base manifest is absent")
    _require(base.get("strict_held_out_advantage") is True, "strict advantage failed")
    _require(base.get("complete_final_version") == 12, "final version drifted")
    _require(base.get("complete_final_retained_cases") == 68, "retained-case count drifted")
    _require(base.get("complete_final_retained_passed") == 68, "retained quality failed")
    arms = base.get("arm_results")
    _require(isinstance(arms, Mapping), "arm results are absent")
    expected = {
        "complete_continued_lineage": (3, 18),
        "fresh_on_b": (0, 0),
        "unchanged_parent_migrated": (0, 0),
        "learned_state_ablated": (0, 0),
    }
    for name, (cycles, hidden) in expected.items():
        arm = arms.get(name)
        _require(isinstance(arm, Mapping), f"arm is absent: {name}")
        quality = arm.get("held_out_quality")
        _require(isinstance(quality, Mapping), f"held-out quality is absent: {name}")
        _require(arm.get("accepted_cycles") == cycles, f"accepted-cycle count drifted: {name}")
        _require(quality.get("hidden_passes") == hidden, f"hidden quality drifted: {name}")
        _require(quality.get("hidden_total") == 18, f"hidden denominator drifted: {name}")
    rollback = base.get("forced_rollback")
    _require(isinstance(rollback, Mapping), "rollback receipt is absent")
    _require(rollback.get("exact_restoration") is True, "rollback was not exact")
    _require(rollback.get("restored_object_is_distinct") is True, "rollback object was not distinct")
    _require(
        rollback.get("corrupted_state_digest") != rollback.get("after_digest"),
        "corrupt and restored states are not distinguished",
    )
    _require(base.get("replay_identical") is True, "deterministic replay failed")

    _require(
        reproduction.get("schema") == "m066-independent-reproduction-v1",
        "reproduction schema drifted",
    )
    _require(reproduction.get("marker_parent_sha") == PARENT_SHA, "reproduction parent drifted")
    _require(reproduction.get("exact_bytes_reproduced") is True, "exact reproduction failed")
    _require(reproduction.get("first_result_sha256") == RESULT_SHA256, "first-result hash drifted")
    _require(
        reproduction.get("reproduced_result_sha256") == RESULT_SHA256,
        "reproduced-result hash drifted",
    )

    _require(seal.get("canonical_head_sha") == HEAD_SHA, "seal head drifted")
    _require(seal.get("workflow_run_id") == 31291899534, "seal run identity drifted")
    _require(seal.get("workflow_run_attempt") == 1, "seal attempt drifted")
    _require(seal.get("canonical_result_sha256") == RESULT_SHA256, "seal result hash drifted")
    _require(seal.get("exact_bytes_reproduced") is True, "seal reproduction verdict drifted")
    _require(seal.get("no_retuning_performed") is True, "seal retuning boundary drifted")

    _require(isinstance(audit, Mapping), "canonical audit is not a mapping")
    _require(audit.get("schema") == "m066-canonical-audit/1", "audit schema drifted")
    _require(audit.get("raw_result_sha256") == RESULT_SHA256, "audit result hash drifted")
    _require(audit.get("raw_first_result_seal_sha256") == SEAL_SHA256, "audit seal hash drifted")
    _require(audit.get("exact_bytes_reproduced") is True, "audit reproduction failed")
    _require(audit.get("all_ten_audited_gates_true") is True, "completion gates are not all true")
    gates = audit.get("audited_gate_verdicts")
    _require(isinstance(gates, Mapping) and len(gates) == 10, "audited gate vector is incomplete")
    _require(all(value is True for value in gates.values()), "an audited completion gate is false")

    return {
        "schema": audit["schema"],
        "status": audit["status"],
        "canonical_head_sha": HEAD_SHA,
        "workflow_run_id": 31291899534,
        "selected_bank_index": 0,
        "manifest_digest": MANIFEST_DIGEST,
        "raw_result_bytes": len(result_bytes),
        "raw_result_sha256": RESULT_SHA256,
        "exact_bytes_reproduced": True,
        "all_ten_audited_gates_true": True,
    }


def main() -> int:
    try:
        result = validate_canonical_evidence()
    except CanonicalEvidenceError as error:
        print(f"M066 canonical evidence failure: {error}")
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
