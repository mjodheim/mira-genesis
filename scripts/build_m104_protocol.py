"""Build the review candidate and owner-accepted final M104 protocol."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import audit_m104_freshness as freshness  # noqa: E402
from scripts import run_m104_qualification as runner  # noqa: E402


EXPERIMENT = ROOT / "experiments" / "M104"
CANDIDATE_PATH = EXPERIMENT / "PROTOCOL_CANDIDATE.json"
PROTOCOL_PATH = EXPERIMENT / "PROTOCOL.json"
RESULT_PATH = EXPERIMENT / "RESULT.json"
REPORT_PATH = EXPERIMENT / "CHECK_REPORT.json"
PRE_REGISTRATION = EXPERIMENT / "PRE_REGISTRATION.md"
DRAFT = EXPERIMENT / "PROTOCOL_DRAFT.json"
POOL = EXPERIMENT / "QUALIFICATION_POOL.json"
M103_PROTOCOL = ROOT / "experiments" / "M103" / "PROTOCOL.json"
FREEZE_TAG = "experiment/m104-frozen-protocol-v1"
SOURCE_TAG = "provenance/m104-owner-review-source-v3"
CANDIDATE_TAG = "provenance/m104-owner-review-candidate-v2"
CANONICAL_PYTHON_IDENTITY = {"implementation": "cpython", "version_info": [3, 11, 16]}
CANONICAL_SQLITE_IDENTITY = {
    "module": "sqlite3",
    "sqlite_version": "3.53.1",
    "sqlite_version_info": [3, 53, 1],
}
M104_FILES = [
    ".gitattributes",
    "experiments/M104/README.md",
    "experiments/M104/PRE_REGISTRATION.md",
    "experiments/M104/PROTOCOL_DRAFT.json",
    "experiments/M104/QUALIFICATION_POOL.json",
    "experiments/M104/ADVERSARIAL_REVIEW.md",
    "docs/IP_REVIEWS/M104_PUBLICATION_REVIEW.md",
    "scripts/author_m104_qualification_pool.py",
    "scripts/audit_m104_freshness.py",
    "scripts/run_m104_qualification.py",
    "scripts/check_m104_result.py",
    "scripts/build_m104_protocol.py",
    "tests/test_m104_successor.py",
]


canonical_json = runner.canonical_json
digest = runner.digest


def _git(*arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments], cwd=ROOT, capture_output=True, text=True, check=False
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or "git command failed")
    return completed.stdout.strip()


def _raw(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _python_identity() -> dict[str, Any]:
    return {"implementation": sys.implementation.name, "version_info": list(sys.version_info[:3])}


def _sqlite_identity() -> dict[str, Any]:
    return {
        "module": "sqlite3",
        "sqlite_version": sqlite3.sqlite_version,
        "sqlite_version_info": list(sqlite3.sqlite_version_info),
    }


def _require_authoring_boundary() -> None:
    if _python_identity() != CANONICAL_PYTHON_IDENTITY or _sqlite_identity() != CANONICAL_SQLITE_IDENTITY:
        raise RuntimeError("M104 protocol construction requires canonical Python and SQLite")
    if _git("status", "--porcelain"):
        raise RuntimeError("M104 protocol construction requires a clean worktree")
    if RESULT_PATH.exists() or REPORT_PATH.exists():
        raise RuntimeError("M104 protocol construction refuses after canonical evidence")


def _file_binding(paths: list[str]) -> dict[str, Any]:
    members = {path: _raw(ROOT / path) for path in paths}
    return {"files": paths, "member_digests": members, "digest": digest(members)}


def _m103_binding() -> dict[str, Any]:
    protocol = json.loads(M103_PROTOCOL.read_text(encoding="ascii"))
    if protocol.get("protocol_digest") != runner.M103_PROTOCOL_DIGEST:
        raise RuntimeError("M103 protocol binding changed")
    bound: dict[str, Any] = {}
    for name in ("mechanism", "checker"):
        expected = protocol["bound_files"][name]
        current = _file_binding(expected["files"])
        if current["member_digests"] != expected["member_digests"]:
            raise RuntimeError(f"M103 {name} bytes changed")
        if current["digest"] != expected["digest"]:
            raise RuntimeError(f"M103 {name} set digest changed")
        bound[name] = current
    return {"protocol_digest": protocol["protocol_digest"], "bound_files": bound}


def _entrypoint_preflight() -> dict[str, Any]:
    before = _raw(POOL)
    completed = subprocess.run(
        [str(Path(sys.executable).resolve()), str(ROOT / "scripts/check_m104_result.py"), "--entrypoint-preflight"],
        cwd=EXPERIMENT,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"M104 checker entrypoint preflight failed: {completed.stderr or completed.stdout}")
    report = json.loads(completed.stdout)
    if (
        report.get("confirmed") is not True
        or report.get("runner_imported") is not True
        or report.get("repository_root_resolved") is not True
    ):
        raise RuntimeError("M104 checker entrypoint preflight is not confirmed")
    if any(report.get(key) is not False for key in ("qualification_pool_opened", "result_opened", "report_opened")):
        raise RuntimeError("M104 checker entrypoint preflight reports data access")
    if _raw(POOL) != before or RESULT_PATH.exists() or REPORT_PATH.exists():
        raise RuntimeError("M104 checker entrypoint preflight changed scientific paths")
    return report


def build_candidate() -> dict[str, Any]:
    _require_authoring_boundary()
    audit = freshness.audit()
    if audit.get("confirmed") is not True:
        raise RuntimeError("M104 freshness audit failed")
    entrypoint = _entrypoint_preflight()
    source_commit = _git("rev-parse", "HEAD")
    if _git("rev-list", "-n", "1", SOURCE_TAG) != source_commit:
        raise RuntimeError("M104 owner-review source tag does not resolve to HEAD")
    payload: dict[str, Any] = {
        "schema": "m104-protocol-candidate-v1",
        "milestone": "M104",
        "hypothesis": "H49",
        "decision": "D073",
        "status": "owner_review_required_run_not_authorized",
        "candidate_source_ref": SOURCE_TAG,
        "pre_registration_raw_sha256": _raw(PRE_REGISTRATION),
        "protocol_draft_raw_sha256": _raw(DRAFT),
        "qualification_pool_digest": runner.POOL_DIGEST,
        "qualification_pool_raw_sha256": _raw(POOL),
        "qualification_population": {
            "complete": True,
            "fresh_from_M103": True,
            "record_count": 11,
            "hidden_case_count": 16,
            "reroll": False,
        },
        "freshness_audit": audit,
        "checker_entrypoint_preflight": entrypoint,
        "m103_exact_binding": _m103_binding(),
        "m104_bound_files": _file_binding(M104_FILES),
        "canonical_runtime": {
            "python": CANONICAL_PYTHON_IDENTITY,
            "sqlite": CANONICAL_SQLITE_IDENTITY,
        },
        "canonical_result_policy": {
            "result_path": "experiments/M104/RESULT.json",
            "checker_path": "experiments/M104/CHECK_REPORT.json",
            "canonical_command": "python scripts/run_m104_qualification.py materialize --authorized-by-owner --i-understand-this-is-the-only-canonical-attempt",
            "checker_command": "python scripts/check_m104_result.py --replay --write",
            "exclusive_create": True,
            "canonical_attempts": 1,
            "canonical_checker_attempts": 1,
            "preserve_first_result_even_if_negative": True,
        },
        "decisive_conditions": [f"P{index}" for index in range(1, 16)],
        "verdict_rule": "positive_iff_P1_through_P15_are_computed_and_true_else_negative",
        "canonical_run_allowed": False,
        "separate_owner_run_authorization_required": True,
        "model_calls_allowed": 0,
        "network_calls_allowed": 0,
        "remote_execution_calls_allowed": 0,
        "claim_if_positive": "bounded acquired constructor-reach improvement on a fresh successor population",
        "claim_exclusions": [
            "retroactive M103 repair",
            "self-hosting",
            "recursive or open-ended self-improvement",
            "closed generality gate",
            "general-agent evidence",
            "AGI",
        ],
        "publication_disposition": "PUBLIC_AGPL_COMMERCIAL_OPTION",
    }
    payload["candidate_digest"] = digest(payload)
    return payload


def materialize_candidate() -> dict[str, Any]:
    candidate = build_candidate()
    encoded = canonical_json(candidate).encode("ascii")
    if CANDIDATE_PATH.exists():
        if CANDIDATE_PATH.read_bytes() != encoded:
            raise RuntimeError("existing M104 candidate differs from current apparatus")
    else:
        with CANDIDATE_PATH.open("xb") as handle:
            handle.write(encoded)
    return candidate


def validate_candidate_commit(candidate: dict[str, Any]) -> str:
    candidate_commit = _git("rev-parse", "HEAD")
    if _git("rev-parse", "HEAD^") != _git("rev-list", "-n", "1", candidate["candidate_source_ref"]):
        raise RuntimeError("M104 candidate commit is not the direct child of its bound source")
    if _git("rev-list", "-n", "1", CANDIDATE_TAG) != candidate_commit:
        raise RuntimeError("M104 owner-review candidate tag does not resolve to HEAD")
    changed_paths = _git("diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD").splitlines()
    if changed_paths != ["experiments/M104/PROTOCOL_CANDIDATE.json"]:
        raise RuntimeError("M104 candidate commit must contain only the candidate artifact")
    committed_candidate = subprocess.run(
        ["git", "show", "HEAD:experiments/M104/PROTOCOL_CANDIDATE.json"],
        cwd=ROOT,
        capture_output=True,
        check=False,
    )
    if committed_candidate.returncode != 0 or committed_candidate.stdout != CANDIDATE_PATH.read_bytes():
        raise RuntimeError("M104 working candidate differs from its committed blob")
    return candidate_commit


def build_final(*, accepted_candidate_digest: str, authorization_reference: str) -> dict[str, Any]:
    _require_authoring_boundary()
    candidate = json.loads(CANDIDATE_PATH.read_text(encoding="ascii"))
    payload_candidate = {key: value for key, value in candidate.items() if key != "candidate_digest"}
    if candidate.get("candidate_digest") != digest(payload_candidate):
        raise RuntimeError("M104 candidate digest mismatch")
    if accepted_candidate_digest != candidate["candidate_digest"]:
        raise RuntimeError("M104 owner acceptance does not match the exact candidate")
    candidate_commit = validate_candidate_commit(candidate)
    payload: dict[str, Any] = {
        "schema": "m104-protocol-v1",
        "milestone": "M104",
        "hypothesis": "H49",
        "decision": "D073",
        "status": "frozen_protocol_run_not_authorized",
        "source_ref": CANDIDATE_TAG,
        "candidate_source_ref": candidate["candidate_source_ref"],
        "freeze_tag": FREEZE_TAG,
        "protocol_candidate": {
            "path": "experiments/M104/PROTOCOL_CANDIDATE.json",
            "candidate_digest": candidate["candidate_digest"],
            "raw_sha256": _raw(CANDIDATE_PATH),
        },
        "owner_protocol_acceptance": {
            "required": True,
            "recorded": True,
            "authorization_reference": authorization_reference,
        },
        "owner_run_authorization_is_separate": True,
        "canonical_run_allowed": False,
        "qualification_pool_digest": candidate["qualification_pool_digest"],
        "qualification_pool_raw_sha256": candidate["qualification_pool_raw_sha256"],
        "m103_protocol_digest": candidate["m103_exact_binding"]["protocol_digest"],
        "m103_exact_binding": candidate["m103_exact_binding"],
        "m104_bound_files": candidate["m104_bound_files"],
        "freshness_audit": candidate["freshness_audit"],
        "checker_entrypoint_preflight": candidate["checker_entrypoint_preflight"],
        "canonical_runtime": candidate["canonical_runtime"],
        "canonical_result_policy": candidate["canonical_result_policy"],
        "decisive_conditions": candidate["decisive_conditions"],
        "verdict_rule": candidate["verdict_rule"],
        "model_calls_allowed": 0,
        "network_calls_allowed": 0,
        "remote_execution_calls_allowed": 0,
        "claim_if_positive": candidate["claim_if_positive"],
        "claim_exclusions": candidate["claim_exclusions"],
        "publication_disposition": candidate["publication_disposition"],
    }
    payload["protocol_digest"] = digest(payload)
    return payload


def materialize_final(*, accepted_candidate_digest: str, authorization_reference: str) -> dict[str, Any]:
    protocol = build_final(
        accepted_candidate_digest=accepted_candidate_digest,
        authorization_reference=authorization_reference,
    )
    with PROTOCOL_PATH.open("xb") as handle:
        handle.write(canonical_json(protocol).encode("ascii"))
    return protocol


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("candidate")
    final_parser = subparsers.add_parser("final")
    final_parser.add_argument("--accepted-candidate-digest", required=True)
    final_parser.add_argument("--authorization-reference", required=True)
    arguments = parser.parse_args()
    try:
        if arguments.command == "candidate":
            report = materialize_candidate()
        else:
            report = materialize_final(
                accepted_candidate_digest=arguments.accepted_candidate_digest,
                authorization_reference=arguments.authorization_reference,
            )
    except Exception as error:
        print(json.dumps({"confirmed": False, "error": f"{type(error).__name__}: {error}"}, indent=2))
        return 3
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
