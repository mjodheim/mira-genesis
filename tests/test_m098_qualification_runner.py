from __future__ import annotations

import copy

import pytest

from scripts import run_m098_qualification as runner
from scripts.author_m098_qualification_pool import load_pool


def test_runner_refuses_without_arming() -> None:
    with pytest.raises(runner.QualificationRefused, match="requires --arm"):
        runner.materialize()


def test_runner_refuses_draft_protocol() -> None:
    protocol = {
        "status": "draft",
        "qualification_population": {"pool_digest": load_pool()["pool_digest"]},
    }
    with pytest.raises(runner.QualificationRefused, match="not frozen"):
        runner.require_frozen(protocol, load_pool())


def test_runner_refuses_an_unbound_pool_before_other_bindings() -> None:
    protocol = {
        "status": "frozen",
        "qualification_population": {"pool_digest": "0" * 64},
    }
    with pytest.raises(runner.QualificationRefused, match="does not bind"):
        runner.require_frozen(protocol, load_pool())


def test_runner_refuses_an_unbound_m097_result() -> None:
    protocol = {
        "status": "frozen",
        "qualification_population": {"pool_digest": load_pool()["pool_digest"]},
        "m097_input": {"result_digest": "0" * 64, "state_digest": "0" * 64},
    }
    with pytest.raises(runner.QualificationRefused, match="M097 preserved result"):
        runner.require_frozen(protocol, load_pool())


def test_stable_projection_removes_only_process_and_location_ephemera() -> None:
    value = {
        "pid": 1,
        "producer_pid": 2,
        "search_path": ["temporary"],
        "nested": {"confirmed": True, "pid": 3},
    }
    projected = runner.stable_projection(copy.deepcopy(value))
    assert projected == {"nested": {"confirmed": True}}
