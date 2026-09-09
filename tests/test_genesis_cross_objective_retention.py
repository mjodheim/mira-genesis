"""DEVELOPMENT regressions for retention across successive policy objectives."""
from __future__ import annotations

import pytest

from genesis import controller
from genesis import development_bodies as bodies
from genesis import policies, policy_controller, recovery
from genesis import recursive_policy_fixtures as fixtures
from genesis import retentive_objectives as retentive
from genesis import state as st
from genesis import trust_root as tr
from genesis.artifacts import ConfiguredBody
from genesis.loop import Genesis

HOST = tr.provenance("host_written", produced_by="cross-objective retention fixture")


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
            limits={"generations": 40, "policy_updates": 2, "policy_evaluations": 16}
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
        operation_names=("increment", "square"),
        max_length=1,
        ceiling_length=3,
        max_candidates=32,
    )


def _reach_first_descendant(genesis, *, directory=None):
    here = _world(fixtures.OBJECTIVE_ONE)
    retentive.run_policy(
        genesis,
        here,
        seed_policy=_seed_policy(),
        max_steps=4,
        checkpoint_directory=directory,
    )
    retentive.expand_policy(genesis, here, checkpoint_directory=directory)
    result = retentive.run_policy(
        genesis,
        here,
        max_steps=4,
        checkpoint_directory=directory,
    )
    assert any(step.get("accepted") for step in result["steps"])
    return here


def test_later_objective_cannot_drop_a_previously_retained_question():
    genesis = _genesis()
    _reach_first_descendant(genesis)
    corpus = retentive.bound_corpus(genesis)
    assert corpus is not None
    assert len(corpus["question_digests"]) == 2

    # A tempting new objective that contains only the new requirement would let the next candidate
    # forget r0/r1 because the ordinary per-cycle retention check could no longer see them.
    narrower = _world((fixtures.OBJECTIVE_TWO[-1],))
    generation = genesis.state["generation"]
    spent = dict(genesis.budget.spent)
    with pytest.raises(retentive.RetentionObjectiveError, match="removes 2 retained"):
        retentive.run_policy(genesis, narrower, max_steps=1)
    assert genesis.state["generation"] == generation
    assert genesis.budget.spent == spent


def test_retention_identity_ignores_task_labels_but_not_question_or_target_contents():
    genesis = _genesis()
    _reach_first_descendant(genesis)

    relabelled = tuple(
        {**task, "task_id": "renamed-%d" % index}
        for index, task in enumerate(fixtures.OBJECTIVE_ONE)
    )
    retentive.assert_retains_prior_work(genesis, _world(relabelled))

    changed_target = list(relabelled)
    changed_target[0] = {**changed_target[0], "expected": 999}
    with pytest.raises(retentive.RetentionObjectiveError, match="removes 1 retained"):
        retentive.assert_retains_prior_work(genesis, _world(changed_target))


def test_recursive_policy_evolution_advances_the_retention_corpus_and_survives_restart(tmp_path):
    genesis = _genesis()
    first = _reach_first_descendant(genesis, directory=tmp_path)
    first_corpus = retentive.bound_corpus(genesis)
    assert first_corpus is not None
    assert len(first_corpus["question_digests"]) == 2

    second = _world(fixtures.OBJECTIVE_TWO)
    # The second objective is admissible precisely because it contains both old questions plus the
    # new one. Every later candidate is therefore scored on the old work too.
    retentive.run_policy(genesis, second, max_steps=8, checkpoint_directory=tmp_path)
    assert retentive.exhausted(genesis, second) is True
    update = retentive.expand_policy(genesis, second, checkpoint_directory=tmp_path)
    assert update["accepted"] is True
    final = retentive.run_policy(genesis, second, max_steps=7, checkpoint_directory=tmp_path)
    assert any(step.get("accepted") for step in final["steps"])

    corpus = retentive.bound_corpus(genesis)
    assert corpus is not None
    assert len(corpus["question_digests"]) == 3
    assert corpus["objective"]["objective_digest"] != first_corpus["objective"]["objective_digest"]
    assert isinstance(genesis.body_factory, ConfiguredBody)
    assert genesis.body_factory.configuration["operations"] == (
        "square",
        "increment",
        "increment",
    )

    restored = recovery.restore_lineage(tmp_path, grade=fixtures.grade_expected)
    restored_corpus = retentive.bound_corpus(restored)
    assert restored_corpus == corpus
    assert policy_controller.bound_policy(restored)["max_length"] == 3

    with pytest.raises(retentive.RetentionObjectiveError, match="retained"):
        retentive.expand_policy(restored, first)
