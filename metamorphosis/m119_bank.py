"""The M119 analysis plan and generator spec, derived rather than authored.

Every scientific input to H64's carrier bank already exists in a frozen predecessor, so M119 does
not write a new one. The prompt template, the output schema and the sampling parameters are taken
from M115's frozen spec **byte for byte**; the route is taken from M118's fixed-route module, which
was fixed before H64 existed and therefore cannot have been chosen to suit it.

Exactly four things differ from M115, each enumerated here and checked mechanically:

    requested carrier count   36, derived prospectively (see `BANK_SIZING`)
    provider route            M118's fixed OpenInference route, not M115's Alibaba route
    max output tokens         131072, the value M118's readiness gate actually proved
    reasoning control         effort "none", the control that gate proved yields zero reasoning

A derivation is auditable in a way an authored artifact is not: `derivation_report` states what was
inherited, what changed and why, and `validate_generator_spec` refuses a spec whose inherited parts
have drifted from the predecessor bytes they claim to inherit.

Nothing here sends a request, reveals a bank or scores anything.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from metamorphosis import m118_route as fixed
from metamorphosis.blind_bank_protocol import canonical_bytes, contamination_hits, sha256_hex

MILESTONE = "M119"
HYPOTHESIS = "H64"

ANALYSIS_PLAN_SCHEMA = "m119-carrier-bank-analysis-plan-v1"
GENERATOR_SPEC_SCHEMA = "m119-carrier-bank-generator-spec-v1"

DIRECTORY = Path("experiments/M119")
ANALYSIS_PLAN_PATH = DIRECTORY / "ANALYSIS_PLAN.json"
GENERATOR_SPEC_PATH = DIRECTORY / "GENERATOR_SPEC.json"
QUALIFYING_INPUT_PATH = DIRECTORY / "QUALIFYING_INPUT.txt"
BANK_NONCE_PATH = DIRECTORY / "BANK_NONCE_COMMITMENT.json"
BANK_SIZING_PATH = DIRECTORY / "BANK_SIZING_DEVELOPMENT.json"

# Inherited, unchanged, from frozen predecessors. These are read, never rewritten.
INHERITED_PROMPT_PATH = Path("experiments/M115/GENERATOR_PROMPT.txt")
INHERITED_SCHEMA_PATH = Path("experiments/M115/OUTPUT_SCHEMA.json")
INHERITED_SPEC_PATH = Path("experiments/M115/GENERATOR_SPEC.json")

# The predecessor bytes this derivation rests on. Recorded so drift is an error rather than a
# silent change of the tested contract.
INHERITED_DIGESTS = {
    "experiments/M115/GENERATOR_PROMPT.txt":
        "f79fb18cde53e0efd4b1defef43460589376c0d3e93ff0eb2443836de526269e",
    "experiments/M115/OUTPUT_SCHEMA.json":
        "1020a1db9625f2734be1f548edd4c5af0139cb17732d13fb25913144f9106075",
}

# ---------------------------------------------------------------------------------------------
# The bank size, derived before any H64 observation exists
# ---------------------------------------------------------------------------------------------
#
# A carrier count chosen after seeing how many carriers qualified would be a forking path. This one
# is fixed here, from DEVELOPMENT evidence that predates H64 entirely, and the derivation is
# recorded so it can be checked rather than believed.

REQUESTED_CARRIER_COUNT = 36

BANK_SIZING = {
    "requested_carriers": REQUESTED_CARRIER_COUNT,
    "token_envelope": {
        "m115_emitted_carriers": 24,
        "m115_max_output_tokens": 32000,
        "implied_tokens_per_carrier": 32000 / 24,
        "m119_expected_completion_tokens": int(36 * 32000 / 24),
        "max_output_tokens": 131072,
        "readiness_proved_completion_tokens": 73731,
        "readiness_proved_finish_reason": "stop",
        "max_output_tokens_is_the_value_the_readiness_gate_proved": True,
        "declared_endpoint_ceiling": 393216,
    },
    "yield_estimate": {
        "source": "metamorphosis.m113_carrier_devkit.development_carrier",
        "seed_prefix": "m119-sizing-",
        "sample": 400,
        "measured_qualification_rate": 0.2475,
        "mean_demand_pairs_per_qualifying_carrier": 2.1313131313131315,
        "demands_per_pair": 2,
        "expected_paired_demands": 38,
        "discordant_pairs_needed_for_significance": 5,
        "margin_over_the_arithmetic_minimum": 7.6,
    },
    "this_is_a_sizing_estimate_not_a_prediction": True,
    "the_estimate_measures_a_devkit_emitter_not_the_blind_generator": True,
    "estimate_caveat": "M113 recorded six per cent over project worlds against twenty-five per "
                      "cent from M112's blind bank. A devkit rate establishes only that the "
                      "plan's minimum is both meetable and missable; the plan may not be read as "
                      "a prediction, and the binding constraint is the minimum below.",
    "no_h64_carrier_existed_when_this_was_fixed": True,
    "the_count_is_not_revisable_after_the_reveal": True,
}

# Admissibility, inherited from M115 unchanged. A minimum rewritten for M119 could be rewritten to
# admit whatever bank arrived.
MINIMUM_QUALIFYING_CARRIERS = 3
MINIMUM_DISTINCT_QUALIFYING_STRUCTURES = 3

# The per-demand observation budget, inherited unchanged from M113/M114/M115 and fixed here so no
# runner can take it from the command line. It is not a number chosen for M119: a budget rewritten
# here could be rewritten until it suited, and at a budget the runtime cannot work within, every
# arm returns `undetermined` and the instrument reports a flat zero for all four cells.
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
    return path.read_bytes()


def inherited_digest_report(root: Path | None = None) -> dict[str, str]:
    """The predecessor bytes this derivation reads, digested now."""
    base = _root(root)
    return {relative: sha256_hex(_read_bytes(base, Path(relative)))
            for relative in sorted(INHERITED_DIGESTS)}


def assert_inherited_unchanged(root: Path | None = None) -> dict[str, str]:
    """Refuse to derive from predecessor bytes that are not the ones recorded here."""
    observed = inherited_digest_report(root)
    drifted = sorted(k for k in INHERITED_DIGESTS if observed.get(k) != INHERITED_DIGESTS[k])
    if drifted:
        raise BankError(
            "an inherited generator input no longer matches the bytes M119 derives from: %s"
            % ", ".join(drifted))
    return observed


def qualifying_input(root: Path | None = None) -> str:
    """The prompt with N substituted, and nothing else changed.

    The substitution is checked rather than assumed: if the template does not contain exactly the
    token this replaces, the derivation stops instead of silently sending an unsubstituted prompt.
    """
    base = _root(root)
    assert_inherited_unchanged(base)
    template = _read_bytes(base, INHERITED_PROMPT_PATH).decode("utf-8")
    marker = "a list of exactly N entries"
    if template.count(marker) != 1:
        raise BankError("the inherited prompt template does not carry exactly one N to substitute")
    text = template.replace(marker, "a list of exactly %d entries" % REQUESTED_CARRIER_COUNT)
    if "exactly N entries" in text:
        raise BankError("the substitution left an unresolved N in the qualifying input")
    return text


def output_schema(root: Path | None = None) -> dict[str, Any]:
    """M115's frozen output schema, unchanged. The structure is the contract."""
    base = _root(root)
    assert_inherited_unchanged(base)
    return json.loads(_read_bytes(base, INHERITED_SCHEMA_PATH).decode("utf-8"))


