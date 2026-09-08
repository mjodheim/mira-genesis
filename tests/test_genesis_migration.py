"""Hostile tests for substrate metamorphosis.

The test that carries the most weight is `test_arriving_intact_without_evolving_is_not_metamorphosis`.
M084 recorded that an agent carried across four real substrates replayed an action list computed
elsewhere, so "one unchanged agent" was an interface result rather than agent competence. A migration
that transports outputs is transported output. Only a lineage that arrives *and then evolves* has
transported the capacity to acquire.
"""
from __future__ import annotations

import pytest

from genesis import development_bodies as bodies
from genesis import state as st
from genesis import trust_root as tr
from genesis.loop import Genesis, Proposal
from genesis.migration import (
    CARRIED,
    MigrationError,
    Substrate,
    capability_carried,
    carried_intact,
    discover,
    metamorphosis_succeeded,
    migrate,
)

TASKS = [{"task_id": "t%d" % index, "input": index} for index in range(8)]
LINEAGE = tr.provenance("lineage_owned", produced_by="lineage")


def _genesis(**limits):
    budget = {"generations": 8, "probes": 10}
    budget.update(limits)
    seed = st.create_state(
        body_digest="b0",
        components=[
            {
                "name": "operator_table",
                "origin": "seed",
                "certificate": None,
                "provenance": tr.provenance("host_written", produced_by="seed"),
            }
        ],
        vocabulary=[{"name": "axis_progress", "origin": "seed", "certificate": None}],
    )
    return Genesis(
        state=seed,
        body_factory=bodies.parent_body,
        budget=tr.Budget(limits=budget),
        isolation=tr.Isolation(),
        grade=bodies.grade,
    )


def _once(genesis, factory, name="candidate", ablated=None, depends_on=""):
    queue = [factory]

    def propose(_genesis, _tasks):
        if not queue:
            return None
        return Proposal(
            name=name,
            body_factory=queue.pop(0),
            provenance=LINEAGE,
            rationale={},
            ablated_body_factory=ablated,
            depends_on=depends_on,
        )

    return genesis.cycle(TASKS, propose)


def _substrate():
    return Substrate(name="record-store", operations=bodies.SUBSTRATE_OPERATIONS)


def _translate(state, operations):
    return bodies.migrated_parent_body


# -- discovery ----------------------------------------------------------------------------------

def test_the_substrate_semantics_are_discovered_rather_than_declared():
    genesis = _genesis()
    substrate = _substrate()
    assert substrate.discovered == {}, "nothing is known before probing"
    found = discover(substrate, ["read", "write", "list", "transact"], genesis.budget)
    assert found["found"] == ["read", "list"]
    assert found["missing"] == ["write", "transact"]
    assert sorted(substrate.discovered) == ["list", "read"]


def test_every_probe_costs_budget():
    genesis = _genesis(probes=3)
    substrate = _substrate()
    discover(substrate, ["read", "write", "list"], genesis.budget)
    assert genesis.budget.remaining("probes") == 0
    with pytest.raises(tr.BudgetExhausted):
        discover(substrate, ["transact"], genesis.budget)


# -- the migration itself -------------------------------------------------------------------------

def test_a_translation_may_not_use_an_operation_the_lineage_never_discovered():
    """Reaching past what was probed means the host redesigned the body for the new substrate."""
    genesis = _genesis()
    substrate = _substrate()
    discover(substrate, ["read"], genesis.budget)
    with pytest.raises(MigrationError, match="never discovered"):
        migrate(genesis, substrate, _translate, used_operations=["read", "transact"])


def test_a_migration_carries_everything_the_lineage_owned():
    genesis = _genesis()
    _once(genesis, bodies.improved_body, name="improved")
    _once(genesis, bodies.regressed_body, name="regressed")
    before_acquisitions = list(genesis.state["acquisitions"])
    before_observations = list(genesis.state["observations"])

    substrate = _substrate()
    discover(substrate, ["read"], genesis.budget)
    record = migrate(genesis, substrate, _translate, used_operations=["read"])

    assert all(counts["missing"] == 0 for counts in record["carried"].values())
    assert genesis.state["acquisitions"] == before_acquisitions
    assert genesis.state["observations"] == before_observations
    assert set(record["carried"]) == set(CARRIED)


