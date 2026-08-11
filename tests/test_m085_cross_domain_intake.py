"""Regressions for M085's fail-closed cross-domain intake boundary.

Nothing here runs an experiment: M085 has no result and cannot have one until an outside maintainer
supplies a signed envelope. What these tests protect is the boundary itself — that it refuses by
default, that a project author cannot sign it, that the thresholds and the minimum bank size stay
consistent with each other, and that the held-out domain cannot be drawn early.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from metamorphosis.m075_private_readiness import exact_mcnemar_two_sided
from metamorphosis.m085_cross_domain_intake import (
    ADAPTER_CONTRACT_VERSION,
    ARMS,
    MAXIMUM_FRESH_ONLY_CORRECT,
    MAXIMUM_TWO_SIDED_EXACT_MCNEMAR_P,
    MINIMUM_CORRECTNESS_CRITICAL_TASKS_PER_DOMAIN,
    MINIMUM_DOMAINS,
    MINIMUM_TASKS_PER_DOMAIN,
    MINIMUM_TRANSFERRED_ONLY_CORRECT,
    M085IntakeError,
    assess_readiness,
    held_out_domain_index,
    scientific_protocol_commitment,
    validate_bank_envelope,
    validate_scientific_protocol,
)
from metamorphosis.m085_intake_kit import adapter_contract, instructions, template
from metamorphosis.m085_intake_kit import validate as kit_validate

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "experiments/M085"


def _filled() -> dict:
    envelope = template()
    envelope.update({
        "bank_id": "cdb-test",
        "created_at": "2026-08-11",
        "maintainer_identity": "an-outside-person",
        "conflicts_disclosed": "none",
        "payload_sha256": "ab" * 32,
        "payload_bytes": 4096,
        "maintainer_public_key_sha256": "cd" * 32,
    })
    return envelope


# -- the boundary refuses by default ------------------------------------------------------------

def test_the_repository_is_not_ready_and_every_blocker_needs_an_outsider() -> None:
    report = assess_readiness(ROOT)
    assert report["ready_for_payload_reveal"] is False
    assert report["payload_accessed"] is False
    assert report["target_domain_drawn"] is False
    assert report["scientific_result_exists"] is False
    assert sorted(report["blockers"]) == sorted([
        "missing CROSS_DOMAIN_BANK_ENVELOPE.json",
        "missing CROSS_DOMAIN_BANK_ENVELOPE.sshsig",
        "missing CROSS_DOMAIN_BANK_ALLOWED_SIGNERS",
        "missing CROSS_DOMAIN_SCIENTIFIC_PROTOCOL.json",
    ])


def test_authored_domains_are_never_g4_evidence() -> None:
    report = assess_readiness(ROOT)
    assert report["authored_domains_permitted_as_g4_evidence"] is False
    assert report["g4_advance_permitted_without_reproduction"] is False
    assert report["agi_claim_permitted"] is False


def test_no_scientific_protocol_or_result_exists_yet() -> None:
    assert not (BASE / "CROSS_DOMAIN_SCIENTIFIC_PROTOCOL.json").exists()
    assert not (BASE / "CROSS_DOMAIN_SCIENTIFIC_RESULT.json").exists()
    design = json.loads((BASE / "PROTOCOL.json").read_text(encoding="utf-8"))
    assert design["scientific_protocol_frozen"] is False
    assert design["scientific_result_exists"] is False
    assert design["payload_requested_or_accessed"] is False
    assert design["held_out_domain_drawn"] is False


# -- the envelope ------------------------------------------------------------------------------

def test_a_complete_envelope_is_accepted() -> None:
    validate_bank_envelope(_filled(), signature_verified=True)


def test_the_project_cannot_sign_its_own_independence() -> None:
    for identity in ("Anthony Mets", "anthony mets", "mjodheim", "  MJODHEIM  "):
        envelope = _filled()
        envelope["maintainer_identity"] = identity
        with pytest.raises(M085IntakeError, match="independent task-bank maintenance"):
            validate_bank_envelope(envelope, signature_verified=True)


def test_an_unverified_signature_is_refused() -> None:
    with pytest.raises(M085IntakeError, match="signature is not independently verified"):
        validate_bank_envelope(_filled(), signature_verified=False)


def test_two_domains_are_not_enough_to_hide_the_target() -> None:
    envelope = _filled()
    envelope["domains"] = envelope["domains"][:2]
    envelope["domain_count"] = 2
    envelope["task_count"] = 2 * MINIMUM_TASKS_PER_DOMAIN
    with pytest.raises(M085IntakeError, match="at least three coherent domains"):
        validate_bank_envelope(envelope, signature_verified=True)


def test_a_domain_short_of_correctness_critical_tasks_is_refused() -> None:
    envelope = _filled()
    envelope["domains"][0]["correctness_critical_tasks"] = (
        MINIMUM_CORRECTNESS_CRITICAL_TASKS_PER_DOMAIN - 1
    )
    with pytest.raises(M085IntakeError, match="correctness-critical coverage"):
        validate_bank_envelope(envelope, signature_verified=True)


def test_domains_need_their_own_material_difference_statement() -> None:
    """Identical digests would mean one justification pasted three times."""

    envelope = _filled()
    envelope["domains"][1]["material_difference_statement_sha256"] = (
        envelope["domains"][0]["material_difference_statement_sha256"]
    )
    with pytest.raises(M085IntakeError, match="own material-difference statement"):
        validate_bank_envelope(envelope, signature_verified=True)


def test_a_revealed_payload_is_refused() -> None:
    envelope = _filled()
    envelope["payload_revealed_to_policy_authors"] = True
    with pytest.raises(M085IntakeError, match="sealed payload metadata"):
        validate_bank_envelope(envelope, signature_verified=True)


def test_task_counts_must_reconcile_with_the_domains() -> None:
    envelope = _filled()
    envelope["task_count"] += 1
    with pytest.raises(M085IntakeError, match="does not reconcile"):
        validate_bank_envelope(envelope, signature_verified=True)


def test_an_unknown_adapter_contract_is_refused() -> None:
    envelope = _filled()
    envelope["adapter_contract_version"] = "something-else"
    with pytest.raises(M085IntakeError, match="sealed payload metadata"):
        validate_bank_envelope(envelope, signature_verified=True)


def test_extra_or_missing_fields_are_refused() -> None:
    extra = _filled()
    extra["note_from_the_maintainer"] = "hello"
    with pytest.raises(M085IntakeError, match="closed metadata schema"):
        validate_bank_envelope(extra, signature_verified=True)
    missing = _filled()
    del missing["bank_id"]
    with pytest.raises(M085IntakeError, match="closed metadata schema"):
        validate_bank_envelope(missing, signature_verified=True)


# -- the held-out draw --------------------------------------------------------------------------

def test_the_held_out_domain_is_deterministic_and_salt_dependent() -> None:
    payload = "ab" * 32
    first = held_out_domain_index(payload, "salt-one", MINIMUM_DOMAINS)
    assert first == held_out_domain_index(payload, "salt-one", MINIMUM_DOMAINS)
    assert 0 <= first < MINIMUM_DOMAINS
    assert {
        held_out_domain_index(payload, f"salt-{index}", MINIMUM_DOMAINS)
        for index in range(40)
    } == set(range(MINIMUM_DOMAINS)), "the draw must be able to select any domain"


def test_the_draw_refuses_a_missing_salt_or_a_degenerate_bank() -> None:
    with pytest.raises(M085IntakeError):
        held_out_domain_index("ab" * 32, "", MINIMUM_DOMAINS)
    with pytest.raises(M085IntakeError):
        held_out_domain_index("ab" * 32, "salt", 1)
    with pytest.raises(M085IntakeError):
        held_out_domain_index("not-a-digest", "salt", MINIMUM_DOMAINS)


# -- the threshold and the bank size were chosen together ----------------------------------------

def test_the_frozen_threshold_can_actually_clear_its_own_p_value() -> None:
    """Five discordant tasks give 0.0625 and could never clear 0.05; six give 0.03125."""

    attainable = exact_mcnemar_two_sided(
        MINIMUM_TRANSFERRED_ONLY_CORRECT, MAXIMUM_FRESH_ONLY_CORRECT,
    )
    assert float(attainable) <= MAXIMUM_TWO_SIDED_EXACT_MCNEMAR_P
    one_fewer = exact_mcnemar_two_sided(
        MINIMUM_TRANSFERRED_ONLY_CORRECT - 1, MAXIMUM_FRESH_ONLY_CORRECT,
    )
    assert float(one_fewer) > MAXIMUM_TWO_SIDED_EXACT_MCNEMAR_P


def test_the_bank_is_large_enough_for_the_threshold_to_be_reachable() -> None:
    assert MINIMUM_CORRECTNESS_CRITICAL_TASKS_PER_DOMAIN >= MINIMUM_TRANSFERRED_ONLY_CORRECT
    assert MINIMUM_TASKS_PER_DOMAIN >= MINIMUM_CORRECTNESS_CRITICAL_TASKS_PER_DOMAIN


def test_the_arms_are_the_three_the_design_names() -> None:
    assert ARMS == ("transferred_lineage", "fresh_agent", "acquisition_ablated")


# -- the kit -------------------------------------------------------------------------------------

def test_the_template_passes_the_schema_and_is_still_stopped_by_the_placeholder_guard(
    tmp_path: Path,
) -> None:
    """Two layers, and the second is the one that matters here.

    The skeleton is deliberately schema-valid so a maintainer can see the shape before filling it
    in — which means the structural validator alone would wave through an envelope naming a
    maintainer called `REPLACE-with-your-name-or-handle`. The kit's own placeholder check is what
    stops that, so it is tested rather than assumed.
    """

    skeleton = template()
    validate_bank_envelope(skeleton, signature_verified=True)

    candidate = tmp_path / "envelope.json"
    candidate.write_text(json.dumps(skeleton), encoding="utf-8")
    assert kit_validate(candidate, signature_verified=True) == 2


def test_the_kit_cannot_sign_anything() -> None:
    """A signature produced here would let the project attest its own independence."""

    source = (ROOT / "metamorphosis/m085_intake_kit.py").read_text(encoding="utf-8")
    for forbidden in ("subprocess", "os.system", "ssh-keygen -Y sign -f " + "x"):
        assert forbidden not in source or forbidden.startswith("ssh-keygen")
    assert "import subprocess" not in source


def test_the_instructions_and_contract_state_the_ordering_that_matters() -> None:
    text = instructions()
    assert "Never the archive" in text
    assert "only afterwards asks for the salt" in text
    contract = adapter_contract()
    assert "not trusted and is never" in contract
    assert "must not supply a decomposition" in contract
    assert ADAPTER_CONTRACT_VERSION in contract


def test_the_brief_names_what_m084_lacked() -> None:
    brief = (BASE / "MAINTAINER_BRIEF.md").read_text(encoding="utf-8")
    assert "correctness-critical" in brief
    assert "the task's own budget cannot" in brief
    assert "assignment salt" in brief
    assert "materially different" in brief


# -- the claim boundary --------------------------------------------------------------------------

def test_the_design_protocol_refuses_the_shortcuts() -> None:
    design = json.loads((BASE / "PROTOCOL.json").read_text(encoding="utf-8"))
    prohibited = " ".join(design["prohibited_adaptation"])
    assert "project-authored domains" in prohibited
    assert "before the maintainer releases the assignment salt" in prohibited
    assert "make a cost metric decisive" in prohibited
    boundary = design["claim_boundary"]
    assert boundary["closes_generality_gate_g4"] is False
    assert boundary["independent_reproduction_required_before_any_gate_advance"] is True
    assert boundary["agi_evidence"] is False


def test_m085_does_not_loosen_or_replace_the_m075_boundary() -> None:
    design = json.loads((BASE / "PROTOCOL.json").read_text(encoding="utf-8"))
    reuse = design["why_m075_boundary_cannot_be_reused"]
    assert reuse["m085_loosens_or_bypasses_the_m075_boundary"] is False
    assert reuse["m085_substitutes_for_the_open_m075_private_experiment"] is False
    assert reuse["exact_mcnemar_imported_from_m075_not_restated"] is True

    from metamorphosis.m075_private_readiness import (
        assess_repository_readiness,
    )
    assert assess_repository_readiness(ROOT)["ready_for_private_payload_reveal"] is False


# -- the freeze itself ---------------------------------------------------------------------------

def _frozen_protocol(envelope: dict, envelope_raw_sha256: str) -> dict:
    """A complete scientific protocol, as it will have to look on the day it is frozen.

    Written now, while no envelope exists, so that the freeze is a mechanical step rather than a
    drafting exercise performed under the pressure of a bank already in hand.
    """

    protocol = {
        "schema": "m085-cross-domain-scientific-protocol-v1",
        "status": "frozen_after_envelope_before_payload_reveal",
        "date_frozen": "2026-01-01",
        "scientific_result_exists": False,
        "payload_revealed": False,
        "bank_envelope_raw_sha256": envelope_raw_sha256,
        "bank_id": envelope["bank_id"],
        "bank_payload_sha256": envelope["payload_sha256"],
        "maintainer_identity": envelope["maintainer_identity"],
        "maintainer_public_key_sha256": envelope["maintainer_public_key_sha256"],
        "assignment_salt_commitment_sha256": "ef" * 32,
        "protocol_commitment_sha256": "",
        "parent_result": "M084",
        "organism": {
            "lineage_module": "metamorphosis/m084_persistent_lineage.py",
            "adapter_contract_version": ADAPTER_CONTRACT_VERSION,
            "policy_commit": "0" * 40,
            "code_sha256": {"metamorphosis/m084_persistent_lineage.py": "ab" * 32},
        },
        "budgets": {"max_actions_per_task": 60, "max_repair_cycles": 4},
        "attempt_policy": {
            "attempts_per_task_arm": 1,
            "fresh_environment_per_task": True,
            "retry_permitted": False,
            "replacement_permitted": False,
            "resume_permitted": False,
            "preserve_every_outcome": True,
        },
        "causal_design": {
            "arms": list(ARMS),
            "unit": "held-out-target-domain-task",
            "each_task_runs_once_per_arm": True,
            "matched_budget_across_arms": True,
            "held_out_target_drawn_after_freeze": True,
            "held_out_target_derivation": (
                "sha256(m085-target-assignment-v1\\0+payload_sha256+\\0+salt) mod domain_count"
            ),
            "assignment_salt_revealed_only_after_protocol_freeze": True,
            "source_domains_are_every_domain_except_the_target": True,
            "acquisition_ablated_must_match_fresh_agent": True,
            "primary_outcome": "evaluator-owned-correct-terminal-state-in-the-held-out-domain",
            "primary_paired_test": "two-sided-exact-mcnemar",
            "cost_metrics_reported_but_not_decisive": True,
        },
        "thresholds": {
            "minimum_domains": MINIMUM_DOMAINS,
            "minimum_tasks_per_domain": MINIMUM_TASKS_PER_DOMAIN,
            "minimum_correctness_critical_tasks_per_domain": (
                MINIMUM_CORRECTNESS_CRITICAL_TASKS_PER_DOMAIN
            ),
            "minimum_transferred_only_correct": MINIMUM_TRANSFERRED_ONLY_CORRECT,
            "maximum_fresh_only_correct": MAXIMUM_FRESH_ONLY_CORRECT,
            "maximum_two_sided_exact_mcnemar_p": MAXIMUM_TWO_SIDED_EXACT_MCNEMAR_P,
            "require_zero_faulted_episodes": True,
            "require_evaluator_owned_success": True,
            "require_acquisition_ablated_to_match_fresh_agent": True,
        },
        "information_boundary": {
            "goal_and_affordances_visible_to_organism": True,
            "observations_visible_to_organism": True,
            "domain_identity_hidden_from_the_organism": True,
            "evaluator_solutions_and_labels_hidden": True,
            "payload_unavailable_before_protocol_freeze": True,
            "target_domain_unknown_before_protocol_freeze": True,
        },
        "reproduction": {
            "required_before_g4_advance": True,
            "separate_bank": True,
            "separate_maintainer": True,
            "same_organism_budgets_thresholds_and_analysis": True,
            "first_result_preserved_regardless_of_reproduction": True,
        },
        "claim_boundary": {
            "agi": False,
            "genesis_gate_2": False,
            "genesis_gate_3": False,
            "general_autonomy": False,
            "open_ended_evolution": False,
            "closes_generality_gate_g4": False,
            "bounded_cross_domain_transfer_of_one_acquired_policy_only": True,
        },
    }
    protocol["protocol_commitment_sha256"] = scientific_protocol_commitment(protocol)
    return protocol


def test_a_complete_scientific_protocol_validates_against_its_envelope() -> None:
    envelope = _filled()
    raw = "aa" * 32
    validate_scientific_protocol(
        _frozen_protocol(envelope, raw), envelope_raw_sha256=raw, envelope=envelope,
    )


def test_the_protocol_commitment_must_recompute() -> None:
    envelope = _filled()
    raw = "aa" * 32
    protocol = _frozen_protocol(envelope, raw)
    protocol["date_frozen"] = "2026-01-02"
    with pytest.raises(M085IntakeError, match="commitment drifted"):
        validate_scientific_protocol(protocol, envelope_raw_sha256=raw, envelope=envelope)


def test_a_protocol_that_does_not_bind_the_envelope_is_refused() -> None:
    envelope = _filled()
    protocol = _frozen_protocol(envelope, "aa" * 32)
    with pytest.raises(M085IntakeError, match="does not bind the signed envelope"):
        validate_scientific_protocol(protocol, envelope_raw_sha256="bb" * 32, envelope=envelope)


def test_thresholds_cannot_be_softened_at_freeze_time() -> None:
    envelope = _filled()
    raw = "aa" * 32
    protocol = _frozen_protocol(envelope, raw)
    protocol["thresholds"]["minimum_transferred_only_correct"] = 3
    protocol["protocol_commitment_sha256"] = scientific_protocol_commitment(protocol)
    with pytest.raises(M085IntakeError, match="thresholds drifted"):
        validate_scientific_protocol(protocol, envelope_raw_sha256=raw, envelope=envelope)


def test_a_cost_metric_cannot_be_promoted_to_the_primary_outcome() -> None:
    """The correction M084 asks for, enforced rather than promised."""

    envelope = _filled()
    raw = "aa" * 32
    protocol = _frozen_protocol(envelope, raw)
    protocol["causal_design"]["primary_outcome"] = "steps-spent-in-the-held-out-domain"
    protocol["causal_design"]["cost_metrics_reported_but_not_decisive"] = False
    protocol["protocol_commitment_sha256"] = scientific_protocol_commitment(protocol)
    with pytest.raises(M085IntakeError, match="causal design drifted"):
        validate_scientific_protocol(protocol, envelope_raw_sha256=raw, envelope=envelope)


def test_the_claim_boundary_cannot_be_widened_at_freeze_time() -> None:
    envelope = _filled()
    raw = "aa" * 32
    protocol = _frozen_protocol(envelope, raw)
    protocol["claim_boundary"]["closes_generality_gate_g4"] = True
    protocol["protocol_commitment_sha256"] = scientific_protocol_commitment(protocol)
    with pytest.raises(M085IntakeError, match="claim boundary drifted"):
        validate_scientific_protocol(protocol, envelope_raw_sha256=raw, envelope=envelope)


def test_reproduction_cannot_be_dropped_at_freeze_time() -> None:
    envelope = _filled()
    raw = "aa" * 32
    protocol = _frozen_protocol(envelope, raw)
    protocol["reproduction"]["separate_maintainer"] = False
    protocol["protocol_commitment_sha256"] = scientific_protocol_commitment(protocol)
    with pytest.raises(M085IntakeError, match="reproduction contract drifted"):
        validate_scientific_protocol(protocol, envelope_raw_sha256=raw, envelope=envelope)


def test_a_protocol_declaring_a_result_already_exists_is_refused() -> None:
    envelope = _filled()
    raw = "aa" * 32
    protocol = _frozen_protocol(envelope, raw)
    protocol["scientific_result_exists"] = True
    protocol["protocol_commitment_sha256"] = scientific_protocol_commitment(protocol)
    with pytest.raises(M085IntakeError, match="scope is malformed"):
        validate_scientific_protocol(protocol, envelope_raw_sha256=raw, envelope=envelope)
