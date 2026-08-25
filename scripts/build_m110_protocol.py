"""Build the M110 candidate and final protocol without running qualification.

M110 follows the binding scheme M108 and M109 established. JSON evidence is bound by its exact bytes,
where digests genuinely depend on them and the repository-wide `experiments/M1*/*.json -text` rule
already makes them identical everywhere; Python and Markdown members are bound by SHA-256 over
LF-normalized content, because `metamorphosis/`, `scripts/` and `tests/` each carry an attribute file
bound by M107 and git reads at most one attribute file per directory. The mode is recorded per member.

`experiments/M109/RESULT.json` is bound as a member. The whole milestone depends on those exact
bytes: they are where the rule cascade is restored from, and a functionally equivalent rebuild of
M109 would end the generational chain rather than continue it.

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
EXPERIMENT = ROOT / "experiments" / "M110"
CANDIDATE_PATH = EXPERIMENT / "PROTOCOL_CANDIDATE.json"
PROTOCOL_PATH = EXPERIMENT / "PROTOCOL.json"
POPULATION_PATH = EXPERIMENT / "POPULATION.json"
PRODUCER_RESULT = ROOT / "experiments" / "M109" / "RESULT.json"
EXPECTED_PREDICATES = ["P%d" % index for index in range(1, 25)]

RAW_BYTE_SUFFIXES = frozenset({".json", ".gitattributes"})

APPARATUS_FILES = sorted(
    {
        # M110 owns this attribute file; no earlier frozen protocol binds it.
        "experiments/M110/.gitattributes",
        "experiments/M110/README.md",
        "experiments/M110/PRE_REGISTRATION.md",
        "experiments/M110/ADVERSARIAL_REVIEW.md",
        "experiments/M110/PRE_FREEZE_REHEARSAL.md",
        "experiments/M110/POPULATION.json",
        "experiments/M110/ADMISSION_LOG.json",
        # The producer bytes the restored cascade is read from.
        "experiments/M109/RESULT.json",
        "metamorphosis/m110_runtime.py",
        "scripts/run_m110_process.py",
        "scripts/run_m110_qualification.py",
        "scripts/check_m110_result.py",
        "scripts/audit_m110_boundaries.py",
        "scripts/author_m110_population.py",
        "scripts/build_m110_protocol.py",
        "tests/test_m110_cross_domain_transfer.py",
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
    producer_bytes = hashlib.sha256(PRODUCER_RESULT.read_bytes()).hexdigest()
    producer = json.loads(PRODUCER_RESULT.read_text(encoding="ascii"))
    payload: dict[str, Any] = {
        "schema": "m110-protocol-candidate-v1",
        "milestone": "M110",
        "hypothesis": "H55",
        "decision_slot": "D079",
        "status": "owner_authorized_candidate_not_finally_frozen",
        "candidate_source_ref": source_ref,
        "population_digest": population["population_digest"],
        "population_world_digests": [item["world_digest"] for item in population["worlds"]],
        "predecessor": {
            "milestone": "M109",
            "decision_slot": "D078",
            "result_digest": producer["result_digest"],
            "result_raw_sha256": producer_bytes,
            "substrate_imported_unchanged": True,
            "cascade_restored_not_reimplemented": True,
        },
        "transferred_content": {
            "what_transfers": "the_rule_cascade_only",
            "restored_from": "experiments/M109/RESULT.json",
            "verified_by": "reproduction_of_the_frozen_m1_and_m2_state_digests",
            "attribution_executed_by": "m109_runtime.attribute",
        },
        "shared_authored_vocabulary": {
            "component_registry": ["operator_table", "signal_interface", "candidate_space"],
            "failure_features": [
                "demand_needs_an_unread_signal",
                "candidate_search_exhausted_for_this_demand",
                "operator_axis_progress_available",
            ],
            "imported_from_the_producer_module": True,
            "excluded_from_the_claim": True,
        },
        "consumer_family": {
            "carrier": "reference_bearing_json_documents_with_a_side_table",
            "value_chain": [0, 1, 2, 3],
            "documents_per_world": 5,
            "target_space_per_world": 1024,
            "visible_fields": ["alpha", "beta", "gamma"],
            "latent_field_reached_only_by_an_accessor": "zeta",
            "held_operators": ["MIN", "MAX"],
            "base_interface_width": 2,
            "max_interface_width": 3,
            "base_candidate_space": "monotone",
            "node_bound": 9,
            "deeper_control_bound": 13,
            "fixed_point_bounds": [7, 9, 11, 13],
            "machinery_step_budget": 1,
            "reach_improve_budget": 2,
            "probe_state_family": 4,
            "second_execution_path": "expression_rendered_as_python_compiled_and_executed",
        },
        "geometry": {
            "producer_reachable_rows": list(
                producer["scientific_evidence"]["domain"]["rows"]
            ),
            "producer_unreachable_rows": list(
                producer["scientific_evidence"]["domain"]["unreachable_rows"]
            ),
            "row_five_is_unreachable_in_the_producer": True,
            "row_five_is_reachable_in_the_consumer_by_the_reference_edge": True,
            "conservative_adoption_never_pinned_row_five": True,
        },
        "posed_rows": {
            "inside_producer_census": [7, 3],
            "outside_producer_census": [5],
            "conservation": [1],
            "demand_selection_rule": "lexicographically_least_determined_target_at_the_base_state",
        },
        "population_admission": {
            "criterion_mentions_structure_only": True,
            "criterion": [
                "census_complete_over_every_target_and_probe_state",
                "no_ambiguous_feature_row",
                "rows_3_5_and_7_present_with_a_determined_label_at_the_base_state",
            ],
            "labels_are_measured_not_required": True,
            "development_seed_range": [0, 999],
            "canonical_seed_range": [1000, 1999],
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
            "consumer_family_is_project_authored_not_independently_maintained": True,
            "registry_and_feature_vocabulary_are_shared_authored_vocabulary": True,
            "consumer_family_was_chosen_to_reach_row_five": True,
            "host_can_widen_either_component_directly": True,
            "candidate_space_step_widens_then_searches": True,
            "one_canonical_demand_per_row_per_world": True,
            "g4_does_not_advance_to_independent_transfer": True,
            "recursive_depth_of_three_is_not_addressed": True,
            "acceleration_is_not_measured": True,
        },
        "canonical_run_allowed": False,
        "separate_final_freeze_required": True,
        "model_calls_allowed": 0,
        "network_calls_allowed": 0,
        "remote_execution_calls_allowed": 0,
        "claim_if_positive": "bounded_multi_generation_acquisition_machinery_improvement_with_census_conditional_causal_transfer",
        "next_ceiling_if_positive": "independently_authored_consumer_family_and_self_directed_diagnosis_of_the_limiting_component",
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
        raise ValueError("M110 candidate digest mismatch")
    payload: dict[str, Any] = {
        "schema": "m110-protocol-v1",
        "milestone": "M110",
        "hypothesis": "H55",
        "decision_slot": "D079",
        "status": "frozen_protocol_owner_authorized",
        "source_ref": source_ref,
        "freeze_tag": freeze_tag,
        "protocol_candidate": {
            "candidate_digest": candidate_value["candidate_digest"],
            "raw_sha256": hashlib.sha256(CANDIDATE_PATH.read_bytes()).hexdigest(),
            "candidate_source_ref": candidate_value["candidate_source_ref"],
        },
        "population_digest": candidate_value["population_digest"],
        "population_world_digests": candidate_value["population_world_digests"],
        "predecessor": candidate_value["predecessor"],
        "transferred_content": candidate_value["transferred_content"],
        "shared_authored_vocabulary": candidate_value["shared_authored_vocabulary"],
        "consumer_family": candidate_value["consumer_family"],
        "geometry": candidate_value["geometry"],
        "posed_rows": candidate_value["posed_rows"],
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
        raise SystemExit("M110 protocol build requires a clean worktree")
    head = _git("rev-parse", "HEAD")
    _require_annotated_tag(arguments.source_ref, head)
    if arguments.command == "candidate":
        if CANDIDATE_PATH.exists() or PROTOCOL_PATH.exists():
            raise SystemExit("M110 candidate or final protocol already exists")
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
        raise SystemExit("M110 final protocol state is invalid")
    candidate_value = json.loads(CANDIDATE_PATH.read_text(encoding="ascii"))
    _write_exclusive(
        PROTOCOL_PATH,
        final_protocol(candidate_value, arguments.source_ref, arguments.freeze_tag),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
