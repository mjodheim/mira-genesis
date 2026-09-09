"""The refusals the endogenous work added, driven to their negatives.

The census over the completed source measured 187 guards and found 43 no test distinguished. Almost
all of them were new again — the program grammar, the artifact store, and the controller's world,
intent and mechanism validation. Same shape as every round before it: a refusal written down and
never made fire, in code whose whole subject is not trusting a record that was never checked.

These are cheap, direct tests. The refusals *are* the boundary, so the cost of exercising them should
never be the reason not to.
"""
from __future__ import annotations

import pytest

from genesis import controller
from genesis import development_bodies as bodies
from genesis import program as pg
from genesis import search_fixtures as fixtures
from genesis import state as st
from genesis import trust_root as tr
from genesis.loop import Genesis
from genesis.store import ArtifactStore, StoreError

HOST = tr.provenance("host_written", produced_by="endogenous guard test")
REGISTRY = bodies.PROBE_REGISTRY


def _genesis(**overrides):
    state = st.create_state(
        body_digest="seed",
        components=[
            {"name": "operator_table", "origin": "seed", "certificate": None, "provenance": HOST}
        ],
        vocabulary=[{"name": "resolvable_by_operator_table", "origin": "seed", "certificate": None}],
    )
    arguments = {
        "state": state,
        "body_factory": fixtures.seed_body,
        "budget": tr.Budget(limits={"generations": 40, "probes": 40}),
        "isolation": tr.Isolation(),
        "grade": fixtures.graded_against_expected,
    }
    arguments.update(overrides)
    return Genesis(**arguments)


# -- the program grammar -------------------------------------------------------------------------

@pytest.mark.parametrize(
    "nodes, match",
    [
        (["not a record"], "node 0 is not a record"),
        ([{"op": "input"}], "reads no named task field"),
        ([{"op": "input", "field": ""}], "reads no named task field"),
        ([{"op": "constant", "value": {"a": 1}}], "constant this grammar cannot carry"),
        ([{"op": "call", "args": []}], "calls no named operation"),
        ([{"op": "call", "operation": "", "args": []}], "calls no named operation"),
        (
            [{"op": "input", "field": "input"}, {"op": "call", "operation": "double", "args": ["0"]}],
            "argument that is not a node index",
        ),
        (
            [{"op": "input", "field": "input"}, {"op": "call", "operation": "double", "args": [True]}],
            "argument that is not a node index",
        ),
    ],
)
def test_the_grammar_refuses_a_node_it_cannot_read(nodes, match):
    with pytest.raises(pg.ProgramError, match=match):
        pg.program(nodes=nodes, root=0, registry_reference=REGISTRY)


def test_a_program_may_not_read_a_field_it_did_not_declare():
    """Inputs are declared so the reachable task surface is visible before the program runs."""
    with pytest.raises(pg.ProgramError, match="did not declare as an input"):
        pg.program(
            nodes=[{"op": "input", "field": "expected"}],
            root=0,
            registry_reference=REGISTRY,
            inputs=("input",),
        )


def test_a_program_names_the_registry_it_composes_over():
    with pytest.raises(pg.ProgramError, match="names the operation registry"):
        pg.program(nodes=[{"op": "input", "field": "input"}], root=0, registry_reference="")


def test_running_a_program_against_a_task_that_lacks_its_field_fails_rather_than_improvising():
    """The withheld answer key arrives here: the field is simply absent, and nothing invents one."""
    body = pg.program_artifact(
        pg.program(
            nodes=[{"op": "input", "field": "expected"}],
            root=0,
            registry_reference=REGISTRY,
            inputs=("expected",),
        )
    )()
    with pytest.raises(pg.ProgramError, match="carries no field"):
        body.attempt({"task_id": "q0", "input": 1})


def test_something_that_is_not_a_canonical_program_is_not_a_program_artifact():
    with pytest.raises(pg.ProgramError, match="not a canonical program"):
        pg.ProgramArtifact(value={"schema": "something-else"})


