from __future__ import annotations

import pytest

from metamorphosis.m020_self_rewrite import (
    Case,
    ToolRegistry,
    VersionedCodeBody,
    apply_patch,
    evaluate_source,
    source_digest,
)
from metamorphosis.m025_rewrite_lifecycle import execute_portable_rewrite


BROKEN = """\
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


def _run_lifecycle():
    body = VersionedCodeBody("policy", BROKEN)
    registry = ToolRegistry()
    outcome = execute_portable_rewrite(
        body,
        registry,
        DEVELOPMENT,
        REGRESSION,
    )
    return body, registry, outcome


def test_complete_rewrite_lifecycle_migrates_replays_and_rolls_back():
    body, registry, outcome = _run_lifecycle()

    assert outcome.adopted
    assert outcome.reason == "independent_workspace_gates_passed"
    assert outcome.evidence.parent_source_digest == source_digest(BROKEN)
    assert outcome.evidence.selected_source_digest == source_digest(body.active_source)
    assert outcome.evidence.learned_tool_name == registry.learned[0].name
    assert outcome.evidence.passport_sha256 == outcome.passport.sha256()
    assert outcome.passport_json

    migrated_body = outcome.migrated_body
    migrated_registry = outcome.migrated_registry
    assert migrated_body is not None
    assert migrated_registry is not None
    assert migrated_body.active_source == body.active_source
    assert migrated_body.archive == [BROKEN]
    assert evaluate_source(migrated_body.active_source, "policy", REGRESSION).perfect
    assert [tool.name for tool in migrated_registry.learned] == [
        tool.name for tool in registry.learned
    ]

    structurally_similar = """\
def policy(value):
    if value >= 0:
        return value + 0
    return -value + 0
"""
    proposals = tuple(migrated_registry.learned[0].propose(structurally_similar))
    assert proposals == (outcome.rewrite.selected.trace,)
    replayed = apply_patch(structurally_similar, proposals[0])
    assert evaluate_source(replayed, "policy", REGRESSION).perfect

    assert migrated_body.rollback()
    assert migrated_body.active_source == BROKEN
    assert migrated_body.run(-9) == 9
    assert body.run(-9) == 10


def test_rejected_regression_restores_body_and_tool_registry_exactly():
    source = "def policy(x):\n    return x + 0\n"
    body = VersionedCodeBody("policy", source)
    registry = ToolRegistry()
    development = (Case((1,), 2), Case((2,), 3))
    regression = (Case((-1,), -1),)
    archive_before = list(body.archive)
    digests_before = list(body.adopted_digests)

    outcome = execute_portable_rewrite(
        body,
        registry,
        development,
        regression,
        max_edits=1,
        beam_width=16,
    )

    assert not outcome.adopted
    assert outcome.reason == "regression_gate_failed"
    assert outcome.passport_json is None
    assert outcome.migrated_body is None
    assert outcome.migrated_registry is None
    assert body.active_source == source
    assert body.archive == archive_before
    assert body.adopted_digests == digests_before
    assert registry.learned == []


def test_already_optimal_body_is_not_replaced_or_exported():
    source = "def policy(x):\n    return x + 1\n"
    body = VersionedCodeBody("policy", source)
    registry = ToolRegistry()
    cases = (Case((1,), 2), Case((-2,), -1))

    outcome = execute_portable_rewrite(body, registry, cases, cases)

    assert not outcome.adopted
    assert outcome.reason == "rewrite_not_selected"
    assert body.active_source == source
    assert body.archive == []
    assert registry.learned == []
    assert outcome.evidence.passport_sha256 is None


def test_complete_lifecycle_is_deterministic():
    first_body, _, first = _run_lifecycle()
    second_body, _, second = _run_lifecycle()

    assert first_body.active_source == second_body.active_source
    assert first.passport_json == second.passport_json
    assert first.evidence == second.evidence


def test_workspace_exception_restores_body_and_tool_registry_exactly():
    class FailingWorkspace:
        def evaluate(self, source, function_name, cases):
            raise RuntimeError("forced independent workspace failure")

    body = VersionedCodeBody("policy", BROKEN)
    registry = ToolRegistry()
    archive_before = list(body.archive)
    digests_before = list(body.adopted_digests)

    with pytest.raises(RuntimeError, match="forced independent workspace failure"):
        execute_portable_rewrite(
            body,
            registry,
            DEVELOPMENT,
            REGRESSION,
            workspace=FailingWorkspace(),
        )

    assert body.active_source == BROKEN
    assert body.archive == archive_before
    assert body.adopted_digests == digests_before
    assert registry.learned == []
