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


def _genesis(*, probes: int = 8):
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
                "probes": probes,
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



def test_campaign_refuses_forged_cursor_jump_without_journal_evidence(tmp_path):
    genesis = _genesis()
    campaign.run(
        genesis,
        _stages(),
        seed_policy=_seed_policy(),
        seed_meta_policy=_seed_meta(),
        checkpoint_directory=tmp_path,
        max_stages=0,
    )

    tools = []
    forged_cursor = None
    for tool in genesis.state["tools"]:
        if tool.get("name") == campaign.CURSOR_TOOL_NAME and tool.get("role") == campaign.CURSOR_ROLE:
            artifact = dict(tool["artifact"])
            artifact["next_stage"] = 2
            artifact["completed_stage_digests"] = list(artifact["stage_digests"][:2])
            payload = {key: value for key, value in artifact.items() if key != "cursor_digest"}
            artifact["cursor_digest"] = tr.digest_of(payload)
            forged_cursor = artifact
            tools.append({**tool, "artifact": artifact})
        else:
            tools.append(tool)
    assert forged_cursor is not None
    genesis.state = st.create_state(
        body_digest=genesis.state["body_digest"],
        components=genesis.state["components"],
        vocabulary=genesis.state["vocabulary"],
        tools=tools,
        acquisitions=genesis.state["acquisitions"],
        observations=genesis.state["observations"],
        generation=genesis.state["generation"],
    )

    with pytest.raises(campaign.MetamorphicCampaignError, match="journal transition sequence"):
        campaign.run(genesis, _stages(), checkpoint_directory=tmp_path)


def test_campaign_refuses_portable_label_rebound_to_old_interpreter(monkeypatch, tmp_path):
    genesis = _genesis()
    # The textual migration target remains genesis.program_forms:portable_program_body, but resolving
    # that symbol now yields the old per-request interpreter. The pre-repair string check accepted
    # exactly this relabel. The frozen executable artifact identity must refuse it before adoption.
    monkeypatch.setattr(program_forms, "portable_program_body", programs.program_body)
    with pytest.raises(Exception, match="relabelled a different executable"):
        campaign.run(
            genesis,
            _stages(),
            seed_policy=_seed_policy(),
            seed_meta_policy=_seed_meta(),
            max_rounds_per_objective=96,
            checkpoint_directory=tmp_path,
            max_stages=2,
        )
    assert genesis.body_factory.target != program_forms.PORTABLE_PROGRAM_TARGET



def _adaptive_stages(*, allowed_targets=(program_forms.PORTABLE_PROGRAM_TARGET,)):
    return (
        campaign.objective(_world(OBJECTIVE_ONE), name="learn-square"),
        campaign.require_form(
            _world(OBJECTIVE_ONE, with_portable_substrate=True),
            allowed_targets,
            name="adapt-form-from-environmental-constraint",
        ),
        campaign.objective(_world(OBJECTIVE_TWO), name="extend-after-selected-transition"),
    )


def test_campaign_makes_first_architectural_form_decision_by_unique_strict_maximum(tmp_path):
    genesis = _genesis()
    prefix = campaign.run(
        genesis,
        _adaptive_stages(),
        seed_policy=_seed_policy(),
        seed_meta_policy=_seed_meta(),
        max_rounds_per_objective=96,
        checkpoint_directory=tmp_path,
        max_stages=2,
    )
    assert prefix["next_stage"] == 2
    decision = prefix["executed"][1]
    assert decision["type"] == "form_requirement"
    assert decision["transition_selection"]["selection_reason"] == "unique_strict_maximum"
    assert decision["selected_action"] == "migrate:portable-generated-program"
    scores = {
        item["kind"]: item["compatibility_score"]
        for item in decision["transition_selection"]["candidates"]
    }
    assert scores["stay"] == 0
    assert scores["migrate"] == 1
    assert decision["migration_result"]["migration"]["capability"]["preserved"] is True

    restored = recovery.restore_lineage(tmp_path, grade=fixtures.grade_expected)
    resumed = campaign.run(
        restored,
        _adaptive_stages(),
        max_rounds_per_objective=96,
        checkpoint_directory=tmp_path,
    )
    assert resumed["completed"] is True
    assert resumed["metamorphosis"]["succeeded"] is True
    assert restored.body_factory.target == program_forms.PORTABLE_PROGRAM_TARGET
    assert tuple(restored.body_factory.configuration["operations"]) == ("square", "square")
    selections = [
        entry for entry in restored.journal.of_kind("observation")
        if (entry.get("payload") or {}).get("arm") == "architectural_transition_selection"
    ]
    assert len(selections) == 1


def test_form_requirement_tie_adopts_no_architectural_transition_and_does_not_advance(tmp_path):
    genesis = _genesis()
    stages = _adaptive_stages(
        allowed_targets=(programs.PROGRAM_TARGET, program_forms.PORTABLE_PROGRAM_TARGET)
    )
    record = campaign.run(
        genesis,
        stages,
        seed_policy=_seed_policy(),
        seed_meta_policy=_seed_meta(),
        max_rounds_per_objective=96,
        checkpoint_directory=tmp_path,
        max_stages=2,
    )
    assert record["next_stage"] == 1
    assert record["completed"] is False
    decision = record["executed"][-1]
    assert decision["type"] == "form_requirement"
    assert decision["transition_selection"]["accepted"] is False
    assert decision["transition_selection"]["selection_reason"] == "ambiguous_no_strict_maximum"
    assert len(genesis.journal.of_kind("migration")) == 0
    assert genesis.body_factory.target == programs.PROGRAM_TARGET


