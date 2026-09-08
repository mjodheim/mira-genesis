"""Executable artifacts whose configuration is data, so the runtime can build their ablations.

A causal ablation is supposed to be *this candidate with one earlier acquisition removed and nothing
else changed*. For a long time the runtime could not construct that, so it accepted one: the
proposer supplied an `ablated_body_factory`, said which acquisition it stood for, and the cycle
measured the loss. Naming a real acquisition was checked; that the supplied arm was that acquisition
removed was not. A deliberately weak unrelated body therefore produced a measured loss and was
recorded as causal dependency — the proposer authoring its own evidence.

The repair is not a stricter check on the caller's arm. It is to make the candidate's configuration
something the runtime can read and edit, so the runtime builds the arm itself:

    candidate  = ConfiguredBody(target=..., configuration=..., dependencies={"a", "b"})
    ablated    = candidate.without("b")

and then *verifies* that the two differ in exactly the licensed removal before either is run. A
proposer can still propose anything it likes; it can no longer decide what the counterfactual is.

**What this does not do.** The configuration is a mapping the host's world admits, and the target is
an importable symbol, so a lineage that generates genuinely new code cannot yet describe itself this
way. Where the runtime cannot construct and authenticate the single-difference arm it records
`established: false` — which is the honest reading of a counterfactual nobody could build, and is
what this module exists to make possible rather than to paper over.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from importlib import import_module
from typing import Any, Mapping

CONFIGURED_BODY_SCHEMA = "genesis-configured-body-v1"


class ArtifactError(RuntimeError):
    """Raised when an artifact cannot be built, or when a derived arm is not the licensed one."""


def _frozen(configuration: Mapping[str, Any]) -> dict[str, Any]:
    return {str(key): configuration[key] for key in sorted(configuration, key=str)}


@dataclass(frozen=True)
class ConfiguredBody:
    """A body factory that publishes what it is made of.

    `dependencies` is the set of earlier acquisitions this body routes work through. It is the only
    field an ablation may change, and `without()` is the only way to change it.
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

    # -- construction ---------------------------------------------------------------------
    def resolve(self) -> Any:
        module_name, _, symbol = str(self.target).partition(":")
        return getattr(import_module(module_name), symbol)

    def __call__(self) -> Any:
        """Build the body. Called in the sandbox's child process, so this must stay picklable."""
        constructor = self.resolve()
        arguments = dict(self.configuration)
        arguments[self.dependency_keyword] = frozenset(self.dependencies)
        return constructor(**arguments)

    # -- the licensed edit ----------------------------------------------------------------
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

    # -- identity -------------------------------------------------------------------------
    def artifact_configuration(self) -> dict[str, Any]:
        """What `trust_root.artifact_digest_of` binds. Bound state is behaviour, so all of it."""
        return {
            "schema": CONFIGURED_BODY_SCHEMA,
            "target": str(self.target),
            "configuration": dict(self.configuration),
            "dependencies": sorted(self.dependencies),
            "dependency_keyword": str(self.dependency_keyword),
        }


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
    """Everything that differs between the two arms beyond the licensed removal.

    An empty list means the ablated arm is the candidate with exactly `dependency` gone. Anything
    else is a second change riding along with the first, which makes the measured loss ambiguous
    between them.
    """
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
        problems.append("the arms differ in configuration beyond the removal: %s" % ", ".join(differing))
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