# -- identity and the store ------------------------------------------------------------------------

def test_an_artifact_claiming_exact_bytes_must_supply_bytes():
    """The protocol cannot be claimed without the thing that makes the claim true."""

    class _Liar:
        def exact_artifact_bytes(self):
            return "not bytes"

        def __call__(self):  # pragma: no cover - never built
            return None

    with pytest.raises(tr.TrustRootError, match="did not return bytes"):
        tr.artifact_digest_of(_Liar())


def test_the_store_stores_bytes_and_says_so_when_it_is_handed_something_else(tmp_path):
    with pytest.raises(StoreError, match="stored as bytes"):
        ArtifactStore(tmp_path).put_bytes("a string is not bytes")


# -- the world: nothing may be reached that it does not admit ---------------------------------------

def _world(**overrides):
    arguments = {
        "tasks": fixtures.SEARCH_TASKS,
        "demands": {},
        "substrates": {},
        "probe_registry": REGISTRY,
        "component_operations": {"operator_table": list(fixtures.SEARCH_ALPHABET)},
        "artifacts": {},
        "grade": fixtures.graded_against_expected,
    }
    arguments.update(overrides)
    return controller.world(**arguments)


def test_an_artifact_the_world_does_not_contain_cannot_be_resolved():
    with pytest.raises(controller.ControllerError, match="does not contain"):
        _world().resolve("nothing_by_that_name")


@pytest.mark.parametrize("reference", ["artifacts", "policies"])
def test_a_target_without_an_importable_shape_is_refused(reference):
    here = _world(**{reference: {"broken": "no_colon_here"}})
    resolve = here.resolve if reference == "artifacts" else here.resolve_policy
    with pytest.raises(controller.ControllerError, match="no importable module:symbol target"):
        resolve("broken")


@pytest.mark.parametrize("reference", ["artifacts", "policies"])
def test_a_target_that_is_not_runnable_is_refused(reference):
    here = _world(**{reference: {"flat": "genesis.development_bodies:PROBE_REGISTRY"}})
    resolve = here.resolve if reference == "artifacts" else here.resolve_policy
    with pytest.raises(controller.ControllerError, match="does not resolve to something runnable"):
        resolve("flat")


def test_a_search_needs_an_alphabet_to_search():
    genesis = _genesis()
    here = _world(component_operations={})
    with pytest.raises(controller.ControllerError, match="needs an operation alphabet"):
        controller._search_transform(genesis, here, controller.SearchTransform(name="empty"))


@pytest.mark.parametrize(
    "intent, match",
    [
        (controller.AcquireComponent(demand="absent", new_component="x"), "no demand named"),
        (controller.SeparateVocabulary(demands=("absent",)), "no demand named"),
        (
            controller.Migrate(
                substrate="absent", probe_for=(), translation="t", used_operations=()
            ),
            "no substrate named",
        ),
    ],
)
def test_an_intent_naming_something_this_world_lacks_is_refused(intent, match):
    genesis = _genesis()
    handler = controller.HANDLERS[type(intent)]
    with pytest.raises(controller.ControllerError, match=match):
        handler(genesis, _world(), intent)


# -- the machinery binding ----------------------------------------------------------------------

def _with_tools(genesis, tools):
    genesis.state = st.create_state(
        body_digest=genesis.state["body_digest"],
        components=genesis.state["components"],
        vocabulary=genesis.state["vocabulary"],
        tools=tools,
        acquisitions=genesis.state["acquisitions"],
        observations=genesis.state["observations"],
        generation=genesis.state["generation"],
    )
    return genesis


def _tool(artifact):
    return {
        "name": controller.MECHANISM_TOOL_NAME,
        "role": controller.MECHANISM_ROLE,
        "artifact": artifact,
        "provenance": HOST,
    }


