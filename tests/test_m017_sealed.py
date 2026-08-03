"""The sealed specification must be bound to an immutable head and to nothing else.

Section 8.3 of the frozen protocol requires sealed environments to be derived from the
head SHA, so that they cannot exist before the commit they judge. These tests pin that
binding, and the rejection of anything that would let a different head produce the same
environments.
"""

from __future__ import annotations

import pytest

from metamorphosis.m017_sealed import (
    EPISODES_PER_ENVIRONMENT,
    LATE_EPISODE_FROM,
    SEALED_ENVIRONMENTS,
    derive_seed,
    head_nonce,
    sealed_spec,
)

HEAD_A = "0123456789abcdef0123456789abcdef01234567"
HEAD_B = "89abcdef0123456789abcdef0123456789abcdef"


def test_the_nonce_is_a_function_of_the_head_alone():
    assert head_nonce(HEAD_A) == head_nonce(HEAD_A)
    assert head_nonce(HEAD_A) != head_nonce(HEAD_B)


def test_the_head_is_normalised_but_not_guessed():
    assert head_nonce(HEAD_A.upper()) == head_nonce(HEAD_A)
    assert head_nonce(f"  {HEAD_A}\n") == head_nonce(HEAD_A)


@pytest.mark.parametrize(
    "bad",
    [
        "0123456",                                    # abbreviated
        "",                                           # empty
        "z" * 40,                                     # not hex
        "0123456789abcdef0123456789abcdef012345678",  # 41 chars
        "0123456789abcdef0123456789abcdef0123456",    # 39 chars
    ],
)
def test_an_unusable_head_is_rejected_rather_than_hashed(bad):
    with pytest.raises(ValueError, match="40-character lowercase head SHA"):
        head_nonce(bad)


def test_two_heads_produce_disjoint_environment_seeds():
    a = sealed_spec(HEAD_A, environments=8)
    b = sealed_spec(HEAD_B, environments=8)
    assert set(a.environment_seeds).isdisjoint(b.environment_seeds)
    assert a.digest() != b.digest()


def test_the_specification_is_deterministic_and_addressable():
    a = sealed_spec(HEAD_A, environments=8)
    b = sealed_spec(HEAD_A, environments=8)
    assert a == b
    assert a.digest() == b.digest()


def test_labels_do_not_collide_across_seed_families():
    spec = sealed_spec(HEAD_A, environments=16)
    families = (spec.environment_seeds, spec.episode_seeds, spec.negative_seeds)
    for family in families:
        assert len(set(family)) == len(family)
    pooled = [seed for family in families for seed in family]
    assert len(set(pooled)) == len(pooled)


def test_derive_seed_is_namespaced_to_m017():
    """A shared nonce must not yield the same seed as another experiment's deriver."""

    nonce = head_nonce(HEAD_A)
    assert derive_seed(nonce, "environment", 0) != derive_seed(nonce, "episode", 0)
    assert derive_seed(nonce, "environment", 0) != derive_seed(nonce, "environment", 1)


def test_frozen_window_matches_the_development_bench():
    spec = sealed_spec(HEAD_A, environments=4)
    assert spec.episodes_per_environment == EPISODES_PER_ENVIRONMENT == 14
    assert spec.late_episode_from == LATE_EPISODE_FROM == 7


def test_environment_count_defaults_to_the_signed_value():
    assert SEALED_ENVIRONMENTS == 50
    assert sealed_spec(HEAD_A).environment_count == 50


def test_a_degenerate_environment_count_is_refused():
    with pytest.raises(ValueError, match="at least one environment"):
        sealed_spec(HEAD_A, environments=0)
