"""Adversarial regressions for non-redrawable MetaPolicy round budgets."""
from __future__ import annotations

import pytest

from genesis import controller
from genesis import development_bodies as bodies
from genesis import durable_meta_policy_evolution as durable
from genesis import meta_policy_controller as meta
from genesis import objective_policy_controller as opc
from genesis import policies, policy_mutations, recovery
from genesis import recursive_policy_fixtures as fixtures
from genesis import state as st
from genesis import trust_root as tr
from genesis.loop import Genesis

HOST = tr.provenance("host_written", produced_by="durable MetaPolicy budget fixture")
SQUARE_OBJECTIVE = (
    {"task_id": "m0", "input": 2, "expected": 4},
    {"task_id": "m1", "input": 3, "expected": 9},
)


class SimulatedProcessDeath(BaseException):
    pass


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


def _exhaust(genesis, here, directory):
    body = opc.run_policy(
        genesis,
        here,
        seed_policy=_seed_policy(),
        max_steps=16,
        checkpoint_directory=directory,
    )
    generated = [step for step in body["steps"] if step["intent"] == "GenerateTransform"]
    assert generated and all(step["accepted"] is False for step in generated)
    assert opc.exhausted(genesis, here)
    meta_run = meta.run_meta_policy(
        genesis,
        here,
        seed_meta_policy=_seed_meta(),
        max_steps=8,
        checkpoint_directory=directory,
    )
    mutations = [step for step in meta_run["steps"] if step.get("intent") == "PolicyMutation"]
    assert len(mutations) == 1 and mutations[0]["accepted"] is False


def _round(genesis):
    records = [
        item
        for item in genesis.state["observations"]
        if item.get("kind") == durable.ROUND_KIND
    ]
    assert len(records) == 1
    return records[0]


def test_normal_durable_round_pays_each_physical_slot_once(tmp_path):
    genesis = _genesis()
    here = _world()
    _exhaust(genesis, here, tmp_path)
    before_candidates = genesis.budget.spent["meta_policy_candidates"]
    before_evaluations = genesis.budget.spent["meta_policy_evaluations"]

    run = durable.evolve_meta_policy(genesis, here, checkpoint_directory=tmp_path)

    assert run["accepted"] is True
    record = _round(genesis)
    assert record["status"] == "completed"
    reserved = record["reserved"]
    assert genesis.budget.spent["meta_policy_candidates"] - before_candidates == reserved["meta_policy_candidates"]
    assert genesis.budget.spent["meta_policy_evaluations"] - before_evaluations == reserved["meta_policy_evaluations"]
    assert reserved["meta_policy_candidates"] > 0
    assert reserved["meta_policy_evaluations"] > 0

    restored = recovery.restore_lineage(tmp_path, grade=fixtures.grade_expected)
    assert restored.budget.spent == genesis.budget.spent
    assert _round(restored)["status"] == "completed"


def test_crash_after_reservation_but_before_charge_is_safe_to_resume(tmp_path, monkeypatch):
    genesis = _genesis()
    here = _world()
    _exhaust(genesis, here, tmp_path)
    original_charge = durable._charge

    def die_before_charge(*_args, **_kwargs):
        raise SimulatedProcessDeath()

    monkeypatch.setattr(durable, "_charge", die_before_charge)
    with pytest.raises(SimulatedProcessDeath):
        durable.evolve_meta_policy(genesis, here, checkpoint_directory=tmp_path)

    restored = recovery.restore_lineage(tmp_path, grade=fixtures.grade_expected)
    record = _round(restored)
    assert record["status"] == "reserved"
    assert restored.budget.spent["meta_policy_candidates"] == record["budget_before"]["meta_policy_candidates"]
    assert restored.budget.spent["meta_policy_evaluations"] == record["budget_before"]["meta_policy_evaluations"]

    monkeypatch.setattr(durable, "_charge", original_charge)
    run = durable.evolve_meta_policy(restored, here, checkpoint_directory=tmp_path)
    assert run["accepted"] is True
    assert _round(restored)["status"] == "completed"


def test_crash_after_durable_charge_never_refunds_or_redraws_round(tmp_path, monkeypatch):
    genesis = _genesis()
    here = _world()
    _exhaust(genesis, here, tmp_path)
    original_evolve = durable.evolution.evolve_meta_policy

    def die_after_charge(*_args, **_kwargs):
        raise SimulatedProcessDeath()

    monkeypatch.setattr(durable.evolution, "evolve_meta_policy", die_after_charge)
    with pytest.raises(SimulatedProcessDeath):
        durable.evolve_meta_policy(genesis, here, checkpoint_directory=tmp_path)

    restored = recovery.restore_lineage(tmp_path, grade=fixtures.grade_expected)
    charged = _round(restored)
    assert charged["status"] == "charged"
    candidate_spent = restored.budget.spent["meta_policy_candidates"]
    evaluation_spent = restored.budget.spent["meta_policy_evaluations"]
    assert candidate_spent == charged["budget_after"]["meta_policy_candidates"]
    assert evaluation_spent == charged["budget_after"]["meta_policy_evaluations"]
    assert candidate_spent > charged["budget_before"]["meta_policy_candidates"]
    assert evaluation_spent > charged["budget_before"]["meta_policy_evaluations"]
    assert not [
        item
        for item in restored.state["observations"]
        if item.get("kind") == durable.evolution.MEASUREMENT_KIND
    ]

    monkeypatch.setattr(durable.evolution, "evolve_meta_policy", original_evolve)
    with pytest.raises(
        durable.DurableMetaPolicyEvolutionError,
        match="redraw is refused",
    ):
        durable.evolve_meta_policy(restored, here, checkpoint_directory=tmp_path)

    assert restored.budget.spent["meta_policy_candidates"] == candidate_spent
    assert restored.budget.spent["meta_policy_evaluations"] == evaluation_spent
    assert _round(restored)["status"] == "crash_incomplete"
