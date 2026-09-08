"""Executable artifacts whose configuration is data, so Genesis can ablate and restore them.

A causal ablation is supposed to be *this candidate with one earlier acquisition removed and nothing
else changed*. For a long time the runtime could not construct that, so it accepted one: the proposer
supplied an ablated body and the runtime measured it. ``ConfiguredBody`` makes the executable
configuration explicit so the runtime can build and authenticate the counterfactual itself.

The same property is what makes generated descendants restorable. A configured artifact record binds
its importable interpreter target, the target's source identity, canonical construction data and
acquisition dependencies. ``reconstruct()`` rebuilds that factory from the committed record and then
requires the complete artifact digest to reproduce. Process death therefore need not ask a host to
remember which generated configuration to recreate.

This is still a DEVELOPMENT artifact kind: importable target identity binds module source rather than
an exact packaged executable blob, and the record says ``binds_exact_executed_bytes: false``. A future
native/generated package store can add a stronger artifact kind without weakening this one.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from importlib import import_module
from typing import Any, Mapping

CONFIGURED_BODY_SCHEMA = "genesis-configured-body-v1"


class ArtifactError(RuntimeError):
    """Raised when an artifact cannot be built, restored, or licensed as a single-difference arm."""


def _frozen(configuration: Mapping[str, Any]) -> dict[str, Any]:
    return {str(key): configuration[key] for key in sorted(configuration, key=str)}


def _resolve_symbol(module_name: str, qualname: str) -> Any:
    if not module_name or not qualname or "<locals>" in qualname or "<lambda>" in qualname:
        raise ArtifactError("artifact names no reconstructible importable symbol")
    resolved: Any = import_module(module_name)
    for part in qualname.split("."):
        resolved = getattr(resolved, part)
    if not callable(resolved):
        raise ArtifactError("artifact resolves to a non-callable symbol")
    return resolved


@dataclass(frozen=True)
class ConfiguredBody:
    """A body factory that publishes what it is made of.

    ``dependencies`` is the set of earlier acquisitions this body routes work through. It is the
    only field an ablation may change, and ``without()`` is the only licensed edit.
    """

    target: str
    configuration: Mapping[str, Any] = field(default_factory=dict)
    dependencies: frozenset[str] = frozenset()
    dependency_keyword: str = "capabilities"

    def __post_init__(self) -> None:
        module_name, separator, symbol = str(self.target).partition(":")
        if not module_name or not separator or not symbol:
            raise ArtifactError("a configured body's target must look like 'module:symbol'")
        object.__setattr__(self, "configuration", _frozen(self.configuration))
        object.__setattr__(self, "dependencies", frozenset(str(name) for name in self.dependencies))

    def resolve(self) -> Any:
        module_name, _, symbol = str(self.target).partition(":")
        return _resolve_symbol(module_name, symbol)

    def __call__(self) -> Any:
        """Build the body. The candidate executor calls this only after its limits exist."""
        constructor = self.resolve()
        arguments = dict(self.configuration)
        arguments[self.dependency_keyword] = frozenset(self.dependencies)
        return constructor(**arguments)

    def without(self, dependency: str) -> "ConfiguredBody":
        """This body with exactly one declared dependency removed."""
        name = str(dependency)
        if name not in self.dependencies:
            raise ArtifactError(
                "this body does not declare %r as a dependency, so removing it is not an ablation "
                "of anything it does" % name
            )
        return ConfiguredBody(
            target=self.target,
            configuration=dict(self.configuration),
            dependencies=self.dependencies - {name},
            dependency_keyword=self.dependency_keyword,
        )

    def artifact_configuration(self) -> dict[str, Any]:
        """Everything the configured artifact digest must bind."""
        from genesis.trust_root import artifact_digest_of

        return {
            "schema": CONFIGURED_BODY_SCHEMA,
            "target": str(self.target),
            "target_artifact": artifact_digest_of(self.resolve()),
            "configuration": dict(self.configuration),
            "dependencies": sorted(self.dependencies),
            "dependency_keyword": str(self.dependency_keyword),
        }


def reconstruct(record: Mapping[str, Any]) -> Any:
    """Rebuild an executable factory from a committed artifact record, or fail closed.

    Only artifact kinds whose complete behaviourally relevant configuration can be reconstructed are
    supported. Opaque callable state and partial applications whose canonical value encoding is not
    invertible here are deliberately refused rather than guessed.
    """
    from genesis.trust_root import artifact_digest_of

    if not isinstance(record, Mapping):
        raise ArtifactError("persisted body carries no executable artifact record")
    kind = str(record.get("kind") or "")

    if kind == "importable_symbol":
        rebuilt = _resolve_symbol(
            str(record.get("module") or ""), str(record.get("qualname") or "")
        )
    elif kind == "configured_artifact":
        published = record.get("configuration")
        if not isinstance(published, Mapping) or published.get("schema") != CONFIGURED_BODY_SCHEMA:
            raise ArtifactError("persisted configured artifact carries no reconstructible configuration")
        target = str(published.get("target") or "")
        target_artifact = published.get("target_artifact")
        if not isinstance(target_artifact, Mapping):
            raise ArtifactError("persisted configured artifact carries no target identity")
        module_name, separator, qualname = target.partition(":")
        if not separator:
            raise ArtifactError("persisted configured artifact target is malformed")
        resolved = _resolve_symbol(module_name, qualname)
        actual_target = artifact_digest_of(resolved)
        if actual_target != dict(target_artifact):
            raise ArtifactError("configured artifact target no longer matches its committed identity")
        raw_configuration = published.get("configuration")
        if not isinstance(raw_configuration, Mapping):
            raise ArtifactError("persisted configured artifact configuration is not a mapping")
        dependencies = published.get("dependencies") or []
        if not isinstance(dependencies, list):
            raise ArtifactError("persisted configured artifact dependencies are not canonical data")
        rebuilt = ConfiguredBody(
            target=target,
            configuration=dict(raw_configuration),
            dependencies=frozenset(str(value) for value in dependencies),
            dependency_keyword=str(published.get("dependency_keyword") or "capabilities"),
        )
    else:
        raise ArtifactError(
            "persisted executable artifact kind %r cannot be reconstructed without an external "
            "resolver" % kind
        )

    actual = artifact_digest_of(rebuilt)
    if actual != dict(record):
        raise ArtifactError("reconstructed executable artifact does not reproduce its committed digest")
    return rebuilt


def derive_ablation(candidate: Any, dependency: str) -> ConfiguredBody:
    """Build *this candidate minus this acquisition*, or refuse to pretend one exists."""
    if not isinstance(candidate, ConfiguredBody):
        raise ArtifactError(
            "this candidate does not publish a configuration the runtime can edit, so no arm can be "
            "constructed from it; an arm supplied by the proposer is the proposer's own evidence "
            "and is not read here"
        )
    return candidate.without(dependency)


def single_difference(candidate: Any, ablated: Any, dependency: str) -> list[str]:
    """Everything that differs between the two arms beyond the licensed removal."""
    problems: list[str] = []
    if not isinstance(candidate, ConfiguredBody) or not isinstance(ablated, ConfiguredBody):
        return ["one of the arms does not publish a configuration to compare"]
    if candidate.target != ablated.target:
        problems.append("the arms are built from different targets")
    if candidate.dependency_keyword != ablated.dependency_keyword:
        problems.append("the arms declare their dependencies differently")
    if dict(candidate.configuration) != dict(ablated.configuration):
        differing = sorted(
            key
            for key in set(candidate.configuration) | set(ablated.configuration)
            if candidate.configuration.get(key) != ablated.configuration.get(key)
        )
        problems.append(
            "the arms differ in configuration beyond the removal: %s" % ", ".join(differing)
        )
    removed = candidate.dependencies - ablated.dependencies
    added = ablated.dependencies - candidate.dependencies
    if removed != {str(dependency)}:
        problems.append(
            "the arm removed %s rather than %r"
            % (", ".join(sorted(removed)) or "nothing", str(dependency))
        )
    if added:
        problems.append("the arm gained %s" % ", ".join(sorted(added)))
    return problems
