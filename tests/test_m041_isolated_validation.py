from __future__ import annotations

from dataclasses import replace
from itertools import product

import pytest

from metamorphosis.m012b_dfa import DFA
from metamorphosis.m041_isolated_validation import (
    DFAWorkspaceLimits,
    IsolatedDFAAdoptionGate,
    IsolatedDFAWorkspace,
    VersionedDFARelease,
    dfa_candidate_digest,
)

Word = tuple[int, ...]

PARENT = DFA(
    alphabet=(0, 1),
    transitions=((0, 0),),
    accepting=(False,),
)

TARGET = DFA(
    alphabet=(0, 1),
    transitions=((0, 1), (1, 1)),
    accepting=(False, True),
)

LAST_SYMBOL_ONLY = DFA(
    alphabet=(0, 1),
    transitions=((0, 1), (0, 1)),
    accepting=(False, True),
)


def words(depth: int) -> tuple[Word, ...]:
    return tuple(
        tuple(int(symbol) for symbol in word)
        for size in range(depth + 1)
        for word in product((0, 1), repeat=size)
    )


OBSERVATIONS = {word: TARGET.accepts(word) for word in words(3)}


def test_exact_candidate_passes_in_a_fresh_passive_workspace():
    result = IsolatedDFAWorkspace().evaluate(
        parent=PARENT,
        candidate=TARGET,
        target=TARGET,
        observations=OBSERVATIONS,
        expected_candidate_digest=dfa_candidate_digest(TARGET),
    )

    assert result.perfect
    assert result.status == "completed"
    assert result.schema_valid
    assert result.task_passed
    assert result.regressions_passed
    assert result.strict_improvement
    assert result.exact
    assert result.candidate_passed == len(OBSERVATIONS)
    assert result.parent_passed < result.candidate_passed
    assert result.return_code == 0
    assert not result.timed_out
    assert result.mapping()["passive_candidate_data"] is True
    assert result.mapping()["candidate_execution_authority"] is False


def test_workspace_identity_is_deterministic_and_candidate_sensitive():
    workspace = IsolatedDFAWorkspace()

    first = workspace.evaluate(
        parent=PARENT,
        candidate=TARGET,
        target=TARGET,
        observations=OBSERVATIONS,
    )
    second = workspace.evaluate(
        parent=PARENT,
        candidate=TARGET,
        target=TARGET,
        observations=OBSERVATIONS,
    )
    changed = workspace.evaluate(
        parent=PARENT,
        candidate=LAST_SYMBOL_ONLY,
        target=TARGET,
        observations=OBSERVATIONS,
    )

    assert first.workspace_digest == second.workspace_digest
    assert first.case_digest == second.case_digest
    assert first.mapping() == second.mapping()
    assert first.workspace_digest != changed.workspace_digest


def test_non_equivalent_candidate_is_rejected_with_an_independent_witness():
    result = IsolatedDFAWorkspace().evaluate(
        parent=PARENT,
        candidate=LAST_SYMBOL_ONLY,
        target=TARGET,
        observations=OBSERVATIONS,
    )

    assert not result.perfect
    assert not result.task_passed
    assert not result.exact
    assert result.equivalence_witness is not None


def test_digest_tampering_blocks_a_functionally_exact_candidate():
    result = IsolatedDFAWorkspace().evaluate(
        parent=PARENT,
        candidate=TARGET,
        target=TARGET,
        observations=OBSERVATIONS,
        expected_candidate_digest="0" * 64,
    )

    assert result.task_passed
    assert result.exact
    assert not result.candidate_digest_matches
    assert not result.perfect


def test_release_adoption_occurs_only_after_isolated_validation():
    release = VersionedDFARelease(PARENT)
    decision = IsolatedDFAAdoptionGate().evaluate_and_adopt(
        release=release,
        expected_parent_digest=dfa_candidate_digest(PARENT),
        candidate=TARGET,
        target=TARGET,
        observations=OBSERVATIONS,
        expected_candidate_digest=dfa_candidate_digest(TARGET),
    )

    assert decision.adopted
    assert decision.reason == "isolated_validation_passed_before_release_adoption"
    assert decision.validation.perfect
    assert release.active == TARGET
    assert release.archive == [PARENT]

    release.rollback()
    assert release.active == PARENT
    assert release.archive == []


def test_failed_validation_leaves_the_release_body_unchanged():
    release = VersionedDFARelease(PARENT)
    decision = IsolatedDFAAdoptionGate().evaluate_and_adopt(
        release=release,
        expected_parent_digest=dfa_candidate_digest(PARENT),
        candidate=LAST_SYMBOL_ONLY,
        target=TARGET,
        observations=OBSERVATIONS,
        expected_candidate_digest=dfa_candidate_digest(LAST_SYMBOL_ONLY),
    )

    assert not decision.adopted
    assert decision.reason == "isolated_validation_failed"
    assert release.active == PARENT
    assert release.archive == []


def test_stale_parent_is_rejected_before_the_workspace_runs():
    release = VersionedDFARelease(PARENT)

    with pytest.raises(ValueError, match="stale"):
        IsolatedDFAAdoptionGate().evaluate_and_adopt(
            release=release,
            expected_parent_digest=dfa_candidate_digest(TARGET),
            candidate=TARGET,
            target=TARGET,
            observations=OBSERVATIONS,
            expected_candidate_digest=dfa_candidate_digest(TARGET),
        )


@pytest.mark.parametrize(
    "kwargs",
    [
        {"cpu_seconds": 0},
        {"memory_bytes": 0},
        {"wall_seconds": 0},
        {"output_bytes": 0},
        {"maximum_states": 0},
        {"maximum_observations": 0},
        {"cpu_seconds": True},
        {"memory_bytes": 1.5},
        {"wall_seconds": "5"},
    ],
)
def test_workspace_limits_are_positive_integers(kwargs):
    with pytest.raises(ValueError, match="positive integer"):
        DFAWorkspaceLimits(**kwargs)


def test_observation_and_state_limits_fail_before_subprocess_execution():
    with pytest.raises(ValueError, match="observation limit"):
        IsolatedDFAWorkspace(
            DFAWorkspaceLimits(maximum_observations=1)
        ).evaluate(
            parent=PARENT,
            candidate=TARGET,
            target=TARGET,
            observations=OBSERVATIONS,
        )

    with pytest.raises(ValueError, match="state limit"):
        IsolatedDFAWorkspace(
            DFAWorkspaceLimits(maximum_states=1)
        ).evaluate(
            parent=PARENT,
            candidate=TARGET,
            target=TARGET,
            observations=OBSERVATIONS,
        )
