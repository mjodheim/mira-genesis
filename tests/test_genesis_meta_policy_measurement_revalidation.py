"""Adversarial regressions for semantic revalidation of retained MetaPolicy evidence."""
from __future__ import annotations

from copy import deepcopy

import pytest

from genesis import controller
from genesis import development_bodies as bodies
from genesis import meta_policy_controller as meta
from genesis import meta_policy_evolution as meta_evolution
from genesis import objective_policy_controller as opc
from genesis import policies, policy_controller, policy_mutations
from genesis import recursive_policy_fixtures as fixtures
from genesis import state as st
from genesis import trust_root as tr
from genesis.loop import Genesis

HOST = tr.provenance("host_written", produced_by="MetaPolicy revalidation fixture")
SQUARE_OBJECTIVE = (
    {"task_id": "m0", "input": 2, "expected": 4},
    {"task_id": "m1", "input": 3, "expected": 9},
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
                "generations": 32,
                "policy_mutations": 16,
                "policy_evaluations": 64,
                "meta_policy_candidates": 32,
                "meta_policy_evaluations": 128,
            }
        ),
        isolation=tr.Isolation(),
        grade=fixtures.grade_expected,
    )


def _world():
    return controller.world(
        tasks=SQUARE_OBJECTIVE,
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
        ceiling_length=1,
        max_candidates=32,
    )


def _seed_meta():
    return meta.create_meta_policy(
        (policy_mutations.create("add_operation", operation="negate"),)
    )


def _exhaust(genesis, here):
    body_run = opc.run_policy(genesis, here, seed_policy=_seed_policy(), max_steps=16)
    assert all(
        step["accepted"] is False
        for step in body_run["steps"]
        if step["intent"] == "GenerateTransform"
    )
    assert opc.exhausted(genesis, here)
    meta_run = meta.run_meta_policy(genesis, here, seed_meta_policy=_seed_meta(), max_steps=8)
    mutations = [step for step in meta_run["steps"] if step.get("intent") == "PolicyMutation"]
    assert len(mutations) == 1 and mutations[0]["accepted"] is False


def _valid_square_measurement():
    genesis = _genesis()
    here = _world()
    _exhaust(genesis, here)
    run = meta_evolution.evolve_meta_policy(genesis, here)
    assert run["accepted"] is True
    return deepcopy(
        next(
            item
            for item in run["measurements"]
            if item["added_mutation"].get("operation") == "square"
        )
    )


def _reseal(record):
    record = deepcopy(record)
    record.pop("measurement_digest", None)
    record["measurement_digest"] = tr.digest_of(record)
    return record


def _inject(genesis, observation):
    genesis.state = st.create_state(
        body_digest=genesis.state["body_digest"],
        components=genesis.state["components"],
        vocabulary=genesis.state["vocabulary"],
        tools=genesis.state["tools"],
        acquisitions=genesis.state["acquisitions"],
        observations=genesis.state["observations"] + [observation],
        generation=genesis.state["generation"],
    )


def _fresh_target():
    genesis = _genesis()
    here = _world()
    _exhaust(genesis, here)
    return genesis, here


def test_resealed_invented_score_cannot_drive_meta_policy_adoption():
    forged = _valid_square_measurement()
    forged["viable"] = True
    forged["selection_score"] = 99
    forged = _reseal(forged)

    genesis, here = _fresh_target()
    before_meta = meta.bound_meta_policy(genesis)
    before_candidates = genesis.budget.spent["meta_policy_candidates"]
    _inject(genesis, forged)

    with pytest.raises(
        meta_evolution.MetaPolicyEvolutionError,
        match="selection score does not reproduce",
    ):
        meta_evolution.evolve_meta_policy(genesis, here)

    assert meta.bound_meta_policy(genesis) == before_meta
    assert genesis.budget.spent["meta_policy_candidates"] == before_candidates


def test_resealed_sibling_meta_policy_cannot_be_installed_as_the_measured_descendant():
    forged = _valid_square_measurement()
    parent_meta = _seed_meta()
    sibling_mutation = policy_mutations.create("add_operation", operation="double")
    sibling = meta_evolution._descendant(parent_meta, sibling_mutation)
    forged["candidate_meta_policy"] = sibling
    forged["candidate_meta_policy_digest"] = sibling["meta_policy_digest"]
    forged = _reseal(forged)

    genesis, here = _fresh_target()
    before_meta = meta.bound_meta_policy(genesis)
    _inject(genesis, forged)

    with pytest.raises(
        meta_evolution.MetaPolicyEvolutionError,
        match="candidate MetaPolicy is not the one-extension descendant",
    ):
        meta_evolution.evolve_meta_policy(genesis, here)

    assert meta.bound_meta_policy(genesis) == before_meta


def test_resealed_sibling_search_policy_cannot_back_a_meta_policy_measurement():
    forged = _valid_square_measurement()
    sibling_mutation = policy_mutations.create("add_operation", operation="double")
    sibling_policy = policy_mutations.apply(_seed_policy(), sibling_mutation)
    forged["candidate_policy"] = sibling_policy
    forged = _reseal(forged)

    genesis, here = _fresh_target()
    before_meta = meta.bound_meta_policy(genesis)
    _inject(genesis, forged)

    with pytest.raises(
        meta_evolution.MetaPolicyEvolutionError,
        match="candidate search policy is not apply",
    ):
        meta_evolution.evolve_meta_policy(genesis, here)

    assert meta.bound_meta_policy(genesis) == before_meta


def test_resealed_attempt_cannot_invent_a_winning_program():
    forged = _valid_square_measurement()
    accepted = next(item for item in forged["attempts"] if item.get("accepted"))
    accepted["candidate_solved_count"] = 1
    forged["selection_score"] = 1
    forged = _reseal(forged)

    genesis, here = _fresh_target()
    _inject(genesis, forged)

    # The forged score is numerically plausible, but the retained summary is still checked against
    # its complete canonical program shell and canonical witness rather than trusted by digest alone.
    with pytest.raises(meta_evolution.MetaPolicyEvolutionError):
        meta_evolution.evolve_meta_policy(genesis, here)


def test_duplicate_retained_measurement_for_same_extension_is_refused():
    measurement = _valid_square_measurement()
    genesis, here = _fresh_target()
    _inject(genesis, measurement)
    _inject(genesis, deepcopy(measurement))

    with pytest.raises(
        meta_evolution.MetaPolicyEvolutionError,
        match="duplicate measurement",
    ):
        meta_evolution.evolve_meta_policy(genesis, here)
