"""Build the M106 candidate and final protocol without running qualification."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "M106"
CANDIDATE_PATH = EXPERIMENT / "PROTOCOL_CANDIDATE.json"
PROTOCOL_PATH = EXPERIMENT / "PROTOCOL.json"
POOL_DIGEST = "701076294bae0d6495446fa009d23c0da0f7e74950bd6616e549edf7db5bd1a2"
POOL_RAW_SHA256 = "12166609e99ea93dc9c49831486baef3f693f54bbd3bd7cd60ee065203b776d2"
DEVELOPMENT_RAW_SHA256 = "7fcbf4364a6540cf7e9c708b1e9a01386c5c21c0b3cd181987dbd3dbd8803a98"
PREDECESSOR_RAW_SHA256 = "98d61df076e6b764f6b00f27793b82ef27e20cd35049780499029dc3ed7edf77"
PREDECESSOR_STATE_DIGEST = "a34b3b9dab99ee848a9c209a95ec9201fd7056eb99393d45d4041c885f19417a"
EXPECTED_PREDICATES = [f"P{index}" for index in range(1, 17)]

APPARATUS_FILES = sorted(
    {
        ".gitattributes",
        "experiments/M106/README.md",
        "experiments/M106/PRE_REGISTRATION.md",
        "experiments/M106/ADVERSARIAL_REVIEW.md",
        "experiments/M106/M104_V3.json",
        "experiments/M106/DEVELOPMENT_FIXTURE.json",
        "experiments/M106/QUALIFICATION_POOL.json",
        "experiments/M104/QUALIFICATION_POOL.json",
        "experiments/M103/PREDECESSOR_CONSERVATION.json",
        # The mechanism, imported unchanged. This is the point of the replication.
        "metamorphosis/m100_runtime.py",
        "metamorphosis/m101_runtime.py",
        "metamorphosis/m102_runtime.py",
        "metamorphosis/m103_runtime.py",
        "metamorphosis/m105_runtime.py",
        "metamorphosis/m101_executor.py",
        "metamorphosis/m102_executor.py",
        "scripts/run_m102_fresh_process.py",
        "scripts/run_m105_process.py",
        "scripts/check_m101_definitions.py",
        "scripts/check_m102_definitions.py",
        "scripts/check_m103_definitions.py",
        "scripts/check_m105_semantics.py",
        "scripts/check_m105_definitions.py",
        "scripts/check_m105_m104_closure.py",
        # The M106 instrument.
        "scripts/run_m106_qualification.py",
        "scripts/check_m106_result.py",
        "scripts/audit_m106_boundaries.py",
        "scripts/author_m106_predecessor.py",
        "scripts/author_m106_development_fixture.py",
        "scripts/author_m106_qualification_pool.py",
        "scripts/build_m106_protocol.py",
        "tests/test_m106_replication.py",
    }
)


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("ascii")).hexdigest()


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(*arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments], cwd=ROOT, capture_output=True, text=True, check=False
    )
    if completed.returncode != 0:
        raise ValueError(completed.stderr.strip() or "git command failed")
    return completed.stdout.strip()


def _require_annotated_tag(reference: str, expected_commit: str) -> None:
    if _git("cat-file", "-t", reference) != "tag":
        raise ValueError(f"{reference} is not an annotated tag")
    if _git("rev-list", "-n", "1", reference) != expected_commit:
        raise ValueError(f"{reference} does not bind the expected commit")


def bound_files() -> dict[str, Any]:
    members = {path: _sha(ROOT / path) for path in APPARATUS_FILES}
    return {"files": APPARATUS_FILES, "member_digests": members, "digest": digest(members)}


def candidate(source_ref: str) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema": "m106-protocol-candidate-v1",
        "milestone": "M106",
        "hypothesis": "H50",
        "decision_slot": "D074",
        "status": "owner_authorized_candidate_not_finally_frozen",
        "candidate_source_ref": source_ref,
        "predecessor": {
            "m104_v3_raw_sha256": PREDECESSOR_RAW_SHA256,
            "m104_v3_state_digest": PREDECESSOR_STATE_DIGEST,
            "m104_protocol_digest": "b3d8a6b3bc231778ab68bfbbc21f15be6d87a8d4652c8c843ee576cfa499a888",
            "m104_result_digest": "f2be4d8516207187f0892eb6c8cecd0f648563456f33aa07fe13787b0e867de3",
        },
        "development_fixture_raw_sha256": DEVELOPMENT_RAW_SHA256,
        "qualification_pool_digest": POOL_DIGEST,
        "qualification_pool_raw_sha256": POOL_RAW_SHA256,
        "lower_substrate": {
            "inputs": 2,
            "operators": ["CONST_FALSE", "CONST_TRUE", "INPUT_0", "INPUT_1", "NOT", "AND", "OR"],
            "maximum_nodes": 8,
            "complete_semantic_image": 16,
        },
        "bound_files": bound_files(),
        "canonical_runtime": {
            "python": {"implementation": "cpython", "version_info": [3, 11, 16]},
            "sqlite": {
                "module": "sqlite3",
                "sqlite_version": "3.53.1",
                "sqlite_version_info": [3, 53, 1],
            },
        },
        "decisive_conditions": EXPECTED_PREDICATES,
        "verdict_rule": "positive_iff_P1_through_P16_all_computed_true_else_negative",
        "canonical_result_policy": {
            "canonical_attempts": 1,
            "canonical_checker_attempts": 1,
            "exclusive_create": True,
            "preserve_first_result_even_if_negative": True,
            "repair_after_result_forbidden": True,
        },
        "owner_workflow_authorization": {
            "recorded": True,
            "date": "2026-08-24",
            "scope": "freeze_single_canonical_attempt_preservation_single_checker_replay_merge",
        },
        "canonical_run_allowed": False,
        "separate_final_freeze_required": True,
        "model_calls_allowed": 0,
        "network_calls_allowed": 0,
        "remote_execution_calls_allowed": 0,
        "claim_if_positive": "bounded_state_owned_executable_constructor_vocabulary_extension",
        "next_ceiling_if_positive": "fixed_lower_boolean_primitives_and_interpreter",
    }
    payload["candidate_digest"] = digest(payload)
    return payload


def final_protocol(candidate_value: dict[str, Any], source_ref: str, freeze_tag: str) -> dict[str, Any]:
    candidate_payload = {
        key: value for key, value in candidate_value.items() if key != "candidate_digest"
    }
    if candidate_value.get("candidate_digest") != digest(candidate_payload):
        raise ValueError("M106 candidate digest mismatch")
    payload: dict[str, Any] = {
        "schema": "m106-protocol-v1",
        "milestone": "M106",
        "hypothesis": "H50",
        "decision_slot": "D074",
        "status": "frozen_protocol_owner_authorized",
        "source_ref": source_ref,
        "freeze_tag": freeze_tag,
        "protocol_candidate": {
            "candidate_digest": candidate_value["candidate_digest"],
            "raw_sha256": _sha(CANDIDATE_PATH),
            "candidate_source_ref": candidate_value["candidate_source_ref"],
        },
        "predecessor": candidate_value["predecessor"],
        "development_fixture_raw_sha256": candidate_value[
            "development_fixture_raw_sha256"
        ],
        "qualification_pool_digest": candidate_value["qualification_pool_digest"],
        "qualification_pool_raw_sha256": candidate_value[
            "qualification_pool_raw_sha256"
        ],
        "lower_substrate": candidate_value["lower_substrate"],
        "bound_files": candidate_value["bound_files"],
        "canonical_runtime": candidate_value["canonical_runtime"],
        "decisive_conditions": candidate_value["decisive_conditions"],
        "verdict_rule": candidate_value["verdict_rule"],
        "canonical_result_policy": candidate_value["canonical_result_policy"],
        "owner_workflow_authorization": candidate_value["owner_workflow_authorization"],
        "canonical_run_allowed": True,
        "model_calls_allowed": 0,
        "network_calls_allowed": 0,
        "remote_execution_calls_allowed": 0,
        "claim_if_positive": candidate_value["claim_if_positive"],
        "next_ceiling_if_positive": candidate_value["next_ceiling_if_positive"],
    }
    payload["protocol_digest"] = digest(payload)
    return payload


def _write_exclusive(path: Path, value: dict[str, Any]) -> None:
    with path.open("xb") as handle:
        handle.write(canonical_json(value).encode("ascii"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    candidate_parser = subparsers.add_parser("candidate")
    candidate_parser.add_argument("--source-ref", required=True)
    final_parser = subparsers.add_parser("final")
    final_parser.add_argument("--source-ref", required=True)
    final_parser.add_argument("--freeze-tag", required=True)
    arguments = parser.parse_args()
    if _git("status", "--porcelain"):
        raise SystemExit("M106 protocol build requires a clean worktree")
    head = _git("rev-parse", "HEAD")
    if arguments.command == "candidate":
        _require_annotated_tag(arguments.source_ref, head)
        if CANDIDATE_PATH.exists() or PROTOCOL_PATH.exists():
            raise SystemExit("M106 candidate or final protocol already exists")
        _write_exclusive(CANDIDATE_PATH, candidate(arguments.source_ref))
        return 0
    _require_annotated_tag(arguments.source_ref, head)
    if PROTOCOL_PATH.exists() or not CANDIDATE_PATH.exists():
        raise SystemExit("M106 final protocol state is invalid")
    candidate_value = json.loads(CANDIDATE_PATH.read_text(encoding="ascii"))
    _write_exclusive(
        PROTOCOL_PATH,
        final_protocol(candidate_value, arguments.source_ref, arguments.freeze_tag),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
