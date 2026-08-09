from __future__ import annotations

import inspect
import json
from pathlib import Path
import subprocess
import sys

import pytest

import metamorphosis.m068_open_command_induction as m068


@pytest.fixture(scope="session")
def source_evidence():
    return m068.observe_source_evidence()


@pytest.fixture(scope="session")
def manifest():
    return m068.run_m068_development()


def test_live_attestation_matches_the_prelearner_freeze() -> None:
    assert m068.attest_body_bank() == m068.FROZEN_ATTESTATION
    assert m068.M068_PROTOCOL.digest() == "2c9296b8232e2ff8b8a74cdb8bc0af6b724dcb324378be2ee3a33fe783ff22b7"


def test_complete_generic_word_language_is_enumerated_once_in_frozen_order() -> None:
    words = m068.enumerate_command_words()
    assert len(words) == len(set(words)) == 37_448
    assert words[:8] == tuple((action,) for action in m068.ACTION_HANDLES)
    assert all(len(left) <= len(right) for left, right in zip(words, words[1:]))
    assert set(words[-1]) <= set(m068.ACTION_HANDLES)
    assert len(words[-1]) == 5


def test_source_targets_are_observed_from_version_eight(source_evidence) -> None:
    assert source_evidence.lineage_version == 8
    assert len(source_evidence.public_cases) == 20
    assert len(source_evidence.hidden_cases) == 12
    assert tuple(sorted(source_evidence.profiles())) == m068.SKILLS
    assert [(tool["tool_name"], tool["origin"]) for tool in source_evidence.tools] == [
        ("add", "founder"),
        ("max", "synthesized"),
        ("mean", "synthesized"),
        ("mul", "founder"),
    ]
    public_domain = {(case.skill, case.args) for case in source_evidence.public_cases}
    hidden_domain = {(case.skill, case.args) for case in source_evidence.hidden_cases}
    assert not public_domain & hidden_domain


def test_discovery_api_has_no_hidden_input_and_does_not_read_target_source() -> None:
    parameters = inspect.signature(m068.discover_public_class).parameters
    assert tuple(parameters) == ("body_handle", "public_cases", "diagnostic_profiles", "protocol")
    assert not any("hidden" in name for name in parameters)
    learner_source = Path(m068.__file__).read_text(encoding="utf-8")
    assert "RUNTIME_PATH.read_text" not in learner_source
    assert "RUNTIME_PATH.read_bytes" not in learner_source
    assert "open(RUNTIME_PATH" not in learner_source


def test_one_unchanged_learner_discovers_every_frozen_body(manifest) -> None:
    value = manifest.to_dict()
    assert value["all_precommitted_bodies_discovered"] is True
    assert value["all_public_classes_passed_hidden"] is True
    assert value["distinct_command_languages_discovered"] == 4
    assert set(value["body_results"]) == set(m068.BODY_HANDLES)
    for result in value["body_results"].values():
        assert result["complete_word_count"] == 37_448
        assert result["accepted_word_count"] == 4
        assert result["public_candidate_class_size"] == 1
        assert result["language_scan_attempts"] == 37_448
        assert result["additional_diagnostic_attempts"] == 4
        assert result["public_validation_attempts"] == 20
        assert result["public_discovery_attempts"] == 37_472
        assert result["hidden_validation_attempts"] == 12
        assert result["all_public_survivors_passed_hidden"] is True
        assert set(result["hidden_results"].values()) == {True}


def test_every_preregistered_control_rejects(manifest) -> None:
    expected = {
        "declaration_order_actions_passed": False,
        "lexical_semantic_assignment_passed": False,
        "empty_transcript_status": "insufficient_evidence",
        "empty_transcript_adapter_count": 0,
        "corrupted_source_observation_status": "no_survivor",
        "corrupted_source_observation_adapter_count": 0,
        "unknown_action_rejected": True,
        "non_command_word_rejected": True,
        "semantic_assignment_mutation_passed_hidden": False,
        "learner_inspected_target_source": False,
    }
    for result in manifest.to_dict()["body_results"].values():
        assert result["controls"] == expected


def test_empty_transcript_and_unknown_body_fail_closed(source_evidence) -> None:
    outcome = m068.discover_public_class(
        m068.BODY_HANDLES[0], (), source_evidence.profiles(),
    )
    assert outcome.status == "insufficient_evidence"
    assert outcome.candidate_class == ()
    assert outcome.attempts == 0
    with pytest.raises(m068.M068Error, match="unknown opaque body"):
        m068.discover_public_class("vessel-not-in-bank", source_evidence.public_cases, source_evidence.profiles())


def test_hidden_validator_rejects_swapped_semantics(source_evidence, manifest) -> None:
    record = manifest.to_dict()["body_results"][m068.BODY_HANDLES[0]]["selected_adapter"]["assignments"]
    assignments = [(skill, tuple(word)) for skill, word in sorted(record.items())]
    assignments[0] = (assignments[0][0], tuple(record[assignments[1][0]]))
    assignments[1] = (assignments[1][0], tuple(record["add"]))
    mutated = m068.CommandAdapter(tuple(assignments))
    validation = m068.independently_validate_hidden_class(
        m068.BODY_HANDLES[0], (mutated,), source_evidence.hidden_cases,
    )
    assert validation.all_survivors_passed is False
    assert validation.selected is None
    assert dict(validation.results)[mutated.digest()] is False


def test_manifest_uses_tamper_evident_core_memory_and_keeps_claim_limits(manifest) -> None:
    value = manifest.to_dict()
    assert value["evidence_memory_schema"] == "mira-memory-ledger-v1"
    assert value["evidence_memory_event_count"] == 6
    assert len(value["evidence_memory_digest"]) == 64
    assert value["descriptor_product_grammar_supplied"] is False
    assert value["complete_target_adapter_supplied"] is False
    assert value["generic_bounded_word_language"] is True
    assert value["target_bank_frozen_before_learner"] is True
    assert value["external_target_authorship"] is False
    assert value["arbitrary_protocol_induction"] is False
    assert value["general_intelligence_claimed"] is False
    assert value["canonical"] is False
    for authority in (
        "network_authority", "repository_write_authority", "credential_authority",
        "deployment_authority",
    ):
        assert value[authority] is False


def test_manifest_is_byte_reproducible_across_processes(manifest) -> None:
    command = (
        "from metamorphosis.m068_open_command_induction import run_m068_development; "
        "print(run_m068_development().to_bytes().decode())"
    )
    completed = subprocess.run(
        [sys.executable, "-c", command], check=True, capture_output=True, text=True, timeout=120,
    )
    assert json.loads(completed.stdout) == manifest.to_dict()