def test_form_requirement_can_select_stay_without_host_authored_migration(tmp_path):
    genesis = _genesis()
    stages = _adaptive_stages(allowed_targets=(programs.PROGRAM_TARGET,))
    record = campaign.run(
        genesis,
        stages,
        seed_policy=_seed_policy(),
        seed_meta_policy=_seed_meta(),
        max_rounds_per_objective=96,
        checkpoint_directory=tmp_path,
        max_stages=2,
    )
    assert record["next_stage"] == 2
    decision = record["executed"][1]
    assert decision["selected_action"] == "stay"
    assert decision["transition_selection"]["selection_reason"] == "unique_strict_maximum"
    assert len(genesis.journal.of_kind("migration")) == 0
    assert genesis.body_factory.target == programs.PROGRAM_TARGET



def _form_requirement_world_with_substrates(substrates):
    return controller.world(
        tasks=OBJECTIVE_ONE,
        demands={},
        substrates={item.name: item for item in substrates},
        probe_registry=bodies.PROBE_REGISTRY,
        component_operations={},
        artifacts={},
        grade=fixtures.grade_expected,
    )


def test_form_transition_scores_only_substrates_that_really_expose_rebind(tmp_path):
    genesis = _genesis()
    bad = migration.Substrate("bad-portable", {})
    good = migration.Substrate(
        "portable-generated-program",
        {program_forms.REBIND_OPERATION: program_forms.portable_target_for},
    )
    transition_world = _form_requirement_world_with_substrates((bad, good))
    stages = (
        campaign.objective(_world(OBJECTIVE_ONE), name="learn-square"),
        campaign.require_form(
            transition_world,
            (program_forms.PORTABLE_PROGRAM_TARGET,),
            name="choose-only-capable-substrate",
        ),
    )
    record = campaign.run(
        genesis,
        stages,
        seed_policy=_seed_policy(),
        seed_meta_policy=_seed_meta(),
        max_rounds_per_objective=96,
        checkpoint_directory=tmp_path,
    )
    decision = record["executed"][1]
    assert decision["selected_action"] == "migrate:portable-generated-program"
    migrations = {
        item["substrate"]: item
        for item in decision["transition_selection"]["candidates"]
        if item["kind"] == "migrate"
    }
    assert migrations["bad-portable"]["required_capability_available"] is False
    assert migrations["bad-portable"]["compatibility_score"] == 0
    assert migrations["bad-portable"]["capability_probe"]["found"] == []
    assert migrations["portable-generated-program"]["required_capability_available"] is True
    assert migrations["portable-generated-program"]["compatibility_score"] == 1
    assert migrations["portable-generated-program"]["capability_probe"]["found"] == [
        program_forms.REBIND_OPERATION
    ]
    # Both relevant candidates were measured once; execution reuses the winning probe rather than
    # charging the selected substrate a second time.
    assert genesis.budget.spent["probes"] == 2


def test_form_transition_with_only_incapable_substrate_refuses_before_execution(tmp_path):
    genesis = _genesis()
    bad = migration.Substrate("bad-portable", {})
    stages = (
        campaign.objective(_world(OBJECTIVE_ONE), name="learn-square"),
        campaign.require_form(
            _form_requirement_world_with_substrates((bad,)),
            (program_forms.PORTABLE_PROGRAM_TARGET,),
            name="no-capable-transition",
        ),
    )
    record = campaign.run(
        genesis,
        stages,
        seed_policy=_seed_policy(),
        seed_meta_policy=_seed_meta(),
        max_rounds_per_objective=96,
        checkpoint_directory=tmp_path,
    )
    assert record["next_stage"] == 1
    decision = record["executed"][-1]
    assert decision["transition_selection"]["selection_reason"] == "no_viable_architectural_transition"
    assert decision["transition_selection"]["accepted"] is False
    assert len(genesis.journal.of_kind("migration")) == 0
    assert genesis.budget.spent["probes"] == 1


def test_form_transition_refuses_incomplete_probe_round_before_first_spend(tmp_path):
    genesis = _genesis(probes=1)
    first = migration.Substrate(
        "portable-a",
        {program_forms.REBIND_OPERATION: program_forms.portable_target_for},
    )
    second = migration.Substrate(
        "portable-b",
        {program_forms.REBIND_OPERATION: program_forms.portable_target_for},
    )
    stages = (
        campaign.objective(_world(OBJECTIVE_ONE), name="learn-square"),
        campaign.require_form(
            _form_requirement_world_with_substrates((first, second)),
            (program_forms.PORTABLE_PROGRAM_TARGET,),
            name="complete-probe-round-required",
        ),
    )
    with pytest.raises(
        campaign.MetamorphicCampaignError,
        match="complete architectural transition comparison requires 2 probe units",
    ):
        campaign.run(
            genesis,
            stages,
            seed_policy=_seed_policy(),
            seed_meta_policy=_seed_meta(),
            max_rounds_per_objective=96,
            checkpoint_directory=tmp_path,
        )
    assert genesis.budget.spent["probes"] == 0
    selections = [
        entry
        for entry in genesis.journal.of_kind("observation")
        if (entry.get("payload") or {}).get("arm") == "architectural_transition_selection"
    ]
    assert selections == []
