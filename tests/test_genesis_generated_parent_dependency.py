"""DEVELOPMENT regressions for runtime-derived ancestry of generated programs."""
from __future__ import annotations

import pytest

from genesis import development_bodies as bodies
from genesis import program_forms, programs
from genesis.artifacts import ConfiguredBody
from genesis import trust_root as tr


def _portable_square():
    return ConfiguredBody(
        target=program_forms.PORTABLE_PROGRAM_TARGET,
        configuration={
            "program_schema": programs.PROGRAM_SCHEMA,
            "registry_reference": bodies.PROBE_REGISTRY,
            "operations": ["square"],
            "input_field": "input",
        },
    )


def test_only_a_strict_program_extension_inherits_the_predecessor_dependency():
    parent = _portable_square()
    dependency = "policy-program:older-objective:square"
    parent_digest = tr.artifact_digest_of(parent)["artifact_digest"]

    with programs.inherit_interpreter_form(parent, dependency=dependency):
        same = programs.artifact(
            registry_reference=bodies.PROBE_REGISTRY,
            operations=("square",),
        )
        sibling = programs.artifact(
            registry_reference=bodies.PROBE_REGISTRY,
            operations=("increment", "square"),
        )
        descendant = programs.artifact(
            registry_reference=bodies.PROBE_REGISTRY,
            operations=("square", "square"),
        )

    assert same.dependencies == frozenset()
    assert sibling.dependencies == frozenset()
    assert descendant.target == program_forms.PORTABLE_PROGRAM_TARGET
    assert descendant.dependencies == frozenset((dependency,))
    assert tuple(descendant.configuration["required_capabilities"]) == (dependency,)
    assert descendant.configuration["parent_body_artifact_digest"] == parent_digest

    # This is executable dependence, not a certificate flag: the intact body computes the new work,
    # while the runtime-derived single-difference ablation cannot execute without its predecessor.
    assert descendant().attempt({"input": 2}) == 16
    ablated = descendant.without(dependency)
    with pytest.raises(RuntimeError, match="retained predecessor capability"):
        ablated().attempt({"input": 2})


def test_parent_dependency_context_does_not_leak_to_other_lineages():
    parent = _portable_square()
    with programs.inherit_interpreter_form(parent, dependency="prior"):
        inherited = programs.artifact(
            registry_reference=bodies.PROBE_REGISTRY,
            operations=("square", "square"),
        )
    ordinary = programs.artifact(
        registry_reference=bodies.PROBE_REGISTRY,
        operations=("square", "square"),
    )

    assert inherited.dependencies == frozenset(("prior",))
    assert ordinary.dependencies == frozenset()
    assert ordinary.target == programs.PROGRAM_TARGET
