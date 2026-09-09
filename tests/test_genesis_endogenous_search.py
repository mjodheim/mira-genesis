"""A lineage that adopts a body nobody installed.

Every descendant this runtime has ever adopted was an importable symbol the host wrote before the run
began: `World.artifacts` listed it and `Transform.body` named it. That is integrated execution of a
host-authored catalogue, and the objective asks for something the catalogue cannot supply — a lineage
that modifies its body, which requires a body that was not there.

These tests are about the difference. The world they build admits **no** body artifacts, so nothing
can be selected; what gets adopted is a program the runtime constructed, evaluated under the same
immutable trust root as any other candidate, and can restore after process death because it kept the
bytes. They are DEVELOPMENT apparatus tests: they establish that the mechanism exists and refuses
what it claims to refuse, not that anything general was learned.
"""
from __future__ import annotations

import json

import pytest

from genesis import controller
from genesis import development_bodies as bodies
from genesis import program as pg
from genesis import search_fixtures as fixtures
from genesis import state as st
from genesis import trust_root as tr
from genesis.loop import ARTIFACT_STORE_NAME, Genesis
from genesis.store import ArtifactStore, StoreError

HOST = tr.provenance("host_written", produced_by="endogenous-search fixture")


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
        # A parent that already answers one question, so a candidate has to beat it rather than
        # merely be better than nothing.
        "body_factory": fixtures.seed_body,
        "budget": tr.Budget(limits={"generations": 40, "probes": 40}),
        "isolation": tr.Isolation(),
        "grade": fixtures.graded_against_expected,
    }
    arguments.update(overrides)
    return Genesis(**arguments)


# -- the program language ------------------------------------------------------------------------

def _double_increment():
    return pg.program(
        nodes=[
            {"op": "input", "field": "input"},
            {"op": "call", "operation": "double", "args": [0]},
            {"op": "call", "operation": "increment", "args": [1]},
        ],
        root=2,
        registry_reference=bodies.PROBE_REGISTRY,
    )


def test_a_program_is_identified_by_the_bytes_that_are_it():
    """The first artifact kind in this runtime whose digest covers what actually executes."""
    artifact = pg.program_artifact(_double_increment())
    identity = tr.artifact_digest_of(artifact)
    assert identity["kind"] == "exact_bytes"
    assert identity["binds_exact_executed_bytes"] is True
    assert identity["bytes_sha256"] == tr.hashlib.sha256(artifact.exact_artifact_bytes()).hexdigest()


def test_changing_one_operation_changes_the_program_identity():
    left = pg.program_artifact(_double_increment())
    right = pg.program_artifact(
        pg.program(
            nodes=[
                {"op": "input", "field": "input"},
                {"op": "call", "operation": "triple", "args": [0]},
                {"op": "call", "operation": "increment", "args": [1]},
            ],
            root=2,
            registry_reference=bodies.PROBE_REGISTRY,
        )
    )
    assert (
        tr.artifact_digest_of(left)["artifact_digest"]
        != tr.artifact_digest_of(right)["artifact_digest"]
    )


@pytest.mark.parametrize(
    "nodes, root, match",
    [
        ([], 0, "computes nothing"),
        ([{"op": "input", "field": "input"}], 5, "root is not one of its nodes"),
        ([{"op": "shell_out", "cmd": "rm"}], 0, "no recognised operation kind"),
        (
            [{"op": "input", "field": "input"}, {"op": "call", "operation": "double", "args": [1]}],
            1,
            "only build on what it has already computed",
        ),
        (
            [{"op": "input", "field": "input"}, {"op": "call", "operation": "double", "args": [0]}],
            1,
            None,
        ),
    ],
)
def test_the_grammar_refuses_what_it_cannot_carry(nodes, root, match):
    """A cycle is impossible by construction, not by a later check that could be wrong."""
    if match is None:
        assert pg.program(nodes=nodes, root=root, registry_reference=bodies.PROBE_REGISTRY)
        return
    with pytest.raises(pg.ProgramError, match=match):
        pg.program(nodes=nodes, root=root, registry_reference=bodies.PROBE_REGISTRY)


