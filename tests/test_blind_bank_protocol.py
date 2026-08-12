"""The blind sealed-bank contract, exercised against the ways it could be weakened.

Every test here answers one question: if someone wanted the bank to say what they hoped, which
edit would they make? Each such edit is written out and required to fail.
"""
from __future__ import annotations

import ast
import copy
import json
from pathlib import Path

import pytest

from metamorphosis.blind_bank_devkit import development_bank, development_generator_spec
from metamorphosis.blind_bank_protocol import (
    BlindBankError,
    CONTAMINATION_TOKENS,
    LEDGER_SCHEMA,
    PAYLOAD_SCHEMA,
    build_public_commitment,
    canonical_bytes,
    contamination_hits,
    generator_commitment,
    opaque_domain_id,
    sha256_hex,
    spec_commitment,
    validate_bank_payload,
    validate_generation_ledger,
    validate_generator_descriptor,
    validate_generator_spec,
    validate_public_commitment,
    validate_reveal_authorization,
)


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture()
def spec() -> dict[str, object]:
    return development_generator_spec()


@pytest.fixture()
def payload(spec: dict[str, object]) -> dict[str, object]:
    return development_bank(spec, seed=0)


def _refrozen(spec: dict[str, object]) -> dict[str, object]:
    spec["spec_commitment_sha256"] = spec_commitment(spec)
    return spec


# ---------------------------------------------------------------------------------------------
# canonical form and digest portability
# ---------------------------------------------------------------------------------------------


def test_canonical_form_is_key_order_independent(payload: dict[str, object]) -> None:
    shuffled = json.loads(json.dumps(payload))
    reordered = {key: shuffled[key] for key in sorted(shuffled, reverse=True)}
    assert canonical_bytes(reordered) == canonical_bytes(payload)


def test_canonical_form_contains_no_line_ending(payload: dict[str, object]) -> None:
    # The M064 defect was a digest that matched only a CRLF working-tree copy. A canonical form
    # with no newline in it cannot acquire one on a Windows checkout.
    raw = canonical_bytes(payload)
    assert b"\n" not in raw and b"\r" not in raw


def test_canonical_form_rejects_non_finite_numbers() -> None:
    with pytest.raises(ValueError):
        canonical_bytes({"value": float("nan")})


def test_digest_is_stable_across_a_round_trip(payload: dict[str, object]) -> None:
    once = sha256_hex(canonical_bytes(payload))
    twice = sha256_hex(canonical_bytes(json.loads(canonical_bytes(payload).decode("utf-8"))))
    assert once == twice


# ---------------------------------------------------------------------------------------------
# generator identity
# ---------------------------------------------------------------------------------------------


def test_a_generator_may_never_claim_training_data_independence(spec: dict[str, object]) -> None:
    descriptor = dict(spec["generator"])  # type: ignore[arg-type]
    descriptor["training_data_independence_proven"] = True
    with pytest.raises(BlindBankError, match="never be recorded as proven"):
        validate_generator_descriptor(descriptor)


def test_antecedence_requires_a_checkpoint_older_than_the_reference(
    spec: dict[str, object],
) -> None:
    descriptor = dict(spec["generator"])  # type: ignore[arg-type]
    descriptor["antecedence_demonstrable"] = True
    descriptor["checkpoint_published_on"] = "2026-09-01"
    descriptor["antecedence_reference_date"] = "2026-08-12"
    with pytest.raises(BlindBankError, match="strictly before"):
        validate_generator_descriptor(descriptor)


def test_an_api_hosted_generator_cannot_carry_a_weights_digest(
    spec: dict[str, object],
) -> None:
    descriptor = dict(spec["generator"])  # type: ignore[arg-type]
    descriptor["weights_openness"] = "api-hosted"
    descriptor["weights_digest_available"] = True
    descriptor["weights_sha256"] = "a" * 64
    with pytest.raises(BlindBankError, match="verifiable weights digest"):
        validate_generator_descriptor(descriptor)


def test_model_identifier_drift_changes_the_generator_commitment(
    spec: dict[str, object],
) -> None:
    before = generator_commitment(spec["generator"])  # type: ignore[arg-type]
    descriptor = dict(spec["generator"])  # type: ignore[arg-type]
    descriptor["model_identifier"] = "development/other-table"
    assert generator_commitment(descriptor) != before


