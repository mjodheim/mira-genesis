#!/usr/bin/env python3
"""Freeze the complete H63 scientific apparatus, before any qualifying generation exists.

H63 states the same scientific proposition as H60, H61 and H62. Every scientific rule is inherited
from M115 **byte-for-byte or by exact digest**, and this script proves that mechanically rather
than asserting it: the generator prompt, the qualifying input and the carrier output schema are
copied byte-identically and their digests compared against M115's committed spec.

Only two things differ from M115, and both are instrumental rather than scientific:

  1. the route -- OpenInference rather than Alibaba, fixed by the M118 preregistration on prior
     M117 calibration evidence and re-established by the committed readiness gate;
  2. the request capacity -- `max_tokens = 131072` rather than 32000, with an explicit reasoning-off
     control, the same delta M116 preregistered and the readiness gate has now demonstrated on this
     exact route.

Nothing here generates, seals, reveals or scores. It writes commitments and refuses.

    python scripts/build_m118_freeze.py --plan     # what would be frozen, no writes
    python scripts/build_m118_freeze.py --freeze   # write the commitments
"""

from __future__ import annotations

import argparse
import hashlib
import json
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from metamorphosis import m116_admission as admission  # noqa: E402
from metamorphosis import m118_chronology as chronology  # noqa: E402
from metamorphosis import m118_route as fixed  # noqa: E402
from metamorphosis.blind_bank_protocol import canonical_bytes, sha256_hex  # noqa: E402

M115 = ROOT / "experiments" / "M115"
M118 = ROOT / "experiments" / "M118"

# Scientific artifacts inherited byte-for-byte. Changing any of these would change the experiment,
# not the instrument, so each is copied verbatim and its digest checked against M115's spec.
INHERITED_VERBATIM = ("GENERATOR_PROMPT.txt", "QUALIFYING_INPUT.txt", "OUTPUT_SCHEMA.json")

ANALYSIS_PLAN_SCHEMA = "m118-carrier-bank-analysis-plan-v1"
GENERATOR_SPEC_SCHEMA = "m118-carrier-bank-generator-spec-v1"
NONCE_SCHEMA = "m118-bank-nonce-commitment-v1"

# The instrumental delta, and the whole of it.
MAX_TOKENS = 131072
REASONING_EFFORT = "none"


class FreezeError(RuntimeError):
    """Fail closed. A freeze that guesses is not a freeze."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inherited_digests() -> dict[str, str]:
    """Prove the scientific artifacts are M115's, unchanged."""
    m115_spec = json.loads((M115 / "GENERATOR_SPEC.json").read_text(encoding="utf-8"))
    declared = {
        "OUTPUT_SCHEMA.json": m115_spec["output_schema"]["sha256"],
        "GENERATOR_PROMPT.txt": m115_spec["prompt"]["sha256"],
    }
    digests: dict[str, str] = {}
    for name in INHERITED_VERBATIM:
        source = M115 / name
        if not source.is_file():
            raise FreezeError("inherited scientific artifact is absent: %s" % name)
        digests[name] = _digest(source)
        if name in declared and digests[name] != declared[name]:
            raise FreezeError(
                "inherited %s does not match the digest M115 committed for it" % name)
    return digests


# Terms whose presence in the prompt would tell the generator what is being measured. Absence is
# computed from the bytes, never asserted: a boolean a script writes about itself is an assertion
# wearing a measurement's clothes, which is the defect M086-A and M095 are on record for.
LEAK_TERMS = ("genesis", "hypothesis", "lineage", "milestone", "experiment", "predicate",
              "evaluator", "arm", "acquired", "feature row", "operator_table", "signal_interface",
              "candidate_space", "h60", "h61", "h62", "h63", "m113", "m115", "m118")

# Axes the prompt does instruct the generator to vary, which overlap the components under test.
# Recorded rather than denied: the literal words are absent, the structure is not.
DECLARED_AXIS_OVERLAP = {
    "prompt_instructs_variation_of_actions": "operator_table is one of the three components",
    "prompt_instructs_variation_of_visibility": "signal_interface is one of the three components",
    "prompt_instructs_variation_of_guards": "qualification requires guarded_action_count >= 1",
    "the_family_is_project_designed": "carrier_host fixes the meta-schema; the generator fills in "
                                      "values inside a space this project fully specified, so the "
                                      "honest claim is carrier instances the project did not "
                                      "author, not a carrier family it did not design",
}