def test_a_program_calling_an_operation_the_registry_lacks_fails_rather_than_improvises():
    body = pg.program_artifact(
        pg.program(
            nodes=[
                {"op": "input", "field": "input"},
                {"op": "call", "operation": "not_in_the_registry", "args": [0]},
            ],
            root=1,
            registry_reference=bodies.PROBE_REGISTRY,
        )
    )()
    with pytest.raises(pg.ProgramError, match="the admitted registry does not have"):
        body.attempt({"task_id": "q0", "input": 1})


# -- the search --------------------------------------------------------------------------------

def test_the_lineage_adopts_a_body_the_world_never_contained(tmp_path):
    """The headline property: nothing was available to select, so what was adopted was built."""
    genesis = _genesis()
    here = fixtures.search_world()
    assert dict(here.artifacts) == {}, "this world must offer nothing to choose"

    run = controller.run(
        genesis, here, fixtures.search_then_stop, max_steps=3, checkpoint_directory=tmp_path
    )
    step = run["steps"][0]

    assert step["intent"] == "SearchTransform"
    assert step["accepted"] is True
    assert step["body_was_constructed_not_selected"] is True
    assert step["candidates_considered"] > 1, "a search that tried one thing is not a search"

    identity = tr.artifact_digest_of(genesis.body_factory)
    assert identity["binds_exact_executed_bytes"] is True
    assert step["adopted_artifact_digest"] == identity["artifact_digest"]
    # The adopted body solves what the parent could not.
    assert genesis.state["generation"] == 1


def test_the_adopted_body_is_the_one_that_answers_the_questions():
    """Adoption came from the trust root's comparison, not from the search liking its own output."""
    genesis = _genesis()
    controller.run(genesis, fixtures.search_world(), fixtures.search_then_stop, max_steps=3)
    body = genesis.body_factory()
    assert [body.attempt(task) for task in fixtures.SEARCH_TASKS] == [
        task["expected"] for task in fixtures.SEARCH_TASKS
    ]


def test_search_stops_at_its_declared_bound_rather_than_when_it_succeeds():
    """A search that ran on because it had not won yet would not be a bounded search."""
    genesis = _genesis()
    run = controller.run(
        genesis, fixtures.search_world(), fixtures.search_once_then_stop, max_steps=3
    )
    step = run["steps"][0]
    assert step["candidates_considered"] <= 2
    assert step["accepted"] is False
    assert step["search_space_exhausted"] is False


def test_a_search_that_finds_nothing_is_recorded_as_a_search_that_found_nothing():
    """The negative has to be reachable, or the positive says nothing about the data."""
    genesis = _genesis()
    run = controller.run(
        genesis,
        fixtures.search_world(),
        fixtures.search_an_alphabet_that_cannot_reach_it,
        max_steps=3,
    )
    step = run["steps"][0]
    assert step["accepted"] is False
    assert step["search_space_exhausted"] is True
    assert step["adopted_artifact_digest"] == ""
    assert genesis.state["acquisitions"] == []
    # The failures are kept, which is what lets a later policy condition on them.
    assert genesis.state["observations"]


def test_the_search_is_charged_to_the_lineage_budget():
    genesis = _genesis(budget=tr.Budget(limits={"generations": 40, "probes": 3}))
    controller.run(genesis, fixtures.search_world(), fixtures.search_once_then_stop, max_steps=3)
    assert genesis.budget.spent["probes"] > 0


# -- process death, with nobody able to hand the body back -----------------------------------------

def test_a_generated_body_is_restored_from_the_store_without_a_caller_supplying_it(tmp_path):
    """The property an importable fixture never needed and a generated descendant cannot do without."""
    genesis = _genesis()
    controller.run(
        genesis, fixtures.search_world(), fixtures.search_then_stop, max_steps=3,
        checkpoint_directory=tmp_path,
    )
    committed = tr.artifact_digest_of(genesis.body_factory)

    restored = Genesis.restore(tmp_path, grade=fixtures.graded_against_expected)

    assert restored.state["state_digest"] == genesis.state["state_digest"]
    assert tr.artifact_digest_of(restored.body_factory) == committed
    assert restored.body_factory()  .attempt(fixtures.SEARCH_TASKS[0]) == fixtures.SEARCH_TASKS[0]["expected"]


def test_restore_fails_closed_when_the_store_lost_the_generated_body(tmp_path):
    genesis = _genesis()
    controller.run(
        genesis, fixtures.search_world(), fixtures.search_then_stop, max_steps=3,
        checkpoint_directory=tmp_path,
    )
    for path in (tmp_path / ARTIFACT_STORE_NAME).rglob("*.json"):
        path.unlink()

    with pytest.raises(tr.TrustRootError, match="cannot be recovered"):
        Genesis.restore(tmp_path, grade=fixtures.graded_against_expected)


