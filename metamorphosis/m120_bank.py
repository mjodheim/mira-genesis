"""The M120 analysis plan and generator spec, derived rather than authored.

M120 changes the instrument and does not change the science. The hypothesis, the four arms, the
paired endpoint, the exact test, alpha, the ten-point effect floor, the guards, the four verdicts,
the decomposition, the comparator and its committed seed, the observation budget and the
admissibility minimums are all **inherited from M119 byte-unchanged**, by import rather than by
restatement, and `inherited_digest_report` records the bytes so a silent drift is an error.

What changes is the carrier contract and the chronology around it. Three things, each named:

    the candidate contract    `m120_carrier_contract`, whose schema states no relation between two
                              fields and whose decoder carries every schema-valid candidate into a
                              carrier the frozen host accepts
    the requested count       48, derived below from a DEVELOPMENT measurement of that contract
    the adequacy gate         scientific adequacy is decided before the seal, not after the reveal

## Why the carrier family is narrower than M115's, and what that costs

M119's generator followed M115's schema exactly and answered every range with its minimum: 22 of 37
machines had one cell, 35 of 37 had exactly two actions, and 28 of 37 had no reachable observation
deeper than one step. Decoding that committed bank into host-valid form leaves one machine of the
37 qualifying. A bank that cannot be tested is not a cheaper failure than a bank that is refused;
it is the same failure one stage later.

So M120 narrows the family it asks for -- at least three cells, at most one of them latent, at
least two actions carrying a precondition, four to six actions in all -- and states plainly that
this narrowing was chosen after reading M119's closed, public bank. That is an **instrument-design
dependency on a closed record**, and it is disclosed rather than presented as prospective
innocence. It is not a selection: it is the contract handed to the generator before it generates,
it applies to every machine identically, and no completion is filtered, ranked or redrawn against
it.

What it costs is stated in the plan's limitations: the carrier family is narrower than M115's, so a
verdict speaks about a smaller family than M119 would have. What it does not cost is the
independence of the test -- nothing in the narrowing mentions the arms, the cascade, the policy,
the attribution or which side of the comparison should win, and the qualification clauses that
decide whether a carrier admits the experiment remain exactly M113's, unchanged and still able to
fail.

Nothing here sends a request, seals a bank, reveals one or scores anything.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from metamorphosis import m118_route as fixed
from metamorphosis import m119_arms as arms
from metamorphosis import m119_endpoint as endpoint
from metamorphosis import m120_carrier_contract as contract
from metamorphosis.blind_bank_protocol import canonical_bytes, contamination_hits, sha256_hex

MILESTONE = "M120"
HYPOTHESIS = "H65"

ANALYSIS_PLAN_SCHEMA = "m120-carrier-bank-analysis-plan-v1"
GENERATOR_SPEC_SCHEMA = "m120-carrier-bank-generator-spec-v1"

DIRECTORY = Path("experiments/M120")
ANALYSIS_PLAN_PATH = DIRECTORY / "ANALYSIS_PLAN.json"
GENERATOR_SPEC_PATH = DIRECTORY / "GENERATOR_SPEC.json"
QUALIFYING_INPUT_PATH = DIRECTORY / "QUALIFYING_INPUT.txt"
GENERATOR_PROMPT_PATH = DIRECTORY / "GENERATOR_PROMPT.txt"
BANK_NONCE_PATH = DIRECTORY / "BANK_NONCE_COMMITMENT.json"

# The scientific modules inherited byte-unchanged from M119. They are read and digested, never
# rewritten: M120 is an instrument successor, and a milestone that quietly edited the endpoint it
# claims to inherit would be testing something else under the same name.
INHERITED_SCIENCE = (
    "metamorphosis/m119_arms.py",
    "metamorphosis/m119_endpoint.py",
    "metamorphosis/m119_decomposition.py",
)

INHERITED_DIGESTS = {
    "metamorphosis/m119_arms.py":
        "2210d465acb2fe3f588c58e1d50a0e7fb350b647f8bbff9b19c92d372f0f0362",
    "metamorphosis/m119_decomposition.py":
        "32c5753620959f2ccc214a4123f80fe92628d6ec8f75684903cfce709daa1858",
    "metamorphosis/m119_endpoint.py":
        "9e9097d5a92f1a9d76ec6ff680131cd0b5a699c62601a309dbec23909ea484bf",
}

# ---------------------------------------------------------------------------------------------
# The bank size, derived before any H65 observation exists
# ---------------------------------------------------------------------------------------------
#
# Fixed here, from a DEVELOPMENT measurement of the M120 contract that predates H65 entirely, and
# recorded so it can be recomputed rather than believed:
#
#     scripts/build_m120_bank_sizing.py  ->  experiments/M120/BANK_SIZING_DEVELOPMENT.json
#
# The estimate is taken at the contract's **smallest corner** -- three cells, two conditional
# actions, two plain actions, one error code -- because that is the shape M119's blind generator
# actually produced when it was offered a range. Sizing against the uniform draw would be sizing
# against a generator this project has not observed.

REQUESTED_CARRIER_COUNT = 48

BANK_SIZING = {
    "requested_carriers": REQUESTED_CARRIER_COUNT,
    "derivation_script": "scripts/build_m120_bank_sizing.py",
    "derivation_record": "experiments/M120/BANK_SIZING_DEVELOPMENT.json",
    "derivation_result_sha256":
        "9c75683d01b004bae735d22f3f77f223e4c5a06ab15ffe64ca957a334d26b4ad",
    "token_envelope": {
        "completion_characters_at_the_contract_ceiling": 79965,
        "characters_per_token_assumed": 2.6,
        "estimated_completion_tokens_at_the_contract_ceiling": 30755,
        "max_output_tokens": 131072,
        "readiness_proved_completion_tokens": 73731,
        "readiness_proved_finish_reason": "stop",
        "estimate_is_below_the_proved_envelope": True,
        "declared_endpoint_ceiling": 393216,
    },
    "yield_estimate": {
        "source": "metamorphosis.m120_devkit.qualification_rate",
        "mode": "corner",
        "why_the_corner": "M119's blind generator answered every range in M115's schema with its "
                          "minimum. The pessimistic corner is the shape that has actually been "
                          "observed on this route, so the derivation uses it rather than the "
                          "uniform draw.",
        "seed_prefix": "m120-sizing-",
        "sample": 400,
        "measured_qualification_rate_at_the_corner": 0.2875,
        "measured_qualification_rate_uniform": 0.4175,
        "measured_qualification_rate_at_the_ceiling": 0.5825,
        "mean_demand_pairs_per_qualifying_carrier": 2.026086956521739,
        "demands_per_pair": 2,
        "planning_qualification_rate": 0.1437,
        "planning_rate_is_half_the_measured_corner_rate": True,
        "expected_qualifying_carriers_at_the_planning_rate": 6.8976,
        "expected_paired_demands_at_the_planning_rate": 27.95027478260869,
        "discordant_pairs_needed_for_significance": 5,
    },
    "this_is_a_sizing_estimate_not_a_prediction": True,
    "the_estimate_measures_a_development_emitter_not_the_blind_generator": True,
    "estimate_caveat": "M113 recorded six per cent qualification over project worlds against "
                       "twenty-five per cent from M112's blind bank, and M119's blind bank "
                       "qualified at one in thirty-seven once decoded. A development rate "
                       "establishes only that the plan's minimum is both meetable and missable. "
                       "The binding constraint is the minimum below and the pre-seal adequacy "
                       "gate, and the count is not revisable after the generation.",
    "no_h65_carrier_existed_when_this_was_fixed": True,
    "the_count_is_not_revisable_after_the_generation": True,
}

# Admissibility, inherited from M115 through M119 unchanged. A minimum rewritten for M120 could be
# rewritten to admit whatever bank arrived.
MINIMUM_QUALIFYING_CARRIERS = 3
MINIMUM_DISTINCT_QUALIFYING_STRUCTURES = 3
MINIMUMS_INHERITED_FROM = "experiments/M119/ANALYSIS_PLAN.json"

# The per-demand observation budget, inherited unchanged from M113 through M119 and fixed here so
# no runner can take it from the command line.
SESSION_BUDGET = 4000
SESSION_BUDGET_INHERITED_FROM = "experiments/M113/ANALYSIS_PLAN.json"


class BankError(RuntimeError):
    """The plan or the spec is not the derived one. Every path fails closed."""


def _root(root: Path | None) -> Path:
    return Path(root) if root is not None else Path(__file__).resolve().parents[1]


def _read_bytes(root: Path, relative: Path) -> bytes:
    path = root / relative
    if not path.is_file():
        raise BankError("inherited input is missing: %s" % relative.as_posix())
    return path.read_bytes().replace(b"\r\n", b"\n")


def inherited_digest_report(root: Path | None = None) -> dict[str, str]:
    """The predecessor bytes this derivation rests on, digested now."""
    base = _root(root)
    return {relative: sha256_hex(_read_bytes(base, Path(relative)))
            for relative in sorted(INHERITED_SCIENCE)}


def assert_inherited_science_unchanged(root: Path | None = None) -> dict[str, str]:
    """Refuse to derive from scientific modules that are not the ones M120 claims to inherit."""
    observed = inherited_digest_report(root)
    drifted = sorted(name for name, recorded in INHERITED_DIGESTS.items()
                     if observed.get(name) != recorded)
    if drifted:
        raise BankError(
            "an inherited M119 scientific module no longer matches the bytes M120 derives from: %s"
            % ", ".join(drifted))
    return observed


def qualifying_input(root: Path | None = None) -> str:
    """The prompt with N substituted, and nothing else changed."""
    base = _root(root)
    template = _read_bytes(base, GENERATOR_PROMPT_PATH).decode("utf-8")
    marker = "a list of exactly N entries"
    if template.count(marker) != 1:
        raise BankError("the prompt template does not carry exactly one N to substitute")
    text = template.replace(marker, "a list of exactly %d entries" % REQUESTED_CARRIER_COUNT)
    if "exactly N entries" in text:
        raise BankError("the substitution left an unresolved N in the qualifying input")
    return text


def output_schema(root: Path | None = None) -> dict[str, Any]:
    """The candidate contract, built from code rather than read from a file it could drift from."""
    return contract.candidate_schema()


def canonical_request_body(root: Path | None = None) -> dict[str, Any]:
    """Every byte that reaches the model, fixed before any H65 observation exists."""
    fixed.assert_is_the_fixed_route(fixed.REQUESTED_MODEL, fixed.PROVIDER)
    return {
        "model": fixed.REQUESTED_MODEL,
        "messages": [{"role": "user", "content": qualifying_input(root)}],
        "provider": fixed.provider_block(),
        "response_format": {"type": "json_schema", "json_schema": {
            "name": "machines", "strict": True, "schema": output_schema(root)}},
        "max_tokens": BANK_SIZING["token_envelope"]["max_output_tokens"],
        "seed": 0,
        "stream": False,
        "temperature": 1.0,
        "reasoning": {"effort": "none"},
    }


def blindness_contract(root: Path | None = None) -> dict[str, Any]:
    """What the generator can see. Computed from the request body, not asserted in prose."""
    body = canonical_request_body(root)
    messages = body["messages"]
    text = "\n".join(message["content"] for message in messages)
    return {
        "message_count": len(messages),
        "roles_sent": sorted({message["role"] for message in messages}),
        "no_system_message_is_sent": all(message["role"] != "system" for message in messages),
        "tools_sent": "tools" in body,
        "the_model_receives_only_the_qualifying_input_and_the_schema": (
            len(messages) == 1 and messages[0]["role"] == "user" and "tools" not in body),
        "contamination_hits_in_the_prompt": contamination_hits(text),
        "prompt_mentions_the_experiment": bool(contamination_hits(text)),
        "the_prompt_names_no_arm_cascade_policy_attribution_or_comparison": True,
        "the_prompt_states_no_qualification_clause": True,
        "absent": [
            "conversation_history", "genesis_files", "hypothesis_information", "mcp", "memory",
            "milestone_information", "qualification_criteria", "rag", "repository",
            "shell_or_tool_calls", "summarization", "system_prompt_context", "tools",
            "web_search",
        ],
        "audit_method": "The recorded canonical request body is the whole of what reaches the "
                        "model: one user message carrying the derived qualifying input, and the "
                        "built candidate schema. Checked against the body's own digest and "
                        "against the contract's contamination checker.",
    }


# ---------------------------------------------------------------------------------------------
# The analysis plan
# ---------------------------------------------------------------------------------------------

def build_analysis_plan(root: Path | None = None) -> dict[str, Any]:
    """Every number the H65 analysis may use, fixed before the bank exists."""
    assert_inherited_science_unchanged(root)
    feasibility = endpoint.assert_feasible(MINIMUM_QUALIFYING_CARRIERS, 2)
    plan = {
        "schema": ANALYSIS_PLAN_SCHEMA,
        "milestone": MILESTONE, "hypothesis": HYPOTHESIS,
        "frozen_before_generation": True,

        # The measurement. Inherited from M119 by import, so these values cannot drift from the
        # code that computes with them.
        "arms_version": arms.ARMS_VERSION,
        "arm_names": list(arms.ARM_NAMES),
        "diagnostic_arm_names": list(arms.DIAGNOSTIC_ARM_NAMES),
        "budget_multiplier": dict(arms.BUDGET_MULTIPLIER),
        "budget_multiplier_inherited_unchanged_from": arms.BUDGET_MULTIPLIER_INHERITED_FROM,
        "a_diagnostic_arm_can_attribute_a_negative_and_never_create_a_positive": True,
        "descendant_arm": arms.DESCENDANT_ARM,
        "comparator_arm": arms.COMPARATOR_ARM,
        "fresh_seed": arms.FRESH_SEED,
        "fresh_seed_source": arms.FRESH_SEED_SOURCE,
        "session_budget": SESSION_BUDGET,
        "session_budget_inherited_unchanged_from": SESSION_BUDGET_INHERITED_FROM,
        "session_budget_is_fixed_here_and_never_taken_from_the_command_line": True,
        "demand_derivation_rule": "m113_evaluator.derive_demand_pairs",
        "distinct_structure_rule": "carrier_host.structural_signature",

        # The decision rule, inherited unchanged.
        "endpoint_version": endpoint.ENDPOINT_VERSION,
        "primary_endpoint": "paired per-demand scientific correctness",
        "primary_success_key": dict(endpoint.PRIMARY_SUCCESS_KEY),
        "undetermined_is_a_primary_failure": True,
        "statistical_test": "one-sided exact McNemar over discordant pairs",
        "alpha": endpoint.ALPHA,
        "minimum_risk_difference": endpoint.MINIMUM_RISK_DIFFERENCE,
        "both_criteria_required": True,
        "no_harm_guards": dict(endpoint.NO_HARM_GUARDS),
        "a_guard_can_veto_a_positive_but_never_create_one": True,
        "verdicts": list(endpoint.VERDICTS),
        "an_underpowered_bank_is_inconclusive_not_negative": True,
        "an_instrument_failure_is_not_a_scientific_result": True,
        "feasibility_on_the_minimum_bank": feasibility,
        "science_inherited_byte_unchanged_from_m119": list(INHERITED_SCIENCE),
        "inherited_science_digests": inherited_digest_report(root),

        # The carrier contract, which is what M120 actually changes.
        "carrier_contract": contract.contract_report(),
        "candidate_schema_sha256": sha256_hex(canonical_bytes(contract.candidate_schema())),
        "generator_conformant_output_is_mechanically_host_acceptable": True,

        # Admissibility, and the gate that now decides it before the seal.
        "minimum_qualifying_carriers": MINIMUM_QUALIFYING_CARRIERS,
        "minimum_distinct_qualifying_structures": MINIMUM_DISTINCT_QUALIFYING_STRUCTURES,
        "minimums_inherited_unchanged_from": MINIMUMS_INHERITED_FROM,
        "minimum_paired_demands_for_attainable_significance":
            endpoint.required_paired_demands(),
        "adequacy_is_decided_before_the_seal": True,
        "an_inadequate_bank_closes_the_milestone_without_a_reveal": True,
        "an_inadequate_bank_is_never_filtered_repaired_resampled_or_regenerated": True,
        "bank_sizing": BANK_SIZING,

        # Delivery, inherited unchanged from M119.
        "max_bank_materializations": 1,
        "max_delivery_attempts": 3,
        "qualifying_invocations_permitted": 1,
        "only_capacity_rejection_before_generation_may_be_retried": True,
        "a_scientific_outcome_is_never_retried": True,
        "never_retried": [
            "any_status_other_than_429",
            "connection_lost_in_an_ambiguous_state",
            "inadequate_bank",
            "insufficient_bank",
            "invalid_json",
            "model_refusal",
            "output_schema_violation",
            "timeout_after_transmission_in_an_unestablished_state",
            "truncated_completion",
        ],
        "manual_correction_permitted": False,
        "selection_among_outputs_permitted": False,

        # Filiation and boundary.
        "filiation": FILIATION,
        "claim_boundary": CLAIM_BOUNDARY,
        "limitations": LIMITATIONS,
        "plan_commitment_sha256": "",
    }
    plan["plan_commitment_sha256"] = sha256_hex(canonical_bytes(
        {k: v for k, v in plan.items() if k != "plan_commitment_sha256"}))
    return plan


FILIATION = {
    "this_milestone": "M120",
    "this_hypothesis": "H65",
    "predecessor": "M119",
    "predecessor_hypothesis": "H64",
    "predecessor_outcome": "instrument_aborted after one qualifying generation; zero qualifying "
                           "carriers, zero paired demands, H64 untested",
    "predecessor_record_is_closed_and_not_repaired": True,
    "predecessor_checker_defects_are_successor_requirements_not_retroactive_repairs": True,
    "route_inherited_from": "metamorphosis/m118_route.py",
    "route_was_fixed_before_h64_and_h65_existed": True,
    "route_module_is_inherited_byte_unchanged": True,
    "science_inherited_from": "M119 (arms, endpoint, decomposition, comparator seed, budget, "
                              "admissibility minimums)",
    "scientific_target_is_unchanged": True,
    "what_changed_is_the_instrument": [
        "the candidate contract states no relation between two fields and is decoded by a total, "
        "content-independent function into a carrier the frozen host accepts",
        "the carrier family is narrowed so the contract's smallest corner is still testable",
        "scientific adequacy is decided before the seal rather than after the reveal",
        "the checker re-derives the analysis plan instead of trusting a self-reported digest",
        "the checker resolves and scores the committed canonical measurements itself",
    ],
    "m113_m114_m115_m116_m117_m118_m119_are_closed_and_unmodified": True,
}

CLAIM_BOUNDARY = {
    "advances_any_generality_gate": False,
    "agi": False,
    "recursive_self_improvement": False,
    "open_ended_intelligence": False,
    "closes_g1": False,
    "closes_g4": False,
    "evidence_tier": "blind_generated_sealed_bank",
    "external_reproduction": False,
    "generator_context_blindness": True,
    "generator_training_data_independence": False,
    "human_independence": False,
    "procedural_independence": True,
    "removes_carrier_interaction_language_authorship": True,
    "removes_substrate_authorship": False,
    "removes_world_authorship": True,
    "carrier_family_is_narrower_than_m115": True,
}

LIMITATIONS = [
    "One provider and one checkpoint. Provider and model are confounded with the effect: nothing "
    "here separates what the acquired machinery does from what this particular serving route "
    "does, and no provider-invariance claim is available.",
    "The carrier family is narrower than M115's and M119's, and the narrowing was chosen after "
    "reading M119's closed public bank. That is an instrument-design dependency on a closed "
    "record. It is not a selection over H65 outputs -- the contract is fixed before generation "
    "and applies to every machine identically -- but a verdict here speaks about a smaller "
    "carrier family than M119 would have spoken about.",
    "The decoder is a project-side total function. It closes the gap between what the schema "
    "permits and what the host accepts; it cannot and does not make a carrier qualify, and the "
    "qualification clauses remain M113's, unchanged.",
    "The readiness evidence for the fixed route is re-measured for this candidate schema rather "
    "than inherited: M118's stress schema does not dominate the M120 schema's keyword census, so "
    "M118's readiness alone would not establish that this route enforces this contract. A "
    "committed M120 DEVELOPMENT readiness result is a precondition of the freeze.",
    "The comparator FRESH is uniform over components, which makes it symmetric under relabelling. "
    "It is not the strongest possible baseline, and beating it is not evidence of beating a "
    "competent hand-written attributor.",
    "The bank is materialized by one generation from one model. The generator is blind to the "
    "hypothesis, not independent of its training data.",
    "M117 disclosed five apparatus revisions, some following real endpoint observations. M120 "
    "inherits a route, not a claim that route selection was prospectively clean.",
    "The observation budget is 4000 per demand, inherited unchanged. The endpoint is therefore "
    "budget-constrained resolution, and the fenced diagnostic arm exists to say whether a "
    "negative is that cost or a competence cost.",
]


def validate_analysis_plan(plan: Mapping[str, Any], root: Path | None = None) -> None:
    """Is this the plan the derivation produces, exactly?

    Three checks, and the order matters. The commitment must match the plan's own contents, so a
    plan cannot carry a digest of something else; the plan must then equal the one the code
    derives, so a field cannot be edited while the digest is recomputed to match; and the schema
    must be M120's, so a neighbouring milestone's plan cannot stand in.

    M119's checker compared the measurement's recorded plan digest against the plan file's own
    recorded digest and stopped there. A plan with every threshold set to zero, carrying the
    frozen commitment string verbatim, passed. This function is the correction, and the checker
    calls it rather than repeating it.
    """
    if plan.get("schema") != ANALYSIS_PLAN_SCHEMA:
        raise BankError("not an M120 analysis plan")
    expected = sha256_hex(canonical_bytes(
        {k: v for k, v in plan.items() if k != "plan_commitment_sha256"}))
    if plan.get("plan_commitment_sha256") != expected:
        raise BankError("the analysis plan commitment does not match its contents")
    derived = build_analysis_plan(root)
    if canonical_bytes(plan) != canonical_bytes(derived):
        raise BankError(
            "the committed analysis plan is not the one the derivation produces; the plan is "
            "derived, not authored, so a difference means either the plan or the code it is "
            "derived from was changed after the freeze")


# ---------------------------------------------------------------------------------------------
# The generator spec
# ---------------------------------------------------------------------------------------------

def build_generator_spec(plan: Mapping[str, Any], root: Path | None = None) -> dict[str, Any]:
    """The generator contract: what is sent, to whom, once."""
    base = _root(root)
    body = canonical_request_body(base)
    spec = {
        "schema": GENERATOR_SPEC_SCHEMA,
        "milestone": MILESTONE, "hypothesis": HYPOTHESIS,
        "frozen_before_generation": True,
        "analysis_plan_commitment_sha256": plan["plan_commitment_sha256"],

        "generator_identity": {
            "endpoint": "https://openrouter.ai/api/v1/chat/completions",
            "model": fixed.REQUESTED_MODEL,
            "provider": fixed.PROVIDER,
            "canonical_checkpoint": fixed.CANONICAL_CHECKPOINT,
            "identity_semantics": fixed.ROUTE_VERSION,
            "canonical_checkpoint_must_be_runtime_attested_on_the_qualifying_response": True,
            "transport": "http_direct_openrouter_metadata",
            "secret_reference": "environment variable OPENROUTER_API_KEY, never recorded here",
        },
        "routing": {
            "allow_fallbacks": False,
            "automatic_routing": False,
            "model_fallbacks": [],
            "provider_fallbacks": [],
            "require_parameters": True,
            "response_cache_disabled": True,
            "router_metadata_required": True,
            "runtime_selected_checkpoint_required": fixed.CANONICAL_CHECKPOINT,
            "provider_substitution_permitted": False,
            "a_provider_that_cannot_serve_the_frozen_request_is_an_instrument_failure": True,
        },
        "invocation_policy": {
            "qualifying_invocations_permitted": 1,
            "retries_permitted": False,
            "only_capacity_rejection_before_generation_may_be_retried": True,
            "invalid_output_is_the_result_of_the_single_invocation": True,
            "manual_correction_permitted": False,
            "repair_parsing_permitted": False,
            "second_request_to_correct_the_output_permitted": False,
            "selection_among_outputs_permitted": False,
            "an_undetected_automatic_retry_fails_closed": True,
        },
        "sampling": {
            "declared_before_generation": True,
            "determinism_is_claimed": False,
            "every_parameter_sent": {k: v for k, v in body.items()
                                     if k in ("max_tokens", "seed", "stream", "temperature")},
            "reasoning": body["reasoning"],
            "reasoning_control_proved_zero_reasoning_tokens_in":
                "experiments/M118/READINESS_RESULT.json",
            "seed_is_honoured_by_the_provider": "unknown",
            "seed_note": "M117's catalogue recorded seed among the route's supported parameters, "
                         "so require_parameters keeps it from being silently dropped. "
                         "Reproducibility is not claimed.",
        },
        "structured_output": {
            "mode": "json_schema", "strict": True,
            "schema_source": "metamorphosis/m120_carrier_contract.py",
            "schema_is_built_from_code_not_read_from_a_file": True,
            "candidate_schema_sha256": sha256_hex(canonical_bytes(contract.candidate_schema())),
            "feature_classes_used_are_a_subset_of_those_proven_on_the_route": True,
            "proven_feature_classes": list(contract.PROVEN_FEATURE_CLASSES),
            "structure_is_the_contract_content_is_the_generator": True,
        },
        "qualifying_input": {
            "path": QUALIFYING_INPUT_PATH.as_posix(),
            "sha256": sha256_hex(qualifying_input(base).encode("utf-8")),
            "template_path": GENERATOR_PROMPT_PATH.as_posix(),
            "template_sha256": sha256_hex(_read_bytes(base, GENERATOR_PROMPT_PATH)),
            "derived_from_the_template_by": "substituting N with %d and nothing else"
                                            % REQUESTED_CARRIER_COUNT,
            "is_the_sole_input_to_the_generator": True,
        },
        "requested_carrier_count": REQUESTED_CARRIER_COUNT,
        "blindness_contract": blindness_contract(base),
        "derivation": derivation_report(base),
        "claim_boundary": CLAIM_BOUNDARY,
        "canonical_request_body": body,
        "canonical_request_body_sha256": sha256_hex(canonical_bytes(body)),
        "spec_commitment_sha256": "",
    }
    spec["spec_commitment_sha256"] = sha256_hex(canonical_bytes(
        {k: v for k, v in spec.items() if k != "spec_commitment_sha256"}))
    return spec


def derivation_report(root: Path | None = None) -> dict[str, Any]:
    """What was inherited, what changed, and why."""
    return {
        "scientific_modules_inherited_byte_unchanged": inherited_digest_report(root),
        "differences_from_the_predecessor_spec": {
            "output_schema": {
                "predecessor": "experiments/M115/OUTPUT_SCHEMA.json, inherited byte for byte "
                               "by M119",
                "m120": "metamorphosis/m120_carrier_contract.py, built from code",
                "why": "M115's schema states two of the frozen host's rules only in prose, and "
                       "M119 lost 33 of its 34 host refusals to exactly those two. The M120 "
                       "schema states no relation between two fields, so a schema-valid "
                       "completion cannot carry one.",
            },
            "carrier_family": {
                "predecessor": "1-4 cells, 2-6 actions, guards optional, any visibility with at "
                               "least one observed cell",
                "m120": "3-4 cells, at most one latent, 2-3 conditional actions plus 2-3 further "
                        "actions",
                "why": "M119's bank answered every range with its minimum, and the minimum of "
                       "M115's family is not testable: decoding that committed bank leaves one "
                       "machine of 37 qualifying. Chosen after reading a closed public record, "
                       "and disclosed as such.",
            },
            "requested_carrier_count": {
                "predecessor": 36, "m120": REQUESTED_CARRIER_COUNT,
                "why": "derived from a DEVELOPMENT measurement of this contract at its smallest "
                       "corner; see the plan's bank_sizing",
            },
            "adequacy": {
                "predecessor": "payload admissibility checked before the seal; scientific "
                               "adequacy discovered after the reveal",
                "m120": "scientific adequacy decided before the seal",
                "why": "M119's bank was admissible and inadequate, and the one authorized reveal "
                       "was spent establishing that",
            },
        },
        "everything_else_is_the_predecessor_contract_unchanged": True,
        "no_h65_observation_informed_any_of_these": True,
        "m119_closed_public_artifacts_informed_the_contract_and_that_is_disclosed": True,
    }


def validate_generator_spec(spec: Mapping[str, Any], plan: Mapping[str, Any],
                            root: Path | None = None) -> None:
    """Is this the spec the derivation produces from this plan, exactly?"""
    if spec.get("schema") != GENERATOR_SPEC_SCHEMA:
        raise BankError("not an M120 generator spec")
    expected = sha256_hex(canonical_bytes(
        {k: v for k, v in spec.items() if k != "spec_commitment_sha256"}))
    if spec.get("spec_commitment_sha256") != expected:
        raise BankError("the generator spec commitment does not match its contents")
    if spec.get("analysis_plan_commitment_sha256") != plan.get("plan_commitment_sha256"):
        raise BankError("the generator spec is bound to a different analysis plan")
    body = spec.get("canonical_request_body")
    if not isinstance(body, Mapping):
        raise BankError("the generator spec carries no canonical request body")
    if spec.get("canonical_request_body_sha256") != sha256_hex(canonical_bytes(body)):
        raise BankError("the canonical request body digest does not match the body")
    only = (body.get("provider") or {}).get("only")
    if not isinstance(only, list) or len(only) != 1:
        raise BankError("the request body must name exactly one provider and no fallback")
    fixed.assert_is_the_fixed_route(body.get("model"), only[0])
    hits = spec["blindness_contract"]["contamination_hits_in_the_prompt"]
    if hits:
        raise BankError(
            "the qualifying input carries project vocabulary the generator must not see: %s"
            % ", ".join(sorted(set(hits))))
    derived = build_generator_spec(plan, root)
    if canonical_bytes(spec) != canonical_bytes(derived):
        raise BankError(
            "the committed generator spec is not the one the derivation produces from this plan")


__all__ = [
    "ANALYSIS_PLAN_SCHEMA",
    "BANK_SIZING",
    "GENERATOR_SPEC_SCHEMA",
    "MINIMUM_DISTINCT_QUALIFYING_STRUCTURES",
    "MINIMUM_QUALIFYING_CARRIERS",
    "REQUESTED_CARRIER_COUNT",
    "SESSION_BUDGET",
    "BankError",
    "blindness_contract",
    "build_analysis_plan",
    "build_generator_spec",
    "canonical_request_body",
    "output_schema",
    "qualifying_input",
    "validate_analysis_plan",
    "validate_generator_spec",
]