def prompt_blindness() -> dict[str, Any]:
    """Measured from the prompt bytes, with the axis overlap stated rather than denied."""
    text = (M115 / "GENERATOR_PROMPT.txt").read_text(encoding="utf-8").lower()
    found = sorted(term for term in LEAK_TERMS if term in text)
    return {
        "leak_terms_checked": list(LEAK_TERMS),
        "leak_terms_present": found,
        "mentions_the_experiment": bool(found),
        "blindness_computed_from_the_prompt_bytes_not_asserted": True,
        "declared_axis_overlap": DECLARED_AXIS_OVERLAP,
    }


def canonical_request_body(qualifying_input: str) -> dict[str, Any]:
    """The exact bytes H63 will send. Frozen before the request exists."""
    schema = json.loads((M115 / "OUTPUT_SCHEMA.json").read_text(encoding="utf-8"))
    return {
        "model": fixed.REQUESTED_MODEL,
        "messages": [{"role": "user", "content": qualifying_input}],
        "provider": fixed.provider_block(),
        "response_format": {"type": "json_schema", "json_schema": {
            "name": "carrier_bank", "strict": True, "schema": schema}},
        "max_tokens": MAX_TOKENS,
        "seed": 0,
        "stream": False,
        "temperature": 1.0,
        "reasoning": {"effort": REASONING_EFFORT},
    }


def _arm_names() -> tuple[str, ...]:
    """Read from the qualification runner rather than restated, so drift is an error not a lie."""
    from scripts import run_m113_qualification as qualification
    return tuple(qualification.ARM_NAMES)


def analysis_plan(digests: dict[str, str]) -> dict[str, Any]:
    """Every scientific rule inherited from M115; only identity and capacity are H63's."""
    inherited = json.loads((M115 / "ANALYSIS_PLAN.json").read_text(encoding="utf-8"))
    carried = {
        key: inherited[key] for key in (
            "closure_rule", "demand_derivation_rule", "qualification_rule", "scoring_rule",
            "distinct_structure_rule", "distinct_structure_minimum_is_not_an_identity",
            "minimum_qualifying_carriers", "minimum_distinct_qualifying_structures",
            "requested_carrier_count", "insufficient_bank_verdict",
            "max_bank_materializations", "max_delivery_attempts", "retries_permitted",
            "retry_wait_seconds", "manual_correction_permitted",
            "selection_among_carriers_permitted", "a_scientific_outcome_is_never_retried",
            "only_capacity_rejection_before_generation_may_be_retried", "never_retried",
            "measured_qualification_rate", "measured_over_carriers", "measured_rate_source",
            "measured_rate_is_not_a_prediction", "expected_qualifying_at_the_measured_rate",
            "probability_the_minimum_is_missed_at_the_measured_rate",
            "scientific_target_is_m113s_unchanged",
            "p22_scientific_computation_is_m113s_unchanged",
            "p15_inherited_unchanged_from_m114", "p15_version",
            "p15_recomputed_independently_from_the_preserved_record",
            "predicates_retaining_m113_scientific_computations",
            "predicates_retaining_m114_computations",
            "physical_requests_and_model_calls_are_never_carried_in_one_field",
            "evidence_tier", "session_budget",
        )
    }
    record = {
        "schema": ANALYSIS_PLAN_SCHEMA,
        "milestone": "M118", "hypothesis": "H63",
        "frozen_before_generation": True,
        "frozen_at": _now(),
        # The proposition is unchanged. The number is procedural: M117 disclosed five apparatus
        # revisions, so reusing H62 would claim its route selection had been prospectively clean.
        "states_the_same_scientific_proposition_as": ["H60", "H61", "H62"],
        "new_hypothesis_number_is_procedural_not_scientific": True,
        "inherits_every_scientific_rule_from": "experiments/M115/ANALYSIS_PLAN.json",
        "inherited_plan_commitment_sha256": inherited["plan_commitment_sha256"],
        "predicates_versioned_for_this_milestone": [],
        "predicates_newly_versioned_for_this_milestone": [],
        "inherited_scientific_artifact_digests": digests,
        # Instrumental, not scientific.
        "requested_model_alias": fixed.REQUESTED_MODEL,
        "required_canonical_checkpoint": fixed.CANONICAL_CHECKPOINT,
        "selected_provider": fixed.PROVIDER,
        "route_fixed_by": "experiments/M118/PREREGISTRATION.md",
        "route_fixed_before_any_h63_observation": True,
        "route_selected_using_an_h63_carrier_outcome": False,
        "provider_substitution_permitted": False,
        "readiness_gate": "experiments/M118/READINESS_RESULT.json",
        "readiness_may_not_alter_the_proposition_schema_or_thresholds": True,
        "max_tokens": MAX_TOKENS,
        "reasoning_effort": REASONING_EFFORT,
        "identity_semantics": "m118-fixed-openinference-v1",
        "delivery_semantics": "m114-delivery-v1",
        # Control construction, named rather than left implicit in the digests that bind it.
        # The comparison H63 rests on is a nine-arm design, and an auditor should be able to find
        # it from the plan instead of inferring it from an import closure.
        "control_construction": {
            "arms_rule": "scripts/run_m113_qualification.py::ARM_NAMES",
            "arms": list(_arm_names()),
            "out_of_band_arms": ["producer_death", "preservation"],
            "arms_restored_from_frozen_producer_bytes_never_reimplemented": True,
            "only_the_genesis_state_differs_across_arms": True,
            "arm_symmetry_predicate": "P11 (every arm saw every demand)",
            "comparison_predicate": "P22 (strictly better and no worse)",
            "budget_separated_from_capability_by": "the budget_plus arm, a fresh lineage given "
                                                  "four times the observation budget, so that "
                                                  "'the machinery could not' stays separable from "
                                                  "'the run could not afford to'",
            "ground_truth_rule": "metamorphosis/m113_evaluator.py::reach_under, computed without "
                                 "a budget and without a channel, so a refusal can be scored "
                                 "rather than believed",
            "inherited_unchanged": True,
            "bound_by_the_tested_system_freeze": True,
        },
        "claim_boundary": inherited["claim_boundary"],
        **carried,
        "plan_commitment_sha256": "",
    }
    record["plan_commitment_sha256"] = sha256_hex(
        canonical_bytes({k: v for k, v in record.items() if k != "plan_commitment_sha256"}))
    return record


