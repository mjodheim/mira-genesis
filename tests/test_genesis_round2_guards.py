"""The refusals the round-two repairs added, each driven to its negative.

The guard census after the round-two work found thirty-five refusals no test distinguished, and
almost every one of them was new: written in this round, asserting a property, exercised by nothing.
That is the same defect shape the round is about — a record testifying to something the code has not
been shown to do — one level up, in the tests rather than in the runtime.

So these are the counterexamples for the remainder: state and certificate validation, restore,
diagnostic-feature semantics, and capability access. Two guards are deliberately absent from this
file and named in `experiments/GENESIS/RUNTIME_NOTES.md` instead, because they assert invariants the
lines above them already establish.
"""
from __future__ import annotations

import functools

import pytest

from genesis import development_bodies as bodies
from genesis import probe
from genesis import state as st
from genesis import trust_root as tr
from genesis.capabilities import Capability, CapabilityError, CapabilitySet, undeclared_use
from genesis.journal import Journal
from genesis.loop import Genesis, Proposal

HOST = tr.provenance("host_written", produced_by="round-two guard test")
LINEAGE = tr.provenance("lineage_owned", produced_by="lineage")
TASKS = [{"task_id": "t%d" % index, "input": index} for index in range(8)]


def _seed_state(**overrides):
    arguments = {
        "body_digest": "b0",
        "components": [
            {"name": "operator_table", "origin": "seed", "certificate": None, "provenance": HOST},
            {"name": "signal_interface", "origin": "seed", "certificate": None, "provenance": HOST},
        ],
        "vocabulary": [
            {"name": "resolvable_by_%s" % name, "origin": "seed", "certificate": None}
            for name in ("operator_table", "signal_interface")
        ],
    }
    arguments.update(overrides)
    return st.create_state(**arguments)


def _genesis(**overrides):
    arguments = {
        "state": _seed_state(),
        "body_factory": bodies.parent_body,
        "budget": tr.Budget(limits={"generations": 8}),
        "isolation": tr.Isolation(),
        "grade": bodies.grade,
    }
    arguments.update(overrides)
    return Genesis(**arguments)


# -- lineage state: an entry has to be a record, and a certificate has to hold up ------------------

def test_a_history_entry_that_is_not_a_record_is_refused():
    with pytest.raises(st.StateError, match="is not a record"):
        _seed_state(tools=["a bare string where a record belongs"])


def test_a_component_artifact_cannot_be_built_without_a_resolving_composition():
    """The machinery an acquisition installs is derived from the evidence, so no evidence, no
    machinery — rather than a component that holds a name and no operations."""
    with pytest.raises(st.StateError, match="no resolving composition"):
        st.component_artifact({"new_component": "joint_registry", "certificate_digest": "d"})


def _component_certificate():
    return st.component_extension_certificate(
        prior_registry=["operator_table", "signal_interface"],
        new_component="joint_registry",
        demand_digest="d",
        probe_records=[
            {
                "component": name,
                "resolved": False,
                "search_exhausted": True,
                "budget_exhausted": False,
                "instrument_failure": False,
            }
            for name in ("operator_table", "signal_interface")
        ],
        resolves_with_new_component=True,
        resolving_composition={"composition_digest": "c0", "operations": ["double", "increment"]},
    )


def test_a_component_certificate_whose_digest_was_swapped_does_not_reconstruct():
    """Rebuilding the certificate from its own records is what checks the evidence; the stored
    digest only says nobody edited it since it was written."""
    certificate = dict(_component_certificate())
    certificate["certificate_digest"] = "0" * 64
    with pytest.raises(st.StateError, match="does not reconstruct from its own evidence"):
        _seed_state(
            components=[
                {"name": "operator_table", "origin": "seed", "certificate": None, "provenance": HOST},
                {"name": "signal_interface", "origin": "seed", "certificate": None, "provenance": HOST},
                {
                    "name": "joint_registry",
                    "origin": "acquired",
                    "certificate": certificate,
                    "provenance": LINEAGE,
                },
            ]
        )


def test_a_probe_whose_search_did_not_exhaust_is_not_evidence_of_insufficiency():
    with pytest.raises(st.StateError, match="did not exhaust"):
        st.component_extension_certificate(
            prior_registry=["operator_table"],
            new_component="joint_registry",
            demand_digest="d",
            probe_records=[{"component": "operator_table", "resolved": False}],
            resolves_with_new_component=True,
            resolving_composition={"composition_digest": "c0", "operations": ["double"]},
        )


def test_a_probe_that_ran_out_of_budget_is_not_evidence_of_insufficiency():
    """A search that stopped because it could not afford to continue found nothing out."""
    with pytest.raises(st.StateError, match="without exhausting its options"):
        st.component_extension_certificate(
            prior_registry=["operator_table"],
            new_component="joint_registry",
            demand_digest="d",
            probe_records=[
                {
                    "component": "operator_table",
                    "resolved": False,
                    "search_exhausted": True,
                    "budget_exhausted": True,
                }
            ],
            resolves_with_new_component=True,
            resolving_composition={"composition_digest": "c0", "operations": ["double"]},
        )


