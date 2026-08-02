from __future__ import annotations

import pytest

from metamorphosis.m020_self_rewrite import (
    Case,
    SelfRewriteEngine,
    ToolRegistry,
    UnsafeSource,
    VersionedCodeBody,
    apply_patch,
    evaluate_source,
    source_digest,
    validate_source,
)


BROKEN_ABSOLUTE_PLUS_ONE = """\
def policy(x):
    if x >= 0:
        return x + 0
    return -x + 0
"""

CORRECT_ABSOLUTE_PLUS_ONE = """\
def policy(x):
    if x >= 0:
        return x + 1
    return -x + 1
"""

DEVELOPMENT_CASES = (
    Case((-3,), 4),
    Case((-1,), 2),
    Case((1,), 2),
    Case((3,), 4),
)

HELD_OUT_CASES = (
    Case((-21,), 22),
    Case((0,), 1),
    Case((34,), 35),
)


def test_policy_language_rejects_imports_calls_attributes_and_loops():
    rejected = (
        "import os\ndef policy(x):\n    return x\n",
        "def policy(x):\n    return abs(x)\n",
        "def policy(x):\n    return x.real\n",
        "def policy(x):\n    while x:\n        x = x - 1\n    return x\n",
    )

    for source in rejected:
        with pytest.raises(UnsafeSource):
            validate_source(source, "policy")


def test_self_rewrite_finds_a_two_edit_body_without_held_out_answers():
    registry = ToolRegistry()
    engine = SelfRewriteEngine(registry, max_edits=2, beam_width=32)

    result = engine.improve(
        BROKEN_ABSOLUTE_PLUS_ONE,
        "policy",
        DEVELOPMENT_CASES,
    )

    assert result.adopted
    assert result.reason == "strict_development_improvement"
    assert result.baseline.development.passed == 0
    assert result.selected.development.perfect
    assert len(result.selected.trace) == 2
    assert result.learned_tool is not None
    assert len(registry.learned) == 1

    # Held-out cases are evaluated only after selection. They were never passed to the
    # rewrite engine and therefore cannot steer its search.
    held_out = evaluate_source(result.selected.source, "policy", HELD_OUT_CASES)
    assert held_out.perfect


def test_adoption_archives_the_previous_body_exactly_and_rollback_restores_it():
    engine = SelfRewriteEngine(max_edits=2, beam_width=32)
    body = VersionedCodeBody("policy", BROKEN_ABSOLUTE_PLUS_ONE)
    original_digest = source_digest(body.active_source)
    result = engine.improve(body.active_source, "policy", DEVELOPMENT_CASES)

    assert body.adopt(result)
    assert body.archive == [BROKEN_ABSOLUTE_PLUS_ONE]
    assert body.adopted_digests[0] == original_digest
    assert body.run(-9) == 10
    assert body.run(0) == 1

    assert body.rollback()
    assert body.active_source == BROKEN_ABSOLUTE_PLUS_ONE
    assert body.run(-9) == 9


def test_an_accepted_patch_becomes_a_reusable_internal_tool():
    registry = ToolRegistry()
    engine = SelfRewriteEngine(registry, max_edits=2, beam_width=32)
    result = engine.improve(BROKEN_ABSOLUTE_PLUS_ONE, "policy", DEVELOPMENT_CASES)
    learned = registry.learned[0]

    structurally_similar = """\
def policy(value):
    if value >= 0:
        return value + 0
    return -value + 0
"""
    proposals = tuple(learned.propose(structurally_similar))

    assert proposals == (result.selected.trace,)
    rewritten = apply_patch(structurally_similar, proposals[0])
    assert evaluate_source(rewritten, "policy", HELD_OUT_CASES).perfect


def test_no_candidate_is_adopted_without_a_strict_improvement():
    engine = SelfRewriteEngine(max_edits=2, beam_width=16)

    result = engine.improve(CORRECT_ABSOLUTE_PLUS_ONE, "policy", DEVELOPMENT_CASES)

    assert not result.adopted
    assert result.reason == "no_strict_development_improvement"
    assert result.selected.source == CORRECT_ABSOLUTE_PLUS_ONE


def test_rewrite_search_is_deterministic():
    first = SelfRewriteEngine(max_edits=2, beam_width=32).improve(
        BROKEN_ABSOLUTE_PLUS_ONE, "policy", DEVELOPMENT_CASES
    )
    second = SelfRewriteEngine(max_edits=2, beam_width=32).improve(
        BROKEN_ABSOLUTE_PLUS_ONE, "policy", DEVELOPMENT_CASES
    )

    assert first.selected.source == second.selected.source
    assert first.selected.trace == second.selected.trace
    assert first.candidates_evaluated == second.candidates_evaluated
