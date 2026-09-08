"""Every refusal the runtime makes, driven to the point where it actually refuses.

These tests exist because of a finding, not because of a plan. `scripts/check_genesis_guards_are_tested.py`
deletes each `raise` in `genesis/` one at a time and reruns the suite; on the first run **35 of 68
guards survived**, meaning just over half the runtime's refusals were never exercised by anything.
A guard no test reaches is a refusal resting on assertion: the code says it will not accept something,
and nobody has ever checked that it does not.

Each test below kills one surviving mutant. They are deliberately small and slightly repetitive —
one bad input, one refusal — because the value is coverage of the refusal set, not elegance.

Four guards are deliberately **not** covered, and their absence is the finding rather than an
omission. Each asserts an invariant the surrounding code already establishes:

* `genesis/sandbox.py` — "the candidate did not report the task set it was given". The child builds
  its rows by iterating the task list it was handed, so no body can return a different task set. The
  check guards against a compromised child, which nothing in this repository can produce.
* `genesis/migration.py` — "the lineage did not arrive intact". `migrate` constructs the arrival
  state from the departing state's own fields, so nothing can be dropped between them.
* `genesis/probe.py` — "diagnosis mutated the lineage state". Probes run in separate processes and
  nothing in the diagnosis path writes to the state.
* `genesis/probe.py` — "the proposed feature gives both demands the same value". The operation comes
  from the symmetric difference of the two resolving compositions, so it is in exactly one of them.

They are kept, marked in place, and left untested on purpose; inventing a contrived path to them
would report coverage without adding knowledge. The current count is 69 of 73 killed — rerun
`scripts/check_genesis_guards_are_tested.py` rather than trusting that number.
"""
from __future__ import annotations

import json

import pytest

from genesis import journal as jr
from genesis import migration as mg
from genesis import state as st
from genesis import trust_root as tr
from genesis.development_bodies import improved_body, parent_body
from genesis.loop import Genesis, Proposal

LINEAGE = tr.provenance("lineage_owned", produced_by="lineage")
TASKS = [{"task_id": "t%d" % index} for index in range(4)]
ROWS = [{"task_id": "t%d" % index, "outcome": "solved"} for index in range(4)]


def _decide(**overrides):
    arguments = {
        "parent_outcomes": ROWS,
        "candidate_outcomes": ROWS,
        "budget": tr.Budget(limits={"generations": 4}),
        "isolation": tr.Isolation(),
        "admitted_isolation": tr.Isolation(),
        "candidate_provenance": LINEAGE,
    }
    arguments.update(overrides)
    return tr.decide(**arguments)


def _seed_state(**overrides):
    arguments = {
        "body_digest": "s0",
        "components": [
            {
                "name": "operator_table",
                "origin": "seed",
                "certificate": None,
                "provenance": tr.provenance("host_written", produced_by="seed"),
            }
        ],
        "vocabulary": [{"name": "axis_progress", "origin": "seed", "certificate": None}],
    }
    arguments.update(overrides)
    return st.create_state(**arguments)


def _component(name, **overrides):
    entry = {
        "name": name,
        "origin": "seed",
        "certificate": None,
        "provenance": tr.provenance("host_written", produced_by="seed"),
    }
    entry.update(overrides)
    return entry


def _vocabulary_certificate():
    return st.vocabulary_extension_certificate(
        prior_vocabulary=["axis_progress"],
        new_feature="joint_undetermined",
        demand_digests=["d1", "d2"],
        shared_prior_row=[True],
        limiting_components=["operator_table", "signal_interface"],
        separated_rows=[[True, True], [True, False]],
    )


# -- trust root -----------------------------------------------------------------------------------

def test_a_budget_cannot_be_declared_with_a_negative_allowance():
    with pytest.raises(tr.TrustRootError, match="is negative"):
        tr.Budget(limits={"probes": -1})


def test_a_negative_spend_cannot_be_used_to_refund_the_ledger():
    budget = tr.Budget(limits={"probes": 1})
    budget.spend("probes")
    with pytest.raises(tr.TrustRootError, match="negative amount"):
        budget.spend("probes", -5)


