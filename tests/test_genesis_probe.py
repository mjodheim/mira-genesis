"""The third authored ceiling: a lineage that composes and runs its probes.

`diagnosis.py` let a lineage exhaust its registry and name a component class, but the question "does
this component resolve the demand?" was answered by a `speculate` callable the host wrote. The host
decided the finding and the certificate recorded the lineage agreeing.

`probe.py` answers the same question by experiment. These tests exist to check that the difference is
real rather than rhetorical, and the load-bearing one is
`test_the_same_machinery_reaches_opposite_findings_on_different_demands`: no host callable changes
between those three cases, only the task data, and the finding changes with it. An apparatus whose
conclusion does not depend on its data has concluded nothing.
"""
from __future__ import annotations

import pytest

from genesis import development_bodies as bodies
from genesis import probe
from genesis import state as st
from genesis import trust_root as tr

REGISTRY = bodies.PROBE_REGISTRY
COMPONENT_OPERATIONS = bodies.COMPONENT_OPERATIONS


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
        vocabulary=[{"name": "axis_progress", "origin": "seed", "certificate": None}],
    )


def _diagnose(tasks, *, budget=None, max_length=2, state=None):
    return probe.diagnose_by_experiment(
        state if state is not None else _seed_state(),
        registry_reference=REGISTRY,
        component_operations=COMPONENT_OPERATIONS,
        tasks=tasks,
        isolation=tr.Isolation(),
        budget=budget or tr.Budget(limits={"probes": 200}),
        max_length=max_length,
    )


# -- the finding follows the data, not a host callable ---------------------------------------------

@pytest.mark.parametrize(
    "demand, exhausted, reachable, licenses",
    [
        (bodies.SPANNING_DEMAND, True, True, True),
        (bodies.LOCAL_DEMAND, False, False, False),
        (bodies.UNREACHABLE_DEMAND, True, False, False),
    ],
    ids=["spanning", "resolved-by-a-held-component", "unreachable-by-anything"],
)
def test_the_same_machinery_reaches_opposite_findings_on_different_demands(
    demand, exhausted, reachable, licenses
):
    """Same components, same operations, same code. Only the task data differs."""
    found = _diagnose(demand)
    assert found["registry_exhausted"] is exhausted
    assert found["reachable_with_wider_operations"] is reachable
    assert found["licenses_naming_a_new_component"] is licenses


def test_the_lineage_finds_the_composition_rather_than_being_handed_it():
    """The composition is a search result. Nothing in the host names `double` then `increment`."""
    found = _diagnose(bodies.SPANNING_DEMAND)
    assert found["resolving_composition"]["operations"] == ["double", "increment"]
    assert found["resolving_composition"]["composition_digest"]


def test_a_held_component_that_resolves_the_demand_ends_the_probing_early():
    found = _diagnose(bodies.LOCAL_DEMAND)
    assert found["resolved_by"] == "operator_table"
    assert [record["component"] for record in found["probes"]] == ["operator_table"]
    assert "an existing component resolves the demand" in found["why_not"]


def test_exhaustion_without_reachability_licenses_nothing():
    """'I could not do it' is not evidence that a representation is missing.

    This is the half that stops an exhausting search from being self-serving: the lineage must also
    show that something *outside* what it has does resolve the demand.
    """
    found = _diagnose(bodies.UNREACHABLE_DEMAND)
    assert found["registry_exhausted"] is True
    assert found["reachable_with_wider_operations"] is False
    assert found["licenses_naming_a_new_component"] is False
    assert "nothing shows a representation is missing" in found["why_not"]
    with pytest.raises(probe.ProbeError, match="does not license"):
        probe.certificate_from_experiment(found, new_component="invented")


def test_a_demand_no_single_operation_solves_needs_a_longer_composition():
    """At length one the spanning demand is unreachable even with every operation available."""
    found = _diagnose(bodies.SPANNING_DEMAND, max_length=1)
    assert found["registry_exhausted"] is True
    assert found["reachable_with_wider_operations"] is False
    assert found["licenses_naming_a_new_component"] is False