def _vocabulary_certificate(**changes):
    arguments = {
        "prior_vocabulary": ["resolvable_by_operator_table", "resolvable_by_signal_interface"],
        "new_feature": "requires_increment",
        "demand_digests": ["d1", "d2"],
        "shared_prior_row": [False, False],
        "limiting_components": ["operator_table", "signal_interface"],
        "separated_rows": [[False, False, True], [False, False, False]],
    }
    arguments.update(changes)
    return st.vocabulary_extension_certificate(**arguments)


def _with_feature(certificate):
    return _seed_state(
        vocabulary=[
            {"name": "resolvable_by_operator_table", "origin": "seed", "certificate": None},
            {"name": "resolvable_by_signal_interface", "origin": "seed", "certificate": None},
            {
                "name": certificate["new_feature"],
                "origin": "acquired",
                "certificate": certificate,
                "provenance": LINEAGE,
            },
        ]
    )


def test_a_feature_certificate_whose_evidence_does_not_separate_is_refused_on_load():
    """A stored certificate is re-run through the builder's rules, not trusted for having a digest."""
    certificate = dict(_vocabulary_certificate())
    certificate["separated_rows"] = [[False, False, True], [False, False, True]]
    certificate["certificate_digest"] = tr.digest_of(
        {k: v for k, v in certificate.items() if k != "certificate_digest"}
    )
    with pytest.raises(st.StateError, match="does not establish it"):
        _with_feature(certificate)


def test_a_feature_certificate_whose_digest_was_swapped_does_not_reconstruct():
    certificate = dict(_vocabulary_certificate())
    certificate["certificate_digest"] = "0" * 64
    with pytest.raises(st.StateError, match="does not reconstruct from its own evidence"):
        _with_feature(certificate)


# -- diagnostic features have to be evaluable, or they are labels ---------------------------------

def _measure(state):
    return probe.measure(
        state,
        bodies.LOCAL_DEMAND,
        registry_reference=bodies.PROBE_REGISTRY,
        component_operations=bodies.COMPONENT_OPERATIONS,
        isolation=tr.Isolation(),
        budget=tr.Budget(limits={"probes": 2000}),
    )


def test_a_feature_naming_a_component_the_lineage_does_not_hold_cannot_be_measured():
    state = _seed_state(
        vocabulary=[{"name": "resolvable_by_a_component_nobody_has", "origin": "seed", "certificate": None}]
    )
    with pytest.raises(probe.ProbeError, match="holds no component"):
        _measure(state)


def test_a_feature_whose_semantics_the_runtime_cannot_evaluate_is_refused_not_defaulted():
    """A made-up boolean in a diagnostic row is worse than a missing one: everything downstream
    reads the row as a measurement."""
    state = _seed_state(
        vocabulary=[{"name": "axis_progress", "origin": "seed", "certificate": None}]
    )
    with pytest.raises(probe.ProbeError, match="cannot evaluate"):
        _measure(state)


def test_the_features_this_runtime_does_understand_still_measure():
    """The control: the refusals above are about unknown semantics, not a measurement that broke."""
    measurement = _measure(_seed_state())
    assert measurement["vocabulary"] == [
        "resolvable_by_operator_table",
        "resolvable_by_signal_interface",
    ]
    assert measurement["row"] == [True, False]


# -- capabilities: what was never discovered is not reachable by name ------------------------------

def test_a_capability_the_lineage_never_discovered_cannot_be_reached():
    handles = CapabilitySet({"read": bodies.SUBSTRATE_OPERATIONS["read"]})
    with pytest.raises(CapabilityError, match="never discovered"):
        handles["list"]


def test_a_capability_handle_counts_its_own_use():
    """`used_operations` is derived from this, so the count is the record rather than a declaration."""
    handles = CapabilitySet({"read": bodies.SUBSTRATE_OPERATIONS["read"]})
    assert handles.used() == []
    assert handles["read"]({"task_id": "x"}) == "x"
    assert handles.used() == ["read"]
    assert handles.use_counts() == {"read": 1}


def test_a_handle_does_not_carry_the_module_that_defined_it():
    handle = Capability("read", bodies.SUBSTRATE_OPERATIONS["read"])
    assert getattr(handle, "__globals__", {}) == {}
    assert "SUBSTRATE_OPERATIONS" not in getattr(handle._call, "__globals__", {})


def test_declared_and_used_operations_are_compared_in_both_directions():
    difference = undeclared_use(["read", "write"], ["read", "list"])
    assert difference["used_but_not_declared"] == ["list"]
    assert difference["declared_but_not_used"] == ["write"]


# -- the evaluator may not change between admission and the cycle that names it --------------------

def _grade_everything_solved(task, answer):  # pragma: no cover - identity only
    return "solved"


