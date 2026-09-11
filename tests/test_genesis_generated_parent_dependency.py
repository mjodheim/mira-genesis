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
    assert descendant.configuration["parent_prefix_length"] == 1
    parent_record = descendant.configuration["parent_body_artifact"]
    assert parent_record["artifact_digest"] == parent_digest
    assert parent_record["configuration"]["target"] == program_forms.PORTABLE_PROGRAM_TARGET
    assert tuple(parent_record["configuration"]["configuration"]["operations"]) == ("square",)

    # This is executable composition, not a certificate flag: the descendant reconstructs and runs
    # its exact parent artifact, then executes only its newly appended suffix operation.
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


def test_tampered_embedded_parent_artifact_is_refused_at_execution_boundary():
    parent = _portable_square()
    dependency = "policy-program:older-objective:square"
    with programs.inherit_interpreter_form(parent, dependency=dependency):
        descendant = programs.artifact(
            registry_reference=bodies.PROBE_REGISTRY,
            operations=("square", "square"),
        )

    configuration = dict(descendant.configuration)
    parent_record = dict(configuration["parent_body_artifact"])
    parent_record["artifact_digest"] = "0" * 64
    configuration["parent_body_artifact"] = parent_record
    tampered = ConfiguredBody(
        target=descendant.target,
        configuration=configuration,
        dependencies=descendant.dependencies,
    )
    with pytest.raises(Exception, match="reproduce its committed digest"):
        tampered()