# ---------------------------------------------------------------------------------------------
# spec, prompt and seed drift
# ---------------------------------------------------------------------------------------------


def test_spec_drift_is_caught_by_its_own_commitment(spec: dict[str, object]) -> None:
    spec["composition"]["pairs_per_domain"] = 3  # type: ignore[index]
    with pytest.raises(BlindBankError, match="commitment drifted"):
        validate_generator_spec(spec)


def test_seed_drift_changes_the_spec_commitment(spec: dict[str, object]) -> None:
    before = spec["spec_commitment_sha256"]
    spec["sampling"]["seed"] = 1  # type: ignore[index]
    assert spec_commitment(spec) != before


def test_prompt_drift_changes_the_spec_commitment(spec: dict[str, object]) -> None:
    before = spec["spec_commitment_sha256"]
    spec["prompt"]["template_sha256"] = "b" * 64  # type: ignore[index]
    assert spec_commitment(spec) != before


def test_a_prompt_naming_the_tested_system_is_refused(spec: dict[str, object]) -> None:
    spec["prompt"]["names_tested_system"] = True  # type: ignore[index]
    with pytest.raises(BlindBankError, match="names_tested_system"):
        validate_generator_spec(_refrozen(spec))


def test_a_prompt_requesting_a_desired_outcome_is_refused(spec: dict[str, object]) -> None:
    spec["prompt"]["requests_a_desired_outcome"] = True  # type: ignore[index]
    with pytest.raises(BlindBankError, match="requests_a_desired_outcome"):
        validate_generator_spec(_refrozen(spec))


def test_a_templated_prompt_is_refused(spec: dict[str, object]) -> None:
    # A digest over a template with variables does not cover the bytes the model received.
    spec["prompt"]["variables"] = ["domain_hint"]  # type: ignore[index]
    with pytest.raises(BlindBankError, match="literal and variable-free"):
        validate_generator_spec(_refrozen(spec))


def test_a_seed_may_not_be_recorded_when_the_runtime_does_not_guarantee_it(
    spec: dict[str, object],
) -> None:
    spec["sampling"]["seed_guaranteed_by_runtime"] = False  # type: ignore[index]
    with pytest.raises(BlindBankError, match="runtime guarantees"):
        validate_generator_spec(_refrozen(spec))


def test_selection_may_not_depend_on_the_tested_system(spec: dict[str, object]) -> None:
    spec["assembly"]["selection_depends_on_tested_system"] = True  # type: ignore[index]
    with pytest.raises(BlindBankError, match="assembly rules drifted"):
        validate_generator_spec(_refrozen(spec))


def test_a_retry_policy_permitting_a_reroll_is_refused(spec: dict[str, object]) -> None:
    spec["retry_policy"]["reroll_permitted"] = True  # type: ignore[index]
    with pytest.raises(BlindBankError, match="retry policy drifted"):
        validate_generator_spec(_refrozen(spec))


def test_an_oracle_may_confirm_a_class_but_never_choose_a_task(
    spec: dict[str, object],
) -> None:
    spec["oracle"]["may_select_among_tasks"] = True  # type: ignore[index]
    with pytest.raises(BlindBankError, match="confirm a class, never choose"):
        validate_generator_spec(_refrozen(spec))


def test_an_oracle_may_not_be_the_tested_system(spec: dict[str, object]) -> None:
    spec["oracle"]["distinct_from_tested_system"] = False  # type: ignore[index]
    with pytest.raises(BlindBankError, match="never be the system under test"):
        validate_generator_spec(_refrozen(spec))


def test_a_claim_boundary_asserting_human_independence_is_refused(
    spec: dict[str, object],
) -> None:
    spec["claim_boundary"]["human_independence_claimed"] = True  # type: ignore[index]
    with pytest.raises(BlindBankError, match="claim boundary drifted"):
        validate_generator_spec(_refrozen(spec))


def test_a_spec_claiming_to_replace_a_human_maintainer_is_refused(
    spec: dict[str, object],
) -> None:
    spec["claim_boundary"][  # type: ignore[index]
        "substitutes_for_an_independent_human_maintainer"
    ] = True
    with pytest.raises(BlindBankError, match="claim boundary drifted"):
        validate_generator_spec(_refrozen(spec))


def test_the_development_spec_is_valid(spec: dict[str, object]) -> None:
    validate_generator_spec(spec)


# ---------------------------------------------------------------------------------------------
# payload structure
# ---------------------------------------------------------------------------------------------


