"""Build the M111 candidate and final protocol without running qualification.

M111 follows the binding scheme M108, M109 and M110 established. JSON evidence is bound by its exact
bytes, where digests genuinely depend on them and the repository-wide `experiments/M1*/*.json -text`
rule already makes them identical everywhere; Python and Markdown members are bound by SHA-256 over
LF-normalized content, because `metamorphosis/`, `scripts/` and `tests/` each carry an attribute file
bound by M107 and git reads at most one attribute file per directory. The mode is recorded per member.

Two predecessor results are bound as members. `experiments/M109/RESULT.json` is where the lineage
states are restored from, including the terminal state that already holds the non-monotone operator
generation 2 adopted; `experiments/M110/RESULT.json` is the carrier result this milestone continues
from. A functionally equivalent rebuild of either would end the chain rather than continue it.

The owner authorization is an explicit input rather than a constant in this file.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "M111"
CANDIDATE_PATH = EXPERIMENT / "PROTOCOL_CANDIDATE.json"
PROTOCOL_PATH = EXPERIMENT / "PROTOCOL.json"
POPULATION_PATH = EXPERIMENT / "POPULATION.json"
MACHINERY_RESULT = ROOT / "experiments" / "M109" / "RESULT.json"
CARRIER_RESULT = ROOT / "experiments" / "M110" / "RESULT.json"
EXPECTED_PREDICATES = ["P%d" % index for index in range(1, 25)]

RAW_BYTE_SUFFIXES = frozenset({".json", ".gitattributes"})

APPARATUS_FILES = sorted(
    {
        # M111 owns this attribute file; no earlier frozen protocol binds it.
        "experiments/M111/.gitattributes",
        "experiments/M111/README.md",
        "experiments/M111/PRE_REGISTRATION.md",
        "experiments/M111/ADVERSARIAL_REVIEW.md",
        "experiments/M111/PRE_FREEZE_REHEARSAL.md",
        "experiments/M111/POPULATION.json",
        "experiments/M111/ADMISSION_LOG.json",
        # The two predecessor results the restored lineage is read from.
        "experiments/M109/RESULT.json",
        "experiments/M110/RESULT.json",
        "metamorphosis/m111_runtime.py",
        "scripts/run_m111_process.py",
        "scripts/run_m111_qualification.py",
        "scripts/check_m111_result.py",
        "scripts/audit_m111_boundaries.py",
        "scripts/author_m111_population.py",
        "scripts/build_m111_protocol.py",
        "tests/test_m111_self_diagnosis.py",
    }
)


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("ascii")).hexdigest()


def digest_mode(path: str) -> str:
    suffix = Path(path).suffix or Path(path).name
    return "raw" if suffix in RAW_BYTE_SUFFIXES else "lf_normalized"


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
    population = json.loads(POPULATION_PATH.read_text(encoding="ascii"))
    machinery_raw = MACHINERY_RESULT.read_bytes()
    carrier_raw = CARRIER_RESULT.read_bytes()
    machinery = json.loads(machinery_raw.decode("ascii"))
    carrier = json.loads(carrier_raw.decode("ascii"))
    terminal = machinery["scientific_evidence"]["stage_two_resolution"]
    payload: dict[str, Any] = {
        "schema": "m111-protocol-candidate-v1",
        "milestone": "M111",
        "hypothesis": "H56",
        "decision_slot": "D080",
        "status": "owner_authorized_candidate_not_finally_frozen",
        "candidate_source_ref": source_ref,
        "population_digest": population["population_digest"],
        "population_ambiguous_world_digests": [
            item["world_digest"] for item in population["ambiguous_worlds"]
        ],
        "population_witness_world_digests": [
            item["world_digest"] for item in population["witness_worlds"]
        ],
        "predecessors": {
            "machinery": {
                "milestone": "M109",
                "decision_slot": "D078",
                "result_digest": machinery["result_digest"],
                "result_raw_sha256": hashlib.sha256(machinery_raw).hexdigest(),
                "terminal_state_digest": terminal["final_state_digest"],
                "terminal_candidate_space": terminal["final_candidate_space"],
            },
            "carrier": {
                "milestone": "M110",
                "decision_slot": "D079",
                "result_digest": carrier["result_digest"],
                "result_raw_sha256": hashlib.sha256(carrier_raw).hexdigest(),
            },
            "states_restored_not_reimplemented": True,
        },
        "registry": {
            "components": [
                "operator_table",
                "signal_interface",
                "candidate_space",
                "diagnostic_policy",
            ],
            "fourth_component_is_new_in_m111": True,
            "failure_features": [
                "demand_needs_an_unread_signal",
                "candidate_search_exhausted_for_this_demand",
                "operator_axis_progress_available",
            ],
            "feature_vocabulary_unchanged_since_m108": True,
        },
        "impossibility": {
            "kind": "exhibited_information_bound",
            "ambiguous_row": 3,
            "upper_row": 7,
            "two_demands_share_one_feature_row_and_differ_in_component": True,
            "no_function_of_the_features_is_right_on_both": True,
            "monotone_rule_space_size": 18,
            "separating_programs_in_the_monotone_space": 0,
            "lower_row_below_upper_row_componentwise": True,
        },
        "probe": {
            "definition": "extend_one_component_test_constructibility_then_roll_back",
            "is_an_adoption": False,
            "rollback_is_measured_by_serialized_bytes": True,
            "budget_per_world": 1,
            "orders_measured": ["candidates_first", "signals_first"],
        },
        "arms": {
            "static": ["M0", "M1", "M2", "always_signal"],
            "diagnostic_forces": ["policy", "never", "always"],
            "sequences": [
                "determined_then_A",
                "determined_then_B",
                "A_then_determined",
                "B_then_determined",
            ],
            "arms_share_one_adapter": True,
        },
        "population_admission": {
            "criterion_mentions_structure_only": True,
            "criterion": [
                "the_only_ambiguous_base_state_row_is_row_three",
                "rows_one_and_seven_are_present_and_determined_at_the_base_state",
                "two_targets_at_row_three_resolve_through_different_components",
            ],
            "labels_are_measured_not_required": True,
            "row_seven_is_required_because_the_lemma_needs_it": True,
            "development_seed_range": [2000, 2999],
            "canonical_seed_range": [3000, 3999],
        },
        "consumer_family": {
            "inherited_unchanged_from": "M110",
            "carrier": "reference_bearing_json_documents_with_a_side_table",
            "value_chain": [0, 1, 2, 3],
            "documents_per_world": 5,
            "node_bound": 9,
        },
        "bound_files": bound_files(),
        "canonical_runtime": {
            "python": {"implementation": "cpython", "version_info": [3, 11, 16]},
        },
        "decisive_conditions": EXPECTED_PREDICATES,
        "verdict_rule": "positive_iff_P1_through_P24_all_computed_true_else_negative",
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
            "registry_probe_primitive_and_budget_remain_authored": True,
            "consumer_family_is_project_authored": True,
            "population_is_selected_for_ambiguity_by_design": True,
            "the_policy_fires_on_an_unreachable_row_as_well": True,
            "elimination_is_complete_because_only_two_candidates_remain": True,
            "acceleration_is_measured_but_not_claimed": True,
            "g1_to_g10_do_not_advance": True,
        },
        "canonical_run_allowed": False,
        "separate_final_freeze_required": True,
        "model_calls_allowed": 0,
        "network_calls_allowed": 0,
        "remote_execution_calls_allowed": 0,
        "claim_if_positive": "bounded_self_directed_diagnosis_and_acquisition_machinery_adaptation_at_recursive_depth_three",
        "next_ceiling_if_positive": "an_independently_authored_consumer_family_and_a_bottleneck_the_registry_does_not_already_name",
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
        raise ValueError("M111 candidate digest mismatch")
    payload: dict[str, Any] = {
        "schema": "m111-protocol-v1",
        "milestone": "M111",
        "hypothesis": "H56",
        "decision_slot": "D080",
        "status": "frozen_protocol_owner_authorized",
        "source_ref": source_ref,
        "freeze_tag": freeze_tag,
        "protocol_candidate": {
            "candidate_digest": candidate_value["candidate_digest"],
            "raw_sha256": hashlib.sha256(CANDIDATE_PATH.read_bytes()).hexdigest(),
            "candidate_source_ref": candidate_value["candidate_source_ref"],
        },
        "population_digest": candidate_value["population_digest"],
        "population_ambiguous_world_digests": candidate_value[
            "population_ambiguous_world_digests"
        ],
        "population_witness_world_digests": candidate_value[
            "population_witness_world_digests"
        ],
        "predecessors": candidate_value["predecessors"],
        "registry": candidate_value["registry"],
        "impossibility": candidate_value["impossibility"],
        "probe": candidate_value["probe"],
        "arms": candidate_value["arms"],
        "consumer_family": candidate_value["consumer_family"],
        "population_admission": candidate_value["population_admission"],
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
        raise SystemExit("M111 protocol build requires a clean worktree")
    head = _git("rev-parse", "HEAD")
    _require_annotated_tag(arguments.source_ref, head)
    if arguments.command == "candidate":
        if CANDIDATE_PATH.exists() or PROTOCOL_PATH.exists():
            raise SystemExit("M111 candidate or final protocol already exists")
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
        raise SystemExit("M111 final protocol state is invalid")
    candidate_value = json.loads(CANDIDATE_PATH.read_text(encoding="ascii"))
    _write_exclusive(
        PROTOCOL_PATH,
        final_protocol(candidate_value, arguments.source_ref, arguments.freeze_tag),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
