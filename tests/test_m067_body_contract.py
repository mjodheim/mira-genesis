from __future__ import annotations

import inspect
import json
from pathlib import Path
import subprocess
import sys

import pytest

import metamorphosis.m067_body_contract as m067


@pytest.fixture(scope="session")
def source_cases():
    return m067.observe_source_cases()


@pytest.fixture(scope="session")
def manifest():
    return m067.run_m067_development()


def test_body_bank_attestation_is_frozen_and_opaque() -> None:
    attestation = m067.attest_body_bank()
    assert attestation == {
        "body_count": 4,
        "body_handles": list(m067.BODY_HANDLES),
        "body_bank_commitment": m067.BODY_BANK_COMMITMENT,
        "body_digests": list(m067.BODY_DIGESTS),
        "contract_descriptors_disclosed": False,
    }


def test_protocol_fixes_the_complete_bounded_grammar() -> None:
    grammar = m067.M067_PROTOCOL.to_dict()["contract_grammar"]
    assert m067.M067_PROTOCOL.base_candidate_count == 3 * 2 * 4 * 3 * 2 * 2 == 288
    assert grammar["result_scale"] == 300
    assert set(grammar["families"]) == {"register", "stack", "mailbox"}
    assert len(grammar["opcode_candidates"]) == 4


def test_source_targets_are_observed_from_the_inherited_lineage(source_cases) -> None:
    public, hidden, tools, lineage_version = source_cases
    assert lineage_version == 8
    assert len(public) == 20
    assert len(hidden) == 12
    assert [(tool["tool_name"], tool["origin"]) for tool in tools] == [
        ("add", "founder"),
        ("max", "synthesized"),
        ("mean", "synthesized"),
        ("mul", "founder"),
    ]
    assert not {
        (case.skill, case.args) for case in public
    } & {(case.skill, case.args) for case in hidden}


def test_discovery_api_has_no_hidden_input() -> None:
    parameters = inspect.signature(m067.discover_public_class).parameters
    assert tuple(parameters) == ("body_handle", "public_cases", "protocol")
    assert not any("hidden" in name for name in parameters)


def test_one_uniform_search_discovers_every_precommitted_body(manifest) -> None:
    value = manifest.to_dict()
    assert value["all_precommitted_bodies_discovered"] is True
    assert value["all_public_classes_passed_hidden"] is True
    assert value["distinct_contracts_discovered"] == 4
    assert value["distinct_frame_families_discovered"] == ["mailbox", "register", "stack"]
    assert set(value["body_results"]) == set(m067.BODY_HANDLES)
    for result in value["body_results"].values():
        assert result["base_candidate_count"] == 288
        assert result["anchor_survivor_count"] == 1
        assert result["public_candidate_class_size"] == 1
        assert result["public_discovery_attempts"] == 1_560
        assert result["hidden_validation_attempts"] == 12
        assert result["all_public_survivors_passed_hidden"] is True
        assert set(result["hidden_results"].values()) == {True}


def test_controls_require_evidence_and_correct_semantics(manifest) -> None:
    for result in manifest.to_dict()["body_results"].values():
        controls = result["controls"]
        assert controls == {
            "default_adapter_passed": False,
            "framing_only_default_semantics_passed": False,
            "no_transcript_status": "insufficient_evidence",
            "no_transcript_adapter_count": 0,
            "corrupted_transcript_status": "no_survivor",
            "corrupted_transcript_survivor_count": 0,
        }


def test_class_wide_hidden_validation_rejects_a_semantic_mutation(source_cases, manifest) -> None:
    _public, hidden, _tools, _version = source_cases
    record = manifest.to_dict()["body_results"][m067.BODY_HANDLES[0]]["selected_adapter"]
    opcodes = dict(record["opcodes"])
    opcodes["add"], opcodes["mul"] = opcodes["mul"], opcodes["add"]
    mutated = m067.AdapterCandidate(
        record["family"], record["checksum"], tuple(sorted(opcodes.items())),
        record["response_offset"], record["response_endian"], record["response_transform"],
    )
    validation = m067.independently_validate_hidden_class(
        m067.BODY_HANDLES[0], (mutated,), hidden,
    )
    assert validation.all_survivors_passed is False
    assert validation.selected is None
    assert dict(validation.results)[mutated.digest()] is False


def test_empty_transcript_cannot_produce_an_adapter() -> None:
    outcome = m067.discover_public_class(m067.BODY_HANDLES[0], ())
    assert outcome.status == "insufficient_evidence"
    assert outcome.candidate_class == ()
    assert outcome.attempts == 0


def test_unknown_body_handle_is_rejected(source_cases) -> None:
    public, _hidden, _tools, _version = source_cases
    with pytest.raises(m067.M067Error, match="unknown opaque body"):
        m067.discover_public_class("body-not-in-bank", public)


def test_post_freeze_selector_is_deterministic_and_reaches_the_bank() -> None:
    observed = {m067.select_body_handle(f"{index:040x}") for index in range(256)}
    assert observed == set(m067.BODY_HANDLES)
    assert m067.select_body_handle("1" * 40) == m067.select_body_handle("1" * 40)
    with pytest.raises(m067.M067Error, match="forty-character"):
        m067.select_body_handle("ABC")


def test_runtime_boundary_has_no_external_authority_or_descriptor_endpoint() -> None:
    source = Path("metamorphosis/m067_opaque_body_runtime.mjs").read_text(encoding="utf-8")
    assert 'from "node:crypto"' in source
    assert 'from "node:fs"' not in source
    assert 'from "node:http"' not in source
    assert "fetch(" not in source
    assert 'mode === "public" || mode === "hidden"' in source
    assert "contract_descriptors_disclosed: false" in source


def test_manifest_keeps_claim_and_authority_boundaries_explicit(manifest) -> None:
    value = manifest.to_dict()
    assert value["bounded_contract_grammar"] is True
    assert value["complete_target_adapter_handed_to_lineage"] is False
    assert value["arbitrary_unknown_body_adaptation"] is False
    assert value["body_contract_descriptors_disclosed"] is False
    assert value["canonical"] is False
    for field in (
        "network_authority", "repository_write_authority", "credential_authority",
        "deployment_authority",
    ):
        assert value[field] is False


def test_manifest_is_byte_reproducible_across_processes(manifest) -> None:
    command = (
        "from metamorphosis.m067_body_contract import run_m067_development; "
        "print(run_m067_development().to_bytes().decode())"
    )
    completed = subprocess.run(
        [sys.executable, "-c", command], check=True, capture_output=True, text=True, timeout=120,
    )
    assert json.loads(completed.stdout) == manifest.to_dict()
