"""M066 governance-only successor to the negative M065 canonical attempt.

M065 canonical run ``31287477458`` stopped in its guard before task-bank
selection because the frozen workflow counted the marker across every fetched
Git reference.  M066 changes no scientific input or mechanism.  It wraps the
unchanged M065 engine and limits marker history to the canonical first-parent
history of the pushed ``main`` commit.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Mapping

import metamorphosis.m065_qualified_completion as base


M066Error = base.M065Error
M066_TASK_BANK = base.M065_TASK_BANK

M066_PROTOCOL: dict[str, object] = {
    "schema": "m066-canonical-governance-protocol-v1",
    "base_experiment": "M065",
    "base_protocol_sha256": base.M065_PROTOCOL_SHA256,
    "task_bank_commitment": base.M065_PROTOCOL["task_bank_commitment"],
    "task_bank_entries": len(M066_TASK_BANK),
    "arms": list(base.M065_PROTOCOL["arms"]),
    "accepted_post_migration_cycles": base.M065_PROTOCOL[
        "accepted_post_migration_cycles"
    ],
    "candidate_budget_per_arm_cycle": base.M065_PROTOCOL[
        "candidate_budget_per_arm_cycle"
    ],
    "public_cases_per_cycle": base.M065_PROTOCOL["public_cases_per_cycle"],
    "hidden_cases_per_cycle": base.M065_PROTOCOL["hidden_cases_per_cycle"],
    "expression_node_limit": base.M065_PROTOCOL["expression_node_limit"],
    "max_candidate_bytes": base.M065_PROTOCOL["max_candidate_bytes"],
    "node_timeout_seconds": base.M065_PROTOCOL["node_timeout_seconds"],
    "scientific_changes": [],
    "governance_corrections": [
        "marker_history_is_first_parent_of_pushed_main_head",
        "side_branch_refs_do_not_count_as_canonical_history",
    ],
    "m065_negative_canonical_run": 31287477458,
    "m065_negative_marker_commit": "a517e6bb76e8476ab6aca8c0a68c5bcfc3501d57",
    "m065_bank_selected": False,
    "canonical_selection_rule": "sha256(m066_protocol_digest || marker_parent_sha) mod bank_size",
}


def _canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


M066_PROTOCOL_SHA256 = hashlib.sha256(
    b"m066-protocol-v1\x00" + _canonical_json(M066_PROTOCOL)
).hexdigest()


@dataclass(frozen=True)
class M066Manifest:
    mapping: Mapping[str, object]

    def to_dict(self) -> dict[str, object]:
        return json.loads(json.dumps(self.mapping))

    def to_bytes(self) -> bytes:
        return _canonical_json(self.mapping)

    def digest(self) -> str:
        return hashlib.sha256(b"m066-manifest-v1\x00" + self.to_bytes()).hexdigest()


def select_task_bank(marker_parent_sha: str) -> int:
    if not re.fullmatch(r"[0-9a-f]{40}", marker_parent_sha):
        raise M066Error("M066 canonical parent must be a lower-case forty-character Git SHA")
    digest = hashlib.sha256(
        b"m066-canonical-bank-selection-v1\x00"
        + bytes.fromhex(M066_PROTOCOL_SHA256)
        + bytes.fromhex(marker_parent_sha)
    ).digest()
    return int.from_bytes(digest, "big") % len(M066_TASK_BANK)


def _run(bank_index: int, *, selection_mode: str, marker_parent_sha: str | None) -> M066Manifest:
    # Execute the frozen M065 science with M066's explicit selection provenance.  The
    # nested M065 workflow-authority flag intentionally remains false: only the outer
    # M066 wrapper may authorise this successor's canonical workflow.
    scientific = base._run(
        bank_index,
        selection_mode=selection_mode,
        marker_parent_sha=marker_parent_sha,
    )
    scientific_mapping = scientific.to_dict()
    outcome = scientific_mapping["base_manifest"]
    if (
        outcome.get("strict_held_out_advantage") is not True
        or outcome.get("complete_final_version") != 12
        or outcome.get("complete_final_retained_passed") != 68
        or outcome["arm_results"]["complete_continued_lineage"]["held_out_quality"]
        != {"hidden_passes": 18, "hidden_total": 18, "exact": True}
    ):
        raise M066Error("M066 received a scientific outcome that differs from frozen M065")
    return M066Manifest(
        {
            "schema": "m066-canonical-governance-manifest-v1",
            "protocol_sha256": M066_PROTOCOL_SHA256,
            "protocol": M066_PROTOCOL,
            "task_bank_commitment": M066_PROTOCOL["task_bank_commitment"],
            "selected_bank_index": bank_index,
            "selection_mode": selection_mode,
            "marker_parent_sha": marker_parent_sha,
            "m065_negative_canonical_run": 31287477458,
            "m065_negative_guard_job": 93178824313,
            "m065_negative_marker_commit": "a517e6bb76e8476ab6aca8c0a68c5bcfc3501d57",
            "m065_bank_selected": False,
            "m065_first_result_created": False,
            "m065_reproduction_created": False,
            "scientific_changes_from_m065": [],
            "governance_correction": "first_parent_history_of_pushed_main_head",
            "base_m065_manifest_digest": scientific.digest(),
            "base_m065_manifest": scientific_mapping,
            "canonical_workflow_authorised": selection_mode
            == "m066_marker_parent_commitment",
            "repository_write_authority_granted_to_lineage": False,
        }
    )


def run_m066_development(bank_index: int = 0) -> M066Manifest:
    return _run(
        bank_index,
        selection_mode="m066_development_explicit_index",
        marker_parent_sha=None,
    )


def run_m066_canonical(marker_parent_sha: str) -> M066Manifest:
    return _run(
        select_task_bank(marker_parent_sha),
        selection_mode="m066_marker_parent_commitment",
        marker_parent_sha=marker_parent_sha,
    )


__all__ = [
    "M066Error",
    "M066Manifest",
    "M066_PROTOCOL",
    "M066_PROTOCOL_SHA256",
    "M066_TASK_BANK",
    "run_m066_canonical",
    "run_m066_development",
    "select_task_bank",
]
