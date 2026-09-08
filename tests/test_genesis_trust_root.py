"""Hostile tests for the Genesis trust root and lineage state.

The load-bearing tests here are not that the runtime works. They are that a mutable Genesis cannot
get a better verdict by reporting one, cannot widen its own limits, cannot spend past its budget, and
cannot grow a registry without evidence that the previous one was insufficient.
"""
from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from genesis import state as st
from genesis import trust_root as tr

ROOT = Path(__file__).resolve().parents[1]
ADMITTED = tr.Isolation()


def _outcomes(solved: int, total: int = 6, *, errors: int = 0, **extra):
    rows = []
    for index in range(total):
        if index < solved:
            outcome = "solved"
        elif index < solved + errors:
            outcome = "error"
        else:
            outcome = "unsolved"
        rows.append({"task_id": "t%d" % index, "outcome": outcome, **extra})
    return rows


def _decide(parent, candidate, control=None, **kwargs):
    return tr.decide(
        parent_outcomes=parent,
        candidate_outcomes=candidate,
        control_outcomes=control,
        budget=tr.Budget(limits={"generations": 10}),
        isolation=ADMITTED,
        admitted_isolation=ADMITTED,
        candidate_provenance=tr.provenance("lineage_owned", produced_by="lineage"),
        **kwargs,
    )


# -- the invariant that must never bend ---------------------------------------------------------