# -- the certificate ------------------------------------------------------------------------------

def test_an_experimental_diagnosis_produces_a_certificate_the_state_accepts():
    found = _diagnose(bodies.SPANNING_DEMAND)
    certificate = probe.certificate_from_experiment(found, new_component="joint_registry")
    state = st.extend_components(
        _seed_state(),
        certificate=certificate,
        provenance=tr.provenance("lineage_owned", produced_by="lineage"),
    )
    assert st.component_names(state)[-1] == "joint_registry"


def test_the_certificate_names_the_experiments_that_were_actually_run():
    found = _diagnose(bodies.SPANNING_DEMAND)
    certificate = probe.certificate_from_experiment(found, new_component="joint_registry")
    tried = [record["compositions_tried"] for record in certificate["probe_records"]]
    assert all(count > 0 for count in tried), "a certificate must rest on probes that ran"
    assert sum(tried) == sum(record["attempts"] for record in found["probes"])


# -- budget, isolation and honesty ------------------------------------------------------------------

def test_a_budget_that_runs_out_is_not_reported_as_exhaustion():
    """Stopping early because the allowance ran out says nothing about the registry."""
    found = _diagnose(bodies.SPANNING_DEMAND, budget=tr.Budget(limits={"probes": 1}))
    assert found["registry_exhausted"] is False
    assert found["licenses_naming_a_new_component"] is False
    assert found["probes"][0]["budget_exhausted"] is True


def test_every_composition_costs_budget():
    budget = tr.Budget(limits={"probes": 200})
    _diagnose(bodies.SPANNING_DEMAND, budget=budget)
    assert budget.spent["probes"] > 0


def test_probing_does_not_touch_the_lineage_state():
    state = _seed_state()
    before = tr.canonical_bytes(dict(state))
    _diagnose(bodies.SPANNING_DEMAND, state=state)
    assert tr.canonical_bytes(dict(state)) == before


def test_a_composition_search_is_shortest_first():
    """The budget should buy the simplest explanations before the elaborate ones."""
    found = list(probe.compositions(["a", "b"], max_length=2))
    assert [item.operations for item in found] == [
        ("a",),
        ("b",),
        ("a", "b"),
        ("b", "a"),
    ]


def test_a_probe_reaching_for_an_operation_it_does_not_have_reports_error_not_a_crash():
    outcome = probe.search(
        registry_reference=REGISTRY,
        operations=["not_an_operation"],
        tasks=bodies.LOCAL_DEMAND,
        isolation=tr.Isolation(),
        budget=tr.Budget(limits={"probes": 4}),
        max_length=1,
    )
    assert outcome["resolved"] is False
    assert outcome["search_exhausted"] is True


def test_an_operation_registry_reference_must_be_resolvable():
    with pytest.raises(probe.ProbeError, match="module:attribute"):
        probe.resolve_registry("not_a_reference")
    with pytest.raises(probe.ProbeError, match="does not name a mapping"):
        probe.resolve_registry("genesis.development_bodies:parent_body")


# -- the vocabulary path, measured rather than declared ---------------------------------------------

def _vocabulary_state():
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
            {"name": "resolvable_by_%s" % name, "origin": "seed", "certificate": None}
            for name in ("operator_table", "signal_interface")
        ],
    )


def _pair(demands, *, budget=None, state=None):
    return probe.find_confusable_pair_by_experiment(
        state if state is not None else _vocabulary_state(),
        demands,
        registry_reference=REGISTRY,
        component_operations=COMPONENT_OPERATIONS,
        isolation=tr.Isolation(),
        budget=budget or tr.Budget(limits={"probes": 4000}),
    )


def test_a_confusable_pair_is_measured_not_declared():
    """Same row by measurement, different cause by measurement. Nothing states either."""
    pair = _pair([bodies.CONFUSABLE_A, bodies.CONFUSABLE_B])
    assert pair is not None
    assert pair["shared_prior_row"] == [False, False]
    assert pair["limiting_components"] == ["operator_table", "signal_interface"]
    assert pair["measurements"][0]["resolving_operations"] == ["increment", "negate", "double"]
    assert pair["measurements"][1]["resolving_operations"] == ["double", "square", "negate"]


