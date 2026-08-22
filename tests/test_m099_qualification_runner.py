from __future__ import annotations

import pytest

from scripts import run_m099_qualification as runner
from scripts.author_m099_qualification_pool import load_pool


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


def test_runner_refuses_unbound_pool() -> None:
    protocol = {
        "status": "frozen",
        "qualification_population": {"pool_digest": "0" * 64},
    }
    with pytest.raises(runner.QualificationRefused, match="does not bind"):
        runner.require_frozen(protocol, load_pool())


def test_projection_removes_every_frozen_ephemeral_key_recursively() -> None:
    value = {
        "pid": 1,
        "producer_pid": 2,
        "consumer_pids": [3, 4],
        "search_path": ["temporary"],
        "nested": {
            "pid": 5,
            "consumer_pids": [6],
            "confirmed": True,
        },
        "process_facts": {
            "fresh_process_invocations": 8,
            "producer_terminated_before_consumers": True,
        },
    }
    assert runner.stable_projection(value) == {
        "nested": {"confirmed": True},
        "process_facts": {
            "fresh_process_invocations": 8,
            "producer_terminated_before_consumers": True,
        },
    }