def test_a_lineage_carrying_two_admitted_mechanisms_is_ambiguous_rather_than_resolved():
    artifact = tr.artifact_digest_of(fixtures.timid_policy)
    genesis = _with_tools(_genesis(), [_tool(artifact), _tool(artifact)])
    with pytest.raises(controller.ControllerError, match="more than one admitted"):
        controller.bound_mechanism_artifact(genesis)


def test_an_admitted_mechanism_without_an_artifact_identity_is_refused():
    genesis = _with_tools(_genesis(), [_tool("just a name")])
    with pytest.raises(controller.ControllerError, match="carries no artifact identity"):
        controller.bound_mechanism_artifact(genesis)


def test_a_different_mechanism_cannot_be_admitted_over_the_one_in_force():
    """The refusal that made the evidence-backed update necessary in the first place."""
    genesis = _genesis()
    controller.run(genesis, _world(), fixtures.timid_policy, max_steps=0)
    with pytest.raises(controller.ControllerError, match="evidence-backed machinery update"):
        controller.run(genesis, _world(), fixtures.bolder_policy, max_steps=0)


def test_a_lambda_cannot_be_admitted_as_decision_machinery():
    genesis = _genesis()
    with pytest.raises(tr.TrustRootError, match="inside another scope"):
        controller.run(genesis, _world(), lambda context: controller.Stop(), max_steps=0)


def test_a_mechanism_artifact_record_of_the_wrong_kind_is_refused():
    with pytest.raises(controller.ControllerError, match="must be importable symbols"):
        controller._resolve_artifact_record({"kind": "exact_bytes"})


def test_a_mechanism_whose_module_no_longer_matches_its_artifact_is_refused():
    """The symbol still imports; what it resolves to is no longer what was admitted.

    Tampering with the recorded source digest alone is not enough, because the identity is
    recomputed from the live module — which is the point. The record has to claim a digest the
    module does not produce.
    """
    artifact = dict(tr.artifact_digest_of(fixtures.timid_policy))
    artifact["artifact_digest"] = "0" * 64
    with pytest.raises(controller.ControllerError, match="no longer matches its admitted artifact"):
        controller._resolve_artifact_record(artifact)


def test_the_lineage_must_still_carry_the_mechanism_each_step_is_run_under():
    """Re-checked per step, not once at admission.

    Going through `run` would re-admit a mechanism the state no longer carries, which is the correct
    behaviour for a fresh lineage. The guard is about a lineage whose binding changed *underneath* an
    invocation, so the invocation is what this reaches.
    """
    genesis = _genesis()
    controller.run(genesis, _world(), fixtures.timid_policy, max_steps=0)
    other = tr.artifact_digest_of(fixtures.bolder_policy)
    with pytest.raises(controller.ControllerError, match="no longer carries the controller"):
        controller._invoke_admitted_mechanism(genesis, fixtures.bolder_policy, other)


# -- intents in and out of the isolated worker ------------------------------------------------------

def test_something_that_is_not_an_intent_cannot_be_encoded():
    with pytest.raises(controller.ControllerError, match="which is not an intent"):
        controller._intent_record("just a string")


def test_an_unrecognised_intent_record_is_refused_rather_than_guessed():
    with pytest.raises(controller.ControllerError, match="unrecognised intent record"):
        controller._intent_from_record({"type": "SomethingNew"})


def test_a_policy_this_lineage_has_not_admitted_cannot_be_replaced():
    genesis = _genesis()
    with pytest.raises(controller.ControllerError, match="no acquisition policy to replace"):
        controller._adopt_policy(
            genesis, fixtures.policy_world(), controller.AdoptPolicy(candidate="bolder")
        )


# -- the isolated call boundary ---------------------------------------------------------------------

def test_an_isolated_call_may_not_be_granted_network_access():
    from genesis.sandbox import run_isolated_callable

    with pytest.raises(tr.TrustRootError, match="may not be granted network access"):
        run_isolated_callable(
            fixtures.graded_against_expected, {}, tr.Isolation(network_permitted=True)
        )
