"""DEVELOPMENT regressions for configured-artifact identity after admission."""
from __future__ import annotations

import pytest

from genesis import development_bodies as bodies
from genesis import programs
from genesis import trust_root as tr
from genesis.artifacts import ConfiguredBody


def test_configured_body_detaches_from_the_mutable_configuration_the_caller_supplied():
    original = {
        "program_schema": programs.PROGRAM_SCHEMA,
        "registry_reference": bodies.PROBE_REGISTRY,
        "operations": ["double", "increment"],
        "input_field": "input",
    }
    body = ConfiguredBody(target=programs.PROGRAM_TARGET, configuration=original)
    admitted = tr.artifact_digest_of(body)

    original["operations"][0] = "negate"
    original["input_field"] = "other"

    assert tuple(body.configuration["operations"]) == ("double", "increment")
    assert body.configuration["input_field"] == "input"
    assert tr.artifact_digest_of(body) == admitted


def test_admitted_configuration_cannot_be_rewritten_through_the_factory_itself():
    body = programs.artifact(
        registry_reference=bodies.PROBE_REGISTRY,
        operations=("double", "increment"),
    )
    admitted = tr.artifact_digest_of(body)

    with pytest.raises(TypeError):
        body.configuration["operations"] = ("negate",)
    with pytest.raises(TypeError):
        body.configuration["operations"][0] = "negate"

    assert tr.artifact_digest_of(body) == admitted


def test_published_artifact_configuration_is_detached_from_the_live_factory():
    body = programs.artifact(
        registry_reference=bodies.PROBE_REGISTRY,
        operations=("double", "increment"),
    )
    published = body.artifact_configuration()
    published["configuration"]["input_field"] = "rewritten"

    assert body.configuration["input_field"] == "input"
    assert body.artifact_configuration()["configuration"]["input_field"] == "input"


def test_nested_mapping_configuration_is_immutable_too():
    body = bodies.migrated_improved_body
    routed = body.configuration["routed"]
    assert routed

    task_id = next(iter(routed))
    with pytest.raises(TypeError):
        routed[task_id] = "something_else"


def test_deep_freeze_does_not_change_existing_configured_artifact_identity_semantics():
    """List/tuple and mutable/frozen mapping representation are not executable semantic changes."""
    left = programs.artifact(
        registry_reference=bodies.PROBE_REGISTRY,
        operations=["double", "increment"],
    )
    right = programs.artifact(
        registry_reference=bodies.PROBE_REGISTRY,
        operations=("double", "increment"),
    )
    assert tr.artifact_digest_of(left) == tr.artifact_digest_of(right)
    assert left().attempt({"task_id": "x", "input": 3}) == 7
    assert right().attempt({"task_id": "x", "input": 3}) == 7
