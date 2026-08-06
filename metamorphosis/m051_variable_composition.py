"""M051: bounded variable-length composition over a closed primitive grammar."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import itertools
import json
from typing import Iterable, Sequence


class M051Error(ValueError):
    """Raised when an M051 artifact violates the frozen protocol."""


def _digest(domain: bytes, value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(domain + payload).hexdigest()


TRANSFORMS = ("absolute", "unique", "nonnegative")
REDUCTIONS = ("maximum", "minimum", "sum", "mean_floor")
EMPTY_POLICIES = ("zero", "reject")
MAX_TRANSFORM_DEPTH = 2
TRANSFORM_CHAINS = ((),) + tuple((name,) for name in TRANSFORMS) + tuple(
    pair for pair in itertools.permutations(TRANSFORMS, 2)
)
COMPOSITION_BUDGET = len(TRANSFORM_CHAINS) * len(REDUCTIONS) * len(EMPTY_POLICIES)


@dataclass(frozen=True)
class Probe:
    values: tuple[int, ...]
    expected: int | None
    expects_error: bool = False


@dataclass(frozen=True)
class Candidate:
    transforms: tuple[str, ...]
    reduction: str
    empty_policy: str

    def apply(self, values: Sequence[int]) -> int:
        if not values:
            if self.empty_policy == "zero":
                return 0
            raise M051Error("candidate rejects empty input")
        current = list(values)
        for transform in self.transforms:
            if transform == "absolute":
                current = [abs(value) for value in current]
            elif transform == "unique":
                current = list(dict.fromkeys(current))
            elif transform == "nonnegative":
                current = [value for value in current if value >= 0]
            else:
                raise M051Error("unknown transform")
        if not current:
            if self.empty_policy == "zero":
                return 0
            raise M051Error("candidate rejects empty transformed input")
        if self.reduction == "maximum":
            return max(current)
        if self.reduction == "minimum":
            return min(current)
        if self.reduction == "sum":
            return sum(current)
        if self.reduction == "mean_floor":
            return sum(current) // len(current)
        raise M051Error("unknown reduction")

    def artifact(self) -> dict[str, object]:
        body = {
            "schema": "m051-candidate-v1",
            "runtime": "node-esm",
            "transforms": list(self.transforms),
            "reduction": self.reduction,
            "empty_policy": self.empty_policy,
        }
        return {**body, "digest": _digest(b"m051-candidate-v1\0", body)}


FROZEN_CANDIDATES = tuple(
    Candidate(chain, reduction, empty_policy)
    for chain, reduction, empty_policy in itertools.product(
        TRANSFORM_CHAINS, REDUCTIONS, EMPTY_POLICIES
    )
)


@dataclass(frozen=True)
class SearchResult:
    status: str
    candidate: dict[str, object] | None
    explored_candidates: int
    surviving_digests: tuple[str, ...]
    evidence_digest: str


def _matches(candidate: Candidate, probe: Probe) -> bool:
    try:
        result = candidate.apply(probe.values)
    except M051Error:
        return probe.expects_error
    return not probe.expects_error and result == probe.expected


def search(public_probes: Iterable[Probe]) -> SearchResult:
    probes = tuple(public_probes)
    if not probes:
        raise M051Error("at least one public probe is required")
    survivors = [candidate for candidate in FROZEN_CANDIDATES if all(_matches(candidate, p) for p in probes)]
    digests = tuple(candidate.artifact()["digest"] for candidate in survivors)
    evidence = [
        {"values": list(p.values), "expected": p.expected, "expects_error": p.expects_error}
        for p in probes
    ]
    return SearchResult(
        status="composed" if len(survivors) == 1 else "insufficient_evidence",
        candidate=survivors[0].artifact() if len(survivors) == 1 else None,
        explored_candidates=len(FROZEN_CANDIDATES),
        surviving_digests=digests,
        evidence_digest=_digest(b"m051-public-evidence-v1\0", evidence),
    )


def independently_validate(result: SearchResult, hidden_probes: Iterable[Probe]) -> bool:
    hidden = tuple(hidden_probes)
    if result.status != "composed" or result.candidate is None:
        raise M051Error("only a unique composition may be validated")
    if not hidden:
        raise M051Error("hidden probes are required")
    body = dict(result.candidate)
    supplied = body.pop("digest", None)
    if supplied != _digest(b"m051-candidate-v1\0", body):
        raise M051Error("candidate digest mismatch")
    candidate = Candidate(tuple(body["transforms"]), body["reduction"], body["empty_policy"])
    if candidate not in FROZEN_CANDIDATES:
        raise M051Error("candidate is outside the frozen grammar")
    return all(_matches(candidate, probe) for probe in hidden)


def run_m051_bounded_variable_composition() -> dict[str, object]:
    public = (
        Probe((-1, 1, -1, 2), 3),
        Probe((-2, -2, 3), 5),
        Probe((), 0),
    )
    hidden = (Probe((-5, 5, 2), 7), Probe((-3, -3, 1), 4))
    positive = search(public)
    if positive.status != "composed" or not independently_validate(positive, hidden):
        raise M051Error("positive episode failed")
    ambiguous = search((Probe((5,), 5), Probe((), 0)))
    misleading = search((Probe((-1, 1), 1), Probe((), 0)))
    manifest = {
        "schema": "m051-manifest-v1",
        "status": "passed_in_development",
        "composition_budget": COMPOSITION_BUDGET,
        "max_transform_depth": MAX_TRANSFORM_DEPTH,
        "positive": positive.__dict__,
        "ambiguous_status": ambiguous.status,
        "misleading_status": misleading.status,
        "arbitrary_code_generation": False,
        "unknown_runtime_discovery": False,
        "network_authority": False,
        "repository_authority": False,
        "credential_authority": False,
        "deployment_authority": False,
        "canonical": False,
    }
    return {**manifest, "digest": _digest(b"m051-manifest-v1\0", manifest)}


__all__ = [
    "COMPOSITION_BUDGET", "FROZEN_CANDIDATES", "MAX_TRANSFORM_DEPTH", "M051Error",
    "Probe", "SearchResult", "independently_validate", "run_m051_bounded_variable_composition",
    "search",
]
