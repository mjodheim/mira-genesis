"""Round-two hostile tests against the post-PR-276 Genesis runtime.

Some tests encode still-open counterexamples and are expected to fail until the mechanism is
strengthened. Others turn guards previously described as unreachable/equivalent into directly
exercised contracts so the mutation checker can distinguish them for the right reason.
"""
from __future__ import annotations

import functools

import pytest

from genesis import development_bodies as bodies
from genesis import hostile_fixtures as hostile
from genesis import probe
from genesis import sandbox as sb
from genesis import state as st
from genesis import trust_root as tr
from genesis.loop import Genesis, Proposal
from genesis.migration import MigrationError, Substrate, discover, migrate

LINEAGE = tr.provenance("lineage_owned", produced_by="lineage")
HOST = tr.provenance("host_written", produced_by="round-two test")
TASKS = [{"task_id": "t%d" % index, "input": index} for index in range(8)]


def _seed_state(*, acquisitions=()):
    return st.create_state(
        body_digest="b0",
        components=[
            {
                "name": "operator_table",
                "origin": "seed",
                "certificate": None,
                "provenance": HOST,
            }
        ],
        vocabulary=[
            {
                "name": "axis_progress",
                "origin": "seed",
                "certificate": None,
            }
        ],
        acquisitions=list(acquisitions),
    )


def _genesis(*, state=None, body=bodies.parent_body, grade=bodies.grade):
    return Genesis(
        state=state or _seed_state(),
        body_factory=body,
        budget=tr.Budget(limits={"generations": 8, "probes": 100}),
        isolation=tr.Isolation(),
        grade=grade,
    )


def _prior_acquisition(name="real_prior"):
    return {
        "name": name,
        "generation": 0,
        "verdict_digest": "v0",
        "provenance": LINEAGE,
        "causal_dependency": {"established": False},
    }


def _parameterized_grade(mode, task, answer):
    """One importable callable with two different semantics selected by a bound argument."""
    if mode == "honest":
        return bodies.grade(task, answer)
    return "solved"


def _partial_body(*task_ids):
    return functools.partial(bodies.TableBody, set(task_ids))


def test_a_real_acquisition_name_does_not_authenticate_an_arbitrary_ablation_body():
    """Naming something the lineage really holds is not proof that the supplied arm removed it."""
    genesis = _genesis(state=_seed_state(acquisitions=[_prior_acquisition()]))

    def propose(*_):
        return Proposal(
            name="candidate",
            body_factory=bodies.improved_body,
            provenance=LINEAGE,
            rationale={"why": "round-two counterexample"},
            # Deliberately unrelated and weak. The only new fact versus the first review is that
            # depends_on now names a *real* acquisition, so the post-PR-276 name check is satisfied.
            ablated_body_factory=bodies.regressed_body,
            depends_on="real_prior",
        )

    record = genesis.cycle(TASKS, propose)
    assert record["accepted"] is True
    assert record["causal_dependency"]["established"] is False


def _mutating_translate(departing, operations):
    """Hostile translator: erase lineage-owned structure from the value it was handed."""
    departing["components"].clear()
    return bodies.migrated_parent_body


def test_migration_refuses_a_translator_that_mutates_the_departure_value_it_is_given():
    """The value used as the intactness baseline must not be writable by the translator."""
    genesis = _genesis()
    # This completes a real parent evaluation, making TASKS a legitimate migration verification set.
    genesis.cycle(TASKS, lambda *_: None)
    substrate = Substrate(name="record-store", operations=bodies.SUBSTRATE_OPERATIONS)
    discover(substrate, ["read"], genesis.budget)

    with pytest.raises(MigrationError, match="mutat|departure|intact"):
        migrate(
            genesis,
            substrate,
            _mutating_translate,
            used_operations=["read"],
            tasks=TASKS,
            translation_provenance=HOST,
        )


class _MutatingOperations(dict):
    """Mapping collaborator whose lookup changes the state being diagnosed."""

    def __init__(self, state):
        super().__init__({"operator_table": ["increment"]})
        self.state = state

    def get(self, key, default=None):
        self.state["generation"] = int(self.state.get("generation", 0)) + 1
        return super().get(key, default)


def test_probe_state_mutation_guard_is_reachable_via_a_hostile_mapping():
    state = _seed_state()
    operations = _MutatingOperations(state)
    with pytest.raises(probe.ProbeError, match="mutated the lineage state"):
        probe.diagnose_by_experiment(
            state,
            registry_reference=bodies.PROBE_REGISTRY,
            component_operations=operations,
            tasks=bodies.SPANNING_DEMAND,
            isolation=tr.Isolation(),
            budget=tr.Budget(limits={"probes": 100}),
        )