def test_the_journal_continues_across_the_migration():
    genesis = _genesis()
    _once(genesis, bodies.improved_body, name="improved")
    departure_head = genesis.journal.head

    substrate = _substrate()
    discover(substrate, ["read"], genesis.budget)
    record = migrate(genesis, substrate, _translate, used_operations=["read"])

    assert record["journal_continues"] is True
    assert record["departure_journal_head"] == departure_head
    migration_entries = genesis.journal.of_kind("migration")
    assert len(migration_entries) == 1
    assert migration_entries[0]["previous_digest"] == departure_head


def test_a_translation_that_produces_no_body_is_refused():
    genesis = _genesis()
    substrate = _substrate()
    discover(substrate, ["read"], genesis.budget)
    with pytest.raises(MigrationError, match="did not produce a body factory"):
        migrate(genesis, substrate, lambda state, ops: "not a factory", used_operations=["read"])


def test_a_lineage_that_loses_something_did_not_arrive_intact():
    departing = st.create_state(
        body_digest="b0",
        components=[
            {
                "name": "operator_table",
                "origin": "seed",
                "certificate": None,
                "provenance": tr.provenance("host_written", produced_by="seed"),
            }
        ],
        vocabulary=[{"name": "axis_progress", "origin": "seed", "certificate": None}],
        acquisitions=[
            {"name": "A", "provenance": LINEAGE},
            {"name": "B", "provenance": LINEAGE},
        ],
    )
    arrived = st.create_state(
        body_digest="b1",
        components=departing["components"],
        vocabulary=departing["vocabulary"],
        acquisitions=[{"name": "A", "provenance": LINEAGE}],
    )
    outcome = carried_intact(departing, arrived)
    assert outcome["intact"] is False
    assert any("acquisitions lost 1 of 2" in entry for entry in outcome["lost"])


# -- what actually counts as metamorphosis --------------------------------------------------------

def test_arriving_intact_without_evolving_is_not_metamorphosis():
    """The M084 correction, made mechanical: transported output is not transported intelligence."""
    genesis = _genesis()
    _once(genesis, bodies.improved_body, name="improved")
    substrate = _substrate()
    discover(substrate, ["read"], genesis.budget)
    record = migrate(genesis, substrate, _translate, used_operations=["read"])

    outcome = metamorphosis_succeeded(record, [])
    assert outcome["succeeded"] is False
    assert any("replayed rather than evolved" in reason for reason in outcome["reasons"])
    assert outcome["is_transported_intelligence_rather_than_transported_output"] is False


def test_a_lineage_that_arrives_and_evolves_again_has_metamorphosed():
    genesis = _genesis()
    _once(genesis, bodies.improved_body, name=bodies.ACQUIRED_COMPONENT)
    substrate = _substrate()
    discover(substrate, ["read"], genesis.budget)
    record = migrate(genesis, substrate, _translate, used_operations=["read"], tasks=TASKS)

    after = [
        _once(
            genesis,
            bodies.migrated_improved_body,
            name="improved_in_B",
            ablated=bodies.migrated_ablated_body,
            depends_on=bodies.ACQUIRED_COMPONENT,
        )
    ]
    outcome = metamorphosis_succeeded(record, after)

    assert outcome["succeeded"] is True
    assert outcome["reasons"] == []
    assert outcome["accepted_after_migration"] == 1
    assert outcome["causally_established_after_migration"] == 1
    assert outcome["is_transported_intelligence_rather_than_transported_output"] is True


def test_an_acceptance_nobody_examined_is_not_metamorphosis():
    """"Accepted a candidate" was too weak a proxy: it counted improvements for unrelated reasons.

    This lineage arrives intact and accepts a better candidate, and that is still not shown to have
    anything to do with what it carried across.
    """
    genesis = _genesis()
    _once(genesis, bodies.improved_body, name="improved")
    substrate = _substrate()
    discover(substrate, ["read"], genesis.budget)
    record = migrate(genesis, substrate, _translate, used_operations=["read"], tasks=TASKS)

    after = [_once(genesis, bodies.migrated_improved_body, name="improved_in_B")]
    outcome = metamorphosis_succeeded(record, after)

    assert outcome["accepted_after_migration"] == 1, "it did accept a candidate"
    assert outcome["causally_established_after_migration"] == 0
    assert outcome["succeeded"] is False
    assert any("may have nothing to do with the migration" in reason for reason in outcome["reasons"])
    assert outcome["is_transported_intelligence_rather_than_transported_output"] is False


