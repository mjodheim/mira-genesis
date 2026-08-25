"""Build the M109 candidate and final protocol without running qualification.

M109 follows the binding scheme M108 established, and for the same reason. M107 pinned its bound
bytes with milestone-local `.gitattributes` files in `metamorphosis/`, `scripts/` and `tests/`, and
bound those files; git reads at most one attribute file per directory, so binding one in a shared
directory locks that directory for every later milestone. M109's sources sit in those same
directories.

So JSON evidence is bound by its exact bytes, where digests genuinely depend on them and the
repository-wide `experiments/M1*/*.json -text` rule already makes them identical everywhere; Python
and Markdown members are bound by SHA-256 over LF-normalized content. The mode is recorded per
member, so a third party recomputes exactly what was frozen and never has to guess.

The owner authorization is an explicit input rather than a constant in this file, as M108 made it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "M109"
CANDIDATE_PATH = EXPERIMENT / "PROTOCOL_CANDIDATE.json"
PROTOCOL_PATH = EXPERIMENT / "PROTOCOL.json"
EXPECTED_PREDICATES = ["P%d" % index for index in range(1, 19)]

RAW_BYTE_SUFFIXES = frozenset({".json"})

APPARATUS_FILES = sorted(
    {
        # M109 owns this attribute file; no earlier frozen protocol binds it.
        "experiments/M109/.gitattributes",
        "experiments/M109/README.md",
        "experiments/M109/PRE_REGISTRATION.md",
        "experiments/M109/ADVERSARIAL_REVIEW.md",
        "experiments/M109/DEMAND_STAGE1.json",
        "experiments/M109/DEMAND_STAGE2.json",
        "metamorphosis/m109_runtime.py",
        "scripts/run_m109_process.py",
        "scripts/run_m109_qualification.py",
        "scripts/check_m109_result.py",
        "scripts/audit_m109_boundaries.py",
        "scripts/author_m109_curriculum.py",
        "scripts/build_m109_protocol.py",
        "tests/test_m109_recursive_depth.py",
    }
)


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("ascii")).hexdigest()


def digest_mode(path: str) -> str:
    return "raw" if Path(path).suffix in RAW_BYTE_SUFFIXES else "lf_normalized"


def member_digest(root: Path, path: str) -> str:
    raw = (root / path).read_bytes()
    if digest_mode(path) == "lf_normalized":
        raw = raw.replace(b"\r\n", b"\n")
    return hashlib.sha256(raw).hexdigest()


def bound_files(root: Path = ROOT) -> dict[str, Any]:
    members = {path: member_digest(root, path) for path in APPARATUS_FILES}
    modes = {path: digest_mode(path) for path in APPARATUS_FILES}
    return {
        "files": APPARATUS_FILES,
        "member_digests": members,
        "member_digest_modes": modes,
        "digest": digest(members),
    }


def _git(*arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments], cwd=ROOT, capture_output=True, text=True, check=False
    )
    if completed.returncode != 0:
        raise ValueError(completed.stderr.strip() or "git command failed")
    return completed.stdout.strip()


def _require_annotated_tag(reference: str, expected_commit: str) -> None:
    if _git("cat-file", "-t", reference) != "tag":
        raise ValueError("%s is not an annotated tag" % reference)
    if _git("rev-list", "-n", "1", reference) != expected_commit:
        raise ValueError("%s does not bind the expected commit" % reference)


def candidate(source_ref: str, authorization: dict[str, Any]) -> dict[str, Any]:
    stage1 = json.loads((EXPERIMENT / "DEMAND_STAGE1.json").read_text(encoding="ascii"))
    stage2 = json.loads((EXPERIMENT / "DEMAND_STAGE2.json").read_text(encoding="ascii"))
    payload: dict[str, Any] = {
        "schema": "m109-protocol-candidate-v1",
        "milestone": "M109",
        "hypothesis": "H54",
        "decision_slot": "D078",
        "status": "owner_authorized_candidate_not_finally_frozen",
        "candidate_source_ref": source_ref,
        "stage_one_digest": stage1["stage_digest"],
        "stage_two_digest": stage2["stage_digest"],
        "predecessor": {
            "milestone": "M108",
            "decision_slot": "D077",
            "substrate_imported_unchanged": True,
        },
        "machinery": {
            "component_registry": ["operator_table", "signal_interface", "candidate_space"],
            "failure_features": [
                "demand_needs_an_unread_signal",
                "candidate_search_exhausted_for_this_demand",
                "operator_axis_progress_available",
            ],
            "rules_form_an_ordered_cascade": True,
            "adoption_is_conservative": True,
            "blame_labels_are_lineage_determined": True,
            "trial_semantics": "minimal_necessary_component",
            "trials_forbidden_at_resolution_time": True,
            "attribution_domain_rows": [1, 2, 3, 6, 7],
            "attribution_domain_unreachable_rows": [0, 4, 5],
            "rule_space_is_the_lineage_own_image": True,
            "max_machinery_generations": 2,
        },
        "world": {
            "signals": 3,
            "base_signal_width": 2,
            "max_signal_width": 3,
            "base_candidate_space": "monotone",
            "node_bound": 9,
            "deeper_control_bound": 13,
            "machinery_step_budget": 1,
            "reach_improve_budget": 2,
            "probe_state_family": 84,
            "world_function_count": 256,
            "curriculum_is_staged": True,
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
        "verdict_rule": "positive_iff_P1_through_P18_all_computed_true_else_negative",
        "canonical_result_policy": {
            "canonical_attempts": 1,
            "canonical_checker_attempts": 1,
            "exclusive_create": True,
            "preserve_first_result_even_if_negative": True,
            "repair_after_result_forbidden": True,
        },
        "owner_workflow_authorization": authorization,
        "governance_constraints": {
            "descendants_are_disposable": True,
            "fixed_budget": True,
            "network_access": False,
            "credentials": False,
            "deployment_access": False,
            "self_granted_permissions": False,
            "evaluator_modification": False,
            "self_granted_merge_or_release_authority": False,
            "persistence_outside_declared_stores": False,
            "constraints_are_part_of_the_claim": True,
        },
        "declared_limitations": {
            "registry_feature_vocabulary_and_curriculum_remain_authored": True,
            "conservative_adoption_is_load_bearing_for_the_positive_half": True,
            "recursive_depth_of_three_is_not_addressed": True,
            "acceleration_is_not_measured": True,
        },
        "canonical_run_allowed": False,
        "separate_final_freeze_required": True,
        "model_calls_allowed": 0,
        "network_calls_allowed": 0,
        "remote_execution_calls_allowed": 0,
        "claim_if_positive": "two_successive_lineage_acquired_machinery_generations_with_a_strict_reach_chain",
        "next_ceiling_if_positive": "recursive_depth_of_three_and_measured_acceleration",
    }
    payload["candidate_digest"] = digest(payload)
    return payload


def final_protocol(
    candidate_value: dict[str, Any], source_ref: str, freeze_tag: str
) -> dict[str, Any]:
    candidate_payload = {
        key: value for key, value in candidate_value.items() if key != "candidate_digest"
    }
    if candidate_value.get("candidate_digest") != digest(candidate_payload):
        raise ValueError("M109 candidate digest mismatch")
    payload: dict[str, Any] = {
        "schema": "m109-protocol-v1",
        "milestone": "M109",
        "hypothesis": "H54",
        "decision_slot": "D078",
        "status": "frozen_protocol_owner_authorized",
        "source_ref": source_ref,
        "freeze_tag": freeze_tag,
        "protocol_candidate": {
            "candidate_digest": candidate_value["candidate_digest"],
            "raw_sha256": hashlib.sha256(CANDIDATE_PATH.read_bytes()).hexdigest(),
            "candidate_source_ref": candidate_value["candidate_source_ref"],
        },
        "stage_one_digest": candidate_value["stage_one_digest"],
        "stage_two_digest": candidate_value["stage_two_digest"],
        "predecessor": candidate_value["predecessor"],
        "machinery": candidate_value["machinery"],
        "world": candidate_value["world"],
        "bound_files": candidate_value["bound_files"],
        "canonical_runtime": candidate_value["canonical_runtime"],
        "decisive_conditions": candidate_value["decisive_conditions"],
        "verdict_rule": candidate_value["verdict_rule"],
        "canonical_result_policy": candidate_value["canonical_result_policy"],
        "owner_workflow_authorization": candidate_value["owner_workflow_authorization"],
        "governance_constraints": candidate_value["governance_constraints"],
        "declared_limitations": candidate_value["declared_limitations"],
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
    candidate_parser.add_argument("--owner-authorization-date", required=True)
    candidate_parser.add_argument("--owner-authorization-scope", required=True)
    final_parser = subparsers.add_parser("final")
    final_parser.add_argument("--source-ref", required=True)
    final_parser.add_argument("--freeze-tag", required=True)
    arguments = parser.parse_args()
    if _git("status", "--porcelain"):
        raise SystemExit("M109 protocol build requires a clean worktree")
    head = _git("rev-parse", "HEAD")
    _require_annotated_tag(arguments.source_ref, head)
    if arguments.command == "candidate":
        if CANDIDATE_PATH.exists() or PROTOCOL_PATH.exists():
            raise SystemExit("M109 candidate or final protocol already exists")
        _write_exclusive(
            CANDIDATE_PATH,
            candidate(
                arguments.source_ref,
                {
                    "recorded": True,
                    "date": arguments.owner_authorization_date,
                    "scope": arguments.owner_authorization_scope,
                    "recorded_as_explicit_input": True,
                },
            ),
        )
        return 0
    if PROTOCOL_PATH.exists() or not CANDIDATE_PATH.exists():
        raise SystemExit("M109 final protocol state is invalid")
    candidate_value = json.loads(CANDIDATE_PATH.read_text(encoding="ascii"))
    _write_exclusive(
        PROTOCOL_PATH,
        final_protocol(candidate_value, arguments.source_ref, arguments.freeze_tag),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
