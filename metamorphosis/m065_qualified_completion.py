"""M065 correction of the failed M064 freeze candidate.

M064 remains preserved at commit ``ec92af78b57203d32c2ee504db91b4166ec83fdf``
and qualification run ``31281234286``.  M065 changes no task, budget,
threshold, substrate or candidate grammar.  It repairs only the transaction
falsifier: a corrupt staged state is discarded, the pre-transaction bytes are
deserialised into a distinct restored object, and that object is audited and
compared with the committed pre-fault digest before execution may continue.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import json
import re
from typing import Iterator, Mapping

import metamorphosis.m064_whole_wasm_completion as whole


M065Error = whole.M064Error
M065_TASK_BANK = whole.M064_TASK_BANK

M065_PROTOCOL: dict[str, object] = {
    "schema": "m065-qualified-completion-protocol-v1",
    "base_experiment": "M064",
    "base_protocol_sha256": whole.M064_PROTOCOL.digest(),
    "task_bank_commitment": whole.M064_PROTOCOL.task_bank_commitment,
    "task_bank_entries": len(M065_TASK_BANK),
    "arms": list(whole.M064_PROTOCOL.arms),
    "accepted_post_migration_cycles": whole.M064_PROTOCOL.accepted_post_migration_cycles,
    "candidate_budget_per_arm_cycle": whole.M064_PROTOCOL.candidate_budget_per_arm_cycle,
    "public_cases_per_cycle": whole.M064_PROTOCOL.public_cases_per_cycle,
    "hidden_cases_per_cycle": whole.M064_PROTOCOL.hidden_cases_per_cycle,
    "expression_node_limit": whole.M064_PROTOCOL.expression_node_limit,
    "max_candidate_bytes": whole.M064_PROTOCOL.max_candidate_bytes,
    "node_timeout_seconds": whole.M064_PROTOCOL.node_timeout_seconds,
    "scientific_corrections": ["non_tautological_snapshot_restoration"],
    "governance_corrections": [
        "marker_must_be_first_path_history_occurrence",
        "canonical_first_result_requires_workflow_attempt_one",
    ],
    "canonical_selection_rule": "sha256(m065_protocol_digest || marker_parent_sha) mod bank_size",
}


def _canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


M065_PROTOCOL_SHA256 = hashlib.sha256(
    b"m065-protocol-v1\x00" + _canonical_json(M065_PROTOCOL)
).hexdigest()


@dataclass(frozen=True)
class M065Manifest:
    mapping: Mapping[str, object]

    def to_dict(self) -> dict[str, object]:
        return json.loads(json.dumps(self.mapping))

    def to_bytes(self) -> bytes:
        return _canonical_json(self.mapping)

    def digest(self) -> str:
        return hashlib.sha256(b"m065-manifest-v1\x00" + self.to_bytes()).hexdigest()


def _restore_snapshot(snapshot_bytes: bytes, expected_digest: str) -> dict[str, object]:
    """Construct and audit the state returned by the rollback path."""
    restored = json.loads(snapshot_bytes)
    if not isinstance(restored, dict):
        raise M065Error("M065 rollback snapshot is not a state mapping")
    whole._audit_state(restored)
    observed = whole._wasm_state_digest(restored)
    if observed != expected_digest:
        raise M065Error("M065 restored state differs from the pre-fault commitment")
    return restored


def _adopt_candidate(
    state: Mapping[str, object],
    task_id: str,
    selection: Mapping[str, object],
    *,
    forced_fault: bool = False,
) -> tuple[dict[str, object], dict[str, object]]:
    """M064 adoption with an actual, independently checked restore operation."""
    before = json.loads(json.dumps(state))
    before_bytes = whole._canonical_json(before)
    before_digest = whole._wasm_state_digest(before)
    candidate = selection.get("selected_candidate")
    if selection.get("action") != "adopt" or not isinstance(candidate, Mapping):
        return before, {"adopted": False, "exact_restoration": False, "reason": "selection_not_admitted"}
    validation_digest = whole._digest(b"m064-whole-wasm-validation-v1\x00", selection)
    record_core = {
        "task_id": task_id,
        "parent_body_digest": whole._wasm_body_digest(state["body"]),
        "candidate_body_digest": whole._wasm_body_digest(candidate["candidate_body"]),
        "expression_digest": candidate["expression_digest"],
        "validation_digest": validation_digest,
        "adopted_version": int(state["version"]) + 1,
    }
    record = {
        **record_core,
        "record_digest": whole._digest(b"m064-whole-wasm-patch-v1\x00", record_core),
    }
    entry = {
        "sequence": int(state["version"]) + 1,
        "event": "adopt_validated_whole_webassembly_rewrite",
        "body_digest": record["candidate_body_digest"],
        "migration_digest": state["migration"]["digest"],
        "patch_digest": record["record_digest"],
        "validation_digest": validation_digest,
        "previous_entry_digest": whole._journal_entry_digest(state["native_journal"][-1]),
    }
    staged = json.loads(json.dumps(state))
    staged["version"] = int(state["version"]) + 1
    staged["body_archive"].append(
        {
            "version": state["version"],
            "body": state["body"],
            "body_digest": whole._wasm_body_digest(state["body"]),
        }
    )
    staged["body"] = candidate["candidate_body"]
    staged["patch_registry"].append(record)
    staged["accepted_task_ids"].append(task_id)
    staged["native_journal"].append(entry)
    memory = dict(staged["causal_memory"])
    episodes = list(memory["native_episodes"])
    episodes.append(
        {
            "task_id": task_id,
            "outcome": "accepted_whole_webassembly_rewrite",
            "expression_digest": candidate["expression_digest"],
            "referenced_tools": list(candidate["referenced_tools"]),
            "validation_digest": validation_digest,
            "reason": selection.get("reason"),
        }
    )
    memory["native_episodes"] = episodes
    staged["causal_memory"] = memory
    try:
        if forced_fault:
            corrupted = json.loads(json.dumps(staged))
            corrupted["native_journal"][-1]["patch_digest"] = "0" * 64
            corrupted_digest = whole._wasm_state_digest(corrupted)
            if whole._canonical_json(corrupted) == before_bytes:
                raise M065Error("M065 forced fault did not create a distinct staged state")
            whole._audit_state(corrupted)
        else:
            whole._audit_state(staged)
    except M065Error as exc:
        if not forced_fault:
            raise
        restored = _restore_snapshot(before_bytes, before_digest)
        after_bytes = whole._canonical_json(restored)
        after_digest = whole._wasm_state_digest(restored)
        exact = after_bytes == before_bytes and after_digest == before_digest
        if not exact:
            raise M065Error("M065 rollback did not restore the exact state") from exc
        return restored, {
            "adopted": False,
            "exact_restoration": True,
            "reason": str(exc),
            "attempted_version": int(state["version"]) + 1,
            "restored_version": restored["version"],
            "before_digest": before_digest,
            "corrupted_state_digest": corrupted_digest,
            "after_digest": after_digest,
            "rollback_operation": "deserialize_and_audit_pretransaction_snapshot",
            "restored_object_is_distinct": restored is not before,
            "restoration_verified_against_pre_fault_snapshot": True,
        }
    return staged, {
        "adopted": True,
        "exact_restoration": False,
        "committed_version": staged["version"],
        "before_digest": before_digest,
        "after_digest": whole._wasm_state_digest(staged),
    }


@contextmanager
def _corrected_transaction_scope() -> Iterator[None]:
    original = whole._adopt_candidate
    whole._adopt_candidate = _adopt_candidate
    try:
        yield
    finally:
        whole._adopt_candidate = original


def select_task_bank(marker_parent_sha: str) -> int:
    if not re.fullmatch(r"[0-9a-f]{40}", marker_parent_sha):
        raise M065Error("M065 canonical parent must be a lower-case forty-character Git SHA")
    digest = hashlib.sha256(
        b"m065-canonical-bank-selection-v1\x00"
        + bytes.fromhex(M065_PROTOCOL_SHA256)
        + bytes.fromhex(marker_parent_sha)
    ).digest()
    return int.from_bytes(digest, "big") % len(M065_TASK_BANK)


def _run(bank_index: int, *, selection_mode: str, marker_parent_sha: str | None) -> M065Manifest:
    with _corrected_transaction_scope():
        base = whole._run_bank(
            bank_index,
            whole.M064_PROTOCOL,
            selection_mode=selection_mode,
            marker_parent_sha=marker_parent_sha,
        )
    base_mapping = base.to_dict()
    rollback = base_mapping["forced_rollback"]
    if (
        rollback.get("rollback_operation") != "deserialize_and_audit_pretransaction_snapshot"
        or rollback.get("restored_object_is_distinct") is not True
        or rollback.get("restoration_verified_against_pre_fault_snapshot") is not True
        or rollback.get("corrupted_state_digest") == rollback.get("after_digest")
    ):
        raise M065Error("M065 corrected rollback evidence is incomplete")
    return M065Manifest(
        {
            "schema": "m065-qualified-completion-manifest-v1",
            "protocol_sha256": M065_PROTOCOL_SHA256,
            "protocol": M065_PROTOCOL,
            "task_bank_commitment": whole.M064_PROTOCOL.task_bank_commitment,
            "selected_bank_index": bank_index,
            "selection_mode": selection_mode,
            "marker_parent_sha": marker_parent_sha,
            "m064_failed_parent_commit": "ec92af78b57203d32c2ee504db91b4166ec83fdf",
            "m064_failed_qualification_run": 31281234286,
            "correction_scope": ["transaction_restoration", "canonical_governance"],
            "base_manifest_digest": base.digest(),
            "base_manifest": base_mapping,
            "canonical_workflow_authorised": selection_mode == "m065_marker_parent_commitment",
            "repository_write_authority_granted_to_lineage": False,
        }
    )


def run_m065_development(bank_index: int = 0) -> M065Manifest:
    return _run(
        bank_index,
        selection_mode="m065_development_explicit_index",
        marker_parent_sha=None,
    )


def run_m065_canonical(marker_parent_sha: str) -> M065Manifest:
    return _run(
        select_task_bank(marker_parent_sha),
        selection_mode="m065_marker_parent_commitment",
        marker_parent_sha=marker_parent_sha,
    )


__all__ = [
    "M065Error",
    "M065Manifest",
    "M065_PROTOCOL",
    "M065_PROTOCOL_SHA256",
    "M065_TASK_BANK",
    "run_m065_canonical",
    "run_m065_development",
    "select_task_bank",
]
