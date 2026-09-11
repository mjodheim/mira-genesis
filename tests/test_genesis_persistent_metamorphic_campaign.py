"""DEVELOPMENT regression for one persistent campaign spanning form change and later evolution."""
from __future__ import annotations

import pytest

from genesis import controller
from genesis import development_bodies as bodies
from genesis import meta_policy_controller as meta
from genesis import metamorphic_campaign as campaign
from genesis import migration, policies, policy_controller, policy_mutations, program_forms, programs
from genesis import recovery
from genesis import recursive_policy_fixtures as fixtures
from genesis import retentive_objectives as retentive
from genesis import state as st
from genesis import trust_root as tr
from genesis.loop import Genesis

HOST = tr.provenance("host_written", produced_by="persistent metamorphic campaign fixture")

OBJECTIVE_ONE = (
    {"task_id": "m0", "input": 1, "expected": 1},
)
OBJECTIVE_TWO = (
    *OBJECTIVE_ONE,
    {"task_id": "m1", "input": 2, "expected": 16},
)


def _state():
    return st.create_state(
        body_digest=tr.artifact_digest_of(fixtures.null_body)["artifact_digest"],
        components=[
            {
                "name": "operator_table",
                "origin": "seed",
                "certificate": None,
                "provenance": HOST,
            }
        ],
        vocabulary=[{"name": "axis_progress", "origin": "seed", "certificate": None}],
    )


def _genesis():
    return Genesis(
        state=_state(),
        body_factory=fixtures.null_body,
        budget=tr.Budget(
            limits={
                "generations": 96,
                "policy_mutations": 64,
                "policy_evaluations": 256,
                "meta_policy_candidates": 64,
                "meta_policy_evaluations": 256,
                "probes": 8,
            }
        ),
        isolation=tr.Isolation(),
        grade=fixtures.grade_expected,
    )


def _world(tasks, *, with_portable_substrate: bool = False, rebind=None):
    substrates = {}
    if with_portable_substrate:
        substrates["portable-generated-program"] = migration.Substrate(
            "portable-generated-program",
            {
                program_forms.REBIND_OPERATION: rebind
                if rebind is not None
                else program_forms.portable_target_for
            },
        )
    return controller.world(
        tasks=tasks,
        demands={},
        substrates=substrates,
        probe_registry=bodies.PROBE_REGISTRY,
        component_operations={},
        artifacts={},
        grade=fixtures.grade_expected,
    )


def _stages(*, rebind=None):
    return (
        campaign.objective(_world(OBJECTIVE_ONE), name="learn-square"),
        campaign.form_migration(
            _world(OBJECTIVE_ONE, with_portable_substrate=True, rebind=rebind),
            "portable-generated-program",
            name="change-executable-form",
        ),
        campaign.objective(_world(OBJECTIVE_TWO), name="extend-after-migration"),
    )


def _seed_policy():
    return policies.create(
        registry_reference=bodies.PROBE_REGISTRY,
        operation_names=("increment",),
        max_length=1,
        ceiling_length=2,
        max_candidates=64,
    )


def _seed_meta():
    return meta.create_meta_policy(
        (policy_mutations.create("add_operation", operation="negate"),)
    )


def test_campaign_cursor_owns_migration_handoff_and_resumes_after_process_death(tmp_path):
    genesis = _genesis()
    admitted_root = genesis.admitted_source_sha256
    admitted_contract = genesis.evaluation_contract["contract_digest"]

    # One runtime call performs objective 1 and the form transition. max_stages is only a kill bound;
    # the persisted cursor, not this caller, records that objective 2 is what comes next.
    prefix = campaign.run(
        genesis,
        _stages(),
        seed_policy=_seed_policy(),
        seed_meta_policy=_seed_meta(),
        max_rounds_per_objective=96,
        checkpoint_directory=tmp_path,
        max_stages=2,
    )
    assert prefix["completed"] is False
    assert prefix["next_stage"] == 2
    assert [step["type"] for step in prefix["executed"]] == ["objective", "form_migration"]
    assert prefix["migration"]["capability"]["preserved"] is True
    assert prefix["metamorphosis"]["succeeded"] is False
    assert prefix["metamorphosis"]["accepted_after_migration"] == 0
    assert genesis.body_factory.target == program_forms.PORTABLE_PROGRAM_TARGET
    assert tuple(genesis.body_factory.configuration["operations"]) == ("square",)
    assert len(genesis.journal.of_kind("migration")) == 1
    probes_after_migration = genesis.budget.spent["probes"]
    assert probes_after_migration == 1

    # New process, new World objects and a fresh Substrate object. The campaign identity ignores
    # mutable discovery state but binds the substrate operation's executable artifact, so this is the
    # same environmental campaign rather than ambient process memory.
    restored = recovery.restore_lineage(tmp_path, grade=fixtures.grade_expected)
    resumed = campaign.run(
        restored,
        _stages(),
        max_rounds_per_objective=96,
        checkpoint_directory=tmp_path,
    )
    assert resumed["campaign_digest"] == prefix["campaign_digest"]
    assert resumed["completed"] is True
    assert resumed["next_stage"] == 3
    assert len(resumed["executed"]) == 1
    assert resumed["executed"][0]["index"] == 2
    assert resumed["executed"][0]["type"] == "objective"
    assert len(restored.journal.of_kind("migration")) == 1
    assert restored.budget.spent["probes"] == probes_after_migration

    assert restored.body_factory.target == program_forms.PORTABLE_PROGRAM_TARGET
    assert tuple(restored.body_factory.configuration["operations"]) == ("square", "square")
    assert len(retentive.bound_corpus(restored)["question_digests"]) == 2
    assert resumed["metamorphosis"]["succeeded"] is True
    assert resumed["metamorphosis"]["accepted_after_migration"] == 1
    assert resumed["metamorphosis"]["causally_established_after_migration"] == 1
    assert resumed["metamorphosis"]["is_transported_intelligence_rather_than_transported_output"] is True

    causal = restored.state["acquisitions"][-1]["causal_dependency"]
    assert causal["established"] is True
    assert causal["newly_solved_lost_without_acquisition"] == ["m1"]
    m2 = meta.bound_meta_policy(restored)
    p2 = policy_controller.bound_policy(restored)
    assert m2 is not None and m2["parent_meta_policy_digest"]
    assert p2 is not None and p2["parent_policy_digest"]
    assert restored.admitted_source_sha256 == admitted_root
    assert restored.evaluation_contract["contract_digest"] == admitted_contract

    # Completion is itself resumable. A third process presented with the same environment executes
    # no stage again, spends no probe again and reconstructs the same metamorphosis verdict from the
    # retained migration plus post-migration acquisition records.
    final = recovery.restore_lineage(tmp_path, grade=fixtures.grade_expected)
    again = campaign.run(final, _stages(), checkpoint_directory=tmp_path)
    assert again["completed"] is True
    assert again["executed"] == []
    assert again["campaign_digest"] == resumed["campaign_digest"]
    assert again["metamorphosis"] == resumed["metamorphosis"]
    assert final.budget.spent["probes"] == probes_after_migration
    assert final.body_factory.target == program_forms.PORTABLE_PROGRAM_TARGET


