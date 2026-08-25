"""M112 - the architecture for receiving a world bank this project did not author.

These tests exercise the payload validator, the analysis plan's honesty conditions, the
tested-system freeze and the fail-closed phase machine. They never create a scientific bank: every
payload here carries the development schema, which the contract keeps separate for exactly this
reason.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

import pytest

from metamorphosis import m110_runtime as consumer
from metamorphosis import m112_world_bank as world_bank
from metamorphosis.blind_bank_protocol import canonical_bytes, opaque_domain_id, sha256_hex

ROOT = Path(__file__).resolve().parents[1]
NONCE = "a" * 64


def _record(rng: random.Random) -> dict:
    return {
        "documents": [
            {
                "alpha": rng.choice(consumer.VALUES),
                "beta": rng.choice(consumer.VALUES),
                "gamma": rng.choice(consumer.VALUES),
                "ref": "k%d" % index,
            }
            for index in range(consumer.DOCUMENT_COUNT)
        ],
        "side": {
            "k%d" % index: {"zeta": rng.choice(consumer.VALUES), "note": "n%d" % index}
            for index in range(consumer.DOCUMENT_COUNT)
        },
    }


def _payload(count: int = 3, *, nonce: str | None = None, seed: int = 7) -> dict:
    """Identifiers always derive from a well-formed nonce; `nonce` overrides only what is stored."""
    rng = random.Random(seed)
    worlds = []
    for index in range(count):
        entry = _record(rng)
        entry["world_ref"] = opaque_domain_id(NONCE, index)
        worlds.append(entry)
    return {
        "schema": world_bank.DEVELOPMENT_WORLD_PAYLOAD_SCHEMA,
        "bank_nonce": NONCE if nonce is None else nonce,
        "worlds": worlds,
    }


# ---------------------------------------------------------------------------------------------
# The payload validator.
# ---------------------------------------------------------------------------------------------


def test_a_well_formed_development_payload_is_accepted() -> None:
    accepted = world_bank.validate_world_bank_payload(_payload(4), development=True)
    assert accepted["world_count"] == 4
    assert len(set(accepted["world_digests"])) == 4
    assert accepted["development"] is True


def test_the_scientific_schema_is_refused_when_development_is_asked_for() -> None:
    payload = _payload()
    payload["schema"] = world_bank.WORLD_PAYLOAD_SCHEMA
    with pytest.raises(world_bank.WorldBankError):
        world_bank.validate_world_bank_payload(payload, development=True)


def test_a_payload_naming_something_a_blind_generator_could_not_know_is_refused() -> None:
    for key in ("row", "component", "stratum", "census", "target", "pair", "policy", "lineage"):
        payload = _payload()
        payload["worlds"][0][key] = "anything"
        with pytest.raises(world_bank.WorldBankError, match="could not know"):
            world_bank.validate_world_bank_payload(payload, development=True)


def test_an_identifier_not_derived_from_the_nonce_is_refused() -> None:
    payload = _payload()
    payload["worlds"][1]["world_ref"] = "domain-two"
    with pytest.raises(world_bank.WorldBankError, match="opaque identifier"):
        world_bank.validate_world_bank_payload(payload, development=True)


def test_a_world_the_carrier_refuses_is_not_a_world() -> None:
    payload = _payload()
    payload["worlds"][0]["documents"][0]["alpha"] = 9
    with pytest.raises(ValueError):
        world_bank.validate_world_bank_payload(payload, development=True)


def test_a_duplicated_world_is_refused() -> None:
    payload = _payload(2)
    payload["worlds"][1] = dict(payload["worlds"][0])
    payload["worlds"][1]["world_ref"] = opaque_domain_id(NONCE, 1)
    with pytest.raises(world_bank.WorldBankError, match="duplicates"):
        world_bank.validate_world_bank_payload(payload, development=True)


def test_an_empty_bank_is_refused() -> None:
    payload = _payload(1)
    payload["worlds"] = []
    with pytest.raises(world_bank.WorldBankError, match="no worlds"):
        world_bank.validate_world_bank_payload(payload, development=True)


def test_a_short_nonce_is_refused() -> None:
    with pytest.raises(world_bank.WorldBankError, match="nonce"):
        world_bank.validate_world_bank_payload(_payload(nonce="abc"), development=True)


# ---------------------------------------------------------------------------------------------
# The analysis plan must be able to fail, and to pass.
# ---------------------------------------------------------------------------------------------


def _plan(**overrides) -> dict:
    plan = {
        "schema": world_bank.ANALYSIS_PLAN_SCHEMA,
        "requested_world_count": 100,
        "minimum_ambiguous_worlds": 3,
        "minimum_witness_worlds": 3,
        "insufficient_bank_verdict": "negative",
        "retries_permitted": False,
        "stratification_criterion": "m111_public_structural_criterion",
        "claim_boundary": world_bank.WORLD_BANK_CLAIM_BOUNDARY,
    }
    plan.update(overrides)
    plan["plan_commitment_sha256"] = world_bank.analysis_plan_commitment(plan)
    return plan


def test_the_frozen_plan_validates() -> None:
    world_bank.validate_analysis_plan(_plan())


def test_a_minimum_the_base_rate_cannot_reach_is_refused() -> None:
    with pytest.raises(world_bank.WorldBankError, match="unreachable"):
        world_bank.validate_analysis_plan(_plan(minimum_ambiguous_worlds=40))


def test_a_minimum_that_could_never_fail_is_refused() -> None:
    with pytest.raises(world_bank.WorldBankError, match="decides\\s+nothing|cannot fail"):
        world_bank.validate_analysis_plan(_plan(minimum_ambiguous_worlds=1))


def test_a_plan_permitting_retries_is_refused() -> None:
    with pytest.raises(world_bank.WorldBankError, match="retries"):
        world_bank.validate_analysis_plan(_plan(retries_permitted=True))


def test_a_plan_treating_a_thin_bank_as_anything_but_negative_is_refused() -> None:
    with pytest.raises(world_bank.WorldBankError, match="negative"):
        world_bank.validate_analysis_plan(_plan(insufficient_bank_verdict="retry"))


def test_a_drifted_claim_boundary_is_refused() -> None:
    boundary = dict(world_bank.WORLD_BANK_CLAIM_BOUNDARY)
    boundary["closes_g4"] = True
    with pytest.raises(world_bank.WorldBankError, match="claim boundary"):
        world_bank.validate_analysis_plan(_plan(claim_boundary=boundary))


def test_a_drifted_plan_commitment_is_refused() -> None:
    plan = _plan()
    plan["requested_world_count"] = 200
    with pytest.raises(world_bank.WorldBankError, match="commitment"):
        world_bank.validate_analysis_plan(plan)


def test_the_committed_plan_on_disk_still_validates() -> None:
    plan = json.loads(
        (ROOT / world_bank.ANALYSIS_PLAN_PATH).read_text(encoding="utf-8")
    )
    world_bank.validate_analysis_plan(plan)
    assert plan["insufficient_bank_verdict"] == "negative"
    assert plan["retries_permitted"] is False


# ---------------------------------------------------------------------------------------------
# The tested-system freeze.
# ---------------------------------------------------------------------------------------------


def _protocol(root: Path, **overrides) -> dict:
    protocol = {
        "schema": world_bank.SYSTEM_PROTOCOL_SCHEMA,
        "tested_system_digests": {
            path: sha256_hex((root / path).read_bytes().replace(b"\r\n", b"\n"))
            for path in world_bank.TESTED_SYSTEM_PATHS
        },
        "tested_system_unmodified_after_reveal": True,
        "claim_boundary": world_bank.WORLD_BANK_CLAIM_BOUNDARY,
    }
    protocol.update(overrides)
    protocol["protocol_commitment_sha256"] = world_bank.system_protocol_commitment(protocol)
    return protocol


def test_a_protocol_binding_the_current_tested_system_validates() -> None:
    world_bank.validate_system_protocol(_protocol(ROOT), root=ROOT)


def test_a_protocol_missing_a_tested_system_member_is_refused() -> None:
    protocol = _protocol(ROOT)
    protocol["tested_system_digests"].pop(world_bank.TESTED_SYSTEM_PATHS[0])
    protocol["protocol_commitment_sha256"] = world_bank.system_protocol_commitment(protocol)
    with pytest.raises(world_bank.WorldBankError, match="exactly the declared tested system"):
        world_bank.validate_system_protocol(protocol, root=ROOT)


def test_a_drifted_tested_system_member_is_refused() -> None:
    protocol = _protocol(ROOT)
    protocol["tested_system_digests"][world_bank.TESTED_SYSTEM_PATHS[0]] = "0" * 64
    protocol["protocol_commitment_sha256"] = world_bank.system_protocol_commitment(protocol)
    with pytest.raises(world_bank.WorldBankError, match="drifted"):
        world_bank.validate_system_protocol(protocol, root=ROOT)


def test_a_protocol_not_asserting_the_post_reveal_invariant_is_refused() -> None:
    with pytest.raises(world_bank.WorldBankError, match="post-reveal"):
        world_bank.validate_system_protocol(
            _protocol(ROOT, tested_system_unmodified_after_reveal=False), root=ROOT
        )


# ---------------------------------------------------------------------------------------------
# The phase machine, and the honesty of the current state.
# ---------------------------------------------------------------------------------------------


def test_the_repository_is_at_spec_frozen_and_no_bank_exists() -> None:
    report = world_bank.assess_world_bank_readiness(ROOT)
    assert report["phase"] == "spec_frozen"
    assert report["ready_for_reveal"] is False
    assert report["revealed"] is False
    assert report["bank_exists"] is False
    assert report["phase_is_declared"] is True
    assert report["evidence_tier_is_declared"] is True


def test_the_remaining_blockers_are_all_artifacts_the_project_cannot_make_alone() -> None:
    report = world_bank.assess_world_bank_readiness(ROOT)
    assert set(report["blockers"]) == {
        "missing PUBLIC_BANK_COMMITMENT.json",
        "missing SYSTEM_PROTOCOL.json",
        "missing REVEAL_AUTHORIZATION.json",
    }


def test_an_empty_tree_fails_closed_at_draft(tmp_path: Path) -> None:
    report = world_bank.assess_world_bank_readiness(tmp_path)
    assert report["phase"] == "draft"
    assert report["ready_for_reveal"] is False
    assert report["blockers"]


def test_the_claim_boundary_never_claims_what_the_tier_cannot_support() -> None:
    boundary = world_bank.WORLD_BANK_CLAIM_BOUNDARY
    assert boundary["evidence_tier"] == "blind_generated_sealed_bank"
    assert boundary["human_independence"] is False
    assert boundary["external_reproduction"] is False
    assert boundary["removes_carrier_authorship"] is False
    assert boundary["closes_g4"] is False
    assert boundary["advances_any_generality_gate"] is False
    assert boundary["agi"] is False


def test_the_frozen_prompt_names_nothing_about_the_experiment() -> None:
    prompt = (ROOT / world_bank.GENERATOR_PROMPT_PATH).read_text(encoding="utf-8").lower()
    for token in (
        "feature",
        "row",
        "component",
        "lineage",
        "machinery",
        "ambigu",
        "genesis",
        "mira",
        "transfer",
        "diagnos",
        "monoton",
    ):
        assert token not in prompt, "the blind prompt mentions %r" % token


def test_the_module_cannot_emit_a_scientific_payload() -> None:
    """The scientific schema may be named, but nothing here builds one."""
    source = (ROOT / "metamorphosis" / "m112_world_bank.py").read_text(encoding="utf-8")
    assert "def build_world_bank" not in source
    assert "def generate_world_bank" not in source
    # No tracked file may carry the scientific payload schema as data.
    for path in (ROOT / "experiments" / "M112").glob("*.json"):
        assert world_bank.WORLD_PAYLOAD_SCHEMA not in path.read_text(encoding="utf-8")
