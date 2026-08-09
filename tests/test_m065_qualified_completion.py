from __future__ import annotations

import inspect

import pytest

import metamorphosis.m065_qualified_completion as m065


@pytest.fixture(scope="session")
def manifests():
    return [m065.run_m065_development(index) for index in range(len(m065.M065_TASK_BANK))]


def test_all_precommitted_banks_keep_the_m064_scientific_outcome(manifests) -> None:
    for value in manifests:
        mapping = value.to_dict()
        base = mapping["base_manifest"]
        assert base["strict_held_out_advantage"] is True
        assert base["complete_final_version"] == 12
        assert base["complete_final_retained_passed"] == 68
        assert base["arm_results"]["complete_continued_lineage"]["held_out_quality"] == {
            "hidden_passes": 18,
            "hidden_total": 18,
            "exact": True,
        }
        for name in m065.M065_PROTOCOL["arms"][1:]:
            assert base["arm_results"][name]["held_out_quality"]["hidden_passes"] == 0


def test_rollback_receipt_binds_corrupted_and_restored_states(manifests) -> None:
    for value in manifests:
        receipt = value.to_dict()["base_manifest"]["forced_rollback"]
        assert receipt["exact_restoration"] is True
        assert receipt["rollback_operation"] == "deserialize_and_audit_pretransaction_snapshot"
        assert receipt["restored_object_is_distinct"] is True
        assert receipt["restoration_verified_against_pre_fault_snapshot"] is True
        assert receipt["before_digest"] == receipt["after_digest"]
        assert receipt["corrupted_state_digest"] != receipt["after_digest"]


def test_corrected_rollback_restores_the_returned_object_not_the_saved_input() -> None:
    source = inspect.getsource(m065._adopt_candidate)
    assert "restored = _restore_snapshot(before_bytes, before_digest)" in source
    assert "_canonical_json(before) == before_bytes" not in source


def test_m065_changes_no_bank_budget_threshold_or_substrate() -> None:
    protocol = m065.M065_PROTOCOL
    assert protocol["base_protocol_sha256"] == m065.whole.M064_PROTOCOL.digest()
    assert protocol["task_bank_commitment"] == m065.whole.M064_PROTOCOL.task_bank_commitment
    assert protocol["candidate_budget_per_arm_cycle"] == 8_192
    assert protocol["accepted_post_migration_cycles"] == 3
    assert protocol["arms"] == list(m065.whole.M064_PROTOCOL.arms)


def test_m064_failed_qualification_is_preserved_in_every_manifest(manifests) -> None:
    for value in manifests:
        mapping = value.to_dict()
        assert mapping["m064_failed_parent_commit"] == "ec92af78b57203d32c2ee504db91b4166ec83fdf"
        assert mapping["m064_failed_qualification_run"] == 31281234286


def test_m065_marker_selection_is_deterministic_and_uses_new_protocol_digest() -> None:
    parent = "1" * 40
    assert m065.select_task_bank(parent) == m065.select_task_bank(parent)
    assert 0 <= m065.select_task_bank(parent) < len(m065.M065_TASK_BANK)
    with pytest.raises(m065.M065Error):
        m065.select_task_bank("not-a-sha")


def test_development_result_cannot_authorise_release_or_canonical_execution(manifests) -> None:
    for value in manifests:
        mapping = value.to_dict()
        assert mapping["canonical_workflow_authorised"] is False
        assert mapping["repository_write_authority_granted_to_lineage"] is False