def test_the_trust_root_imports_nothing_from_mutable_genesis():
    """Data flows one way. There must be no import through which an evolving component reaches in."""
    tree = ast.parse((ROOT / "genesis" / "trust_root.py").read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    reaching_in = sorted(
        name for name in imported if name == "genesis" or name.startswith("genesis.")
    )
    assert not reaching_in, "the trust root imports mutable Genesis: %s" % reaching_in
    assert not any(name.startswith("metamorphosis") for name in imported)


def test_a_candidate_cannot_improve_its_verdict_by_reporting_a_better_score():
    """Every number is recomputed from raw rows; a self-reported summary is not read."""
    parent = _outcomes(3)
    honest = _decide(parent, _outcomes(2))
    assert honest["accepted"] is False

    lying = _decide(
        parent,
        _outcomes(2, score=99.0, solved_count=6, accepted=True, verdict="accepted"),
    )
    assert lying["accepted"] is False
    assert lying["candidate"]["counts"]["solved"] == 2
    assert lying["read_any_self_reported_score"] is False
    assert lying["rejection_reasons"] == honest["rejection_reasons"]


def test_a_candidate_that_genuinely_improves_is_accepted():
    verdict = _decide(_outcomes(3), _outcomes(5))
    assert verdict["accepted"] is True
    assert verdict["rejection_reasons"] == []
    assert verdict["improved"] is True


def test_the_verdict_records_the_bytes_of_the_evaluator_that_produced_it():
    verdict = _decide(_outcomes(3), _outcomes(5))
    assert verdict["trust_root_source_sha256"] == tr.source_digest()
    assert tr.verify_verdict(verdict, admitted_source_sha256=tr.source_digest()) == []


def test_a_verdict_from_another_trust_root_is_refused():
    verdict = _decide(_outcomes(3), _outcomes(5))
    problems = tr.verify_verdict(verdict, admitted_source_sha256="0" * 64)
    assert any("different trust root" in problem for problem in problems)


def test_a_tampered_verdict_does_not_reproduce():
    verdict = _decide(_outcomes(3), _outcomes(2))
    verdict["accepted"] = True
    verdict["rejection_reasons"] = []
    problems = tr.verify_verdict(verdict, admitted_source_sha256=tr.source_digest())
    assert any("digest does not reproduce" in problem for problem in problems)


# -- isolation, budget, provenance --------------------------------------------------------------

def test_a_candidate_may_not_run_under_wider_limits_than_the_lineage_was_admitted_under():
    wider = tr.Isolation(network_permitted=True)
    with pytest.raises(tr.TrustRootError, match="wider than the admitted envelope"):
        tr.decide(
            parent_outcomes=_outcomes(3),
            candidate_outcomes=_outcomes(5),
            budget=tr.Budget(limits={"generations": 1}),
            isolation=wider,
            admitted_isolation=ADMITTED,
            candidate_provenance=tr.provenance("lineage_owned", produced_by="lineage"),
        )


@pytest.mark.parametrize(
    "field,value",
    (
        ("cpu_seconds", 10_000.0),
        ("memory_bytes", 2**40),
        ("wall_clock_seconds", 10_000.0),
        ("filesystem_writes_permitted", True),
        ("subprocess_permitted", True),
    ),
)
def test_every_isolation_dimension_is_checked(field, value):
    with pytest.raises(tr.TrustRootError):
        tr.Isolation(**{field: value}).assert_no_wider_than(ADMITTED)


def test_the_budget_refuses_rather_than_overrunning():
    budget = tr.Budget(limits={"generations": 2})
    assert budget.spend("generations") == 1
    assert budget.spend("generations") == 0
    with pytest.raises(tr.BudgetExhausted, match="exhausted"):
        budget.spend("generations")


def test_an_undeclared_budget_dimension_cannot_be_spent():
    with pytest.raises(tr.TrustRootError, match="undeclared budget dimension"):
        tr.Budget(limits={"generations": 1}).spend("probes")


def test_an_unclassifiable_artifact_is_refused_rather_than_defaulted():
    with pytest.raises(tr.TrustRootError, match="unrecognised provenance"):
        tr.provenance("obviously_fine", produced_by="lineage")
    with pytest.raises(tr.TrustRootError, match="names no producer"):
        tr.provenance("lineage_owned", produced_by="  ")


def test_a_model_written_transformation_is_recorded_as_model_mediated():
    verdict = tr.decide(
        parent_outcomes=_outcomes(3),
        candidate_outcomes=_outcomes(5),
        budget=tr.Budget(limits={"generations": 1}),
        isolation=ADMITTED,
        admitted_isolation=ADMITTED,
        candidate_provenance=tr.provenance("model_mediated", produced_by="an external model"),
    )
    assert verdict["candidate_provenance"]["class"] == "model_mediated"


# -- the comparison itself ----------------------------------------------------------------------

def test_arms_must_face_the_same_tasks():
    with pytest.raises(tr.TrustRootError, match="same tasks"):
        _decide(_outcomes(3, total=6), _outcomes(5, total=5))


def test_a_repeated_task_row_is_refused():
    rows = _outcomes(3)
    rows.append(dict(rows[0]))
    with pytest.raises(tr.TrustRootError, match="twice"):
        _decide(_outcomes(3, total=7), rows)


def test_an_unrecognised_outcome_is_refused():
    rows = _outcomes(3)
    rows[0]["outcome"] = "brilliant"
    with pytest.raises(tr.TrustRootError, match="unrecognised outcome"):
        _decide(_outcomes(3), rows)


def test_rising_errors_reject_even_when_more_tasks_are_solved():
    verdict = _decide(_outcomes(2, total=6), _outcomes(3, total=6, errors=2))
    assert verdict["accepted"] is False
    assert any("errors rose" in reason for reason in verdict["rejection_reasons"])


def test_a_candidate_must_beat_the_equal_budget_control():
    verdict = _decide(_outcomes(2), _outcomes(4), control=_outcomes(4))
    assert verdict["accepted"] is False
    assert any("equal-budget control" in reason for reason in verdict["rejection_reasons"])


def test_refusal_is_an_outcome_rather_than_an_absence():
    rows = _outcomes(3)
    rows[5]["outcome"] = "refused"
    verdict = _decide(_outcomes(3), rows)
    assert verdict["candidate"]["counts"]["refused"] == 1


# -- registries grow only against evidence ------------------------------------------------------

def _seed_state():
    return st.create_state(
        body_digest="b0",
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


def _component_certificate(**overrides):
    kwargs = {
        "prior_registry": ["operator_table", "signal_interface"],
        "new_component": "candidate_space",
        "demand_digest": "d0",
        "probe_records": [
            {"component": "operator_table", "resolved": False, "search_exhausted": True},
            {"component": "signal_interface", "resolved": False, "search_exhausted": True},
        ],
        "resolves_with_new_component": True,
        "resolving_composition": {
            "schema": "genesis-composed-probe-v1",
            "operations": ["double", "increment"],
            "composition_digest": "measured",
        },
    }
    kwargs.update(overrides)
    return st.component_extension_certificate(**kwargs)


def test_the_lineage_can_name_a_component_its_registry_did_not_have():
    grown = st.extend_components(
        _seed_state(),
        certificate=_component_certificate(),
        provenance=tr.provenance("lineage_owned", produced_by="lineage"),
    )
    assert st.component_names(grown) == ["operator_table", "signal_interface", "candidate_space"]
    assert grown["components"][-1]["origin"] == "acquired"
    assert st.decode_state(st.encode_state(grown))["state_digest"] == grown["state_digest"]


def test_a_component_cannot_be_added_when_an_existing_one_resolved_the_demand():
    with pytest.raises(st.StateError, match="prior registry was sufficient"):
        _component_certificate(
            probe_records=[
                {"component": "operator_table", "resolved": True},
                {"component": "signal_interface", "resolved": False},
            ]
        )


def test_a_component_cannot_be_added_without_probing_every_prior_component():
    with pytest.raises(st.StateError, match="never probed"):
        _component_certificate(
            probe_records=[
                {"component": "operator_table", "resolved": False, "search_exhausted": True}
            ]
        )


def test_a_component_that_does_not_resolve_the_demand_is_refused():
    with pytest.raises(st.StateError, match="does not resolve the demand"):
        _component_certificate(resolves_with_new_component=False)


def test_a_certificate_issued_against_another_registry_is_refused():
    grown = st.extend_components(
        _seed_state(),
        certificate=_component_certificate(),
        provenance=tr.provenance("lineage_owned", produced_by="lineage"),
    )
    with pytest.raises(st.StateError, match="different registry"):
        st.extend_components(
            grown,
            certificate=_component_certificate(new_component="diagnostic_policy"),
            provenance=tr.provenance("lineage_owned", produced_by="lineage"),
        )


def test_a_tampered_component_certificate_does_not_reproduce():
    certificate = dict(_component_certificate())
    certificate["prior_registry_exhausted"] = True
    certificate["new_component"] = "smuggled"
    with pytest.raises(st.StateError, match="does not reproduce"):
        st.extend_components(
            _seed_state(),
            certificate=certificate,
            provenance=tr.provenance("lineage_owned", produced_by="lineage"),
        )


def _vocabulary_certificate(**overrides):
    kwargs = {
        "prior_vocabulary": ["axis_progress", "signals_consistent"],
        "new_feature": "candidate_space_undetermined",
        "demand_digests": ["da", "db"],
        "shared_prior_row": [True, False],
        "limiting_components": ["signal_interface", "candidate_space"],
        "separated_rows": [[True, False, True], [True, False, False]],
    }
    kwargs.update(overrides)
    return st.vocabulary_extension_certificate(**kwargs)


def test_the_lineage_can_extend_its_vocabulary_on_a_confusable_pair():
    grown = st.extend_vocabulary(_seed_state(), certificate=_vocabulary_certificate())
    assert st.vocabulary_names(grown)[-1] == "candidate_space_undetermined"
    assert st.decode_state(st.encode_state(grown))["state_digest"] == grown["state_digest"]


def test_a_feature_that_does_not_separate_the_pair_is_refused():
    with pytest.raises(st.StateError, match="does not separate"):
        _vocabulary_certificate(separated_rows=[[True, False, True], [True, False, True]])


def test_two_demands_with_the_same_limiting_component_are_not_confusable():
    with pytest.raises(st.StateError, match="different limiting components"):
        _vocabulary_certificate(limiting_components=["signal_interface", "signal_interface"])


def test_the_pair_must_actually_share_the_prior_row():
    with pytest.raises(st.StateError, match="disagree with the shared prior row"):
        _vocabulary_certificate(separated_rows=[[True, True, True], [True, False, False]])


def test_one_demand_is_not_a_pair():
    with pytest.raises(st.StateError, match="two distinct demands"):
        _vocabulary_certificate(demand_digests=["da", "da"])


# -- state integrity and persistence ------------------------------------------------------------

def test_an_acquired_entry_without_a_certificate_is_refused():
    with pytest.raises(st.StateError, match="carries no certificate"):
        st.create_state(
            body_digest="b0",
            components=[
                {
                    "name": "invented",
                    "origin": "acquired",
                    "certificate": None,
                    "provenance": tr.provenance("lineage_owned", produced_by="lineage"),
                }
            ],
            vocabulary=[],
        )


def test_a_seed_entry_may_not_carry_an_extension_certificate():
    with pytest.raises(st.StateError, match="may not carry an extension certificate"):
        st.create_state(
            body_digest="b0",
            components=[
                {
                    "name": "operator_table",
                    "origin": "seed",
                    "certificate": _component_certificate(),
                    "provenance": tr.provenance("host_written", produced_by="seed"),
                }
            ],
            vocabulary=[],
        )


def test_a_component_without_provenance_is_refused():
    with pytest.raises(st.StateError, match="no recognised provenance"):
        st.create_state(
            body_digest="b0",
            components=[
                {"name": "operator_table", "origin": "seed", "certificate": None, "provenance": {}}
            ],
            vocabulary=[],
        )


def test_a_forged_state_is_a_value_that_does_not_reconstruct():
    forged = json.loads(st.encode_state(_seed_state()).decode())
    forged["generation"] = 99
    with pytest.raises(st.StateError, match="digest does not reproduce"):
        st.decode_state(forged)


def test_the_state_survives_process_death(tmp_path):
    original = st.extend_components(
        _seed_state(),
        certificate=_component_certificate(),
        provenance=tr.provenance("lineage_owned", produced_by="lineage"),
    )
    path = tmp_path / "nested" / "lineage.json"
    st.save_state(original, path)
    restored = st.load_state(path)
    assert restored["state_digest"] == original["state_digest"]
    assert st.component_names(restored) == st.component_names(original)
    assert restored["components"][-1]["certificate"]["prior_registry_exhausted"] is True


def test_saving_leaves_no_torn_state_behind(tmp_path):
    path = tmp_path / "lineage.json"
    st.save_state(_seed_state(), path)
    assert path.exists()
    assert not list(tmp_path.glob("*.partial"))
