"""M115/H60: M114 science and delivery behind a versioned model-identity gate.

M113 and M114 are closed. M115 does not repair either record.  It inherits M114's scientific
carrier protocol and delivery semantics, changes only the provider route selected from preserved
DEVELOPMENT evidence, and versions model identity from literal alias equality to an explicitly
attested alias -> canonical checkpoint relation.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Mapping

from metamorphosis import m114_carrier_bank as predecessor
from metamorphosis import m115_delivery as delivery
from metamorphosis import m115_identity as identity
from metamorphosis import m115_route_selection as route_selection
from metamorphosis.blind_bank_protocol import canonical_bytes, sha256_hex

MILESTONE = "M115"
HYPOTHESIS = "H60"
ANALYSIS_PLAN_SCHEMA = "m115-carrier-bank-analysis-plan-v1"
GENERATOR_SPEC_SCHEMA = "m115-carrier-bank-generator-spec-v1"
IDENTITY_SEMANTICS = identity.IDENTITY_VERSION

EXPERIMENT_DIRECTORY = Path("experiments/M115")
ANALYSIS_PLAN_PATH = EXPERIMENT_DIRECTORY / "ANALYSIS_PLAN.json"
ANALYSIS_PLAN_CANDIDATE_PATH = EXPERIMENT_DIRECTORY / "ANALYSIS_PLAN_CANDIDATE.json"
GENERATOR_SPEC_PATH = EXPERIMENT_DIRECTORY / "GENERATOR_SPEC.json"
GENERATOR_PROMPT_PATH = EXPERIMENT_DIRECTORY / "GENERATOR_PROMPT.txt"
QUALIFYING_INPUT_PATH = EXPERIMENT_DIRECTORY / "QUALIFYING_INPUT.txt"
OUTPUT_SCHEMA_PATH = EXPERIMENT_DIRECTORY / "OUTPUT_SCHEMA.json"
DELIVERY_LEDGER_PATH = EXPERIMENT_DIRECTORY / "DELIVERY_LEDGER.json"
BANK_COMMITMENT_PATH = EXPERIMENT_DIRECTORY / "PUBLIC_BANK_COMMITMENT.json"
SYSTEM_PROTOCOL_PATH = EXPERIMENT_DIRECTORY / "SYSTEM_PROTOCOL.json"
REVEAL_AUTHORIZATION_PATH = EXPERIMENT_DIRECTORY / "REVEAL_AUTHORIZATION.json"
SEALED_BANK_PATH = EXPERIMENT_DIRECTORY / "SEALED_BANK.json.gpg"
RESULT_PATH = EXPERIMENT_DIRECTORY / "RESULT.json"
ROUTE_SELECTION_PATH = EXPERIMENT_DIRECTORY / "ROUTE_SELECTION_DECISION.json"
MATRIX_PATH = EXPERIMENT_DIRECTORY / "RUNTIME_ROUTE_MATRIX_DEVELOPMENT.json"

PREDECESSOR_PLAN_PATH = Path("experiments/M114/ANALYSIS_PLAN.json")
PREDECESSOR_SPEC_PATH = Path("experiments/M114/GENERATOR_SPEC.json")

GENERATOR_INPUT_DIGESTS = {
    "GENERATOR_PROMPT.txt": "f79fb18cde53e0efd4b1defef43460589376c0d3e93ff0eb2443836de526269e",
    "QUALIFYING_INPUT.txt": "c73721aec1de46b792551c9b16291b69806f21b4181a212b356bcc73e3f592e0",
    "OUTPUT_SCHEMA.json": "1020a1db9625f2734be1f548edd4c5af0139cb17732d13fb25913144f9106075",
}

PLAN_FILIATION = {
    "predecessor": "M114",
    "predecessor_hypothesis": "H59",
    "predecessor_outcome": "instrument-aborted before bank materialization after three capacity rejections",
    "predecessor_record_is_closed_and_not_repaired": True,
    "this_milestone": "M115",
    "this_hypothesis": "H60",
    "relationship": "corrective replication with canonical-checkpoint identity semantics preregistered before generation",
    "scientific_target_is_unchanged": True,
    "identity_rule_decided_after_m114_instrument_failure": True,
    "identity_rule_decided_after_the_development_matrix": True,
    "identity_rule_decided_before_any_m115_bank_existed": True,
    "identity_rule_decided_before_any_m115_qualifying_invocation": True,
    "identity_rule_decided_before_m115_freeze": True,
    "identity_rule_does_not_reinterpret_m113_or_m114": True,
}

# Every shared scientific/delivery key below must remain byte-equivalent as a JSON value to M114.
SHARED_PLAN_KEYS = (
    "a_scientific_outcome_is_never_retried",
    "cardinality_derivation",
    "claim_boundary",
    "closure_rule",
    "delivery_semantics",
    "demand_derivation_rule",
    "distinct_structure_minimum_is_not_an_identity",
    "distinct_structure_rule",
    "evidence_tier",
    "expected_qualifying_at_the_measured_rate",
    "frozen_before_generation",
    "insufficient_bank_verdict",
    "manual_correction_permitted",
    "max_bank_materializations",
    "max_delivery_attempts",
    "measured_over_carriers",
    "measured_qualification_rate",
    "measured_rate_is_not_a_prediction",
    "measured_rate_source",
    "minimum_distinct_qualifying_structures",
    "minimum_qualifying_carriers",
    "never_retried",
    "only_capacity_rejection_before_generation_may_be_retried",
    "p15_is_versioned_because_delivery_and_materialization_are_separated",
    "p15_recomputed_independently_from_the_preserved_record",
    "p15_version",
    "p15_versioning_gives_no_advantage_to_the_hypothesis",
    "p22_scientific_computation_is_m113s_unchanged",
    "physical_requests_and_model_calls_are_never_carried_in_one_field",
    "predicates_retaining_m113_scientific_computations",
    "predicates_versioned_for_this_milestone",
    "probability_the_minimum_is_missed_at_the_measured_rate",
    "qualification_rule",
    "requested_carrier_count",
    "retries_permitted",
    "retry_wait_seconds",
    "scientific_target_is_m113s_unchanged",
    "scoring_rule",
    "selection_among_carriers_permitted",
    "session_budget",
)

CarrierBankError = predecessor.CarrierBankError


def _root(root: Path | None) -> Path:
    return Path.cwd().resolve() if root is None else Path(root).resolve()


def _load_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise CarrierBankError("cannot read %s: %s" % (path, exc))
    if not isinstance(value, dict):
        raise CarrierBankError("%s is not an object" % path)
    return value


def analysis_plan_commitment(plan: Mapping[str, Any]) -> str:
    return sha256_hex(canonical_bytes({k: v for k, v in plan.items() if k != "plan_commitment_sha256"}))


def generator_spec_commitment(spec: Mapping[str, Any]) -> str:
    return sha256_hex(canonical_bytes({k: v for k, v in spec.items() if k != "spec_commitment_sha256"}))


def generator_inputs_match_predecessor(root: Path | None = None) -> dict[str, bool]:
    base = _root(root)
    return {
        name: (base / EXPERIMENT_DIRECTORY / name).is_file()
        and sha256_hex((base / EXPERIMENT_DIRECTORY / name).read_bytes()) == digest
        for name, digest in GENERATOR_INPUT_DIGESTS.items()
    }


def validate_analysis_plan(plan: Mapping[str, Any], *, root: Path | None = None) -> None:
    if not isinstance(plan, Mapping) or plan.get("schema") != ANALYSIS_PLAN_SCHEMA:
        raise CarrierBankError("analysis plan schema is not M115's declared schema")
    base = _root(root)
    predecessor_plan = _load_object(base / PREDECESSOR_PLAN_PATH)
    if plan.get("inherited_plan_commitment_sha256") != predecessor_plan.get("plan_commitment_sha256"):
        raise CarrierBankError("M115 does not bind the frozen M114 plan commitment")
    for key in SHARED_PLAN_KEYS:
        if plan.get(key) != predecessor_plan.get(key):
            raise CarrierBankError("M115 changed inherited scientific/delivery plan key %s" % key)
    if plan.get("milestone") != MILESTONE or plan.get("hypothesis") != HYPOTHESIS:
        raise CarrierBankError("analysis plan does not name M115/H60")
    if plan.get("filiation") != PLAN_FILIATION:
        raise CarrierBankError("M115 filiation is incomplete or drifted")
    if plan.get("identity_semantics") != IDENTITY_SEMANTICS:
        raise CarrierBankError("M115 identity semantics are not the owner-authorized version")
    if plan.get("requested_model_alias") != identity.REQUESTED_MODEL:
        raise CarrierBankError("M115 requested alias drifted")
    if plan.get("required_canonical_checkpoint") != identity.CANONICAL_CHECKPOINT:
        raise CarrierBankError("M115 canonical checkpoint drifted")
    if plan.get("selected_provider") != identity.SELECTED_PROVIDER:
        raise CarrierBankError("M115 provider drifted")
    if plan.get("provider_selection_decision") != str(ROUTE_SELECTION_PATH).replace("\\", "/"):
        raise CarrierBankError("M115 plan does not bind the route-selection decision")
    for key in (
        "provider_selection_rule_was_defined_before_the_development_matrix",
        "provider_selection_rule_adopted_for_milestone_after_matrix_observation",
        "provider_selection_rule_adopted_before_any_h60_freeze_or_bank",
        "selected_provider_quantization_is_not_a_selection_input",
        "p15_inherited_unchanged_from_m114",
    ):
        if plan.get(key) is not True:
            raise CarrierBankError("M115 plan must explicitly declare %s" % key)
    if plan.get("predicates_retaining_m114_computations") != ["P%d" % i for i in range(1, 23)]:
        raise CarrierBankError("M115 must retain all P1-P22 computations from M114")
    if plan.get("predicates_newly_versioned_for_this_milestone") != []:
        raise CarrierBankError("M115 must not quietly version a scientific predicate")
    selection = route_selection.derive_preserved_selection(base)
    if selection["selected_provider"] != plan.get("selected_provider"):
        raise CarrierBankError("plan provider is not the provider derived from preserved evidence")
    decision = _load_object(base / ROUTE_SELECTION_PATH)
    if decision.get("selected_provider") != selection["selected_provider"]:
        raise CarrierBankError("route-selection decision and recomputation disagree")
    if decision.get("canonical_checkpoint") != identity.CANONICAL_CHECKPOINT:
        raise CarrierBankError("route-selection decision binds a different checkpoint")
    if plan.get("plan_commitment_sha256") != analysis_plan_commitment(plan):
        raise CarrierBankError("M115 analysis-plan commitment drifted")


def _m114_spec(root: Path) -> dict[str, Any]:
    return _load_object(root / PREDECESSOR_SPEC_PATH)


def build_generator_spec_candidate(root: Path | None = None) -> dict[str, Any]:
    """Materialize the only M115 spec the committed plan/route decision permit."""
    base = _root(root)
    plan = _load_object(base / ANALYSIS_PLAN_CANDIDATE_PATH)
    validate_analysis_plan(plan, root=base)
    old = _m114_spec(base)
    selection = route_selection.derive_preserved_selection(base)

    # Start from M114's frozen generator contract and make the route/identity delta explicit.
    spec = copy.deepcopy(old)
    spec.pop("frozen_at", None)
    spec["schema"] = GENERATOR_SPEC_SCHEMA
    spec["milestone"] = MILESTONE
    spec["analysis_plan_commitment_sha256"] = plan["plan_commitment_sha256"]
    spec["frozen_before_generation"] = False
    spec["unset_before_freeze"] = ["frozen_before_generation"]
    spec["delivery_semantics"] = "m114-delivery-v1"
    spec["inherited_spec_commitment_sha256"] = old["spec_commitment_sha256"]
    spec["inherited_scientific_generator_contract_from"] = str(PREDECESSOR_SPEC_PATH).replace("\\", "/")

    body = copy.deepcopy(old["canonical_request_body"])
    body["provider"] = {
        "allow_fallbacks": False,
        "only": [selection["selected_provider"]],
        "require_parameters": True,
    }
    spec["canonical_request_body"] = body
    spec["canonical_request_body_sha256"] = sha256_hex(canonical_bytes(body))

    for key, path in (
        ("output_schema", OUTPUT_SCHEMA_PATH),
        ("prompt", GENERATOR_PROMPT_PATH),
        ("qualifying_input", QUALIFYING_INPUT_PATH),
    ):
        record = dict(spec[key])
        record["path"] = str(path).replace("\\", "/")
        spec[key] = record
    spec["structured_output"] = dict(
        spec["structured_output"], schema_path=str(OUTPUT_SCHEMA_PATH).replace("\\", "/")
    )

    spec["generator_identity"] = {
        "transport": "http_direct_openrouter_metadata",
        "endpoint": "https://openrouter.ai/api/v1/chat/completions",
        "model": identity.REQUESTED_MODEL,
        "canonical_checkpoint": identity.CANONICAL_CHECKPOINT,
        "identity_semantics": IDENTITY_SEMANTICS,
        "provider": selection["selected_provider"],
        "provider_serves_the_model_confirmed_by_development_smoke": True,
        "canonical_checkpoint_confirmed_by_development_smoke": True,
        "canonical_checkpoint_must_be_runtime_attested_on_the_qualifying_response": True,
        "quantization": selection["selected_quantization"],
        "quantization_source": "preserved provider discovery catalogue",
        "quantization_is_runtime_attested": False,
        "secret_reference": "environment variable OPENROUTER_API_KEY, never recorded here",
    }
    spec["provider_selection"] = {
        "decision_path": str(ROUTE_SELECTION_PATH).replace("\\", "/"),
        "matrix_path": str(MATRIX_PATH).replace("\\", "/"),
        "matrix_commit": route_selection.PRESERVED_MATRIX_COMMIT,
        "matrix_git_blob": route_selection.PRESERVED_MATRIX_BLOB,
        "selection_ordering": list(route_selection.RELIABILITY_ORDERING),
        "selected": selection["selected_provider"],
        "selected_metrics": selection["selected_metrics"],
        "quantization_was_a_ranking_input": False,
        "byok_was_a_ranking_input": False,
        "rule_defined_before_matrix": True,
        "rule_adopted_for_milestone_after_matrix_observation": True,
        "adopted_before_h60_freeze_or_bank": True,
        "depends_on_any_h58_h59_h60_carrier_result": False,
    }
    sampling = dict(spec["sampling"])
    sampling["seed_note"] = (
        "Alibaba listed seed among supported parameters in the preserved DEVELOPMENT discovery, "
        "so require_parameters keeps seed from being silently dropped. Reproducibility is not claimed."
    )
    spec["sampling"] = sampling
    spec["routing"] = dict(
        spec["routing"],
        router_metadata_required=True,
        response_cache_disabled=True,
        runtime_selected_checkpoint_required=identity.CANONICAL_CHECKPOINT,
    )
    spec["runtime_identity_attestation"] = {
        "version": IDENTITY_SEMANTICS,
        "requested_alias": identity.REQUESTED_MODEL,
        "required_checkpoint": identity.CANONICAL_CHECKPOINT,
        "required_provider": identity.SELECTED_PROVIDER,
        "direct_strategy_required": True,
        "one_router_attempt_required": True,
        "no_fallback_required": True,
        "empty_pipeline_required": True,
        "byok_required": False,
    }
    spec["spec_commitment_sha256"] = generator_spec_commitment(spec)
    return spec


def validate_generator_spec(
    spec: Mapping[str, Any], *, root: Path | None = None, plan_commitment_sha256: str | None = None
) -> None:
    if not isinstance(spec, Mapping) or spec.get("schema") != GENERATOR_SPEC_SCHEMA:
        raise CarrierBankError("generator spec schema is not M115's declared schema")
    base = _root(root)
    plan_path = ANALYSIS_PLAN_PATH if (base / ANALYSIS_PLAN_PATH).is_file() else ANALYSIS_PLAN_CANDIDATE_PATH
    plan = _load_object(base / plan_path)
    validate_analysis_plan(plan, root=base)
    expected = build_generator_spec_candidate(base)

    # A frozen spec differs from the deterministic candidate only by freeze bookkeeping.
    candidate = copy.deepcopy(dict(spec))
    candidate.pop("frozen_at", None)
    if candidate.get("frozen_before_generation") is True:
        candidate["frozen_before_generation"] = False
        candidate["unset_before_freeze"] = ["frozen_before_generation"]
        candidate["spec_commitment_sha256"] = generator_spec_commitment(candidate)
    if candidate != expected:
        raise CarrierBankError("generator spec differs from the deterministic M115 candidate")
    if plan_commitment_sha256 is not None and spec.get("analysis_plan_commitment_sha256") != plan_commitment_sha256:
        raise CarrierBankError("generator spec is not bound to the frozen analysis plan")
    if not all(generator_inputs_match_predecessor(base).values()):
        raise CarrierBankError("M115 generator prompt/input/schema are not M114's byte-for-byte")
    body = spec.get("canonical_request_body")
    if not isinstance(body, Mapping) or body.get("model") != identity.REQUESTED_MODEL:
        raise CarrierBankError("canonical request body model drifted")
    provider = body.get("provider")
    if provider != {"allow_fallbacks": False, "only": [identity.SELECTED_PROVIDER], "require_parameters": True}:
        raise CarrierBankError("canonical request body provider/routing drifted")
    if spec.get("canonical_request_body_sha256") != sha256_hex(canonical_bytes(body)):
        raise CarrierBankError("canonical request body digest drifted")
    if spec.get("spec_commitment_sha256") != generator_spec_commitment(spec):
        raise CarrierBankError("M115 generator-spec commitment drifted")


def readiness(root: Path | None = None) -> dict[str, Any]:
    base = _root(root)
    blockers: list[str] = []
    plan_path = base / ANALYSIS_PLAN_PATH
    spec_path = base / GENERATOR_SPEC_PATH
    phase = "draft"
    plan = None
    spec = None
    if not plan_path.is_file():
        blockers.append("missing ANALYSIS_PLAN.json: M115 is not frozen")
    else:
        try:
            plan = _load_object(plan_path)
            validate_analysis_plan(plan, root=base)
        except CarrierBankError as exc:
            blockers.append("analysis plan: %s" % exc)
    if not spec_path.is_file():
        blockers.append("missing GENERATOR_SPEC.json: M115 generator identity is not frozen")
    else:
        try:
            spec = _load_object(spec_path)
            validate_generator_spec(
                spec,
                root=base,
                plan_commitment_sha256=plan.get("plan_commitment_sha256") if plan else None,
            )
            if spec.get("frozen_before_generation") is not True:
                blockers.append("generator spec is not marked frozen")
        except CarrierBankError as exc:
            blockers.append("generator spec: %s" % exc)
    if plan is not None and spec is not None and not blockers:
        phase = "spec_frozen"
    if (base / DELIVERY_LEDGER_PATH).is_file():
        ledger = _load_object(base / DELIVERY_LEDGER_PATH)
        try:
            delivery.validate_delivery_ledger(
                ledger,
                spec_commitment_sha256=spec.get("spec_commitment_sha256") if spec else None,
                request_body_sha256=spec.get("canonical_request_body_sha256") if spec else None,
            )
        except delivery.DeliveryError as exc:
            blockers.append("delivery ledger: %s" % exc)
        else:
            summary = delivery.delivery_summary(ledger)
            if summary["bank_materializations"] == 1:
                phase = "generated_sealed"
            elif summary["delivery_attempts"] >= delivery.MAX_DELIVERY_ATTEMPTS:
                blockers.append("delivery budget exhausted without bank materialization")
    return {
        "schema": "m115-carrier-bank-readiness-v1",
        "milestone": MILESTONE,
        "hypothesis": HYPOTHESIS,
        "phase": phase,
        "blockers": blockers,
        "revealed": (base / REVEAL_AUTHORIZATION_PATH).is_file(),
        "identity_semantics": IDENTITY_SEMANTICS,
        "selected_provider": identity.SELECTED_PROVIDER,
        "canonical_checkpoint": identity.CANONICAL_CHECKPOINT,
    }