def canonical_request_body(root: Path | None = None) -> dict[str, Any]:
    """Every byte that reaches the model, fixed before any H64 observation exists."""
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
        # The route supports reasoning, so the control is sent explicitly rather than left to a
        # provider default. M118's readiness gate observed zero reasoning tokens under exactly
        # this control on exactly this route.
        "reasoning": {"effort": "none"},
    }


def blindness_contract(root: Path | None = None) -> dict[str, Any]:
    """What the generator can see. Computed from the request body, not asserted in prose."""
    body = canonical_request_body(root)
    messages = body["messages"]
    text = "\n".join(m["content"] for m in messages)
    return {
        "message_count": len(messages),
        "roles_sent": sorted({m["role"] for m in messages}),
        "no_system_message_is_sent": all(m["role"] != "system" for m in messages),
        "tools_sent": "tools" in body,
        "the_model_receives_only_the_qualifying_input_and_the_schema": (
            len(messages) == 1 and messages[0]["role"] == "user" and "tools" not in body),
        "contamination_hits_in_the_prompt": contamination_hits(text),
        "prompt_mentions_the_experiment": bool(contamination_hits(text)),
        "absent": [
            "conversation_history", "genesis_files", "hypothesis_information", "mcp", "memory",
            "milestone_information", "qualification_criteria", "rag", "repository",
            "shell_or_tool_calls", "summarization", "system_prompt_context", "tools",
            "web_search",
        ],
        "audit_method": "The recorded canonical request body is the whole of what reaches the "
                        "model: one user message carrying the derived qualifying input, and the "
                        "inherited JSON schema. Checked against the body's own digest and against "
                        "the contract's contamination checker.",
    }


