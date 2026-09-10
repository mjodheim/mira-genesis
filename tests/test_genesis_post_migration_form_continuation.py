"""DEVELOPMENT regression for generated-body continuation after executable-form migration."""
from __future__ import annotations

from genesis import controller
from genesis import development_bodies as bodies
from genesis import meta_policy_controller as meta
from genesis import metamorphic_form_runtime as runtime
from genesis import migration, policies, policy_controller, policy_mutations, program_forms, programs
from genesis import recovery
from genesis import recursive_policy_fixtures as fixtures
from genesis import retentive_objectives as retentive
from genesis import state as st
from genesis import trust_root as tr
from genesis.loop import Genesis

HOST = tr.provenance("host_written", produced_by="post-migration form continuation fixture")

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


def _world(tasks):
    return controller.world(
        tasks=tasks,
        demands={},
        substrates={},
        probe_registry=bodies.PROBE_REGISTRY,
        component_operations={},
        artifacts={},
        grade=fixtures.grade_expected,
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


def _accepted_body_step(run):
    accepted = [
        step
        for step in run["steps"]
        if step.get("intent") == "GenerateTransform" and step.get("accepted")
    ]
    assert len(accepted) == 1
    return accepted[0]


def test_migrated_generated_form_survives_restart_and_produces_next_descendant(tmp_path):
    genesis = _genesis()
    admitted_root = genesis.admitted_source_sha256
    admitted_contract = genesis.evaluation_contract["contract_digest"]

    # First limitation drives the established M0 -> M1(add square) -> P1 -> B1(square) path.
    first = runtime.run_objective(
        genesis,
        _world(OBJECTIVE_ONE),
        seed_policy=_seed_policy(),
        seed_meta_policy=_seed_meta(),
        max_rounds=96,
        checkpoint_directory=tmp_path,
    )
    assert first["body_adopted"] is True
    b1 = _accepted_body_step(first)
    assert b1["program"]["operations"] == ["square"]
    assert genesis.body_factory.target == programs.PROGRAM_TARGET
    m1 = meta.bound_meta_policy(genesis)
    p1 = policy_controller.bound_policy(genesis)
    assert m1 is not None and p1 is not None

    # The target form is not handed to the translator. It is obtained through one capability whose
    # existence the lineage first has to discover under the ordinary probe budget.
    substrate = migration.Substrate(
        "portable-generated-program",
        {program_forms.REBIND_OPERATION: program_forms.portable_target_for},
    )
    probing = migration.discover(substrate, [program_forms.REBIND_OPERATION], genesis.budget)
    assert probing["found"] == [program_forms.REBIND_OPERATION]

    departure_artifact = tr.artifact_digest_of(genesis.body_factory)
    moved = migration.migrate(
        genesis,
        substrate,
        program_forms.translate_current_program,
        used_operations=[program_forms.REBIND_OPERATION],
        tasks=OBJECTIVE_ONE,
        translation_provenance=tr.provenance(
            "host_written",
            produced_by="portable generated-program translation fixture",
            detail="form change is apparatus; continuation is the property under test",
        ),
    )
    arrival_artifact = tr.artifact_digest_of(genesis.body_factory)
    assert moved["journal_continues"] is True
    assert moved["capability"]["measured"] is True
    assert moved["capability"]["preserved"] is True
    assert moved["used_operations"] == [program_forms.REBIND_OPERATION]
    assert departure_artifact["artifact_digest"] != arrival_artifact["artifact_digest"]
    assert genesis.body_factory.target == program_forms.PORTABLE_PROGRAM_TARGET
    assert tuple(genesis.body_factory.configuration["operations"]) == ("square",)

    # Kill the process boundary here conceptually: the next runtime receives only the committed
    # checkpoint. The alternate form must be reconstructed from the authenticated body artifact.
    genesis.persist(tmp_path)
    restored = recovery.restore_lineage(tmp_path, grade=fixtures.grade_expected)
    assert restored.admitted_source_sha256 == admitted_root
    assert restored.evaluation_contract["contract_digest"] == admitted_contract
    assert restored.body_factory.target == program_forms.PORTABLE_PROGRAM_TARGET
    assert tuple(restored.body_factory.configuration["operations"]) == ("square",)
    assert meta.bound_meta_policy(restored) == m1
    assert policy_controller.bound_policy(restored) == p1

    # A retained second limitation forces another machinery transition and B2=square->square. Every
    # nested program evaluation is scoped to the reconstructed current form, so the accepted B2 must
    # not fall back to genesis.programs:program_body.
    second = runtime.run_objective(
        restored,
        _world(OBJECTIVE_TWO),
        max_rounds=96,
        checkpoint_directory=tmp_path,
    )
    assert second["body_adopted"] is True
    b2 = _accepted_body_step(second)
    assert b2["program"]["operations"] == ["square", "square"]
    assert b2["body_artifact"]["configuration"]["target"] == program_forms.PORTABLE_PROGRAM_TARGET
    assert restored.body_factory.target == program_forms.PORTABLE_PROGRAM_TARGET
    assert tuple(restored.body_factory.configuration["operations"]) == ("square", "square")
    assert second["generated_form_target"] == program_forms.PORTABLE_PROGRAM_TARGET
    assert len(retentive.bound_corpus(restored)["question_digests"]) == 2

    m2 = meta.bound_meta_policy(restored)
    p2 = policy_controller.bound_policy(restored)
    assert m2 is not None and p2 is not None
    assert m2["parent_meta_policy_digest"] == m1["meta_policy_digest"]
    assert p2["parent_policy_digest"] == p1["policy_digest"]
    assert restored.admitted_source_sha256 == admitted_root
    assert restored.evaluation_contract["contract_digest"] == admitted_contract

    # The newly evolved body/form pair itself is durable too.
    restored.persist(tmp_path)
    final = recovery.restore_lineage(tmp_path, grade=fixtures.grade_expected)
    assert final.body_factory.target == program_forms.PORTABLE_PROGRAM_TARGET
    assert tuple(final.body_factory.configuration["operations"]) == ("square", "square")
    assert meta.bound_meta_policy(final) == m2
    assert policy_controller.bound_policy(final) == p2
    assert retentive.bound_corpus(final) == retentive.bound_corpus(restored)
    assert final.admitted_source_sha256 == admitted_root
    assert final.evaluation_contract["contract_digest"] == admitted_contract
