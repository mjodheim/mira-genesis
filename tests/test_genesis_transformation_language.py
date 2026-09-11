from copy import deepcopy

import pytest

from genesis import development_bodies as bodies
from genesis import policies, policy_mutations
from genesis import transformation_language as tl


def _policy():
    return policies.create(
        registry_reference=bodies.PROBE_REGISTRY,
        operation_names=("increment",),
        max_length=1,
        ceiling_length=2,
        max_candidates=8,
    )


def _seed_language():
    return tl.create_language(
        [
            tl.create_operator(
                "add-negate",
                [tl.create_step("append_policy_operation", operation="negate")],
            ),
            tl.create_operator(
                "deepen",
                [tl.create_step("increase_policy_depth")],
            ),
        ],
        max_operator_steps=2,
    )


def test_language_extension_can_express_a_composite_edit_no_v1_atomic_mutation_can_make():
    prior = _policy()
    seed = _seed_language()
    composite = tl.create_operator(
        "add-negate-and-deepen",
        [
            tl.create_step("append_policy_operation", operation="negate"),
            tl.create_step("increase_policy_depth"),
        ],
    )
    extended = tl.extend_language(seed, composite)
    descendant = tl.apply_operator(prior, extended, "add-negate-and-deepen")

    assert extended["parent_language_digest"] == seed["language_digest"]
    assert descendant["parent_policy_digest"] == prior["policy_digest"]
    assert descendant["operation_names"] == ["increment", "negate"]
    assert descendant["max_length"] == 2
    assert policy_mutations.structural_difference(prior, descendant) == [
        "max_length",
        "operation_names",
    ]

    atomic_differences = []
    for mutation in (
        policy_mutations.create("add_operation", operation="negate"),
        policy_mutations.create("increase_depth"),
    ):
        atomic_differences.append(
            policy_mutations.structural_difference(
                prior, policy_mutations.apply(prior, mutation)
            )
        )
    assert atomic_differences == [["operation_names"], ["max_length"]]


def test_operator_digest_tampering_is_refused():
    operator = tl.create_operator(
        "deepen",
        [tl.create_step("increase_policy_depth")],
    )
    tampered = deepcopy(operator)
    tampered["steps"][0]["amount"] = 2
    with pytest.raises(tl.TransformationLanguageError):
        tl.validate_operator(tampered)


def test_language_extension_must_be_one_new_bounded_operator():
    seed = _seed_language()
    with pytest.raises(tl.TransformationLanguageError):
        tl.extend_language(
            seed,
            tl.create_operator(
                "too-wide",
                [
                    tl.create_step("increase_candidate_limit", amount=1),
                    tl.create_step("increase_candidate_limit", amount=1),
                    tl.create_step("increase_candidate_limit", amount=1),
                ],
            ),
        )


def test_operator_cannot_escape_policy_registry_or_depth_ceiling():
    seed = _seed_language()
    bad_registry = tl.extend_language(
        seed,
        tl.create_operator(
            "unknown-op",
            [tl.create_step("append_policy_operation", operation="does-not-exist")],
        ),
    )
    with pytest.raises(tl.TransformationLanguageError):
        tl.apply_operator(_policy(), bad_registry, "unknown-op")

    already_deep = policies.create(
        registry_reference=bodies.PROBE_REGISTRY,
        operation_names=("increment",),
        max_length=2,
        ceiling_length=2,
        max_candidates=8,
    )
    with pytest.raises(tl.TransformationLanguageError):
        tl.apply_operator(already_deep, seed, "deepen")


def test_unknown_micro_step_and_unknown_operator_fail_closed():
    with pytest.raises(tl.TransformationLanguageError):
        tl.create_step("rewrite-trust-root")
    with pytest.raises(tl.TransformationLanguageError):
        tl.apply_operator(_policy(), _seed_language(), "missing")
