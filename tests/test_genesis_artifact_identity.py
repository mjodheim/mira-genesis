"""Executable identity, and the refusals that make it an identity rather than a label.

The round-two review's first finding was that `artifact_digest_of` unwrapped `functools.partial` to
its underlying callable and discarded the bound arguments. Two differently configured bodies shared a
digest, so restore could substitute one for the other, and the same collision applied to the grader —
which is the measure itself.

The repair has two halves and only one of them is about hashing more. The other is **failing
closed**: a callable whose behaviour depends on state no descriptor here can reconstruct is refused
rather than reduced to its name. That half is what these tests are for. A weak identity that silently
covers two different executables is worse than no identity at all, because a record then testifies to
a binding that does not hold — and a guard nobody exercises is a claim of the same kind.
"""
from __future__ import annotations

import functools

import pytest

from genesis import development_bodies as bodies
from genesis import trust_root as tr
from genesis.artifacts import ArtifactError, ConfiguredBody, derive_ablation, single_difference


def _module_level(value):
    return value


class _Opaque:
    """A value with no canonical form. Hashing its `repr` would be hashing its address."""

    def __init__(self):
        self.state = object()


# -- what identity must distinguish ------------------------------------------------------------

def test_bound_arguments_are_part_of_identity():
    left = functools.partial(bodies.TableBody, {"t0"})
    right = functools.partial(bodies.TableBody, {"t0", "t1"})
    assert tr.artifact_digest_of(left) != tr.artifact_digest_of(right)


def test_bound_keywords_are_part_of_identity():
    left = functools.partial(bodies.TableBody, {"t0"}, refuses={"t1"})
    right = functools.partial(bodies.TableBody, {"t0"}, refuses={"t2"})
    assert (
        tr.artifact_digest_of(left)["artifact_digest"]
        != tr.artifact_digest_of(right)["artifact_digest"]
    )


def test_the_same_configuration_produces_the_same_identity():
    """Identity has to be stable, or nothing downstream can compare two records."""
    first = functools.partial(bodies.TableBody, {"t1", "t0"})
    second = functools.partial(bodies.TableBody, {"t0", "t1"})
    assert (
        tr.artifact_digest_of(first)["artifact_digest"]
        == tr.artifact_digest_of(second)["artifact_digest"]
    )


def test_a_published_configuration_is_bound_exactly():
    left = ConfiguredBody(target="genesis.development_bodies:RecordBody", dependencies={"a"})
    right = ConfiguredBody(target="genesis.development_bodies:RecordBody", dependencies={"a", "b"})
    assert (
        tr.artifact_digest_of(left)["artifact_digest"]
        != tr.artifact_digest_of(right)["artifact_digest"]
    )


def test_an_artifact_descriptor_says_it_does_not_bind_the_executed_bytes():
    """No descriptor this runtime produces binds exact bytes, and the record must not imply it."""
    descriptor = tr.artifact_digest_of(bodies.parent_body)
    assert descriptor["binds_exact_executed_bytes"] is False


# -- what identity must refuse -------------------------------------------------------------------

def test_a_lambda_is_refused_rather_than_identified_by_its_name():
    with pytest.raises(tr.TrustRootError, match="inside another scope"):
        tr.artifact_digest_of(lambda: None)


def test_a_nested_function_is_refused():
    """Two nested functions with the same qualname can close over entirely different values."""

    def inner():  # pragma: no cover - never called; only its identity is asked for
        return None

    with pytest.raises(tr.TrustRootError, match="inside another scope"):
        tr.artifact_digest_of(inner)


def test_a_closure_is_refused_even_through_a_partial():
    """The refusal has to survive the wrapper, or the wrapper is the way around it."""

    def make(bound):
        def closed_over():  # pragma: no cover - identity only
            return bound

        return closed_over

    with pytest.raises(tr.TrustRootError):
        tr.artifact_digest_of(functools.partial(make(1)))


def test_a_closure_wearing_a_module_level_name_is_still_refused():
    """The name check is not the whole guard, and a rebound function can get past it.

    A function defined at module level cannot close over anything, so the `<locals>` check normally
    fires first and this refusal looks unreachable. It is not: `types.FunctionType` rebuilds a
    function from a code object with whatever globals, name and closure the caller supplies —
    `genesis.capabilities` does exactly that to sever a capability from its defining module. Two such
    functions can share every part of an importable-symbol descriptor while closing over different
    values, so identity has to refuse them rather than call them the same executable.
    """
    import types

    def _make(bound):
        def _inner():  # pragma: no cover - identity only
            return bound

        return _inner

    closured = _make(1)
    disguised = types.FunctionType(
        closured.__code__, {}, "looks_module_level", None, closured.__closure__
    )
    disguised.__qualname__ = "looks_module_level"
    assert "<locals>" not in disguised.__qualname__
    with pytest.raises(tr.TrustRootError, match="closes over live values"):
        tr.artifact_digest_of(disguised)


