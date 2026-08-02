from __future__ import annotations

from dataclasses import replace

import pytest

from metamorphosis.m020_self_rewrite import (
    Case,
    SelfRewriteEngine,
    VersionedCodeBody,
)
from metamorphosis.m023_workspace import (
    CandidateWorkspace,
    SandboxLimits,
    WorkspaceAdoptionGate,
)


ABSOLUTE_PLUS_ZERO = """\
def policy(x):
    if x >= 0:
        return x + 0
    return -x + 0
"""

DEVELOPMENT = (
    Case((-3,), 4),
    Case((-1,), 2),
    Case((1,), 2),
    Case((3,), 4),
)

REGRESSION = (
    Case((-21,), 22),
    Case((0,), 1),
    Case((34,), 35),
)


def test_candidate_runs_in_a_disposable_subprocess_workspace():
    source = "def policy(x):\n    return x * 2\n"
    cases = (Case((2,), 4), Case((-3,), -6))

    result = CandidateWorkspace().evaluate(source, "policy", cases)

    assert result.status == "completed"
    assert result.perfect
    assert result.return_code == 0
    assert not result.timed_out
    assert result.source_digest
    assert result.workspace_digest


def test_runtime_fault_is_reported_without_crashing_the_host():
    source = "def policy(x):\n    return 10 // x\n"

    result = CandidateWorkspace().evaluate(
        source,
        "policy",
        (Case((2,), 5), Case((0,), 0)),
    )

    assert result.status == "completed"
    assert result.passed == 1
    assert result.total == 2
    assert result.failures[0]["kind"] == "ZeroDivisionError"


def test_workspace_digest_is_deterministic_and_case_sensitive():
    workspace = CandidateWorkspace()
    source = "def policy(x):\n    return x + 1\n"

    first = workspace.evaluate(source, "policy", (Case((1,), 2),))
    second = workspace.evaluate(source, "policy", (Case((1,), 2),))
    changed = workspace.evaluate(source, "policy", (Case((2,), 3),))

    assert first.workspace_digest == second.workspace_digest
    assert first.workspace_digest != changed.workspace_digest


def test_independent_workspace_gate_adopts_a_verified_rewrite():
    body = VersionedCodeBody("policy", ABSOLUTE_PLUS_ZERO)
    rewrite = SelfRewriteEngine(max_edits=2, beam_width=32).improve(
        body.active_source,
        body.function_name,
        DEVELOPMENT,
    )

    decision = WorkspaceAdoptionGate().evaluate_and_adopt(
        body,
        rewrite,
        DEVELOPMENT,
        REGRESSION,
    )

    assert decision.adopted
    assert decision.reason == "independent_workspace_gates_passed"
    assert decision.candidate_development.perfect
    assert decision.candidate_regression.perfect
    assert body.run(-9) == 10
    assert body.archive == [ABSOLUTE_PLUS_ZERO]


def test_regression_gate_blocks_an_improving_but_incompatible_candidate():
    source = "def policy(x):\n    return x + 0\n"
    body = VersionedCodeBody("policy", source)
    development = (Case((1,), 2), Case((2,), 3))
    regression = (Case((-1,), -1),)
    rewrite = SelfRewriteEngine(max_edits=1, beam_width=16).improve(
        source,
        "policy",
        development,
    )

    decision = WorkspaceAdoptionGate().evaluate_and_adopt(
        body,
        rewrite,
        development,
        regression,
    )

    assert rewrite.adopted
    assert not decision.adopted
    assert decision.reason == "regression_gate_failed"
    assert body.active_source == source
    assert body.archive == []


def test_failed_baseline_workspace_blocks_adoption(monkeypatch):
    body = VersionedCodeBody("policy", ABSOLUTE_PLUS_ZERO)
    rewrite = SelfRewriteEngine(max_edits=2, beam_width=32).improve(
        body.active_source,
        body.function_name,
        DEVELOPMENT,
    )
    workspace = CandidateWorkspace()
    real_evaluate = workspace.evaluate
    calls = 0

    def fail_first_evaluation(source, function_name, cases):
        nonlocal calls
        calls += 1
        result = real_evaluate(source, function_name, cases)
        if calls == 1:
            return replace(result, status="subprocess_failed", return_code=1)
        return result

    monkeypatch.setattr(workspace, "evaluate", fail_first_evaluation)

    decision = WorkspaceAdoptionGate(workspace).evaluate_and_adopt(
        body,
        rewrite,
        DEVELOPMENT,
        REGRESSION,
    )

    assert not decision.adopted
    assert decision.reason == "baseline_workspace_failed"
    assert body.active_source == ABSOLUTE_PLUS_ZERO
    assert body.archive == []


def test_stale_rewrite_cannot_overwrite_a_newer_body():
    body = VersionedCodeBody("policy", ABSOLUTE_PLUS_ZERO)
    rewrite = SelfRewriteEngine(max_edits=2, beam_width=32).improve(
        body.active_source,
        "policy",
        DEVELOPMENT,
    )
    body.active_source = "def policy(x):\n    return x\n"

    with pytest.raises(ValueError, match="stale"):
        WorkspaceAdoptionGate().evaluate_and_adopt(
            body,
            rewrite,
            DEVELOPMENT,
            REGRESSION,
        )


@pytest.mark.parametrize(
    "kwargs",
    [
        {"cpu_seconds": 0},
        {"memory_bytes": 0},
        {"wall_seconds": 0},
        {"output_bytes": 0},
        {"cpu_seconds": True},
        {"memory_bytes": 1.5},
        {"wall_seconds": "5"},
    ],
)
def test_resource_limits_must_be_positive(kwargs):
    with pytest.raises(ValueError, match="positive integer"):
        SandboxLimits(**kwargs)
