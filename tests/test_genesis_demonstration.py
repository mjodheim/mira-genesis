"""Lock the end-to-end Genesis demonstration and the diagnosis machinery that drives it.

The stopping criterion is not that the components exist. It is that **one lineage** measures itself,
diagnoses itself, transforms itself, verifies the transformation, adopts or rejects it on evidence,
keeps what it learned, extends the machinery that enables later transformations, changes form, and
goes on evolving in the new form. These tests assert each of those on the same run.
"""
from __future__ import annotations

import pytest

from genesis import development_bodies as bodies
from genesis import diagnosis
from genesis import state as st
from genesis import trust_root as tr
from genesis.sandbox import run_candidate
from scripts.run_genesis_demonstration import TASKS, causal_step, demonstrate


@pytest.fixture(scope="module")
def record():
    return demonstrate()


def _step(record, name):
    for step in record["steps"]:
        if step["step"] == name:
            return step
    raise AssertionError("the demonstration never reached step %r" % name)


# -- the demonstration, step by step --------------------------------------------------------------

def test_the_demonstration_claims_nothing_scientific(record):
    assert record["development"] is True
    assert record["is_a_scientific_observation"] is False
    assert record["advances_a_generality_gate"] is False
    assert record["frozen"] is False


def test_a_rejection_does_not_end_the_run_and_is_kept(record):
    step = _step(record, "rejected_candidate_does_not_end_the_run")
    assert step["accepted"] is False
    assert step["observations_kept"] == 1


def test_a_transformation_is_adopted_on_evidence(record):
    step = _step(record, "candidate_accepted_on_evidence")
    assert step["accepted"] is True
    assert step["acquisitions"] == 1


def test_the_lineage_names_a_component_class_it_did_not_have(record):
    """The first authored ceiling, opened by the lineage rather than by editing a tuple."""
    step = _step(record, "lineage_names_a_component_class_it_did_not_have")
    assert step["registry_exhausted"] is True
    assert step["probed"] == ["operator_table", "signal_interface"]
    assert step["registry_after"][-1] == "joint_registry"
    assert record["final_components"] == [
        "operator_table",
        "signal_interface",
        "joint_registry",
    ]


def test_the_lineage_extends_its_own_diagnostic_vocabulary(record):
    """The second ceiling: extended on a demonstrated confusable pair, not on a whim."""
    step = _step(record, "lineage_extends_its_own_diagnostic_vocabulary")
    assert step["limiting_components"] == ["operator_table", "signal_interface"]
    assert step["vocabulary_after"][-1] == "joint_constraint_undetermined"


def test_the_substrate_is_discovered_and_the_lineage_arrives_intact(record):
    step = _step(record, "substrate_semantics_discovered_then_migrated")
    assert step["found"] == ["read", "list"]
    assert step["missing"] == ["write", "transact"]
    assert step["journal_continues"] is True
    assert step["nothing_lost"] is True


def test_the_lineage_evolves_again_in_its_new_form(record):
    """Transported intelligence rather than transported output. This is the whole objective."""
    step = _step(record, "evolved_again_in_the_new_form")
    assert step["metamorphosis_succeeded"] is True
    assert step["accepted_after_migration"] == 1
    assert step["transported_intelligence"] is True


def test_a_later_generation_needed_the_earlier_acquisition(record):
    step = _step(record, "causal_dependency_between_generations")
    assert step["supported"] is True
    assert step["solved_without_acquisition"] < step["solved_with_acquisition"]
    assert step["equal_budget"] is True
    assert step["ablated_arm_ran_separately"] is True
    # Without this the "ablation" is the parent arm, and the comparison merely repeats the verdict
    # that accepted the candidate.
    assert step["ablated_arm_differs_from_the_parent_arm"] is True
    assert step["establishes_causal_dependency"] is True
    assert step["why_not"] == ""


def test_the_ablated_arm_is_the_candidate_minus_the_acquisition_and_nothing_else():
    """The record only *states* how the arm was built. This checks it."""
    candidate = bodies.migrated_improved_body()
    ablated = bodies.migrated_ablated_body()
    assert ablated.solves == candidate.solves
    assert ablated.operation_names == candidate.operation_names
    assert ablated.routed == candidate.routed
    assert candidate.capabilities == frozenset({bodies.ACQUIRED_COMPONENT})
    assert ablated.capabilities == frozenset()


def test_the_causal_check_refuses_an_arm_that_never_depended_on_the_acquisition():
    """The negative control. A check that cannot come out False decides nothing.

    This arm solves less than the candidate, so the measured loss alone would call it supported.
    It is refused because it is behaviourally the parent: nothing was removed from it.
    """
    isolation = tr.Isolation()
    candidate = run_candidate(bodies.migrated_improved_body, TASKS, isolation)
    parent = run_candidate(bodies.migrated_parent_body, TASKS, isolation)
    uncoupled = run_candidate(bodies.migrated_uncoupled_ablation_body, TASKS, isolation)

    causal = causal_step(
        candidate_sandbox=candidate, parent_sandbox=parent, ablated_sandbox=uncoupled
    )
    assert causal["supported"] is True, "the naive loss measure alone would accept this arm"
    assert causal["ablated_arm_differs_from_the_parent_arm"] is False
    assert causal["establishes_causal_dependency"] is False
    assert "identical to the parent arm" in causal["why_not"]


