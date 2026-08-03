"""The confirmation is complete only within the language, and §3.2 tests outside it.

`_confirm` derives its W-method margin from the source's state count, justified by "the
structural language does not create states, so the target cannot have more than the
source". That bound is sound for in-language targets.

The §3.2 out-of-language negative control is defined by *adding* a state, so it lies
outside the bound by construction. The organism can therefore announce a solution that is
not equivalent, which is a §7 falsifier.

These tests pin the mechanism and the measured repair, so that the confirmation bound is
signed as a protocol parameter rather than adjusted after an observation.
"""

from __future__ import annotations

from metamorphosis.conformance import w_method_suite
from metamorphosis.m012b_dfa import exact_equivalence
from metamorphosis.m017_engine import SelfExtendingOrganism
from metamorphosis.m017_lab import (
    BehavioralOracle,
    generate_episodes,
    make_environment,
    make_out_of_language_target,
)
from metamorphosis.m017_sealed import sealed_spec

# The head that exposed it. Kept literal so the case is reproducible without a run.
EXPOSING_HEAD = "1111111111111111111111111111111111111111"


def _exposing_case():
    spec = sealed_spec(EXPOSING_HEAD, environments=2)
    environment = make_environment(spec.environment_seeds[0])
    episodes = generate_episodes(
        environment, spec.episode_seeds[0], count=spec.episodes_per_environment
    )
    base = episodes[0].base
    target = make_out_of_language_target(base, spec.negative_seeds[0])
    return base, target


def test_the_negative_control_adds_a_state_by_construction():
    base, target = _exposing_case()
    assert target.n_states > base.n_states


def test_the_organism_announces_a_non_equivalent_solution():
    """The defect: a §7 falsifier, reproduced from a fixed head."""

    base, target = _exposing_case()
    result = SelfExtendingOrganism().solve(base, BehavioralOracle(target))
    assert result.status == "success"
    assert result.solution is not None
    equal, witness = exact_equivalence(result.solution, target)
    assert not equal
    assert witness == (0, 0, 1, 0, 0, 0)


def test_the_suite_misses_the_witness_at_the_current_bound():
    base, target = _exposing_case()
    result = SelfExtendingOrganism().solve(base, BehavioralOracle(target))
    solution = result.solution
    assert solution is not None

    suite = w_method_suite(solution, solution.n_states)
    assert not any(
        solution.accepts(word) != target.accepts(word) for word in suite
    )


def test_one_extra_state_in_the_bound_restores_detection():
    base, target = _exposing_case()
    result = SelfExtendingOrganism().solve(base, BehavioralOracle(target))
    solution = result.solution
    assert solution is not None

    narrow = w_method_suite(solution, solution.n_states)
    wide = w_method_suite(solution, solution.n_states + 1)
    assert len(wide) > len(narrow)
    assert any(solution.accepts(word) != target.accepts(word) for word in wide)


def test_the_development_controls_do_not_expose_it():
    """Gate 5 passed on two controls; both abstain. The sample was too small."""

    control_environment = make_environment(74_000)
    control_episodes = generate_episodes(control_environment, 74_100, count=4)
    for position in (0, 2):
        episode = control_episodes[position]
        target = make_out_of_language_target(episode.base, 74_500 + position)
        result = SelfExtendingOrganism().solve(episode.base, BehavioralOracle(target))
        assert result.status == "abstained"