def test_the_development_bank_validates(
    spec: dict[str, object], payload: dict[str, object],
) -> None:
    validate_bank_payload(payload, spec=spec, development=True)


def test_a_development_payload_may_not_claim_the_scientific_schema(
    spec: dict[str, object], payload: dict[str, object],
) -> None:
    payload["schema"] = PAYLOAD_SCHEMA
    with pytest.raises(BlindBankError):
        validate_bank_payload(payload, spec=spec, development=True)


def test_a_payload_naming_this_project_is_refused(
    spec: dict[str, object], payload: dict[str, object],
) -> None:
    payload["domains"][0]["tasks"][0]["instruction"] = (  # type: ignore[index]
        "Reproduce the behaviour recorded in the M075 development bank."
    )
    with pytest.raises(BlindBankError, match="mentions the tested system"):
        validate_bank_payload(payload, spec=spec, development=True)


def test_every_contamination_token_is_detected() -> None:
    for token in CONTAMINATION_TOKENS:
        assert contamination_hits({"instruction": f"prefix {token} suffix"}) == [token]


def test_a_payload_carrying_an_expected_outcome_is_refused(
    spec: dict[str, object], payload: dict[str, object],
) -> None:
    payload["domains"][0]["tasks"][0]["should_refuse"] = True  # type: ignore[index]
    with pytest.raises(BlindBankError, match="forbidden key"):
        validate_bank_payload(payload, spec=spec, development=True)


def test_an_impossible_task_whose_capability_is_present_is_refused(
    spec: dict[str, object], payload: dict[str, object],
) -> None:
    domain = payload["domains"][0]  # type: ignore[index]
    impossible = next(
        task for task in domain["tasks"] if task["feasibility_class"] == "capability_absent"
    )
    impossible["environment"]["provides_capabilities"].append(
        impossible["absent_capability"]["capability"]
    )
    with pytest.raises(BlindBankError, match="present in the task environment"):
        validate_bank_payload(payload, spec=spec, development=True)


def test_an_impossible_task_unreachable_for_two_reasons_is_refused(
    spec: dict[str, object], payload: dict[str, object],
) -> None:
    # If two capabilities are missing, a failure carries no information about which one mattered.
    domain = payload["domains"][0]  # type: ignore[index]
    impossible = next(
        task for task in domain["tasks"] if task["feasibility_class"] == "capability_absent"
    )
    impossible["required_capabilities"].append("a_second_missing_capability")
    with pytest.raises(BlindBankError, match="more than one reason"):
        validate_bank_payload(payload, spec=spec, development=True)


def test_a_feasible_task_requiring_an_absent_capability_is_refused(
    spec: dict[str, object], payload: dict[str, object],
) -> None:
    domain = payload["domains"][0]  # type: ignore[index]
    feasible = next(
        task for task in domain["tasks"] if task["feasibility_class"] == "feasible"
    )
    feasible["required_capabilities"].append("not_provided_anywhere")
    with pytest.raises(BlindBankError, match="requires unavailable capabilities"):
        validate_bank_payload(payload, spec=spec, development=True)


def test_a_pair_not_sharing_one_environment_is_refused(
    spec: dict[str, object], payload: dict[str, object],
) -> None:
    domain = payload["domains"][0]  # type: ignore[index]
    impossible = next(
        task for task in domain["tasks"] if task["feasibility_class"] == "capability_absent"
    )
    impossible["environment"]["image_digest_sha256"] = "c" * 64
    with pytest.raises(BlindBankError, match="does not share one environment"):
        validate_bank_payload(payload, spec=spec, development=True)


def test_a_pair_differing_by_more_than_the_absent_capability_is_refused(
    spec: dict[str, object], payload: dict[str, object],
) -> None:
    domain = payload["domains"][0]  # type: ignore[index]
    feasible = next(
        task for task in domain["tasks"] if task["feasibility_class"] == "feasible"
    )
    feasible["required_capabilities"] = feasible["required_capabilities"][:1]
    with pytest.raises(BlindBankError, match="differ by exactly the absent capability"):
        validate_bank_payload(payload, spec=spec, development=True)