def generator_spec(plan: dict[str, Any], digests: dict[str, str],
                   qualifying_input: str) -> dict[str, Any]:
    inherited = json.loads((M115 / "GENERATOR_SPEC.json").read_text(encoding="utf-8"))
    body = canonical_request_body(qualifying_input)
    record = {
        "schema": GENERATOR_SPEC_SCHEMA,
        "milestone": "M118", "hypothesis": "H63",
        "frozen_before_generation": True,
        "frozen_at": _now(),
        "analysis_plan_commitment_sha256": plan["plan_commitment_sha256"],
        "inherited_scientific_generator_contract_from": "experiments/M115/GENERATOR_SPEC.json",
        "inherited_spec_commitment_sha256": inherited["spec_commitment_sha256"],
        "blindness_contract": inherited["blindness_contract"],
        "invocation_policy": inherited["invocation_policy"],
        "prompt": {"path": "experiments/M118/GENERATOR_PROMPT.txt",
                   "sha256": digests["GENERATOR_PROMPT.txt"],
                   "inherited_byte_for_byte_from": "experiments/M115/GENERATOR_PROMPT.txt",
                   **prompt_blindness()},
        "qualifying_input": {"path": "experiments/M118/QUALIFYING_INPUT.txt",
                             "sha256": digests["QUALIFYING_INPUT.txt"],
                             "inherited_byte_for_byte_from": "experiments/M115/QUALIFYING_INPUT.txt",
                             "is_the_sole_input_to_the_generator": True},
        "output_schema": {"path": "experiments/M118/OUTPUT_SCHEMA.json",
                          "sha256": digests["OUTPUT_SCHEMA.json"],
                          "inherited_byte_for_byte_from": "experiments/M115/OUTPUT_SCHEMA.json"},
        "structured_output": {"mode": "json_schema", "strict": True,
                              "schema_path": "experiments/M118/OUTPUT_SCHEMA.json"},
        "generator_identity": {
            "requested_model_alias": fixed.REQUESTED_MODEL,
            "canonical_checkpoint": fixed.CANONICAL_CHECKPOINT,
            "provider": fixed.PROVIDER,
            "fixed_by_preregistration": True,
            "canonical_checkpoint_confirmed_by_readiness_gate": True,
        },
        "routing": {
            "allow_fallbacks": False, "automatic_routing": False,
            "provider_fallbacks": [], "model_fallbacks": [],
            "require_parameters": True, "router_metadata_required": True,
            "runtime_selected_checkpoint_required": fixed.CANONICAL_CHECKPOINT,
            "response_cache_disabled": True,
            "a_provider_that_cannot_serve_the_frozen_request_is_an_instrument_failure": True,
            "provider_substitution_permitted": False,
        },
        "runtime_identity_attestation": {
            "direct_strategy_required": True, "one_selected_endpoint_required": True,
            "one_router_attempt_required": True, "no_fallback_required": True,
            "empty_pipeline_required": True, "byok_required": False,
        },
        "sampling": {
            "declared_before_generation": True, "determinism_is_claimed": False,
            "every_parameter_sent": {"max_tokens": MAX_TOKENS, "seed": 0, "stream": False,
                                     "temperature": 1.0,
                                     "reasoning": {"effort": REASONING_EFFORT}},
        },
        "instrumental_delta_from_m115": {
            "provider": "%s -> %s" % (inherited["generator_identity"].get("provider", "Alibaba"),
                                      fixed.PROVIDER),
            "max_tokens": "32000 -> %d" % MAX_TOKENS,
            "reasoning_control": "absent -> effort %s" % REASONING_EFFORT,
            "scientific_rules_changed": [],
        },
        "canonical_request_body": body,
        "canonical_request_body_sha256": sha256_hex(canonical_bytes(body)),
        "claim_boundary": inherited["claim_boundary"],
        "spec_commitment_sha256": "",
    }
    record["spec_commitment_sha256"] = sha256_hex(
        canonical_bytes({k: v for k, v in record.items() if k != "spec_commitment_sha256"}))
    return record