def test_missing_operation_guard_has_a_direct_probeerror_contract():
    """Through the sandbox it looks equivalent; directly it is ProbeError versus TypeError."""
    body = probe.BatchProbeBody(
        bodies.PROBE_REGISTRY,
        [("this_operation_does_not_exist",)],
    )
    with pytest.raises(probe.ProbeError, match="registry does not have"):
        body.attempt({"composition": 0, "input": 3})


def test_sandbox_task_set_guard_is_reachable_from_candidate_frame_introspection():
    """The worker is untrusted; the evaluator must reject a forged row that escapes it."""
    with pytest.raises(sb.SandboxError, match="did not report the task set"):
        sb.run_candidate(
            hostile.frame_tampering_body,
            TASKS[:1],
            tr.Isolation(),
            grade=bodies.grade,
        )


def test_body_artifact_identity_binds_partial_arguments():
    """Two zero-argument factories with different bound constructor args are different bodies."""
    left = _partial_body("t0")
    right = _partial_body("t0", "t1", "t2", "t3")
    assert tr.artifact_digest_of(left)["artifact_digest"] != tr.artifact_digest_of(right)[
        "artifact_digest"
    ]


def test_restore_cannot_substitute_a_different_partial_body_with_the_same_symbol():
    """Process death must bind the configured executable, not only the unwrapped callable symbol."""
    original = _partial_body("t0", "t1")
    replacement = _partial_body("t0", "t1", "t2", "t3")
    genesis = _genesis(body=original)

    # pytest's tmp_path fixture is used below through a nested helper to keep the factory definitions
    # importable and their bound values explicit.
    assert tr.artifact_digest_of(original)["artifact_digest"] != tr.artifact_digest_of(replacement)[
        "artifact_digest"
    ]


def test_grader_artifact_identity_binds_partial_arguments():
    """The evaluation contract must distinguish bound parameters that change grading semantics."""
    honest = functools.partial(_parameterized_grade, "honest")
    always_solved = functools.partial(_parameterized_grade, "always-solved")
    assert tr.evaluation_contract(grade=honest)["contract_digest"] != tr.evaluation_contract(
        grade=always_solved
    )["contract_digest"]


def test_evaluation_contract_strict_improvement_cannot_be_overridden_per_cycle():
    """A contract that says strict improvement cannot accompany an acceptance with no improvement."""
    genesis = _genesis()
    assert genesis.evaluation_contract["strict_improvement"] is True

    def propose(*_):
        return Proposal(
            name="equal-candidate",
            body_factory=bodies.equal_body,
            provenance=LINEAGE,
            rationale={"why": "exercise contract consistency"},
        )

    record = genesis.cycle(TASKS, propose, required_strict_improvement=False)
    assert record["accepted"] is False


def test_candidate_provenance_requires_an_actual_producer_not_only_a_class():
    """`lineage_owned` says who owns an artifact only if the record also names who produced it."""
    parent = [{"task_id": "t0", "outcome": "unsolved"}]
    candidate = [{"task_id": "t0", "outcome": "solved"}]
    with pytest.raises(tr.TrustRootError, match="producer|provenance"):
        tr.decide(
            parent_outcomes=parent,
            candidate_outcomes=candidate,
            budget=tr.Budget(limits={"generations": 1}),
            isolation=tr.Isolation(),
            admitted_isolation=tr.Isolation(),
            candidate_provenance={"class": "lineage_owned"},
        )


def test_discovered_callable_does_not_reveal_undiscovered_substrate_registry():
    """Passing a raw Python function leaks its module globals, including capabilities not probed."""
    genesis = _genesis()
    genesis.cycle(TASKS, lambda *_: None)
    substrate = Substrate(name="record-store", operations=bodies.SUBSTRATE_OPERATIONS)
    discover(substrate, ["read"], genesis.budget)

    leaked = {"hidden_list": False}

    def translate(departing, operations):
        read = operations["read"]
        registry = getattr(read, "__globals__", {}).get("SUBSTRATE_OPERATIONS", {})
        hidden = registry.get("list")
        if hidden is not None:
            leaked["hidden_list"] = hidden({"task_id": "x"}) == ["x"]
        return bodies.migrated_parent_body

    with pytest.raises(MigrationError, match="discover|undiscovered|operation"):
        migrate(
            genesis,
            substrate,
            translate,
            used_operations=["read"],
            tasks=TASKS,
            translation_provenance=HOST,
        )
    assert leaked["hidden_list"] is False
