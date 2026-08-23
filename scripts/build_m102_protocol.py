"""Build the exact M102 owner-review candidate or accepted frozen protocol.

This script never runs M102.  Final protocol materialisation is fail-closed unless the
pool is already frozen, the source commit is explicit, the owner-acceptance switch is
present, and a non-empty authorization reference is recorded.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "M102"
CANDIDATE_PATH = EXPERIMENT / "PROTOCOL_CANDIDATE.json"
FINAL_PATH = EXPERIMENT / "PROTOCOL.json"
M101_RESULT_PATH = ROOT / "experiments" / "M101" / "RESULT.json"
M101_CHECK_PATH = ROOT / "experiments" / "M101" / "CHECK_REPORT.json"
FREEZE_TAG = "experiment/m102-frozen-protocol-v1"

from author_m102_qualification_pool import canonical_json, digest, load_pool
from run_m102_qualification import (
    CAPSULE_SOURCES,
    EPHEMERAL_KEYS,
    capsule_binding,
    file_set_digest,
    m101_t2_bytes,
)


MECHANISM_FILES = [
    "metamorphosis/m101_runtime.py",
    "metamorphosis/m101_executor.py",
    "metamorphosis/m102_runtime.py",
    "metamorphosis/m102_executor.py",
    "scripts/run_m102_acquisition_process.py",
    "scripts/run_m102_fresh_process.py",
]

APPARATUS_FILES = [
    "experiments/M102/PRE_REGISTRATION.md",
    "experiments/M102/PROTOCOL_DRAFT.json",
    "experiments/M102/ADVERSARIAL_REVIEW.md",
    "experiments/M102/QUALIFICATION_POOL.json",
    "scripts/author_m102_qualification_pool.py",
    "scripts/audit_m102_boundaries.py",
    "scripts/build_m102_protocol.py",
    "scripts/check_m101_definitions.py",
    "scripts/check_m102_definitions.py",
    "scripts/run_m102_qualification.py",
]

CHECKER_FILES = ["scripts/check_m102_result.py"]


def _raw_sha256(path: str) -> str:
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def _git_head() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def _bound_files(paths: list[str]) -> dict[str, Any]:
    measured, members = file_set_digest(paths)
    return {"files": paths, "member_digests": members, "digest": measured}


def _predecessor() -> dict[str, Any]:
    result = json.loads(M101_RESULT_PATH.read_text(encoding="utf-8"))
    checker = json.loads(M101_CHECK_PATH.read_text(encoding="utf-8"))
    raw, state = m101_t2_bytes()
    commit = subprocess.run(
        ["git", "rev-list", "-n", "1", "experiment/m101-positive-result"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    return {
        "milestone": "M101",
        "result_digest": result["result_digest"],
        "stable_evidence_digest": result["stable_evidence_digest"],
        "checker_digest": checker["report_digest"],
        "m101_t2_raw_sha256": hashlib.sha256(raw).hexdigest(),
        "m101_t2_state_digest": state["state_digest"],
        "m100_sha256": state["m100_sha256"],
        "preservation_tag": "experiment/m101-positive-result",
        "preservation_commit": commit,
        "positive_checker_required": True,
    }


def _capsules() -> dict[str, Any]:
    values: dict[str, Any] = {}
    for name, sources in CAPSULE_SOURCES.items():
        measured, members = capsule_binding(sources)
        values[name] = {
            "members": sorted(sources),
            "member_sources": sources,
            "member_digests": members,
            "digest": measured,
        }
    return values


def _base() -> dict[str, Any]:
    pool = load_pool()
    return {
        "milestone": "M102",
        "attempt": 1,
        "hypothesis": "H47",
        "decision": "D071",
        "publication_disposition": "PUBLIC_AGPL_COMMERCIAL_OPTION",
        "pre_registration": {
            "path": "experiments/M102/PRE_REGISTRATION.md",
            "raw_sha256": _raw_sha256("experiments/M102/PRE_REGISTRATION.md"),
            "draft_path": "experiments/M102/PROTOCOL_DRAFT.json",
            "draft_raw_sha256": _raw_sha256("experiments/M102/PROTOCOL_DRAFT.json"),
        },
        "adversarial_review": {
            "path": "experiments/M102/ADVERSARIAL_REVIEW.md",
            "raw_sha256": _raw_sha256("experiments/M102/ADVERSARIAL_REVIEW.md"),
            "qualification_executed": False,
        },
        "publication": {
            "review_record": "docs/IP_REVIEWS/M102_PUBLICATION_REVIEW.md",
            "review_raw_sha256": _raw_sha256("docs/IP_REVIEWS/M102_PUBLICATION_REVIEW.md"),
            "disposition": "PUBLIC_AGPL_COMMERCIAL_OPTION",
        },
        "predecessor": _predecessor(),
        "qualification_population": {
            "path": "experiments/M102/QUALIFICATION_POOL.json",
            "raw_sha256": _raw_sha256("experiments/M102/QUALIFICATION_POOL.json"),
            "pool_digest": pool["pool_digest"],
            "status": pool["status"],
            "population_size": 13,
            "role_counts": pool["role_counts"],
            "result_dependent_draw": False,
            "reroll": False,
            "scientifically_executed_before_freeze": False,
        },
        "mechanism": _bound_files(MECHANISM_FILES),
        "qualification_apparatus": _bound_files(APPARATUS_FILES),
        "checker": _bound_files(CHECKER_FILES),
        "capsules": _capsules(),
        "sqlite_identity": {
            "module": "sqlite3",
            "sqlite_version": sqlite3.sqlite_version,
            "sqlite_version_info": list(sqlite3.sqlite_version_info),
        },
        "stable_projection": {
            "excluded_keys": sorted(EPHEMERAL_KEYS),
            "recursive": True,
            "policy_frozen_before_qualification": True,
        },
        "phase_order": [
            "create_U0_from_exact_M101_T2",
            "close_flat_image_and_build_K_without_registration",
            "run_fail_closed_and_destructive_flat_controls",
            "acquire_register_K_as_U1",
            "terminate_K_producer",
            "materialize_record_hidden_and_test_retention",
            "register_SQLite_events_through_K",
            "test_no_K_joint_registry_baseline",
            "build_C_without_registration",
            "acquire_register_C_as_U2",
            "terminate_C_producer",
            "materialize_SQLite_hidden_and_reuse",
            "execute_retention_and_conservation",
            "execute_mutation_ablation_corruption_controls",
            "exact_byte_rollback_and_full_restoration",
        ],
        "decisive_conditions": [f"P{index}" for index in range(1, 16)],
        "verdict_rule": "positive_iff_P1_through_P15_are_computed_and_true_else_negative",
        "information_boundary": {
            "K_sees": "U0 journal, incoming public events and four public lookup requirements only",
            "C_sees": "U1-reached SQLite descriptors and four public trigger cases only",
            "hidden_record_material_after_U1_producer_death": True,
            "hidden_SQLite_and_reuse_material_after_U2_producer_death": True,
            "qualification_pool_absent_from_capsules": True,
            "result_checker_absent_from_acquisition_and_execution_capsules": True,
        },
        "runtime_constraints": {
            "fresh_isolated_process_per_scientific_action": True,
            "model_calls": 0,
            "network_calls": 0,
            "remote_execution_calls": 0,
            "repository_authority": False,
            "credential_authority": False,
            "deployment_authority": False,
            "official_adoption": "human-controlled and out of scope",
        },
        "canonical_result_policy": {
            "result_path": "experiments/M102/RESULT.json",
            "checker_path": "experiments/M102/CHECK_REPORT.json",
            "exclusive_create": True,
            "preserve_first_result_even_if_negative": True,
            "repair_after_verdict_belongs_to_M103": True,
            "canonical_command": (
                "python scripts/run_m102_qualification.py materialize --authorized-by-owner "
                "--i-understand-this-is-the-only-canonical-attempt"
            ),
        },
        "claim_if_positive": (
            "bounded continual interference and registry meta-improvement mechanism evidence "
            "under an independently maintained SQLite execution interface"
        ),
        "claim_exclusions": [
            "independent task authorship",
            "closed G4",
            "closed G5",
            "broad continual learning",
            "general-agent evidence",
            "AGI",
            "independent human reproduction",
            "external deployment authority",
        ],
    }


def build_candidate() -> dict[str, Any]:
    value = {
        "schema": "m102-protocol-candidate-v1",
        "status": "owner_review_required",
        "canonical_run_allowed": False,
        "candidate_source_commit": _git_head(),
        "protocol_candidate": {
            "path": "experiments/M102/PROTOCOL_CANDIDATE.json",
            "raw_sha256": None,
            "self_binding_deferred_to_final_protocol": True,
        },
        "freeze": {
            "source_commit": None,
            "protocol_commit": None,
            "tag": FREEZE_TAG,
            "annotated_tag_required": True,
            "owner_acceptance_required": True,
            "owner_authorization_reference": None,
        },
        **_base(),
    }
    return value


def build_final(source_commit: str, owner_authorization_reference: str) -> dict[str, Any]:
    if not re.fullmatch(r"[0-9a-f]{40}", source_commit):
        raise ValueError("final M102 source commit must be a full lowercase Git commit id")
    if source_commit != _git_head():
        raise ValueError("final M102 source commit must equal the current frozen-source HEAD")
    if not owner_authorization_reference.strip():
        raise ValueError("owner authorization reference is required")
    pool = load_pool()
    if pool["status"] != "frozen":
        raise ValueError("M102 pool must be frozen before final protocol construction")
    if not CANDIDATE_PATH.exists():
        raise ValueError("owner-review protocol candidate is absent")
    value = {
        "schema": "m102-protocol-v1",
        "status": "frozen",
        "canonical_run_allowed": True,
        "protocol_candidate": {
            "path": "experiments/M102/PROTOCOL_CANDIDATE.json",
            "raw_sha256": hashlib.sha256(CANDIDATE_PATH.read_bytes()).hexdigest(),
            "self_binding_deferred_to_final_protocol": False,
        },
        "freeze": {
            "source_commit": source_commit,
            "protocol_commit": "bound_by_annotated_tag_commit",
            "tag": FREEZE_TAG,
            "annotated_tag_required": True,
            "owner_acceptance_required": True,
            "owner_authorization_reference": owner_authorization_reference.strip(),
        },
        **_base(),
    }
    if value["qualification_population"]["status"] != "frozen":
        raise ValueError("final M102 protocol did not bind a frozen pool")
    return value


def _write_exclusive(path: Path, value: dict[str, Any]) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--candidate", action="store_true")
    mode.add_argument("--final", action="store_true")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--source-commit")
    parser.add_argument("--owner-authorization-reference")
    parser.add_argument("--i-accept-frozen-protocol", action="store_true")
    arguments = parser.parse_args()
    if arguments.candidate:
        value = build_candidate()
        target = CANDIDATE_PATH
    else:
        if not arguments.i_accept_frozen_protocol:
            raise ValueError("explicit owner acceptance of the frozen M102 protocol is required")
        value = build_final(
            str(arguments.source_commit or ""),
            str(arguments.owner_authorization_reference or ""),
        )
        target = FINAL_PATH
    if arguments.write:
        _write_exclusive(target, value)
    print(
        json.dumps(
            {
                "target": str(target.relative_to(ROOT)).replace("\\", "/"),
                "status": value["status"],
                "canonical_run_allowed": value["canonical_run_allowed"],
                "protocol_digest": digest(value),
                "written": bool(arguments.write),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