# ---------------------------------------------------------------------------------------------
# The analysis plan
# ---------------------------------------------------------------------------------------------

def build_analysis_plan(root: Path | None = None) -> dict[str, Any]:
    """Every number the H64 analysis may use, fixed before the bank exists."""
    from metamorphosis import m119_arms as arms
    from metamorphosis import m119_endpoint as endpoint

    feasibility = endpoint.assert_feasible(MINIMUM_QUALIFYING_CARRIERS, 2)
    plan = {
        "schema": ANALYSIS_PLAN_SCHEMA,
        "milestone": MILESTONE, "hypothesis": HYPOTHESIS,
        "frozen_before_generation": True,

        # The measurement.
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

        # The decision rule.
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

        # Admissibility.
        "minimum_qualifying_carriers": MINIMUM_QUALIFYING_CARRIERS,
        "minimum_distinct_qualifying_structures": MINIMUM_DISTINCT_QUALIFYING_STRUCTURES,
        "minimums_inherited_unchanged_from": "experiments/M115/ANALYSIS_PLAN.json",
        "bank_sizing": BANK_SIZING,

        # Delivery.
        "max_bank_materializations": 1,
        "max_delivery_attempts": 3,
        "qualifying_invocations_permitted": 1,
        "only_capacity_rejection_before_generation_may_be_retried": True,
        "a_scientific_outcome_is_never_retried": True,
        "never_retried": [
            "any_status_other_than_429",
            "connection_lost_in_an_ambiguous_state",
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
    "this_milestone": "M119",
    "this_hypothesis": "H64",
    "predecessor": "M118",
    "predecessor_hypothesis": "H63",
    "predecessor_outcome": "closed as instrument design and audit; H63 was never frozen, never "
                           "generated a bank and remains untested",
    "predecessor_record_is_closed_and_not_repaired": True,
    "route_inherited_from": "metamorphosis/m118_route.py",
    "route_was_fixed_before_h64_existed": True,
    "route_module_is_inherited_byte_unchanged": True,
    "readiness_evidence_inherited_from": "experiments/M118/READINESS_RESULT.json",
    "generator_inputs_inherited_from": "experiments/M115/GENERATOR_SPEC.json",
    "m113_m114_m115_m116_m117_m118_are_closed_and_unmodified": True,
    "relationship": "a deliberately minimal design: the four-cell factorial that separates the "
                    "acquired cascade from the acquired policy, one paired endpoint, one "
                    "comparison, three guards",
    "scientific_target_is_unchanged": True,
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
}

LIMITATIONS = [
    "One provider and one checkpoint. Provider and model are confounded with the effect: nothing "
    "here separates what the acquired machinery does from what this particular serving route "
    "does, and no provider-invariance claim is available.",
    "The readiness evidence for the fixed route is inherited from M118's committed DEVELOPMENT "
    "run rather than re-measured. It establishes that this route served the frozen request shape "
    "conformingly on that date; it does not establish that it still does. The live check is "
    "admission: a response that fails identity, schema or truncation is a terminal instrument "
    "failure and is never redrawn.",
    "The comparator FRESH is uniform over components, which makes it symmetric under relabelling. "
    "It is not the strongest possible baseline, and beating it is not evidence of beating a "
    "competent hand-written attributor.",
    "The carrier family is the one this project's meta-schema defines. Nothing here supports a "
    "claim of generality beyond it.",
    "The bank is materialized by one generation from one model. The generator is blind to the "
    "hypothesis, not independent of its training data.",
    "M117 disclosed five apparatus revisions, some following real endpoint observations. M119 "
    "inherits a route, not a claim that route selection was prospectively clean.",
]


def validate_analysis_plan(plan: Mapping[str, Any], root: Path | None = None) -> None:
    """Is this the plan the derivation produces, exactly?"""
    if plan.get("schema") != ANALYSIS_PLAN_SCHEMA:
        raise BankError("not an M119 analysis plan")
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
            "reasoning_control_proved_zero_reasoning_tokens_in": (
                "experiments/M118/READINESS_RESULT.json"),
            "seed_is_honoured_by_the_provider": "unknown",
            "seed_note": "M117's catalogue recorded seed among the route's supported parameters, "
                         "so require_parameters keeps it from being silently dropped. "
                         "Reproducibility is not claimed.",
        },
        "structured_output": {
            "mode": "json_schema", "strict": True,
            "inherited_schema_path": INHERITED_SCHEMA_PATH.as_posix(),
            "inherited_schema_sha256": INHERITED_DIGESTS[INHERITED_SCHEMA_PATH.as_posix()],
            "structure_is_the_contract_content_is_the_generator": True,
        },
        "qualifying_input": {
            "path": QUALIFYING_INPUT_PATH.as_posix(),
            "sha256": sha256_hex(qualifying_input(base).encode("utf-8")),
            "inherited_template_path": INHERITED_PROMPT_PATH.as_posix(),
            "inherited_template_sha256": INHERITED_DIGESTS[INHERITED_PROMPT_PATH.as_posix()],
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
    """What was inherited, what changed, and why. Four differences, each named."""
    return {
        "inherited_byte_for_byte": inherited_digest_report(root),
        "inherited_from": INHERITED_SPEC_PATH.as_posix(),
        "differences_from_the_predecessor_spec": {
            "requested_carrier_count": {
                "predecessor": 24, "m119": REQUESTED_CARRIER_COUNT,
                "why": "derived prospectively from the token envelope and the DEVELOPMENT yield "
                       "estimate; see the plan's bank_sizing",
            },
            "provider": {
                "predecessor": "Alibaba", "m119": fixed.PROVIDER,
                "why": "M118's fixed route, fixed before H64 existed and not substitutable",
            },
            "max_tokens": {
                "predecessor": 32000,
                "m119": BANK_SIZING["token_envelope"]["max_output_tokens"],
                "why": "the value M118's readiness gate actually proved on this route, not a new "
                       "number chosen here",
            },
            "reasoning": {
                "predecessor": None, "m119": {"effort": "none"},
                "why": "this route supports reasoning, so the control is explicit rather than a "
                       "provider default; the readiness gate observed zero reasoning tokens "
                       "under exactly this control",
            },
        },
        "everything_else_is_the_predecessor_contract_unchanged": True,
        "no_h64_observation_informed_any_of_these": True,
    }


def validate_generator_spec(spec: Mapping[str, Any], plan: Mapping[str, Any],
                            root: Path | None = None) -> None:
    """Is this the spec the derivation produces from this plan, exactly?"""
    if spec.get("schema") != GENERATOR_SPEC_SCHEMA:
        raise BankError("not an M119 generator spec")
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
    fixed.assert_is_the_fixed_route(body.get("model"), (body.get("provider") or {}).get("only", [
        None])[0])
    hits = spec["blindness_contract"]["contamination_hits_in_the_prompt"]
    if hits:
        raise BankError(
            "the qualifying input carries project vocabulary the generator must not see: %s"
            % ", ".join(sorted(set(hits))))
    derived = build_generator_spec(plan, root)
    if canonical_bytes(spec) != canonical_bytes(derived):
        raise BankError(
            "the committed generator spec is not the one the derivation produces from this plan")