def test_an_outcome_row_that_is_not_a_record_is_refused():
    with pytest.raises(tr.TrustRootError, match="is not a record"):
        _decide(candidate_outcomes=[["t0", "solved"]])


def test_an_outcome_row_without_a_task_id_is_refused():
    with pytest.raises(tr.TrustRootError, match="carries no task id"):
        _decide(candidate_outcomes=[{"outcome": "solved"}])


def test_a_candidate_without_recognised_provenance_cannot_be_decided_on():
    """The provenance vocabulary is only worth anything if an unclassifiable candidate is refused."""
    with pytest.raises(tr.TrustRootError, match="no recognised provenance"):
        _decide(candidate_provenance={"class": "invented_by_the_lineage"})


def test_a_control_arm_that_faced_different_tasks_voids_the_comparison():
    with pytest.raises(tr.TrustRootError, match="control did not face the same tasks"):
        _decide(control_outcomes=[{"task_id": "other", "outcome": "solved"}])


# -- lineage state: names -------------------------------------------------------------------------

def test_an_empty_name_is_refused():
    with pytest.raises(st.StateError, match="non-empty name"):
        st.component_extension_certificate(
            prior_registry=[""],
            new_component="joint",
            demand_digest="d",
            probe_records=[],
            resolves_with_new_component=True,
        )


def test_a_duplicated_prior_registry_entry_is_refused():
    with pytest.raises(st.StateError, match="contains a duplicate"):
        st.component_extension_certificate(
            prior_registry=["a", "a"],
            new_component="joint",
            demand_digest="d",
            probe_records=[],
            resolves_with_new_component=True,
        )


# -- lineage state: component certificates --------------------------------------------------------

def test_a_component_certificate_cannot_name_a_component_already_held():
    with pytest.raises(st.StateError, match="already in the registry"):
        st.component_extension_certificate(
            prior_registry=["a"],
            new_component="a",
            demand_digest="d",
            probe_records=[{"component": "a", "resolved": False}],
            resolves_with_new_component=True,
        )


def test_a_probe_record_that_is_not_a_record_is_refused():
    with pytest.raises(st.StateError, match="not a record"):
        st.component_extension_certificate(
            prior_registry=["a"],
            new_component="joint",
            demand_digest="d",
            probe_records=[["a", False]],
            resolves_with_new_component=True,
        )


def test_a_probe_record_naming_a_component_outside_the_registry_is_refused():
    """Otherwise exhaustion could be claimed by probing components the lineage never had."""
    with pytest.raises(st.StateError, match="not in the prior registry"):
        st.component_extension_certificate(
            prior_registry=["a"],
            new_component="joint",
            demand_digest="d",
            probe_records=[{"component": "invented", "resolved": False}],
            resolves_with_new_component=True,
        )


def test_probing_one_component_twice_cannot_stand_in_for_probing_two():
    with pytest.raises(st.StateError, match="probed twice"):
        st.component_extension_certificate(
            prior_registry=["a", "b"],
            new_component="joint",
            demand_digest="d",
            probe_records=[
                {"component": "a", "resolved": False},
                {"component": "a", "resolved": False},
            ],
            resolves_with_new_component=True,
        )


# -- lineage state: vocabulary certificates -------------------------------------------------------

def test_a_vocabulary_certificate_cannot_name_a_feature_already_held():
    with pytest.raises(st.StateError, match="already in the vocabulary"):
        st.vocabulary_extension_certificate(
            prior_vocabulary=["axis_progress"],
            new_feature="axis_progress",
            demand_digests=["d1", "d2"],
            shared_prior_row=[True],
            limiting_components=["a", "b"],
            separated_rows=[[True, True], [True, False]],
        )


def test_a_shared_row_of_the_wrong_width_is_refused():
    with pytest.raises(st.StateError, match="prior vocabulary width"):
        st.vocabulary_extension_certificate(
            prior_vocabulary=["axis_progress"],
            new_feature="joint",
            demand_digests=["d1", "d2"],
            shared_prior_row=[True, False],
            limiting_components=["a", "b"],
            separated_rows=[[True, True], [True, False]],
        )


