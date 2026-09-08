"""Round-two hostile tests against the post-PR-276 Genesis runtime.

Some tests encode still-open counterexamples and are expected to fail until the mechanism is
strengthened. Others turn guards previously described as unreachable/equivalent into directly
exercised contracts so the mutation checker can distinguish them for the right reason.
"""
from __future__ import annotations

import inspect

import pytest

from genesis import development_bodies as bodies
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


def _genesis(*, state=None, body=bodies.parent_body):
    return Genesis(
        state=state or _seed_state(),
        body_factory=body,
        budget=tr.Budget(limits={"generations": 8, "probes": 100}),
        isolation=tr.Isolation(),
        grade=bodies.grade,
    )


def _prior_acquisition(name="real_prior"):
    return {
        "name": name,
        "generation": 0,
        "verdict_digest": "v0",
        "provenance": LINEAGE,
        "causal_dependency": {"established": False},
    }


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


class _FrameTamperingBody:
    def attempt(self, task):
        # The body runs inside sandbox._child. The caller frame owns the mutable rows list whose
        # integrity the final sandbox guard claims is structurally guaranteed.
        caller = inspect.currentframe().f_back
        caller.f_locals["rows"].append({"task_id": "forged-task", "answer": None})
        return bodies.answer_to(task)


def _frame_tampering_body():
    return _FrameTamperingBody()


def test_sandbox_task_set_guard_is_reachable_from_candidate_frame_introspection():
    with pytest.raises(sb.SandboxError, match="did not report the task set"):
        sb.run_candidate(
            _frame_tampering_body,
            TASKS[:1],
            tr.Isolation(),
            grade=bodies.grade,
        )