def test_a_bound_value_a_digest_cannot_cover_is_refused():
    """Silently omitting it would put two different executables under one digest."""
    with pytest.raises(tr.TrustRootError, match="digest cannot cover"):
        tr.artifact_digest_of(functools.partial(_module_level, _Opaque()))


def test_a_callable_instance_that_publishes_no_configuration_is_refused():
    """Its behaviour lives in instance state, and it does not even carry a name to fall back on.

    Falling back to the class name would be the original defect exactly: every instance of the class,
    however configured, would share one digest. A callable object that wants an identity has to
    publish a configuration the runtime can bind.
    """

    class _Configured:
        def __init__(self, table):
            self.table = table

        def __call__(self):  # pragma: no cover - never built
            return self.table

    with pytest.raises(tr.TrustRootError, match="no name a digest could bind"):
        tr.artifact_digest_of(_Configured({"t0"}))


def test_something_that_is_not_callable_has_no_executable_identity():
    with pytest.raises(tr.TrustRootError, match="must be callable"):
        tr.artifact_digest_of("genesis.development_bodies:parent_body")


def test_an_object_publishing_a_configuration_that_is_not_a_record_is_refused():
    class _Wrong:
        def artifact_configuration(self):
            return ["not", "a", "record"]

        def __call__(self):  # pragma: no cover - never built
            return None

    with pytest.raises(tr.TrustRootError, match="did not return a record"):
        tr.artifact_digest_of(_Wrong())


# -- the evaluation contract inherits all of it --------------------------------------------------

def test_the_contract_refuses_a_grader_it_cannot_identify():
    """The grader is the measure. An unidentifiable measure is not a measure that was admitted."""
    with pytest.raises(tr.TrustRootError):
        tr.evaluation_contract(grade=lambda task, answer: "solved")


def test_a_contract_requiring_a_control_must_name_which_control():
    with pytest.raises(tr.TrustRootError, match="which control"):
        tr.evaluation_contract(grade=bodies.grade, control_policy="required")


def test_a_control_artifact_under_a_contract_that_uses_none_is_refused():
    with pytest.raises(tr.TrustRootError, match="does not use one"):
        tr.evaluation_contract(grade=bodies.grade, control=bodies.improved_body)


def test_an_unrecognised_control_policy_is_refused():
    with pytest.raises(tr.TrustRootError, match="unrecognised control policy"):
        tr.evaluation_contract(grade=bodies.grade, control_policy="whatever_the_caller_likes")


# -- deriving an ablation, and refusing to invent one ---------------------------------------------

def test_an_ablation_cannot_be_derived_from_a_body_the_runtime_cannot_read():
    with pytest.raises(ArtifactError, match="does not publish a configuration"):
        derive_ablation(bodies.parent_body, "joint_registry")


def test_removing_something_the_body_never_declared_is_not_an_ablation_of_it():
    with pytest.raises(ArtifactError, match="does not declare"):
        bodies.migrated_improved_body.without("never_declared")


def test_a_configured_body_needs_a_resolvable_target():
    with pytest.raises(ArtifactError, match="module:symbol"):
        ConfiguredBody(target="not_a_reference")


def test_single_difference_reports_a_second_change_riding_along_with_the_first():
    """A second change makes the measured loss ambiguous between the two."""
    candidate = bodies.migrated_improved_body
    tampered = ConfiguredBody(
        target=candidate.target,
        configuration={**dict(candidate.configuration), "solves": ["t0"]},
        dependencies=candidate.dependencies - {bodies.ACQUIRED_COMPONENT},
        dependency_keyword=candidate.dependency_keyword,
    )
    problems = single_difference(candidate, tampered, bodies.ACQUIRED_COMPONENT)
    assert any("beyond the removal" in problem for problem in problems)


def test_single_difference_reports_removing_the_wrong_dependency():
    candidate = bodies.migrated_improved_body
    other = candidate.without(bodies.SECOND_ACQUISITION)
    problems = single_difference(candidate, other, bodies.ACQUIRED_COMPONENT)
    assert any("rather than" in problem for problem in problems)


def test_single_difference_accepts_the_licensed_removal_and_nothing_else():
    """The positive case, so the refusals above are a finding rather than a broken comparison."""
    candidate = bodies.migrated_improved_body
    arm = derive_ablation(candidate, bodies.ACQUIRED_COMPONENT)
    assert single_difference(candidate, arm, bodies.ACQUIRED_COMPONENT) == []


def test_an_arm_that_does_not_publish_a_configuration_cannot_be_compared():
    problems = single_difference(bodies.migrated_improved_body, bodies.parent_body, "anything")
    assert problems == ["one of the arms does not publish a configuration to compare"]