def test_the_limiting_component_is_where_the_composition_mostly_lives():
    pair = _pair([bodies.CONFUSABLE_A, bodies.CONFUSABLE_B])
    assert pair["measurements"][0]["component_shares"] == {
        "operator_table": 2,
        "signal_interface": 1,
    }
    assert pair["measurements"][1]["component_shares"] == {
        "operator_table": 1,
        "signal_interface": 2,
    }


def test_two_demands_with_the_same_measured_cause_are_not_confusable():
    """Reading alike is not enough; the causes have to differ or there is nothing to separate."""
    assert _pair([bodies.CONFUSABLE_A, bodies.CONFUSABLE_A]) is None


def test_two_demands_the_vocabulary_already_separates_are_not_confusable():
    """`LOCAL_DEMAND` reads [True, False]; `CONFUSABLE_A` reads [False, False]."""
    assert _pair([bodies.LOCAL_DEMAND, bodies.CONFUSABLE_A]) is None


def test_a_demand_nothing_resolves_cannot_be_half_of_a_pair():
    """Without a resolving composition there is no measured cause, so there is nothing to compare."""
    assert _pair([bodies.UNREACHABLE_DEMAND, bodies.CONFUSABLE_A]) is None


def test_the_separating_feature_is_read_out_of_the_measurements():
    state = _vocabulary_state()
    pair = _pair([bodies.CONFUSABLE_A, bodies.CONFUSABLE_B], state=state)
    certificate = probe.vocabulary_certificate_from_experiment(state, pair)
    assert certificate["new_feature"] == "requires_increment"
    assert certificate["separated_rows"] == [[False, False, True], [False, False, False]]
    extended = st.extend_vocabulary(state, certificate=certificate)
    assert st.vocabulary_names(extended)[-1] == "requires_increment"


def test_a_vocabulary_certificate_needs_a_row_that_describes_the_same_thing():
    """The measured row has one entry per component; the certificate refuses a width mismatch."""
    state = _vocabulary_state()
    pair = _pair([bodies.CONFUSABLE_A, bodies.CONFUSABLE_B], state=state)
    narrower = st.create_state(
        body_digest="s0",
        components=state["components"],
        vocabulary=[{"name": "only_one", "origin": "seed", "certificate": None}],
    )
    with pytest.raises(probe.ProbeError, match="describe the same thing"):
        probe.vocabulary_certificate_from_experiment(narrower, pair)


def test_demands_resolving_through_identical_operations_separate_nothing():
    state = _vocabulary_state()
    pair = _pair([bodies.CONFUSABLE_A, bodies.CONFUSABLE_B], state=state)
    same = dict(pair)
    same["measurements"] = [pair["measurements"][0], dict(pair["measurements"][0])]
    with pytest.raises(probe.ProbeError, match="no measured feature separates them"):
        probe.vocabulary_certificate_from_experiment(state, same)


def test_measuring_a_demand_costs_budget_and_the_budget_can_refuse():
    budget = tr.Budget(limits={"probes": 2})
    pair = _pair([bodies.CONFUSABLE_A, bodies.CONFUSABLE_B], budget=budget)
    assert pair is None, "a measurement the budget cut short must not become a finding"


def test_a_probe_body_computes_a_value_and_does_not_judge_it():
    """The body itself, outside the sandbox, so the sandbox tests are not proving this by proxy.

    A probe that decided for itself whether it had solved the demand would be a candidate marking
    its own paper, and every certificate resting on it would inherit that.
    """
    body = probe.composed_probe_body(REGISTRY, ("double", "increment"))
    assert body.attempt({"task_id": "p0", "input": 3, "expected": 7}) == 7
    # The same call, with the task expecting something else, returns the same value: the body has
    # no opinion about correctness at all.
    assert body.attempt({"task_id": "p0", "input": 3, "expected": 999}) == 7
    assert probe.grade_probe({"expected": 7}, 7) == "solved"
    assert probe.grade_probe({"expected": 8}, 7) == "unsolved"
