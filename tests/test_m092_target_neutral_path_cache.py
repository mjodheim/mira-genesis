"""Pre-arm equivalence tests for the runner-local M092 symbolic-path cache."""
from __future__ import annotations

from collections.abc import Callable

import metamorphosis.m092_certificate_policy_search as policies
from metamorphosis.m092_certificate_verifier import COUNTDOWN_POSTCONDITION
from metamorphosis.m092_kernel import Program
from scripts import run_m092_criterion_search as canonical_runner
from scripts import run_m092_independent_reproduction as reproduction_runner


COUNTDOWN_PROGRAM: Program = (
    ("SPOP", 0),
    ("LOADI", 1, 1),
    ("JZ", 0, 5),
    ("SUB", 0, 0, 1),
    ("JMP", 2),
    ("SPUSH", 0),
    ("HALT",),
)


def _records(limit: int = 8) -> list[dict[str, object]]:
    return [
        record.to_dict()
        for record in policies.enumerate_certificate_policy_records(
            COUNTDOWN_PROGRAM,
            COUNTDOWN_POSTCONDITION,
            limit=limit,
        )
    ]


def _prove_installer_equivalence(installer: Callable[[], None]) -> None:
    original = policies._paths_for_policy
    baseline = _records()
    calls = [0]

    def counted(program, ghosts):
        calls[0] += 1
        return original(program, ghosts)

    policies._paths_for_policy = counted
    try:
        installer()
        cached = _records()
        assert cached == baseline
        # MAX_GHOST_COUNTERS is two, so at most one real symbolic-path preparation is needed for
        # each ghost-count family represented in the first eight attempts.  Without the cache the
        # builder would prepare the same paths again for every policy vector.
        assert calls[0] <= policies.base.MAX_GHOST_COUNTERS + 1

        header_one, paths_one = policies._paths_for_policy(COUNTDOWN_PROGRAM, ())
        header_two, paths_two = policies._paths_for_policy(COUNTDOWN_PROGRAM, ())
        assert header_one == header_two
        assert paths_one == paths_two
        assert paths_one is not paths_two
        original_length = len(paths_two)
        paths_one.pop()
        _, paths_three = policies._paths_for_policy(COUNTDOWN_PROGRAM, ())
        assert len(paths_three) == original_length
    finally:
        policies._paths_for_policy = original


def test_canonical_runner_cache_is_byte_equivalent_and_bounded() -> None:
    _prove_installer_equivalence(canonical_runner._install_target_neutral_path_cache)


def test_reproduction_runner_cache_is_byte_equivalent_and_bounded() -> None:
    _prove_installer_equivalence(reproduction_runner._install_target_neutral_path_cache)


def test_cache_installation_is_idempotent_across_both_runners() -> None:
    original = policies._paths_for_policy
    try:
        canonical_runner._install_target_neutral_path_cache()
        first = policies._paths_for_policy
        canonical_runner._install_target_neutral_path_cache()
        reproduction_runner._install_target_neutral_path_cache()
        assert policies._paths_for_policy is first
        assert getattr(first, "_m092_target_neutral_cache", False) is True
    finally:
        policies._paths_for_policy = original