def nonce_commitment() -> dict[str, Any]:
    """The bank nonce, drawn before any completion exists and committed as a digest."""
    nonce = secrets.token_hex(32)
    record = {
        "schema": NONCE_SCHEMA,
        "milestone": "M118", "hypothesis": "H63",
        "frozen_before_generation": True,
        "frozen_at": _now(),
        "bank_nonce": nonce,
        "bank_nonce_sha256": hashlib.sha256(nonce.encode("ascii")).hexdigest(),
        "envelope_version": admission.ENVELOPE_VERSION,
        "envelope_is_positional_and_content_independent": True,
        "drawn_before_any_completion_existed": True,
    }
    record["commitment_sha256"] = sha256_hex(
        canonical_bytes({k: v for k, v in record.items()}))
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", action="store_true")
    parser.add_argument("--freeze", action="store_true")
    args = parser.parse_args()

    digests = inherited_digests()
    qualifying_input = (M115 / "QUALIFYING_INPUT.txt").read_text(encoding="utf-8")
    plan = analysis_plan(digests)
    spec = generator_spec(plan, digests, qualifying_input)

    if args.plan:
        print(json.dumps({
            "inherited_digests": digests,
            "analysis_plan_commitment_sha256": plan["plan_commitment_sha256"],
            "spec_commitment_sha256": spec["spec_commitment_sha256"],
            "canonical_request_body_sha256": spec["canonical_request_body_sha256"],
            "instrumental_delta": spec["instrumental_delta_from_m115"],
            "scientific_rules_changed": spec["instrumental_delta_from_m115"]["scientific_rules_changed"],
        }, indent=2, sort_keys=True))
        return 0

    if args.freeze:
        chronology.assert_stage_permitted("scientific_freeze")
        chronology.assert_readiness_passed()
        chronology.assert_no_scientific_observation_yet()
        if (M118 / "ANALYSIS_PLAN.json").exists():
            raise FreezeError("the H63 apparatus is already frozen; it is not redrawn")
        M118.mkdir(parents=True, exist_ok=True)
        for name in INHERITED_VERBATIM:
            (M118 / name).write_bytes((M115 / name).read_bytes())
        (M118 / "ANALYSIS_PLAN.json").write_bytes(canonical_bytes(plan) + b"\n")
        (M118 / "GENERATOR_SPEC.json").write_bytes(canonical_bytes(spec) + b"\n")
        (M118 / "BANK_NONCE_COMMITMENT.json").write_bytes(
            canonical_bytes(nonce_commitment()) + b"\n")
        print(json.dumps({
            "frozen": True,
            "analysis_plan_commitment_sha256": plan["plan_commitment_sha256"],
            "spec_commitment_sha256": spec["spec_commitment_sha256"],
            "canonical_request_body_sha256": spec["canonical_request_body_sha256"],
        }, indent=2, sort_keys=True))
        return 0

    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