def test_the_extension_must_report_a_row_for_each_demand():
    with pytest.raises(st.StateError, match="a row for each demand"):
        st.vocabulary_extension_certificate(
            prior_vocabulary=["axis_progress"],
            new_feature="joint",
            demand_digests=["d1", "d2"],
            shared_prior_row=[True],
            limiting_components=["a", "b"],
            separated_rows=[[True, True]],
        )


def test_separated_rows_of_the_wrong_width_are_refused():
    with pytest.raises(st.StateError, match="extended vocabulary width"):
        st.vocabulary_extension_certificate(
            prior_vocabulary=["axis_progress"],
            new_feature="joint",
            demand_digests=["d1", "d2"],
            shared_prior_row=[True],
            limiting_components=["a", "b"],
            separated_rows=[[True], [False]],
        )


# -- lineage state: registry construction ---------------------------------------------------------

def test_a_component_with_an_unrecognised_origin_is_refused():
    with pytest.raises(st.StateError, match="unrecognised origin"):
        _seed_state(components=[_component("a", origin="invented")])


def test_an_acquired_component_carrying_the_wrong_certificate_kind_is_refused():
    """A vocabulary certificate must not be able to buy a component."""
    with pytest.raises(st.StateError, match="wrong certificate kind"):
        _seed_state(
            components=[
                _component("a", origin="acquired", certificate=_vocabulary_certificate())
            ]
        )


def test_a_component_certified_under_another_name_is_refused():
    certificate = st.component_extension_certificate(
        prior_registry=["operator_table"],
        new_component="joint_registry",
        demand_digest="d",
        probe_records=[{"component": "operator_table", "resolved": False}],
        resolves_with_new_component=True,
    )
    with pytest.raises(st.StateError, match="certified under another name"):
        _seed_state(
            components=[_component("something_else", origin="acquired", certificate=certificate)]
        )


def test_a_duplicated_component_registry_is_refused():
    with pytest.raises(st.StateError, match="registry contains a duplicate"):
        _seed_state(components=[_component("a"), _component("a")])


def test_a_feature_with_an_unrecognised_origin_is_refused():
    with pytest.raises(st.StateError, match="unrecognised origin"):
        _seed_state(vocabulary=[{"name": "f", "origin": "invented", "certificate": None}])


def test_an_acquired_feature_without_a_certificate_is_refused():
    with pytest.raises(st.StateError, match="carries no certificate"):
        _seed_state(vocabulary=[{"name": "f", "origin": "acquired", "certificate": None}])


def test_an_acquired_feature_carrying_the_wrong_certificate_kind_is_refused():
    """A component certificate must not be able to buy a diagnostic feature either."""
    component_certificate = st.component_extension_certificate(
        prior_registry=["operator_table"],
        new_component="joint_registry",
        demand_digest="d",
        probe_records=[{"component": "operator_table", "resolved": False}],
        resolves_with_new_component=True,
    )
    with pytest.raises(st.StateError, match="wrong certificate kind"):
        _seed_state(
            vocabulary=[
                {"name": "f", "origin": "acquired", "certificate": component_certificate}
            ]
        )


def test_a_feature_certified_under_another_name_is_refused():
    with pytest.raises(st.StateError, match="certified under another name"):
        _seed_state(
            vocabulary=[
                {"name": "not_the_certified_one", "origin": "acquired", "certificate": _vocabulary_certificate()}
            ]
        )


def test_a_seed_feature_may_not_carry_an_extension_certificate():
    """A seed entry with a certificate would be an acquisition backdated into the origin."""
    with pytest.raises(st.StateError, match="may not carry an extension certificate"):
        _seed_state(
            vocabulary=[
                {"name": "axis_progress", "origin": "seed", "certificate": _vocabulary_certificate()}
            ]
        )


def test_a_duplicated_vocabulary_is_refused():
    with pytest.raises(st.StateError, match="vocabulary contains a duplicate"):
        _seed_state(
            vocabulary=[
                {"name": "f", "origin": "seed", "certificate": None},
                {"name": "f", "origin": "seed", "certificate": None},
            ]
        )


