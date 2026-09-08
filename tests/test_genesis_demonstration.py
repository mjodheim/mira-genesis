"""Lock the end-to-end Genesis demonstration.

The stopping criterion is not that the components exist. It is that **one lineage** measures itself,
diagnoses itself, transforms itself, verifies the transformation, adopts or rejects it on evidence,
keeps what it learned, extends the machinery that enables later transformations, changes form, and
goes on evolving in the new form. These tests assert each of those on the same run.
"""
from __future__ import annotations

import pytest

from genesis import development_bodies as bodies
from genesis import trust_root as tr
from genesis.sandbox import run_candidate
from scripts.run_genesis_demonstration import TASKS, demonstrate


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


def test_the_probes_were_composed_and_run_rather_than_consulted(record):
    """The third ceiling. No host callable answers 'does this component resolve the demand'.

    Compositions are built by the lineage, executed in isolation, and judged on raw per-task
    outcomes. `tests/test_genesis_probe.py` carries the load-bearing check that the finding follows
    the data; this asserts the demonstration actually goes through that path.
    """
    step = _step(record, "lineage_names_a_component_class_it_did_not_have")
    assert step["probe_is_experimental_not_an_oracle"] is True
    assert step["compositions_run"] > 0, "a certificate must rest on probes that ran"
    # Exhaustion alone would only be a failed search.
    assert step["reachable_with_wider_operations"] is True
    assert step["composition_the_lineage_found"] == ["double", "increment"]


def test_the_lineage_extends_its_own_diagnostic_vocabulary(record):
    """The second ceiling: extended on a *measured* confusable pair, not on a whim.

    Both demands read identically through the lineage's per-component vocabulary and their causes
    differ, and both halves of that come from probes rather than from a callable that was told the
    answer.
    """
    step = _step(record, "lineage_extends_its_own_diagnostic_vocabulary")
    assert step["shared_prior_row"] == [False, False]
    assert step["limiting_components"] == ["operator_table", "signal_interface"]
    assert step["resolving_operations"] == [
        ["increment", "negate", "double"],
        ["double", "square", "negate"],
    ]
    assert step["vocabulary_after"][-1] == "requires_increment"


def test_neither_ceiling_is_held_up_by_an_oracle_any_more(record):
    """Both steps now run experiments, and the record has to say which is which.

    This assertion is the one that would fail first if a host-written shortcut were reintroduced
    into either path, which is why it reads the flags rather than trusting the step names.
    """
    component_step = _step(record, "lineage_names_a_component_class_it_did_not_have")
    vocabulary_step = _step(record, "lineage_extends_its_own_diagnostic_vocabulary")
    assert component_step["probe_is_experimental_not_an_oracle"] is True
    assert vocabulary_step["rests_on_a_host_supplied_oracle"] is False
    assert vocabulary_step["feature_read_out_of_the_measurements"] == "requires_increment"


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
    assert step["accepted_after_migration"] == 2
    assert step["transported_intelligence"] is True


def test_the_lineage_accepts_three_transformations_not_one(record):
    """A single acceptance shows the runtime works. Three show the lineage is still going."""
    step = _step(record, "evolved_again_in_the_new_form")
    assert step["accepted_cycles_in_the_lineage"] == 3
    assert record["final_generation"] == 3


def test_the_translation_is_verified_rather_than_assumed(record):
    """State arriving intact says nothing about what the arrival can do.

    `carried_intact` compares components, certificates and acquisitions. A translation could drop
    every capability and still pass it, because nothing being counted would have been lost.
    """
    step = _step(record, "substrate_semantics_discovered_then_migrated")
    assert step["capability_measured"] is True
    assert step["capability_preserved"] is True
    assert step["solved_before_and_after"] == [4, 4]


@pytest.mark.parametrize("depends_on", ["joint_registry", "carrier_index"])
def test_each_generation_needed_the_one_before_it(record, depends_on):
    """Two consecutive ablations. One shows a dependency; two show a chain."""
    step = _step(record, "causal_dependency:%s" % depends_on)
    assert step["established"] is True
    assert step["arm_supplied"] is True
    assert step["solved_without_acquisition"] < step["solved_with_acquisition"]
    # Without this the "ablation" is the parent arm, and the comparison merely repeats the verdict
    # that accepted the candidate.
    assert step["ablated_arm_differs_from_the_parent_arm"] is True
    assert step["why"] == ""


def test_the_ablation_is_run_by_the_runtime_not_by_the_script(record):
    """The loop called this a permanent obligation of the runtime while a script was doing it."""
    step = _step(record, "causal_dependency:joint_registry")
    assert step["checked_by"] == "genesis.loop.Genesis.cycle, not by this script"


def test_the_lineage_reports_a_chain_length_that_could_have_been_smaller(record):
    """Three acquisitions, two established links: the first depended on nothing earlier."""
    step = _step(record, "the_acquisitions_form_a_chain_rather_than_a_sequence")
    assert step["acquisitions"] == 3
    assert step["established_links"] == 2
    assert step["is_a_chain_rather_than_a_sequence"] is True


@pytest.mark.parametrize(
    "candidate_factory, ablated_factory, removed",
    [
        ("migrated_improved_body", "migrated_ablated_body", "ACQUIRED_COMPONENT"),
        ("migrated_further_body", "migrated_further_ablated_body", "SECOND_ACQUISITION"),
    ],
)
def test_each_ablated_arm_is_its_candidate_minus_one_acquisition(
    candidate_factory, ablated_factory, removed
):
    """The record only *states* how each arm was built. This checks it, field by field."""
    candidate = getattr(bodies, candidate_factory)()
    ablated = getattr(bodies, ablated_factory)()
    assert ablated.solves == candidate.solves
    assert ablated.operation_names == candidate.operation_names
    assert ablated.routed == candidate.routed
    assert candidate.capabilities - ablated.capabilities == {getattr(bodies, removed)}
    assert ablated.capabilities < candidate.capabilities


def test_the_ablated_generation_breaks_rather_than_falling_back_to_its_parent():
    """What makes the removal real: the candidate reaches for a component that is not there."""
    outcomes = {
        row["task_id"]: row["outcome"]
        for row in run_candidate(bodies.migrated_ablated_body, TASKS, tr.Isolation())["outcomes"]
    }
    assert outcomes == {
        "t0": "solved",
        "t1": "solved",
        "t2": "error",
        "t3": "error",
        "t4": "solved",
        "t5": "unsolved",
    }


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
