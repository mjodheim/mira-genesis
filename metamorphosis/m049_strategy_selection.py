"""M049: bounded migration-strategy selection with independent validation.

This development experiment asks a narrow question: can a continuing lineage select
one migration strategy from a fixed admissible family using public evidence only,
then submit the selected artifact to an independent hidden validator?

It does not synthesize arbitrary compilers or discover unknown runtimes.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Iterable, Mapping, Sequence


class M049Error(ValueError):
    """Raised when an M049 artifact violates the frozen protocol."""


def _digest(domain: bytes, value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(domain + payload).hexdigest()


@dataclass(frozen=True)
class Strategy:
    name: str
    aggregate: str
    empty_policy: str

    def apply(self, values: Sequence[int]) -> int:
        if not values:
            if self.empty_policy == "zero":
                return 0
            raise M049Error("strategy rejects empty input")
        if self.aggregate == "maximum":
            return max(values)
        if self.aggregate == "minimum":
            return min(values)
        if self.aggregate == "sum":
            return sum(values)
        if self.aggregate == "mean_floor":
            return sum(values) // len(values)
        raise M049Error(f"unsupported aggregate {self.aggregate!r}")

    def artifact(self) -> dict[str, object]:
        body = {
            "schema": "m049-node-strategy-v1",
            "runtime": "node-esm",
            "name": self.name,
            "aggregate": self.aggregate,
            "empty_policy": self.empty_policy,
        }
        return {**body, "digest": _digest(b"m049-strategy-v1\0", body)}


FROZEN_STRATEGIES: tuple[Strategy, ...] = (
    Strategy("max-zero", "maximum", "zero"),
    Strategy("min-zero", "minimum", "zero"),
    Strategy("sum-zero", "sum", "zero"),
    Strategy("mean-zero", "mean_floor", "zero"),
)


@dataclass(frozen=True)
class Probe:
    values: tuple[int, ...]
    expected: int


@dataclass(frozen=True)
class Selection:
    status: str
    strategy: Mapping[str, object] | None
    public_evidence_digest: str
    surviving_strategy_digests: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": "m049-selection-v1",
            "status": self.status,
            "strategy": dict(self.strategy) if self.strategy is not None else None,
            "public_evidence_digest": self.public_evidence_digest,
            "surviving_strategy_digests": list(self.surviving_strategy_digests),
        }


def select_strategy(public_probes: Iterable[Probe]) -> Selection:
    """Select exactly one strategy from public probes, otherwise fail closed."""
    probes = tuple(public_probes)
    if not probes:
        raise M049Error("at least one public probe is required")
    evidence = [
        {"values": list(probe.values), "expected": probe.expected} for probe in probes
    ]
    evidence_digest = _digest(b"m049-public-evidence-v1\0", evidence)
    survivors: list[Strategy] = []
    for strategy in FROZEN_STRATEGIES:
        if all(strategy.apply(probe.values) == probe.expected for probe in probes):
            survivors.append(strategy)
    survivor_digests = tuple(strategy.artifact()["digest"] for strategy in survivors)
    if len(survivors) != 1:
        return Selection(
            status="insufficient_evidence",
            strategy=None,
            public_evidence_digest=evidence_digest,
            surviving_strategy_digests=survivor_digests,
        )
    return Selection(
        status="selected",
        strategy=survivors[0].artifact(),
        public_evidence_digest=evidence_digest,
        surviving_strategy_digests=survivor_digests,
    )


@dataclass(frozen=True)
class Validation:
    accepted: bool
    selection_digest: str
    hidden_evidence_digest: str
    verdict_digest: str

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": "m049-validation-v1",
            "accepted": self.accepted,
            "selection_digest": self.selection_digest,
            "hidden_evidence_digest": self.hidden_evidence_digest,
            "verdict_digest": self.verdict_digest,
        }


def independently_validate(
    selection: Selection, hidden_probes: Iterable[Probe]
) -> Validation:
    """Validate a public selection against hidden evidence without adoption authority."""
    hidden = tuple(hidden_probes)
    if selection.status != "selected" or selection.strategy is None:
        raise M049Error("only a uniquely selected strategy may be validated")
    if not hidden:
        raise M049Error("independent validation requires hidden probes")
    artifact = dict(selection.strategy)
    expected_digest = artifact.pop("digest", None)
    if expected_digest != _digest(b"m049-strategy-v1\0", artifact):
        raise M049Error("strategy artifact digest mismatch")
    matches = [
        strategy
        for strategy in FROZEN_STRATEGIES
        if strategy.name == artifact["name"]
        and strategy.aggregate == artifact["aggregate"]
        and strategy.empty_policy == artifact["empty_policy"]
    ]
    if len(matches) != 1:
        raise M049Error("strategy is outside the frozen admissible family")
    strategy = matches[0]
    hidden_payload = [
        {"values": list(probe.values), "expected": probe.expected} for probe in hidden
    ]
    accepted = all(strategy.apply(probe.values) == probe.expected for probe in hidden)
    selection_digest = _digest(b"m049-selection-v1\0", selection.to_dict())
    hidden_digest = _digest(b"m049-hidden-evidence-v1\0", hidden_payload)
    verdict = {
        "accepted": accepted,
        "selection_digest": selection_digest,
        "hidden_evidence_digest": hidden_digest,
    }
    return Validation(
        accepted=accepted,
        selection_digest=selection_digest,
        hidden_evidence_digest=hidden_digest,
        verdict_digest=_digest(b"m049-validation-v1\0", verdict),
    )


def run_m049_bounded_strategy_selection() -> dict[str, object]:
    """Run the frozen positive and insufficient-evidence development episodes."""
    positive_public = (
        Probe((2, 9, 4), 9),
        Probe((-5, -2, -8), -2),
        Probe((), 0),
    )
    positive_hidden = (
        Probe((7, 1, 7, 3), 7),
        Probe((-1, 0, -3), 0),
    )
    selected = select_strategy(positive_public)
    validated = independently_validate(selected, positive_hidden)
    if not validated.accepted:
        raise M049Error("frozen positive episode failed independent validation")

    ambiguous = select_strategy((Probe((5,), 5), Probe((), 0)))
    if ambiguous.status != "insufficient_evidence":
        raise M049Error("ambiguous episode did not fail closed")

    manifest = {
        "schema": "m049-manifest-v1",
        "status": "passed_in_development",
        "selected": selected.to_dict(),
        "validation": validated.to_dict(),
        "ambiguous": ambiguous.to_dict(),
        "strategy_budget": len(FROZEN_STRATEGIES),
        "arbitrary_compiler_synthesis": False,
        "unknown_runtime_discovery": False,
        "repository_authority": False,
        "network_authority": False,
        "deployment_authority": False,
        "canonical": False,
    }
    return {**manifest, "digest": _digest(b"m049-manifest-v1\0", manifest)}


__all__ = [
    "FROZEN_STRATEGIES",
    "M049Error",
    "Probe",
    "Selection",
    "Strategy",
    "Validation",
    "independently_validate",
    "run_m049_bounded_strategy_selection",
    "select_strategy",
]