def test_a_state_payload_of_the_wrong_schema_is_refused():
    with pytest.raises(st.StateError, match="payload is invalid"):
        st.decode_state(b'{"schema": "something-else", "generation": 0}')


# -- lineage state: extension against a certificate -----------------------------------------------

def test_a_vocabulary_certificate_issued_against_another_vocabulary_is_refused():
    certificate = _vocabulary_certificate()
    state = _seed_state(vocabulary=[{"name": "different", "origin": "seed", "certificate": None}])
    with pytest.raises(st.StateError, match="issued against a different vocabulary"):
        st.extend_vocabulary(state, certificate=certificate)


def test_a_tampered_vocabulary_certificate_does_not_reproduce():
    """The certificate is content-addressed: editing its evidence invalidates it."""
    certificate = dict(_vocabulary_certificate())
    certificate["demand_digests"] = ["forged", "evidence"]
    with pytest.raises(st.StateError, match="certificate does not reproduce"):
        st.extend_vocabulary(_seed_state(), certificate=certificate)


# -- the descent journal --------------------------------------------------------------------------

def test_a_journal_constructed_from_a_broken_chain_is_refused():
    """`Journal.load` catches a tampered file by its digest; this is the chain check itself."""
    good = jr.Journal()
    good.append("seed", 0, {"a": 1})
    good.append("observation", 0, {"a": 2})
    entries = good.entries()
    entries[1]["previous_digest"] = jr.GENESIS_DIGEST
    with pytest.raises(jr.JournalError):
        jr.Journal(entries)


def test_a_journal_file_of_the_wrong_schema_is_refused(tmp_path):
    path = tmp_path / "j.json"
    path.write_text(json.dumps({"schema": "something-else", "entries": []}), encoding="utf-8")
    with pytest.raises(jr.JournalError, match="payload is invalid"):
        jr.Journal.load(path)


def test_a_journal_file_whose_own_digest_is_wrong_is_refused(tmp_path):
    """A file with an internally consistent chain but a forged outer digest."""
    journal = jr.Journal()
    journal.append("seed", 0, {"a": 1})
    payload = journal.record()
    payload["journal_digest"] = "0" * 64
    path = tmp_path / "j.json"
    path.write_bytes(tr.canonical_bytes(payload) + b"\n")
    with pytest.raises(jr.JournalError, match="digest does not reproduce"):
        jr.Journal.load(path)


# -- the loop -------------------------------------------------------------------------------------

def test_a_verdict_from_an_unadmitted_trust_root_stops_the_cycle():
    """The loop must act on `verify_verdict`, not merely call it.

    A lineage admitted under one trust root receives a verdict naming another. That is the shape of
    a Genesis that rewrote its own evaluator, and the cycle must refuse it rather than adopt.
    """
    genesis = Genesis(
        state=_seed_state(),
        body_factory=parent_body,
        budget=tr.Budget(limits={"generations": 4}),
        isolation=tr.Isolation(),
        admitted_source_sha256="f" * 64,
    )
    with pytest.raises(tr.TrustRootError, match="different trust root"):
        genesis.cycle(
            TASKS,
            lambda _g, _t: Proposal(
                name="improved",
                body_factory=improved_body,
                provenance=LINEAGE,
                rationale={},
            ),
        )


# -- the two guards deliberately left untested ----------------------------------------------------

def test_the_intactness_check_itself_detects_loss_even_though_migrate_cannot_cause_it():
    """`migrate` cannot lose anything, so its raise is unreachable. The comparison is not.

    This documents the split: the invariant is checked here, and the assertion in `migrate` stays as
    an assertion. See this module's docstring.
    """
    departing = _seed_state(components=[_component("a"), _component("b")])
    arrived = _seed_state(components=[_component("a")])
    outcome = mg.carried_intact(departing, arrived)
    assert outcome["intact"] is False
    assert outcome["carried"]["components"]["missing"] == 1