def test_an_evaluator_reading_the_agent_self_report_is_refused(
    spec: dict[str, object], payload: dict[str, object],
) -> None:
    # M081 recorded a self-report control that over-reported twice. An evaluator scoring the
    # agent's own claim would make that failure invisible instead of measurable.
    task = payload["domains"][0]["tasks"][0]  # type: ignore[index]
    task["evaluator"]["reads_agent_self_report"] = True
    with pytest.raises(BlindBankError, match="never read the agent's own report"):
        validate_bank_payload(payload, spec=spec, development=True)


def test_a_subjective_terminal_predicate_is_refused(
    spec: dict[str, object], payload: dict[str, object],
) -> None:
    task = payload["domains"][0]["tasks"][0]  # type: ignore[index]
    task["terminal_success_predicate"]["expression"] = "the output is reasonable"
    with pytest.raises(BlindBankError, match="subjective term"):
        validate_bank_payload(payload, spec=spec, development=True)


def test_an_evaluator_delegating_to_a_model_is_refused(
    spec: dict[str, object], payload: dict[str, object],
) -> None:
    task = payload["domains"][0]["tasks"][0]  # type: ignore[index]
    task["evaluator"]["spec"] = {"judgement": "an llm scores the transcript"}
    with pytest.raises(BlindBankError, match="subjective term"):
        validate_bank_payload(payload, spec=spec, development=True)


def test_an_opaque_domain_identifier_must_derive_from_the_bank_nonce(
    spec: dict[str, object], payload: dict[str, object],
) -> None:
    domain = payload["domains"][0]  # type: ignore[index]
    domain["opaque_domain_id"] = "opaque-" + "0" * 16
    for task in domain["tasks"]:
        task["opaque_domain_id"] = domain["opaque_domain_id"]
    with pytest.raises(BlindBankError, match="derived from the bank nonce"):
        validate_bank_payload(payload, spec=spec, development=True)


def test_opaque_domain_identifiers_carry_no_content(spec: dict[str, object]) -> None:
    # Two banks over the same subject matter, with different nonces, must produce unrelated
    # identifiers. Otherwise the public commitment leaks the domain before reveal.
    first = opaque_domain_id("a" * 64, 0)
    second = opaque_domain_id("b" * 64, 0)
    assert first != second


def test_a_bank_not_binding_the_frozen_spec_is_refused(
    spec: dict[str, object], payload: dict[str, object],
) -> None:
    payload["spec_commitment_sha256"] = "d" * 64
    with pytest.raises(BlindBankError, match="does not bind the frozen generator spec"):
        validate_bank_payload(payload, spec=spec, development=True)


def test_a_bank_with_the_wrong_domain_count_is_refused(
    spec: dict[str, object], payload: dict[str, object],
) -> None:
    payload["domains"] = payload["domains"][:-1]  # type: ignore[index]
    with pytest.raises(BlindBankError, match="domain count does not match"):
        validate_bank_payload(payload, spec=spec, development=True)


def test_a_network_enabled_task_environment_is_refused(
    spec: dict[str, object], payload: dict[str, object],
) -> None:
    task = payload["domains"][0]["tasks"][0]  # type: ignore[index]
    task["environment"]["network"] = "bridge"
    with pytest.raises(BlindBankError, match="without network access"):
        validate_bank_payload(payload, spec=spec, development=True)


# ---------------------------------------------------------------------------------------------
# public commitment
# ---------------------------------------------------------------------------------------------


def _commitment(spec: dict[str, object], payload: dict[str, object]) -> dict[str, object]:
    canonical = canonical_bytes(payload)
    composition = spec["composition"]  # type: ignore[index]
    return build_public_commitment(
        bank_id=str(payload["bank_id"]),
        milestone="M075B",
        spec_commitment_sha256=str(spec["spec_commitment_sha256"]),
        generator_commitment_sha256=generator_commitment(spec["generator"]),  # type: ignore[arg-type]
        payload_sha256=sha256_hex(canonical),
        payload_bytes=len(canonical),
        ciphertext_sha256="e" * 64,
        cipher="age-v1-x25519",
        key_custody="offline-project-holder",
        sealed_at="2026-08-12T00:00:00Z",
        isolation_attestation_sha256="f" * 64,
        opaque_domain_ids=[
            str(domain["opaque_domain_id"]) for domain in payload["domains"]  # type: ignore[index]
        ],
        domain_count=int(composition["domain_count"]),
        pairs_per_domain=int(composition["pairs_per_domain"]),
        task_count=int(composition["task_count"]),
    )


