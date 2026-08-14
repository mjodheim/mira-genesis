"""Validate the frozen M092-B protocol and its exact M092-A dependency.

This checker performs no extension search and reads no qualification artifact. It establishes only
that the pre-search contract is closed, internally consistent, tied to the exact committed M092-A
seal and honest about the theorem/certificate/finite-evidence boundary.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROTOCOL = ROOT / "experiments" / "M092" / "PROTOCOL.json"

from metamorphosis.m092_kernel import INSTRUCTION_SET  # noqa: E402
from scripts.check_m092a_checkpoint import (  # noqa: E402
    M092ACheckpointError,
    verify_checkpoint,
)

TOP_LEVEL_KEYS = {
    "anti_cheating",
    "arm_requirements",
    "arms",
    "certificate_contract",
    "claim_boundary",
    "conditions",
    "date_frozen",
    "decision_slot",
    "dependency_matrix",
    "development_rehearsal",
    "downstream_language_contract",
    "falsifiers",
    "hypothesis",
    "integrity",
    "k1_frozen",
    "m092a_checkpoint",
    "milestone",
    "predecessors",
    "qualification",
    "registration_contract",
    "retry_policy",
    "rollback",
    "schema",
    "search",
    "status",
    "target_contract",
    "title",
    "track",
    "validation_contract",
    "verdict_rule",
}

ARMS = (
    "evolvable_substrate",
    "fixed_substrate",
    "substrate_acquisition_ablated",
    "proof_certificate_ablated",
    "extension_built_but_not_registered",
    "substrate_registered_downstream_not_registered",
    "registered_but_dependency_ablated",
    "qualification_use_ablated",
    "more_budget_same_substrate",
    "macro_only_substrate_extension",
    "fresh_agent",
)

CONDITIONS = (
    "P1_m092a_checkpoint_is_exact_and_predates_extension_search_and_qualification",
    "P2_inherited_registered_substrate_is_proved_unable_to_express_the_global_target",
    "P3_candidate_k1_program_is_generated_by_the_frozen_search_and_not_selected_from_authored_solutions",
    "P4_candidate_passes_structural_capability_and_anti_cheating_validation",
    "P5_candidate_carries_a_valid_global_correctness_termination_and_frame_certificate_bound_to_its_exact_program",
    "P6_independent_validation_receipt_is_recomputed_without_qualification_access",
    "P7_validated_operation_is_registered_as_executable_serialized_substrate_state",
    "P8_downstream_language_primitive_is_assembled_registered_and_depends_on_the_acquired_operation",
    "P9_required_transformation_is_outside_checkpoint_reach_and_inside_extended_reach",
    "P10_post_registration_qualification_shows_the_correctness_difference_with_certificate_and_empiricism_kept_distinct",
    "P11_every_fixed_budget_macro_registration_and_dependency_ablation_control_closes_nothing",
    "P12_one_acquired_operation_is_reused_by_composition_across_both_families_without_a_second_target_operation",
    "P13_rollback_is_byte_exact_and_behavioural_at_all_three_frozen_boundaries",
    "P14_extension_persists_in_a_fresh_isolated_process_with_track_a_chronology_and_zero_model_or_network_calls",
    "P15_attempt_provenance_artifact_bindings_and_the_conjunctive_verdict_are_recomputed_without_skip_paths",
)

CERTIFICATE_FIELDS = {
    "schema",
    "program_digest",
    "precondition",
    "control_flow_graph",
    "loop_invariants",
    "well_founded_variants",
    "inductive_steps",
    "termination_argument",
    "linear_step_bound",
    "postcondition",
    "frame_condition",
}

CHECKPOINT_COMMIT = "aa18d15b9a628e2f24fb963efd1d17b6e31cff61"
CHECKPOINT_DIGEST = "d8bacb1c94dd06da8ceb5ddf2c9a94f8d2bc8c598b307ea1171e3dc7dfc86ce8"
CHECKPOINT_BLOB = "fa41639b18160090289e8233e99a48c0fda7c5ce"
CHECKPOINT_BLOB_SHA256 = "9dabc86b43299f791c55bf0ebae1880344aed3f8a8c0c6223b7cfb3063919436"
CHECKPOINT_VERIFIER_BLOB = "1371f873b283fe51d0719eed88ccc7d034dd8f13"
CHECKPOINT_VERIFIER_SHA256 = "f71f7eaf968ba56b05201af04a2802eb1e0d2dd4e16675edc468728b4382764e"
SUBSTRATE_DIGEST = "296230ae97384d12b2371c3ff572ae38d87d771ad195ed8f97a6761eb2c84717"


class M092BProtocolError(RuntimeError):
    """The pre-search protocol is not the closed M092-B contract."""


def _git(*arguments: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", *arguments], cwd=ROOT, capture_output=True, check=check,
    )


def _blob(commit: str, path: str) -> tuple[str, bytes]:
    object_id = _git("rev-parse", f"{commit}:{path}").stdout.decode("ascii").strip()
    return object_id, _git("cat-file", "blob", object_id).stdout


def verify_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    problems: list[str] = []

    if set(value) != TOP_LEVEL_KEYS:
        problems.append("protocol fields differ from the closed schema")
    if value.get("schema") != "m092-endogenous-substrate-extension-protocol-v1":
        problems.append("unexpected protocol schema")
    if value.get("milestone") != "M092" or value.get("track") != "A":
        problems.append("milestone or epistemic track differs")
    if value.get("status") != "frozen_before_any_m092b_extension_search_or_qualification":
        problems.append("protocol is not frozen at the pre-search boundary")
    if value.get("hypothesis", {}).get("id") != "H38" or value.get("decision_slot") != "D062":
        problems.append("hypothesis or decision slot differs")

    if tuple(value.get("arms", ())) != ARMS:
        problems.append("arm list differs from the frozen order")
    if set(value.get("arm_requirements", {})) != set(ARMS):
        problems.append("arm requirements do not cover exactly the frozen arms")
    if tuple(value.get("conditions", ())) != CONDITIONS:
        problems.append("condition list differs from the frozen order")
    if len(set(CONDITIONS)) != 15:
        problems.append("conditions are not fifteen unique obligations")

    matrix = value.get("dependency_matrix", [])
    expected_matrix_ablations = {
        "substrate_acquisition_ablated",
        "proof_certificate_ablated",
        "extension_built_but_not_registered",
        "substrate_registered_downstream_not_registered",
        "registered_but_dependency_ablated",
        "qualification_use_ablated",
    }
    if len(matrix) != 6 or {row.get("ablation") for row in matrix} != expected_matrix_ablations:
        problems.append("dependency matrix does not cover every causal arrow exactly once")

    checkpoint = value.get("m092a_checkpoint", {})
    exact_checkpoint = {
        "checkpoint_commit": CHECKPOINT_COMMIT,
        "checkpoint_digest": CHECKPOINT_DIGEST,
        "checkpoint_git_blob_sha1": CHECKPOINT_BLOB,
        "checkpoint_blob_sha256": CHECKPOINT_BLOB_SHA256,
        "checkpoint_verifier_git_blob_sha1": CHECKPOINT_VERIFIER_BLOB,
        "checkpoint_verifier_blob_sha256": CHECKPOINT_VERIFIER_SHA256,
        "source_commit": "5adfaa671d242d1589d85985014dbd1c6f4bf2c8",
        "substrate_digest": SUBSTRATE_DIGEST,
        "verified_before_protocol_freeze": True,
    }
    if checkpoint != exact_checkpoint:
        problems.append("protocol does not bind the exact M092-A checkpoint")
    ancestry = _git(
        "merge-base", "--is-ancestor", CHECKPOINT_COMMIT, "HEAD", check=False,
    )
    if ancestry.returncode != 0:
        problems.append("M092-A checkpoint commit is not an ancestor of HEAD")
    for artifact_path, object_id, sha256 in (
        ("experiments/M092/CHECKPOINT_A.json", CHECKPOINT_BLOB, CHECKPOINT_BLOB_SHA256),
        ("scripts/check_m092a_checkpoint.py", CHECKPOINT_VERIFIER_BLOB,
         CHECKPOINT_VERIFIER_SHA256),
    ):
        try:
            observed_id, data = _blob(CHECKPOINT_COMMIT, artifact_path)
        except subprocess.CalledProcessError:
            problems.append(f"checkpoint dependency is missing: {artifact_path}")
            continue
        if observed_id != object_id or hashlib.sha256(data).hexdigest() != sha256:
            problems.append(f"checkpoint dependency differs: {artifact_path}")
    try:
        checkpoint_report = verify_checkpoint()
    except (M092ACheckpointError, OSError, ValueError) as error:
        problems.append(f"M092-A checkpoint no longer verifies: {error}")
    else:
        if checkpoint_report["checkpoint_digest"] != CHECKPOINT_DIGEST:
            problems.append("live checkpoint verifier returned another digest")

    kernel = value.get("k1_frozen", {})
    allowed = set(kernel.get("candidate_allowed_opcodes", []))
    forbidden = set(kernel.get("candidate_forbidden_opcodes", []))
    if allowed & forbidden or allowed | forbidden != set(INSTRUCTION_SET):
        problems.append("candidate opcode partition differs from the frozen K1 instruction set")
    if kernel.get("lower_kernel_is_authored_and_the_next_ceiling") is not True:
        problems.append("protocol hides the authored lower-kernel ceiling")

    certificate = value.get("certificate_contract", {})
    if set(certificate.get("required_fields", [])) != CERTIFICATE_FIELDS:
        problems.append("global certificate fields differ")
    for required in (
        "candidate_supplies_certificate",
        "independent_verifier_rechecks_against_program",
        "empirical_execution_is_separate_corroboration",
        "verifier_must_refuse_if_outside_the_accepted_logic",
    ):
        if certificate.get(required) is not True:
            problems.append(f"certificate obligation is not binding: {required}")
    if "every original_x >= 0" not in " ".join(certificate.get("required_proofs", [])):
        problems.append("certificate contract lacks an unbounded-domain obligation")

    search = value.get("search", {})
    if search.get("candidate_program_max_length") != 14:
        problems.append("candidate program bound differs")
    if search.get("candidate_literal_set") != [-1, 0, 1]:
        problems.append("candidate literal set differs")
    if search.get("candidate_cap") != 2_000_000 or search.get("deterministic_seed") != 9202:
        problems.append("candidate cap or deterministic seed differs")
    certificate_bounds = search.get("certificate_search_bounds", {})
    if certificate_bounds != {
        "affine_coefficient_inclusive_maximum": 4,
        "affine_coefficient_inclusive_minimum": -4,
        "certificates_examined_per_program_maximum": 4096,
        "constraints_per_loop_maximum": 8,
        "ghost_counters_maximum": 2,
        "loop_headers_maximum": 1,
        "total_certificates_examined_maximum": 2_000_000,
    }:
        problems.append("certificate search bounds differ")
    if search.get("search_failure_is_not_an_impossibility_proof") is not True:
        problems.append("search is being treated as the impossibility proof")
    if search.get("no_finished_candidate_catalogue") is not True:
        problems.append("protocol permits an authored candidate catalogue")

    target = value.get("target_contract", {})
    if target.get("system_authority_added") is not False or target.get(
        "operation_capabilities"
    ) != []:
        problems.append("target operation adds system authority")
    if "content-addressed" not in target.get("operation_key", ""):
        problems.append("target operation has an authored target name")

    registration = value.get("registration_contract", {})
    for required in (
        "built_but_not_registered_executes_substrate_a",
        "forbidden_capability_vocabulary_unchanged",
        "host_function_or_side_registry_forbidden",
        "operation_key_is_content_addressed",
        "permitted_capability_vocabulary_unchanged",
        "program_bytes_live_inside_the_registered_operation",
        "validated_program_digest_must_equal_registered_program_digest",
    ):
        if registration.get(required) is not True:
            problems.append(f"registration obligation is not binding: {required}")
    if registration.get("substrate_version_increment") != 1:
        problems.append("substrate version increment differs")

    downstream = value.get("downstream_language_contract", {})
    if downstream.get("acquired_primitive_count") != 1 or downstream.get(
        "body_max_length"
    ) != 4:
        problems.append("downstream acquisition count or body bound differs")
    if downstream.get("parameter_kinds") != ["slot", "input"]:
        problems.append("downstream primitive signature differs")
    for required in (
        "body_must_reference_the_acquired_substrate_key",
        "builder_may_not_execute_k1_directly",
        "registration_changes_the_serialized_language_digest",
    ):
        if downstream.get(required) is not True:
            problems.append(f"downstream obligation is not binding: {required}")

    validation = value.get("validation_contract", {})
    expected_receipt_fields = {
        "schema",
        "checkpoint_digest",
        "program_digest",
        "certificate_digest",
        "validator_blob_sha256",
        "structural_findings",
        "anti_cheating_findings",
        "global_proof_findings",
        "frame_findings",
        "accepted",
        "qualification_imported",
        "receipt_digest",
    }
    if set(validation.get("receipt_required_fields", [])) != expected_receipt_fields:
        problems.append("validation receipt fields differ")
    if validation.get("allowed_project_imports") != [
        "metamorphosis.m092_kernel",
        "metamorphosis.m092_runtime",
    ]:
        problems.append("independent validator import boundary differs")
    for required in (
        "candidate_builder_import_forbidden",
        "fresh_process_required",
        "qualification_modules_and_artifacts_forbidden",
        "result_checker_recomputes_receipt_from_exact_program_and_certificate",
        "verifier_may_not_repair_or_complete_a_certificate",
    ):
        if validation.get(required) is not True:
            problems.append(f"validation obligation is not binding: {required}")

    qualification = value.get("qualification", {})
    if qualification.get("theorem_certificate_and_empirical_fields_are_separate") is not True:
        problems.append("qualification conflates proof and finite execution")
    if qualification.get("fixed_arm_passing_is_a_falsification_not_an_explanation") is not True:
        problems.append("fixed-arm success is not treated as a falsification")
    if qualification.get("materialized_after_protocol_freeze_and_after_extended_state_exists") is not True:
        problems.append("qualification chronology is not post-freeze and post-extension")
    if qualification.get("hidden_instances_per_family") != 6 or qualification.get(
        "hidden_value_domain"
    ) != {
        "inclusive_maximum": 9999,
        "inclusive_minimum": 3000,
        "stratification": (
            "three even and three odd values per family, with stratum order derived from the "
            "family-domain-separated digest"
        ),
    }:
        problems.append("hidden qualification domain or stratification differs")
    if "SHA-256" not in qualification.get("draw_algorithm", ""):
        problems.append("qualification draw algorithm is not fixed")

    if any(value.get("claim_boundary", {}).values()):
        problems.append("protocol makes a forbidden result or generality claim")
    integrity = value.get("integrity", {})
    if integrity.get("model_calls_during_qualification") != 0 or integrity.get(
        "network_calls_during_qualification"
    ) != 0:
        problems.append("protocol permits a model or network call during qualification")
    if integrity.get("checker_skip_flags_forbidden") is not True:
        problems.append("protocol permits a decisive checker skip path")
    if integrity.get("m093_not_implemented") is not True:
        problems.append("protocol crosses into M093")

    attribute = _git("check-attr", "eol", "--", "experiments/M092/PROTOCOL.json").stdout
    if not attribute.decode("utf-8").rstrip().endswith(": lf"):
        problems.append("protocol blob is not protected as canonical LF")
    register = (ROOT / "IP_ASSET_REGISTER.md").read_text(encoding="utf-8")
    if "| P-008 | M092 /" not in register or "PUBLIC_AGPL_COMMERCIAL_OPTION" not in register:
        problems.append("M092 public disposition P-008 is absent")

    if problems:
        raise M092BProtocolError("; ".join(problems))
    return {
        "status": "verified",
        "checkpoint_digest": CHECKPOINT_DIGEST,
        "arms": len(ARMS),
        "conditions": len(CONDITIONS),
        "dependency_arrows": len(matrix),
        "candidate_cap": search["candidate_cap"],
        "qualification_read": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    arguments = parser.parse_args()
    try:
        report = verify_protocol(arguments.protocol)
    except (M092BProtocolError, OSError, ValueError, json.JSONDecodeError) as error:
        print(str(error))
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