def test_a_cycle_cannot_narrow_the_comparison_while_swapping_the_evaluator():
    """Narrowing is licensed; rewriting the measure under cover of narrowing it is not."""
    genesis = _genesis()
    genesis.grade = _grade_everything_solved

    def propose(*_):
        return Proposal(
            name="candidate",
            body_factory=bodies.improved_body,
            provenance=LINEAGE,
            rationale={},
        )

    with pytest.raises(tr.TrustRootError, match="not rewrite the measure"):
        genesis.cycle(TASKS, propose, control_factory=bodies.regressed_body)


# -- restore: a lineage resumes one committed checkpoint, or it does not resume --------------------

def test_restore_refuses_a_directory_with_no_committed_checkpoint(tmp_path):
    genesis = _genesis()
    st.save_state(genesis.state, tmp_path / "lineage_state.json")
    genesis.journal.save(tmp_path / "descent_journal.json")
    with pytest.raises(tr.TrustRootError, match="no committed checkpoint"):
        Genesis.restore(tmp_path, body_factory=bodies.parent_body, grade=bodies.grade)


def _persisted(tmp_path):
    genesis = _genesis()
    genesis.persist(tmp_path)
    return genesis


def _rewrite_manifest(tmp_path, **changes):
    import json

    path = tmp_path / "runtime_checkpoint.json"
    manifest = json.loads(path.read_bytes().decode("utf-8"))
    manifest.update(changes)
    path.write_bytes(tr.canonical_bytes(manifest) + b"\n")
    return manifest


def test_restore_refuses_a_manifest_that_does_not_reproduce_its_own_digest(tmp_path):
    _persisted(tmp_path)
    _rewrite_manifest(tmp_path, generation=99)
    with pytest.raises(tr.TrustRootError, match="does not reproduce its own digest"):
        Genesis.restore(tmp_path, body_factory=bodies.parent_body, grade=bodies.grade)


def _reseal(tmp_path, **changes):
    """Change the manifest and recompute its digest, so only the binding it makes can catch it."""
    manifest = _rewrite_manifest(tmp_path, **changes)
    payload = {k: v for k, v in manifest.items() if k != "checkpoint_digest"}
    (tmp_path / "runtime_checkpoint.json").write_bytes(
        tr.canonical_bytes({**payload, "checkpoint_digest": tr.digest_of(payload)}) + b"\n"
    )


def test_restore_refuses_a_state_the_checkpoint_did_not_commit(tmp_path):
    _persisted(tmp_path)
    _reseal(tmp_path, state_digest="0" * 64)
    with pytest.raises(tr.TrustRootError, match="not the one this checkpoint committed"):
        Genesis.restore(tmp_path, body_factory=bodies.parent_body, grade=bodies.grade)


def test_restore_refuses_a_journal_the_checkpoint_did_not_commit(tmp_path):
    _persisted(tmp_path)
    _reseal(tmp_path, journal_head="0" * 64)
    with pytest.raises(tr.TrustRootError, match="journal is not the one this checkpoint committed"):
        Genesis.restore(tmp_path, body_factory=bodies.parent_body, grade=bodies.grade)


def test_restore_refuses_to_re_admit_a_different_allowance(tmp_path):
    """Process death must not be a way to negotiate a new budget."""
    _persisted(tmp_path)
    with pytest.raises(tr.TrustRootError, match="may not re-admit a different allowance"):
        Genesis.restore(
            tmp_path,
            body_factory=bodies.parent_body,
            budget=tr.Budget(limits={"generations": 9999}),
            grade=bodies.grade,
        )


def test_restore_resumes_the_lineage_it_committed(tmp_path):
    """The control, so the refusals above are findings rather than a restore that never works."""
    genesis = _persisted(tmp_path)
    resumed = Genesis.restore(tmp_path, body_factory=bodies.parent_body, grade=bodies.grade)
    assert resumed.state["state_digest"] == genesis.state["state_digest"]
    assert resumed.journal.head == genesis.journal.head
    assert dict(resumed.budget.limits) == dict(genesis.budget.limits)


def test_a_journal_is_still_a_journal_after_a_restore(tmp_path):
    _persisted(tmp_path)
    resumed = Genesis.restore(tmp_path, body_factory=bodies.parent_body, grade=bodies.grade)
    assert isinstance(resumed.journal, Journal)
    assert len(resumed.journal) >= 1


def test_a_partial_grader_survives_the_round_trip(tmp_path):
    """Identity now covers bound state, so a configured grader has to restore as itself."""
    grade = functools.partial(_graded_by, "honest")
    genesis = _genesis(grade=grade)
    genesis.persist(tmp_path)
    resumed = Genesis.restore(tmp_path, body_factory=bodies.parent_body, grade=grade)
    assert (
        resumed.evaluation_contract["contract_digest"]
        == genesis.evaluation_contract["contract_digest"]
    )


def _graded_by(mode, task, answer):
    if mode == "honest":
        return bodies.grade(task, answer)
    return "solved"  # pragma: no cover - the dishonest arm is only ever an identity here