def test_a_public_commitment_validates(
    spec: dict[str, object], payload: dict[str, object],
) -> None:
    validate_public_commitment(_commitment(spec, payload), spec=spec)


def test_modification_after_sealing_breaks_the_commitment(
    spec: dict[str, object], payload: dict[str, object],
) -> None:
    commitment = _commitment(spec, payload)
    commitment["payload_sha256"] = "0" * 64
    with pytest.raises(BlindBankError, match="commitment digest drifted"):
        validate_public_commitment(commitment, spec=spec)


def test_a_commitment_admitting_the_payload_is_in_the_repository_is_refused(
    spec: dict[str, object], payload: dict[str, object],
) -> None:
    commitment = _commitment(spec, payload)
    commitment["payload_present_in_repository"] = True
    commitment["commitment_sha256"] = ""
    from metamorphosis.blind_bank_protocol import commitment_of

    commitment["commitment_sha256"] = commitment_of(commitment, omit="commitment_sha256")
    with pytest.raises(BlindBankError, match="never be present in this repository"):
        validate_public_commitment(commitment, spec=spec)


def test_a_commitment_disagreeing_with_the_frozen_composition_is_refused(
    spec: dict[str, object], payload: dict[str, object],
) -> None:
    other = development_generator_spec(domain_count=5, pairs_per_domain=2)
    with pytest.raises(BlindBankError, match="does not bind the frozen generator spec"):
        validate_public_commitment(_commitment(spec, payload), spec=other)


def test_a_commitment_leaking_project_context_is_refused(
    spec: dict[str, object], payload: dict[str, object],
) -> None:
    commitment = _commitment(spec, payload)
    commitment["bank_id"] = "m075-private-bank"
    from metamorphosis.blind_bank_protocol import commitment_of

    commitment["commitment_sha256"] = ""
    commitment["commitment_sha256"] = commitment_of(commitment, omit="commitment_sha256")
    with pytest.raises(BlindBankError, match="leaks project context"):
        validate_public_commitment(commitment, spec=spec)


# ---------------------------------------------------------------------------------------------
# non-retry
# ---------------------------------------------------------------------------------------------


def _ledger(entries: list[dict[str, object]]) -> dict[str, object]:
    return {"schema": LEDGER_SCHEMA, "entries": entries}


def _entry(
    attempt: int, commitment: str, outcome: str, payload_digest: str | None = None,
) -> dict[str, object]:
    return {
        "attempt_index": attempt,
        "spec_commitment_sha256": commitment,
        "started_at": "2026-08-12T00:00:00Z",
        "outcome": outcome,
        "payload_sha256": payload_digest,
        "isolation_attestation_sha256": "f" * 64 if outcome == "materialized" else None,
        "note": "",
    }


def test_one_frozen_spec_admits_one_materialized_bank() -> None:
    commitment = "a" * 64
    ledger = _ledger([
        _entry(1, commitment, "materialized", "b" * 64),
        _entry(2, commitment, "materialized", "c" * 64),
    ])
    with pytest.raises(BlindBankError, match="one frozen spec admits one"):
        validate_generation_ledger(ledger, spec_commitment_sha256=commitment)


def test_a_failed_materialization_may_be_preserved_before_a_successful_one() -> None:
    commitment = "a" * 64
    ledger = _ledger([
        _entry(1, commitment, "failed_structural_validation"),
        _entry(2, commitment, "materialized", "b" * 64),
    ])
    validate_generation_ledger(ledger, spec_commitment_sha256=commitment)


def test_a_silent_retry_cannot_hide_behind_a_repeated_attempt_index() -> None:
    commitment = "a" * 64
    ledger = _ledger([
        _entry(1, commitment, "materialized", "b" * 64),
        _entry(1, commitment, "aborted"),
    ])
    with pytest.raises(BlindBankError, match="repeats an attempt index"):
        validate_generation_ledger(ledger)


def test_a_non_materialized_attempt_may_not_record_a_payload_digest() -> None:
    ledger = _ledger([_entry(1, "a" * 64, "aborted", "b" * 64)])
    with pytest.raises(BlindBankError, match="may not record a payload digest"):
        validate_generation_ledger(ledger)


# ---------------------------------------------------------------------------------------------
# reveal
# ---------------------------------------------------------------------------------------------