def test_campaign_identity_binds_substrate_operation_code_after_restart(tmp_path):
    genesis = _genesis()
    campaign.run(
        genesis,
        _stages(),
        seed_policy=_seed_policy(),
        seed_meta_policy=_seed_meta(),
        max_rounds_per_objective=96,
        checkpoint_directory=tmp_path,
        max_stages=1,
    )
    restored = recovery.restore_lineage(tmp_path, grade=fixtures.grade_expected)

    # Same substrate/operation name, different executable. Without the operation artifact in the
    # campaign identity this would silently become "the same" future migration after process death.
    with pytest.raises(campaign.MetamorphicCampaignError, match="different campaign"):
        campaign.run(
            restored,
            _stages(rebind=fixtures.grade_expected),
            checkpoint_directory=tmp_path,
        )


def test_campaign_refuses_world_registry_different_from_seed_search_machinery(tmp_path):
    genesis = _genesis()
    wrong_world = controller.world(
        tasks=OBJECTIVE_ONE,
        demands={},
        substrates={},
        probe_registry="genesis.development_bodies:SUBSTRATE_OPERATIONS",
        component_operations={},
        artifacts={},
        grade=fixtures.grade_expected,
    )
    with pytest.raises(campaign.MetamorphicCampaignError, match="differs from held search-policy"):
        campaign.run(
            genesis,
            (campaign.objective(wrong_world),),
            seed_policy=_seed_policy(),
            seed_meta_policy=_seed_meta(),
            checkpoint_directory=tmp_path,
        )
    assert genesis.state["generation"] == 0



def _forge_cursor(genesis, stages, *, next_stage):
    admitted = campaign.campaign_record(genesis, stages)
    stage_digests = list(admitted["stage_digests"])
    payload = {
        "schema": campaign.CURSOR_SCHEMA,
        "campaign_digest": admitted["campaign_digest"],
        "stage_digests": stage_digests,
        "completed_stage_digests": stage_digests[:next_stage],
        "next_stage": next_stage,
        "migration": None,
        "acquisition_count_at_migration": None,
    }
    forged = {**payload, "cursor_digest": tr.digest_of(payload)}
    tools = []
    for tool in genesis.state["tools"]:
        if tool.get("name") == campaign.CURSOR_TOOL_NAME and tool.get("role") == campaign.CURSOR_ROLE:
            tools.append({**tool, "artifact": forged})
        else:
            tools.append(tool)
    genesis.state = st.create_state(
        body_digest=genesis.state["body_digest"],
        components=genesis.state["components"],
        vocabulary=genesis.state["vocabulary"],
        tools=tools,
        acquisitions=genesis.state["acquisitions"],
        observations=genesis.state["observations"],
        generation=genesis.state["generation"],
    )


def test_campaign_refuses_resealed_cursor_that_skips_objective_without_journal_evidence():
    genesis = _genesis()
    stages = _stages()
    admitted = campaign.run(
        genesis,
        stages,
        seed_policy=_seed_policy(),
        seed_meta_policy=_seed_meta(),
        max_stages=0,
    )
    assert admitted["next_stage"] == 0

    # Structurally exact prefix + freshly recomputed cursor digest.  Before this repair the cursor
    # was accepted and stage 0 could be skipped because objective stages had no journal binding.
    _forge_cursor(genesis, stages, next_stage=1)
    with pytest.raises(campaign.MetamorphicCampaignError, match="journal evidence"):
        campaign.run(genesis, stages, max_stages=0)


def test_campaign_refuses_resealed_cursor_rollback_despite_valid_prefix():
    genesis = _genesis()
    stages = _stages()
    progressed = campaign.run(
        genesis,
        stages,
        seed_policy=_seed_policy(),
        seed_meta_policy=_seed_meta(),
        max_rounds_per_objective=96,
        max_stages=1,
    )
    assert progressed["next_stage"] == 1

    # The forged cursor is internally valid for stage zero, but the journal proves that stage one
    # was already committed.  Rollback cannot erase spent work or reopen an earlier campaign path.
    _forge_cursor(genesis, stages, next_stage=0)
    with pytest.raises(campaign.MetamorphicCampaignError, match="journal evidence"):
        campaign.run(genesis, stages, max_stages=0)