def test_restore_still_requires_a_body_for_an_importable_fixture(tmp_path):
    """Only a generated body can be reconstructed; a fixture's behaviour lives in a module."""
    genesis = _genesis()
    genesis.persist(tmp_path)
    with pytest.raises(tr.TrustRootError, match="supply body_factory"):
        Genesis.restore(tmp_path, grade=fixtures.graded_against_expected)


# -- the store -----------------------------------------------------------------------------------

def test_the_store_refuses_to_pretend_it_holds_an_importable_symbol(tmp_path):
    store = ArtifactStore(tmp_path)
    with pytest.raises(StoreError, match="recorded as a pointer"):
        store.put(bodies.parent_body)


def test_one_digest_keeps_its_bytes(tmp_path):
    store = ArtifactStore(tmp_path)
    artifact = pg.program_artifact(_double_increment())
    digest = store.put(artifact)
    assert store.put(artifact) == digest, "storing the same artifact twice is not a change"

    path = store.path_for(digest)
    path.write_bytes(b'{"schema":"tampered"}')
    with pytest.raises(StoreError, match="are not those bytes"):
        store.get_bytes(digest)


def test_a_stored_program_comes_back_as_the_program_that_went_in(tmp_path):
    store = ArtifactStore(tmp_path)
    artifact = pg.program_artifact(_double_increment())
    digest = store.put(artifact)
    assert tr.artifact_digest_of(store.get_program(digest)) == tr.artifact_digest_of(artifact)


def test_a_program_that_does_not_canonicalise_to_its_own_name_is_refused(tmp_path):
    """Reordered keys are the same program; they are not the same bytes, and the store says so."""
    store = ArtifactStore(tmp_path)
    artifact = pg.program_artifact(_double_increment())
    digest = store.put(artifact)
    reordered = json.dumps(dict(reversed(list(artifact.value.items()))), separators=(", ", ": "))
    store.path_for(digest).write_bytes(reordered.encode())
    with pytest.raises(StoreError):
        store.get_program(digest)


def test_the_search_record_distinguishes_two_candidates_that_use_the_same_operations():
    """`increment` twice and `increment` once reach for the same operations and are not the same
    program. These records are what a later policy would reason over, so they have to tell them
    apart."""
    genesis = _genesis()
    run = controller.run(genesis, fixtures.search_world(), fixtures.search_then_stop, max_steps=3)
    chains = ["->".join(candidate["calls"]) for candidate in run["steps"][0]["candidates"]]
    assert len(chains) == len(set(chains)), "the search evaluated the same program twice"
    assert "increment->increment" in chains and "increment" in chains


def test_the_generator_never_holds_the_grader_or_the_answers():
    """The separation that makes an adopted descendant evidence rather than a preference.

    The programs the search builds are inert data over an operation alphabet. There is no path from
    a candidate to `expected`: the sandbox withholds it on the way in, so a body that tried to read
    the answer key finds the field absent.
    """
    peeking = pg.program_artifact(
        pg.program(
            nodes=[{"op": "input", "field": "expected"}],
            root=0,
            registry_reference=bodies.PROBE_REGISTRY,
            inputs=("expected",),
        )
    )
    from genesis.sandbox import run_candidate

    run = run_candidate(
        peeking, fixtures.SEARCH_TASKS, tr.Isolation(), grade=fixtures.graded_against_expected
    )
    assert run["completed"] is True
    assert "expected" in run["withheld_from_the_candidate"]
    # Every row is an error: the field it reached for was not there to read.
    assert {row["outcome"] for row in run["outcomes"]} == {"error"}


def test_two_runs_from_the_same_seed_reproduce_the_same_artifact(tmp_path):
    """Deterministic search: the same lineage and the same bound reach the same program."""
    first, second = _genesis(), _genesis()
    controller.run(first, fixtures.search_world(), fixtures.search_then_stop, max_steps=3)
    controller.run(second, fixtures.search_world(), fixtures.search_then_stop, max_steps=3)
    assert tr.artifact_digest_of(first.body_factory) == tr.artifact_digest_of(second.body_factory)
    assert first.state["state_digest"] == second.state["state_digest"]