def test_post_migration_cycles_that_all_reject_do_not_count_as_evolving():
    genesis = _genesis()
    substrate = _substrate()
    discover(substrate, ["read"], genesis.budget)
    record = migrate(genesis, substrate, _translate, used_operations=["read"])
    after = [_once(genesis, bodies.regressed_body, name="worse_in_B")]
    outcome = metamorphosis_succeeded(record, after)
    assert outcome["succeeded"] is False
    assert outcome["accepted_after_migration"] == 0


def test_a_broken_journal_link_defeats_the_claim_even_with_a_new_acquisition():
    genesis = _genesis()
    substrate = _substrate()
    discover(substrate, ["read"], genesis.budget)
    record = dict(migrate(genesis, substrate, _translate, used_operations=["read"]))
    record["journal_continues"] = False
    after = [_once(genesis, bodies.migrated_improved_body, name="improved_in_B")]
    outcome = metamorphosis_succeeded(record, after)
    assert outcome["succeeded"] is False
    assert any("does not chain" in reason for reason in outcome["reasons"])


def test_the_migrated_body_actually_runs_in_the_new_substrate():
    genesis = _genesis()
    substrate = _substrate()
    discover(substrate, ["read"], genesis.budget)
    migrate(genesis, substrate, _translate, used_operations=["read"])
    record = _once(genesis, bodies.migrated_improved_body, name="improved_in_B")
    assert record["accepted"] is True
    assert record["parent_sandbox"]["completed"] is True
    assert record["candidate_sandbox"]["completed"] is True


def test_the_whole_metamorphosis_survives_process_death(tmp_path):
    genesis = _genesis()
    _once(genesis, bodies.improved_body, name="improved")
    substrate = _substrate()
    discover(substrate, ["read"], genesis.budget)
    migrate(genesis, substrate, _translate, used_operations=["read"])
    _once(genesis, bodies.migrated_improved_body, name="improved_in_B")
    genesis.persist(tmp_path)

    restored = Genesis.restore(
        tmp_path,
        body_factory=bodies.migrated_improved_body,
        budget=tr.Budget(limits={"generations": 8, "probes": 10}),
        isolation=tr.Isolation(),
        grade=bodies.grade,
    )
    assert restored.state["state_digest"] == genesis.state["state_digest"]
    assert restored.journal.head == genesis.journal.head
    assert [entry["kind"] for entry in restored.journal] == [
        entry["kind"] for entry in genesis.journal
    ]
    assert restored.journal.of_kind("migration")


# -- what arrived, as opposed to what was recorded as arriving --------------------------------------
#
# `carried_intact` compares components, certificates and acquisitions. For a long time nothing
# compared what the arrival could still *do*, so a translation could drop every capability the
# lineage had and the migration record would report that nothing was lost — because nothing being
# counted had been. These tests exist because of that gap.

def test_a_translation_that_loses_capability_is_refused():
    """The lossy body carries every component and certificate. It simply cannot do the work."""
    genesis = _genesis()
    _once(genesis, bodies.improved_body, name="improved")
    substrate = _substrate()
    discover(substrate, ["read"], genesis.budget)
    with pytest.raises(MigrationError, match="lost capability"):
        migrate(
            genesis,
            substrate,
            lambda state, operations: bodies.migrated_lossy_body,
            used_operations=["read"],
            tasks=TASKS,
        )


def test_a_refused_translation_does_not_half_move_the_lineage():
    """A migration that is refused must leave the lineage where it was, not partly elsewhere."""
    genesis = _genesis()
    _once(genesis, bodies.improved_body, name="improved")
    before_state, before_body = genesis.state["state_digest"], genesis.body_factory
    substrate = _substrate()
    discover(substrate, ["read"], genesis.budget)
    with pytest.raises(MigrationError):
        migrate(
            genesis,
            substrate,
            lambda state, operations: bodies.migrated_lossy_body,
            used_operations=["read"],
            tasks=TASKS,
        )
    assert genesis.state["state_digest"] == before_state
    assert genesis.body_factory is before_body