def test_the_ablated_generation_breaks_rather_than_falling_back_to_its_parent():
    """What makes the removal real: the candidate reaches for a component that is not there."""
    outcomes = {
        row["task_id"]: row["outcome"]
        for row in run_candidate(bodies.migrated_ablated_body, TASKS, tr.Isolation())["outcomes"]
    }
    assert outcomes == {"t0": "solved", "t1": "solved", "t2": "error", "t3": "error"}


def test_the_whole_lineage_comes_back_from_disk(record):
    step = _step(record, "survives_process_death")
    assert step["state_digest_matches"] is True
    assert step["journal_head_matches"] is True
    assert step["journal_length"] > 10


def test_the_journal_is_one_continuous_descent_through_the_migration(record):
    kinds = record["journal_kinds"]
    assert kinds[0] == "seed"
    assert "candidate_rejected" in kinds
    assert "component_acquired" in kinds
    assert "vocabulary_extended" in kinds
    assert "migration" in kinds
    # Evolution continued after the change of form.
    assert "candidate_accepted" in kinds[kinds.index("migration") :]


def test_the_demonstration_is_reproducible(record):
    assert demonstrate()["record_digest"] == record["record_digest"]


# -- the diagnosis machinery ------------------------------------------------------------------------

def _seed_state():
    return st.create_state(
        body_digest="s0",
        components=[
            {
                "name": name,
                "origin": "seed",
                "certificate": None,
                "provenance": tr.provenance("host_written", produced_by="seed"),
            }
            for name in ("operator_table", "signal_interface")
        ],
        vocabulary=[
            {"name": name, "origin": "seed", "certificate": None}
            for name in ("axis_progress", "signals_consistent")
        ],
    )


def test_a_speculation_that_does_not_roll_back_exactly_is_refused():
    """The rollback is proved by comparing serialized bytes, not promised."""
    state = _seed_state()

    def leaky(inner_state, component, demand):
        inner_state["generation"] = 99  # a speculation that kept something
        return True

    with pytest.raises(diagnosis.DiagnosisError, match="must roll back exactly"):
        diagnosis.probe_component(state, "operator_table", {"d": 1}, speculate=leaky)


def test_probing_a_component_outside_the_registry_is_refused():
    with pytest.raises(diagnosis.DiagnosisError, match="not in the lineage's registry"):
        diagnosis.probe_component(
            _seed_state(), "invented", {"d": 1}, speculate=lambda *args: True
        )


def test_a_diagnosis_that_finds_an_answer_does_not_license_a_new_component():
    """'I could not fix it' is not evidence; only exhausting the registry is."""
    found = diagnosis.diagnose(
        _seed_state(),
        {"d": 1},
        speculate=lambda state, component, demand: component == "signal_interface",
        budget=tr.Budget(limits={"probes": 5}),
    )
    assert found["resolved_by"] == "signal_interface"
    assert found["registry_exhausted"] is False
    with pytest.raises(diagnosis.DiagnosisError, match="was not exhausted"):
        diagnosis.certificate_from_diagnosis(
            found, new_component="invented", resolves_with_new_component=True
        )


def test_each_probe_costs_budget_and_the_budget_can_refuse():
    with pytest.raises(tr.BudgetExhausted):
        diagnosis.diagnose(
            _seed_state(),
            {"d": 1},
            speculate=lambda *args: False,
            budget=tr.Budget(limits={"probes": 1}),
        )


def test_no_confusable_pair_means_no_vocabulary_extension():
    pair = diagnosis.find_indistinguishable_pair(
        _seed_state(),
        ({"limiting": "operator_table"}, {"limiting": "operator_table"}),
        feature_row=lambda state, demand: [True, False],
        limiting_component=lambda demand: demand["limiting"],
    )
    assert pair is None, "two demands with the same cause are not confusable"


def test_a_feature_that_gives_both_demands_the_same_value_is_refused():
    pair = diagnosis.find_indistinguishable_pair(
        _seed_state(),
        ({"limiting": "operator_table"}, {"limiting": "signal_interface"}),
        feature_row=lambda state, demand: [True, False],
        limiting_component=lambda demand: demand["limiting"],
    )
    assert pair is not None
    with pytest.raises(diagnosis.DiagnosisError, match="same value"):
        diagnosis.certificate_from_pair(
            _seed_state(), pair, new_feature="useless", separates=lambda demand: True
        )
