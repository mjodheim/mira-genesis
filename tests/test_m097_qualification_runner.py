from __future__ import annotations

import pytest

from scripts import run_m097_qualification as runner
from scripts.author_m097_qualification_pool import load_pool


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


def test_runner_refuses_an_unbound_pool_before_mechanism_checks() -> None:
    protocol = {
        "status": "frozen",
        "qualification_population": {"pool_digest": "0" * 64},
    }
    with pytest.raises(runner.QualificationRefused, match="pool digest"):
        runner.require_frozen(protocol, load_pool())