def test_a_lossy_translation_is_allowed_when_it_is_explicitly_intended():
    """A substrate may genuinely be less capable. Silence is the problem, not the loss."""
    genesis = _genesis()
    _once(genesis, bodies.improved_body, name="improved")
    substrate = _substrate()
    discover(substrate, ["read"], genesis.budget)
    record = migrate(
        genesis,
        substrate,
        lambda state, operations: bodies.migrated_lossy_body,
        used_operations=["read"],
        tasks=TASKS,
        permit_capability_loss=True,
    )
    assert record["capability"]["preserved"] is False
    assert record["capability"]["lost_tasks"] == ["t2", "t3"]


def test_an_unverified_migration_claims_nothing_about_what_arrived():
    """Without tasks nothing is measured, and the record must not imply otherwise."""
    genesis = _genesis()
    substrate = _substrate()
    discover(substrate, ["read"], genesis.budget)
    record = migrate(genesis, substrate, _translate, used_operations=["read"])
    assert record["capability"]["measured"] is False
    assert record["capability"]["preserved"] is None
    assert "nothing checked" in record["capability"]["why"]


def test_a_verified_migration_reports_both_sides_of_the_comparison():
    genesis = _genesis()
    _once(genesis, bodies.improved_body, name="improved")
    substrate = _substrate()
    discover(substrate, ["read"], genesis.budget)
    record = migrate(genesis, substrate, _translate, used_operations=["read"], tasks=TASKS)
    capability = record["capability"]
    assert capability["measured"] is True
    assert capability["preserved"] is True
    assert capability["solved_before"] == capability["solved_after"] == 4
    assert capability["lost_tasks"] == []


def test_a_comparison_that_could_not_run_is_not_a_comparison_that_passed():
    """An instrument failure must not be read as a translation that preserved everything."""
    genesis = _genesis()
    _once(genesis, bodies.improved_body, name="improved")  # so TASKS is a set it was judged by
    with pytest.raises(MigrationError, match="did not run"):
        capability_carried(genesis, bodies.unconstructible_body, TASKS)


def test_a_migration_cannot_be_verified_against_tasks_the_lineage_never_faced():
    """Otherwise the verification set is chosen by whoever wants the migration to pass."""
    genesis = _genesis()
    _once(genesis, bodies.improved_body, name="improved")
    convenient = [{"task_id": "easy%d" % index, "input": index} for index in range(3)]
    substrate = _substrate()
    discover(substrate, ["read"], genesis.budget)
    with pytest.raises(MigrationError, match="never been evaluated on"):
        migrate(genesis, substrate, _translate, used_operations=["read"], tasks=convenient)


def test_substituting_easier_questions_under_the_same_labels_is_refused():
    """Identity is the question, not the label on it.

    This test used to assert the opposite of its second half: that *renaming* got past the check.
    Under the old label-based digest that was the only thing the check could see, which is exactly
    the hole an independent reviewer found — reuse the identifiers, put easier contents underneath,
    and an unevaluated set looks like evaluated work. Now the contents decide, so relabelling the
    same questions is the same work and changing the questions is not.
    """
    genesis = _genesis()
    _once(genesis, bodies.improved_body, name="improved")
    substrate = _substrate()
    discover(substrate, ["read"], genesis.budget)

    easier = [dict(task, input=0) for task in TASKS]
    with pytest.raises(MigrationError, match="never been evaluated on"):
        migrate(genesis, substrate, _translate, used_operations=["read"], tasks=easier)


def test_relabelling_the_same_questions_is_the_same_work():
    """Non-vacuity for the line above: the check refuses substituted questions, not new names."""
    genesis = _genesis()
    _once(genesis, bodies.improved_body, name="improved")
    renamed = [dict(task, task_id=task["task_id"].upper()) for task in TASKS]
    substrate = _substrate()
    discover(substrate, ["read"], genesis.budget)
    record = migrate(genesis, substrate, _translate, used_operations=["read"], tasks=renamed)
    assert record["capability"]["measured"] is True


def test_the_task_set_the_lineage_was_judged_by_is_accepted():
    """Non-vacuity: the check refuses a substituted set, not every set."""
    genesis = _genesis()
    _once(genesis, bodies.improved_body, name="improved")
    substrate = _substrate()
    discover(substrate, ["read"], genesis.budget)
    record = migrate(genesis, substrate, _translate, used_operations=["read"], tasks=TASKS)
    assert record["capability"]["measured"] is True
