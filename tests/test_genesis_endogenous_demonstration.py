"""Lock the second demonstration: a lineage that builds its descendants and changes how it builds.

The first demonstration drives a fixed programme and its bodies are importable symbols the host
wrote, so every descendant it adopts is *selected*. This one starts with an empty catalogue. The
properties below are the ones that would be worth something if a real mechanism were attached, and
each is driven to its negative somewhere in the suite — `tests/test_genesis_endogenous_search.py`
for the search and store, `tests/test_genesis_policy_update.py` for the machinery change.

DEVELOPMENT apparatus. Nothing here is a scientific observation and no gate moves.
"""
from __future__ import annotations

import pytest

from genesis import search_fixtures as fixtures
from genesis import trust_root as tr
from scripts.run_genesis_endogenous_demonstration import demonstrate


@pytest.fixture(scope="module")
def record():
    return demonstrate()


def _step(record, intent):
    for step in record["run"]["steps"]:
        if step["intent"] == intent:
            return step
    raise AssertionError("the demonstration never reached a %s step" % intent)


def test_it_claims_nothing_scientific(record):
    assert record["development"] is True
    assert record["is_a_scientific_observation"] is False
    assert record["advances_a_generality_gate"] is False
    assert record["frozen"] is False


def test_there_was_nothing_to_select(record):
    """The property the first demonstration cannot have: an empty catalogue."""
    assert record["world_offered_no_body_to_select"] is True


def test_the_parent_could_not_do_the_work(record):
    """A limitation the run has to overcome, rather than a parent that was already right."""
    assert record["parent_answered"] == [True, False, False, False, False, False]


def test_the_machinery_changed_on_evidence_about_what_it_produced(record):
    step = _step(record, "AdoptPolicy")
    assert step["policy_updated"] is True
    assert step["incumbent_solved"] < step["candidate_solved"]
    assert step["descendants_compared_by"] == "genesis.trust_root.decide"
    assert step["graded_by_either_policy"] is False


def test_the_body_was_constructed_and_had_to_be_searched_for(record):
    step = _step(record, "SearchTransform")
    assert step["accepted"] is True
    assert step["body_was_constructed_not_selected"] is True
    assert step["candidates_considered"] > 1
    rejected = [c for c in step["candidates"] if not c["accepted"]]
    assert rejected, "a search where nothing was rejected did not search"


def test_the_adopted_body_answers_what_the_parent_could_not(record):
    assert record["final_body"]["calls_in_order"] == ["double", "increment"]
    assert record["final_body"]["answers"] == [True] * len(fixtures.SEARCH_TASKS)


def test_the_body_identity_binds_the_bytes_that_run(record):
    assert record["final_body"]["artifact"]["binds_exact_executed_bytes"] is True


def test_the_new_machinery_is_what_found_the_body(record):
    """Order matters: the policy changed first, and the search that worked ran under the new one."""
    intents = [step["intent"] for step in record["run"]["steps"]]
    assert intents.index("AdoptPolicy") < intents.index("SearchTransform")
    assert (
        record["machinery_in_force"]["artifact_digest"]
        == tr.artifact_digest_of(fixtures.bolder_policy)["artifact_digest"]
    )


def test_the_lineage_comes_back_from_disk_with_a_body_nobody_could_hand_it(record):
    survival = record["survives_process_death"]
    assert survival["state_digest_matches"] is True
    assert survival["journal_head_matches"] is True
    assert survival["body_recovered_without_a_caller_supplying_it"] is True
    assert survival["machinery_matches"] is True


def test_the_run_is_reproducible(record):
    assert demonstrate()["record_digest"] == record["record_digest"]