def _authorization(commitment: dict[str, object], protocol_digest: str) -> dict[str, object]:
    from metamorphosis.blind_bank_protocol import REVEAL_SCHEMA, REVEAL_SIGNATURE_NAMESPACE

    return {
        "schema": REVEAL_SCHEMA,
        "milestone": "M075B",
        "bank_id": commitment["bank_id"],
        "bank_commitment_sha256": commitment["commitment_sha256"],
        "system_protocol_commitment_sha256": protocol_digest,
        "authorized_by": "an-authorizing-identity",
        "authorized_at": "2026-08-12T00:00:00Z",
        "signature_namespace": REVEAL_SIGNATURE_NAMESPACE,
        "authorizer_public_key_sha256": "a" * 64,
        "single_execution_only": True,
        "result_preserved_regardless_of_outcome": True,
    }


def test_an_unsigned_reveal_authorization_is_refused(
    spec: dict[str, object], payload: dict[str, object],
) -> None:
    commitment = _commitment(spec, payload)
    authorization = _authorization(commitment, "b" * 64)
    with pytest.raises(BlindBankError, match="signature is not verified"):
        validate_reveal_authorization(
            authorization, commitment=commitment, protocol_commitment_sha256="b" * 64,
            signature_verified=False,
        )


def test_a_reveal_bound_to_another_bank_is_refused(
    spec: dict[str, object], payload: dict[str, object],
) -> None:
    commitment = _commitment(spec, payload)
    authorization = _authorization(commitment, "b" * 64)
    authorization["bank_commitment_sha256"] = "0" * 64
    with pytest.raises(BlindBankError, match="does not bind the sealed bank commitment"):
        validate_reveal_authorization(
            authorization, commitment=commitment, protocol_commitment_sha256="b" * 64,
            signature_verified=True,
        )


def test_a_reveal_authorizing_more_than_one_execution_is_refused(
    spec: dict[str, object], payload: dict[str, object],
) -> None:
    commitment = _commitment(spec, payload)
    authorization = _authorization(commitment, "b" * 64)
    authorization["single_execution_only"] = False
    with pytest.raises(BlindBankError, match="exactly one execution"):
        validate_reveal_authorization(
            authorization, commitment=commitment, protocol_commitment_sha256="b" * 64,
            signature_verified=True,
        )


# ---------------------------------------------------------------------------------------------
# the validator may not consult the system under test
# ---------------------------------------------------------------------------------------------


VALIDATOR_MODULES = (
    "metamorphosis/blind_bank_protocol.py",
    "metamorphosis/blind_bank_sealing.py",
    "metamorphosis/blind_bank_isolation.py",
    "metamorphosis/blind_bank_devkit.py",
)


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


@pytest.mark.parametrize("relative", VALIDATOR_MODULES)
def test_the_validator_never_imports_the_system_under_test(relative: str) -> None:
    # A validator that could run the agent could admit tasks by watching how it handled them,
    # which is the selection this whole contract exists to prevent. The prohibition is structural:
    # the module graph contains no path to an agent, a runner or a subprocess.
    imports = _imported_modules(ROOT / relative)
    forbidden = {"subprocess", "socket", "urllib", "urllib.request", "http", "http.client"}
    assert not (imports & forbidden), f"{relative} imports {sorted(imports & forbidden)}"
    agent_like = {
        name for name in imports
        if name.startswith("metamorphosis.m0") or name.startswith("mira_core")
    }
    assert not agent_like, f"{relative} imports the system under test: {sorted(agent_like)}"


def test_the_devkit_can_only_emit_a_development_payload(spec: dict[str, object]) -> None:
    # The spec the devkit assembles legitimately *names* the scientific payload schema, because a
    # spec states what a real generator must emit. What must be impossible is for the emitting
    # function to produce one: its schema is a literal with no parameter reaching it.
    tree = ast.parse((ROOT / "metamorphosis/blind_bank_devkit.py").read_text(encoding="utf-8"))
    emitter = next(
        node for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "development_bank"
    )
    literals = {
        node.value for node in ast.walk(emitter)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    assert PAYLOAD_SCHEMA not in literals
    for seed in (0, 1, 7):
        assert development_bank(spec, seed=seed)["schema"] != PAYLOAD_SCHEMA


def test_a_development_bank_is_deterministic(spec: dict[str, object]) -> None:
    first = development_bank(spec, seed=3)
    second = development_bank(copy.deepcopy(spec), seed=3)
    assert canonical_bytes(first) == canonical_bytes(second)
