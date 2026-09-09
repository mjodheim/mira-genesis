"""Executable artifacts whose configuration is immutable data Genesis can ablate and restore.

A configured artifact is useful only if the configuration whose digest was admitted cannot later be
rewritten through an alias. ``@dataclass(frozen=True)`` freezes attribute assignment, not a dict held
inside the attribute: the earlier implementation copied only the outer mapping, so both
``body.configuration['x'] = ...`` and mutation through nested lists/dicts could silently change an
adopted executable after its proposal/verdict identity had been recorded.

``ConfiguredBody`` now deep-freezes every container on construction and detaches from the caller's
input. Runtime constructors receive a fresh mutable/plain copy; artifact publication returns a fresh
structural copy; neither exposes a handle back into the admitted factory. This preserves the existing
canonical artifact digest because the trust-root canonicalizer already treats list/tuple values
identically and mappings by value.

The same reconstructible configuration supports runtime-derived single-difference ablation and
process-death restoration. Importable target identity remains DEVELOPMENT-grade module-source identity
rather than exact packaged executed bytes, and the artifact record says so.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from importlib import import_module
from types import MappingProxyType
from typing import Any, Mapping

CONFIGURED_BODY_SCHEMA = "genesis-configured-body-v1"


class ArtifactError(RuntimeError):
    """Raised when an artifact cannot be built, restored, or licensed as a single-difference arm."""


def _freeze_value(value: Any) -> Any:
    """Detach recursively and remove every ordinary container mutation surface."""
    if isinstance(value, Mapping):
        return MappingProxyType(
            {
                str(key): _freeze_value(value[key])
                for key in sorted(value, key=lambda item: str(item))
            }
        )
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_value(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(_freeze_value(item) for item in value)
    return value


def _published_value(value: Any) -> Any:
    """Return detached structural data without exposing the factory's frozen containers."""
    if isinstance(value, Mapping):
        return {str(key): _published_value(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return tuple(_published_value(item) for item in value)
    if isinstance(value, frozenset):
        return frozenset(_published_value(item) for item in value)
    return value


def _runtime_value(value: Any) -> Any:
    """Give a body constructor ordinary containers it may own without reaching the artifact."""
    if isinstance(value, Mapping):
        return {str(key): _runtime_value(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_runtime_value(item) for item in value]
    if isinstance(value, frozenset):
        return {_runtime_value(item) for item in value}
    return value


def _frozen(configuration: Mapping[str, Any]) -> Mapping[str, Any]:
    frozen = _freeze_value(configuration)
    if not isinstance(frozen, Mapping):  # defensive: callers are typed as Mapping
        raise ArtifactError("configured body configuration is not a mapping")
    return frozen


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
    """A body factory whose published configuration cannot change after construction."""

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
        """Build a body from detached runtime values after the candidate limits exist."""
        constructor = self.resolve()
        arguments = _runtime_value(self.configuration)
        if not isinstance(arguments, dict):  # defensive: configuration is always a mapping
            raise ArtifactError("configured body did not reconstruct keyword arguments")
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
            configuration=self.configuration,
            dependencies=self.dependencies - {name},
            dependency_keyword=self.dependency_keyword,
        )

    def artifact_configuration(self) -> dict[str, Any]:
        """Everything the configured artifact digest binds, returned without mutable aliases."""
        from genesis.trust_root import artifact_digest_of

        return {
            "schema": CONFIGURED_BODY_SCHEMA,
            "target": str(self.target),
            "target_artifact": artifact_digest_of(self.resolve()),
            "configuration": _published_value(self.configuration),
            "dependencies": sorted(self.dependencies),
            "dependency_keyword": str(self.dependency_keyword),
        }


def reconstruct(record: Mapping[str, Any]) -> Any:
    """Rebuild an executable factory from a committed artifact record, or fail closed."""
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
            raise ArtifactError(
                "persisted configured artifact carries no reconstructible configuration"
            )
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
        raise ArtifactError(
            "reconstructed executable artifact does not reproduce its committed digest"
        )
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
