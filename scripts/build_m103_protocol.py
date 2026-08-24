"""Build the exact M103 owner-review candidate or accepted frozen protocol.

This script never executes M103 qualification.  Final protocol materialization is
fail-closed unless the exact candidate remains current, the canonical local runtime
is present, and a distinct owner acceptance reference is recorded.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "M103"
CANDIDATE_PATH = EXPERIMENT / "PROTOCOL_CANDIDATE.json"
FINAL_PATH = EXPERIMENT / "PROTOCOL.json"
M102_RESULT_PATH = ROOT / "experiments" / "M102" / "RESULT.json"
M102_CHECK_PATH = ROOT / "experiments" / "M102" / "CHECK_REPORT.json"
FREEZE_TAG = "experiment/m103-frozen-protocol-v1"

sys.path.insert(0, str(ROOT / "scripts"))

from audit_m103_boundaries import audit as boundary_audit  # noqa: E402
from run_m103_qualification import (  # noqa: E402
    CAPSULE_SOURCES,
    DEVELOPMENT_DIGEST,
    DEVELOPMENT_PATH,
    EPHEMERAL_KEYS,
    M100_S3_RAW_SHA256,
    M101_T2_RAW_SHA256,
    M102_RESULT_DIGEST,
    M102_STABLE_EVIDENCE_DIGEST,
    M102_U2_RAW_SHA256,
    M102_U2_STATE_DIGEST,
    POOL_DIGEST,
    POOL_PATH,
    PREDECESSOR_CONSERVATION_DIGEST,
    PREDECESSOR_CONSERVATION_PATH,
    PREDECESSOR_CONSERVATION_RAW_SHA256,
    capsule_binding,
    canonical_json,
    digest,
    file_set_digest,
)


MECHANISM_FILES = [
    "metamorphosis/m100_runtime.py",
    "metamorphosis/m101_runtime.py",
    "metamorphosis/m101_executor.py",
    "metamorphosis/m102_runtime.py",
    "metamorphosis/m102_executor.py",
    "metamorphosis/m103_runtime.py",
    "scripts/run_m102_fresh_process.py",
    "scripts/run_m103_process.py",
]

APPARATUS_FILES = [
    "experiments/M103/PRE_REGISTRATION.md",
    "experiments/M103/PROTOCOL_DRAFT.json",
    "experiments/M103/ADVERSARIAL_REVIEW.md",
    "experiments/M103/DEVELOPMENT_FIXTURE.json",
    "experiments/M103/QUALIFICATION_POOL.json",
    "experiments/M103/PREDECESSOR_CONSERVATION.json",
    "scripts/author_m103_development_fixture.py",
    "scripts/author_m103_qualification_pool.py",
    "scripts/author_m103_predecessor_conservation.py",
    "scripts/audit_m103_boundaries.py",
    "scripts/build_m103_protocol.py",
    "scripts/run_m103_development.py",
    "scripts/run_m103_qualification.py",
]

CHECKER_FILES = [
    "scripts/check_m101_definitions.py",
    "scripts/check_m102_definitions.py",
    "scripts/check_m103_definitions.py",
    "scripts/check_m103_closure.py",
    "scripts/check_m103_result.py",
]

CANONICAL_PYTHON_IDENTITY = {
    "implementation": "cpython",
    "version_info": [3, 11, 16],
}
CANONICAL_SQLITE_IDENTITY = {
    "module": "sqlite3",
    "sqlite_version": "3.53.1",
    "sqlite_version_info": [3, 53, 1],
}


def _raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def _current_python_identity() -> dict[str, Any]:
    return {
        "implementation": sys.implementation.name,
        "version_info": [
            sys.version_info.major,
            sys.version_info.minor,
            sys.version_info.micro,
        ],
    }


def _current_sqlite_identity() -> dict[str, Any]:
    return {
        "module": "sqlite3",
        "sqlite_version": sqlite3.sqlite_version,
        "sqlite_version_info": list(sqlite3.sqlite_version_info),
    }


def _require_canonical_runtime() -> None:
    python_identity = _current_python_identity()
    sqlite_identity = _current_sqlite_identity()
    if python_identity != CANONICAL_PYTHON_IDENTITY:
        raise RuntimeError(
            "M103 protocol construction requires canonical CPython 3.11.16; "
            f"observed {python_identity}"
        )
    if sqlite_identity != CANONICAL_SQLITE_IDENTITY:
        raise RuntimeError(
            "M103 protocol construction requires canonical SQLite 3.53.1; "
            f"observed {sqlite_identity}"
        )


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


def _predecessor() -> dict[str, Any]:
    result = json.loads(M102_RESULT_PATH.read_text(encoding="utf-8"))
    checker = json.loads(M102_CHECK_PATH.read_text(encoding="utf-8"))
    return {
        "milestone": "M102",
        "protocol_digest": "59689da64a6007589aefc15a633b069672b190ab799384503a02064bbf8599dc",
        "qualification_pool_digest": (
            "3d6785dd63e66b92d0c727323e9bde39ba21629aaa81222b442a82b9f2949e38"
        ),
        "result_digest": M102_RESULT_DIGEST,
        "stable_evidence_digest": M102_STABLE_EVIDENCE_DIGEST,
        "checker_digest": checker["report_digest"],
        "result_raw_sha256": _raw_sha256(M102_RESULT_PATH),
        "checker_raw_sha256": _raw_sha256(M102_CHECK_PATH),
        "u2_raw_sha256": M102_U2_RAW_SHA256,
        "u2_state_digest": M102_U2_STATE_DIGEST,
        "m101_t2_raw_sha256": M101_T2_RAW_SHA256,
        "m100_s3_raw_sha256": M100_S3_RAW_SHA256,
        "source_commit": "608ab0465795893aeebf6a2b772993c99b5647fc",
        "protocol_tag": "experiment/m102-frozen-protocol-v1",
        "positive_tag": "experiment/m102-positive-result",
        "positive_checker_required": True,
        "preserved_result_matches_constants": result.get("result_digest")
        == M102_RESULT_DIGEST,
    }


def _base() -> dict[str, Any]:
    pool = json.loads(POOL_PATH.read_text(encoding="ascii"))
    conservation = json.loads(PREDECESSOR_CONSERVATION_PATH.read_text(encoding="ascii"))
    audit = boundary_audit()
    if audit.get("confirmed") is not True:
        raise RuntimeError("M103 boundary audit is not clean")
    return {
        "milestone": "M103",
        "attempt": 1,
        "hypothesis": "H48",
        "decision": "D072",
        "publication_disposition": "PUBLIC_AGPL_COMMERCIAL_OPTION",
        "pre_registration": {
            "path": "experiments/M103/PRE_REGISTRATION.md",
            "raw_sha256": _raw_sha256(EXPERIMENT / "PRE_REGISTRATION.md"),
            "draft_path": "experiments/M103/PROTOCOL_DRAFT.json",
            "draft_raw_sha256": _raw_sha256(EXPERIMENT / "PROTOCOL_DRAFT.json"),
        },
        "adversarial_review": {
            "path": "experiments/M103/ADVERSARIAL_REVIEW.md",
            "raw_sha256": _raw_sha256(EXPERIMENT / "ADVERSARIAL_REVIEW.md"),
            "boundary_audit_report_digest": audit["report_digest"],
            "qualification_executed": False,
            "unresolved_decisive_falsifiers": 0,
        },
        "publication": {
            "review_record": "docs/IP_REVIEWS/M103_PUBLICATION_REVIEW.md",
            "review_raw_sha256": _raw_sha256(
                ROOT / "docs" / "IP_REVIEWS" / "M103_PUBLICATION_REVIEW.md"
            ),
            "disposition": "PUBLIC_AGPL_COMMERCIAL_OPTION",
        },
        "predecessor": _predecessor(),
        "development_fixture_digest": DEVELOPMENT_DIGEST,
        "development_fixture_raw_sha256": _raw_sha256(DEVELOPMENT_PATH),
        "qualification_pool_digest": POOL_DIGEST,
        "qualification_pool_raw_sha256": _raw_sha256(POOL_PATH),
        "qualification_population": {
            "path": "experiments/M103/QUALIFICATION_POOL.json",
            "complete_population": True,
            "result_dependent_draw": False,
            "reroll": False,
            "record_count": pool["record_count"],
            "hidden_case_count": pool["hidden_case_count"],
            "configuration_hidden_worlds": len(pool["configuration"]["hidden_worlds"]),
            "filesystem_hidden_worlds": len(pool["filesystem"]["hidden_worlds"]),
            "scientifically_executed_before_freeze": False,
        },
        "predecessor_conservation_fixture_digest": PREDECESSOR_CONSERVATION_DIGEST,
        "predecessor_conservation_fixture_raw_sha256": (
            PREDECESSOR_CONSERVATION_RAW_SHA256
        ),
        "predecessor_conservation_population": {
            "path": "experiments/M103/PREDECESSOR_CONSERVATION.json",
            "entry_count": conservation["entry_count"],
            "fresh_m103_cases": True,
            "scientifically_executed_before_freeze": False,
        },
        "bound_files": {
            "mechanism": _bound_files(MECHANISM_FILES),
            "apparatus": _bound_files(APPARATUS_FILES),
            "checker": _bound_files(CHECKER_FILES),
        },
        "capsules": _capsules(),
        "canonical_runtime": {
            "python": CANONICAL_PYTHON_IDENTITY,
            "sqlite": CANONICAL_SQLITE_IDENTITY,
        },
        "stable_projection": {
            "excluded_exact_keys": sorted(EPHEMERAL_KEYS),
            "excluded_suffixes": ["_pid", "_pids"],
            "recursive": True,
            "policy_frozen_before_qualification": True,
        },
        "phase_order": [
            "create_V0_from_exact_M102_U2",
            "close_S0_and_acquire_S_prime_on_DEVELOPMENT_only",
            "terminate_S_prime_producer",
            "materialize_configuration_and_acquire_D_as_V2",
            "terminate_D_producer",
            "materialize_filesystem_and_acquire_E_as_V3",
            "terminate_E_producer",
            "execute_hidden_worlds_and_causal_controls",
            "execute_fresh_M100_M102_behavioral_conservation",
            "exact_byte_rollback_and_stable_replay",
        ],
        "decisive_conditions": [f"P{index}" for index in range(1, 16)],
        "verdict_rule": "positive_iff_P1_through_P15_are_computed_and_true_else_negative",
        "information_boundary": {
            "S_prime_sees": "exact V0, DEVELOPMENT demand, generic feature vocabulary and bounds",
            "qualification_demands_materialized_after_S_prime_producer_exit": True,
            "filesystem_materialized_after_D_producer_exit": True,
            "qualification_pool_absent_from_runtime_capsule": True,
            "result_checker_absent_from_runtime_capsule": True,
            "repository_root_absent_from_isolated_search_path": True,
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
            "result_path": "experiments/M103/RESULT.json",
            "checker_path": "experiments/M103/CHECK_REPORT.json",
            "exclusive_create": True,
            "preserve_first_result_even_if_negative": True,
            "repair_after_verdict_belongs_to_M104": True,
            "separate_owner_run_authorization_required": True,
            "canonical_command": (
                "python scripts/run_m103_qualification.py materialize --authorized-by-owner "
                "--i-understand-this-is-the-only-canonical-attempt"
            ),
        },
        "claim_if_positive": (
            "bounded acquired constructor-reach improvement with persistent causal reuse across "
            "two project-authored software carriers"
        ),
        "claim_exclusions": [
            "self-hosting",
            "recursive or open-ended self-improvement",
            "independent task authorship",
            "closed G1-G10",
            "general-agent evidence",
            "AGI",
            "independent human reproduction",
            "external deployment authority",
        ],
    }


def build_candidate() -> dict[str, Any]:
    _require_canonical_runtime()
    payload = {
        "schema": "m103-protocol-candidate-v1",
        "status": "owner_review_required",
        "canonical_run_allowed": False,
        "candidate_source_commit": _git_head(),
        "source_commit": None,
        "freeze_tag": FREEZE_TAG,
        "owner_protocol_acceptance_required": True,
        "owner_run_authorization_is_separate": True,
        **_base(),
    }
    return {**payload, "candidate_digest": digest(payload)}


def _load_valid_candidate() -> dict[str, Any]:
    candidate = json.loads(CANDIDATE_PATH.read_text(encoding="ascii"))
    payload = {key: value for key, value in candidate.items() if key != "candidate_digest"}
    if candidate.get("candidate_digest") != digest(payload):
        raise ValueError("M103 owner-review candidate digest is invalid")
    current = _base()
    for key, value in current.items():
        if candidate.get(key) != value:
            raise ValueError(f"M103 owner-review candidate binding moved: {key}")
    return candidate


def build_final(source_commit: str, owner_authorization_reference: str) -> dict[str, Any]:
    if not re.fullmatch(r"[0-9a-f]{40}", source_commit):
        raise ValueError("final M103 source commit must be a full lowercase Git commit id")
    if source_commit != _git_head():
        raise ValueError("final M103 source commit must equal current owner-reviewed HEAD")
    if not owner_authorization_reference.strip():
        raise ValueError("owner protocol-acceptance reference is required")
    _require_canonical_runtime()
    candidate = _load_valid_candidate()
    payload = {
        "schema": "m103-protocol-v1",
        "status": "frozen_protocol_run_not_authorized",
        "canonical_run_allowed": False,
        "source_commit": source_commit,
        "freeze_tag": FREEZE_TAG,
        "protocol_candidate": {
            "path": "experiments/M103/PROTOCOL_CANDIDATE.json",
            "candidate_digest": candidate["candidate_digest"],
            "raw_sha256": _raw_sha256(CANDIDATE_PATH),
        },
        "owner_protocol_acceptance": {
            "required": True,
            "recorded": True,
            "authorization_reference": owner_authorization_reference.strip(),
        },
        "owner_run_authorization_is_separate": True,
        **_base(),
    }
    return {**payload, "protocol_digest": digest(payload)}


def _write_exclusive(path: Path, value: dict[str, Any]) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite {path}")
    path.write_bytes(canonical_json(value).encode("ascii"))


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
            raise ValueError("explicit owner acceptance of the frozen M103 protocol is required")
        value = build_final(
            str(arguments.source_commit or ""),
            str(arguments.owner_authorization_reference or ""),
        )
        target = FINAL_PATH
    if arguments.write:
        _write_exclusive(target, value)
    else:
        print(json.dumps(value, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
