"""M052: exact behavioral-equivalence pruning over the frozen M051 grammar."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import itertools
import json
from typing import Iterable, Sequence

from metamorphosis.m051_variable_composition import Candidate, FROZEN_CANDIDATES, M051Error, Probe


class M052Error(ValueError):
    """Raised when an M052 artifact violates the frozen protocol."""


def _digest(domain: bytes, value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(domain + payload).hexdigest()


DOMAIN_VALUES = (-2, -1, 0, 1, 2)
MAX_DOMAIN_LENGTH = 3
FINITE_DOMAIN = tuple(
    values
    for length in range(MAX_DOMAIN_LENGTH + 1)
    for values in itertools.product(DOMAIN_VALUES, repeat=length)
)


def _outcome(candidate: Candidate, values: Sequence[int]) -> tuple[str, int | None]:
    try:
        return ("value", candidate.apply(values))
    except M051Error:
        return ("error", None)


def behavioral_signature(candidate: Candidate) -> str:
    outcomes = [
        {"values": list(values), "outcome": _outcome(candidate, values)}
        for values in FINITE_DOMAIN
    ]
    return _digest(b"m052-finite-behavior-v1\0", outcomes)


EQUIVALENCE_CLASSES: dict[str, tuple[Candidate, ...]] = {}
for _candidate in FROZEN_CANDIDATES:
    _signature = behavioral_signature(_candidate)
    EQUIVALENCE_CLASSES.setdefault(_signature, tuple())
    EQUIVALENCE_CLASSES[_signature] = EQUIVALENCE_CLASSES[_signature] + (_candidate,)

CANONICAL_REPRESENTATIVES = tuple(
    sorted(members, key=lambda candidate: candidate.artifact()["digest"])[0]
    for _, members in sorted(EQUIVALENCE_CLASSES.items())
)


@dataclass(frozen=True)
class PrunedSearchResult:
    status: str
    candidate: dict[str, object] | None
    raw_candidate_count: int
    equivalence_class_count: int
    pruned_candidate_count: int
    surviving_class_signatures: tuple[str, ...]
    evidence_digest: str


def _matches(candidate: Candidate, probe: Probe) -> bool:
    try:
        result = candidate.apply(probe.values)
    except M051Error:
        return probe.expects_error
    return not probe.expects_error and result == probe.expected


def _validate_probe_domain(probes: tuple[Probe, ...]) -> None:
    allowed = set(FINITE_DOMAIN)
    if any(probe.values not in allowed for probe in probes):
        raise M052Error("all probes must remain inside the frozen finite domain")


def search_with_pruning(public_probes: Iterable[Probe]) -> PrunedSearchResult:
    probes = tuple(public_probes)
    if not probes:
        raise M052Error("at least one public probe is required")
    _validate_probe_domain(probes)
    survivors = [
        candidate
        for candidate in CANONICAL_REPRESENTATIVES
        if all(_matches(candidate, probe) for probe in probes)
    ]
    signatures = tuple(sorted(behavioral_signature(candidate) for candidate in survivors))
    evidence = [
        {"values": list(probe.values), "expected": probe.expected, "expects_error": probe.expects_error}
        for probe in probes
    ]
    return PrunedSearchResult(
        status="composed" if len(survivors) == 1 else "insufficient_evidence",
        candidate=survivors[0].artifact() if len(survivors) == 1 else None,
        raw_candidate_count=len(FROZEN_CANDIDATES),
        equivalence_class_count=len(CANONICAL_REPRESENTATIVES),
        pruned_candidate_count=len(FROZEN_CANDIDATES) - len(CANONICAL_REPRESENTATIVES),
        surviving_class_signatures=signatures,
        evidence_digest=_digest(b"m052-public-evidence-v1\0", evidence),
    )


def independently_validate(result: PrunedSearchResult, hidden_probes: Iterable[Probe]) -> bool:
    hidden = tuple(hidden_probes)
    if result.status != "composed" or result.candidate is None:
        raise M052Error("only a unique behavioral class may be validated")
    if not hidden:
        raise M052Error("hidden probes are required")
    _validate_probe_domain(hidden)
    body = dict(result.candidate)
    supplied = body.pop("digest", None)
    expected = _digest(b"m051-candidate-v1\0", body)
    if supplied != expected:
        raise M052Error("candidate digest mismatch")
    candidate = Candidate(tuple(body["transforms"]), body["reduction"], body["empty_policy"])
    if candidate not in CANONICAL_REPRESENTATIVES:
        raise M052Error("candidate is not a canonical class representative")
    return all(_matches(candidate, probe) for probe in hidden)


def run_m052_behavioral_equivalence_pruning() -> dict[str, object]:
    public = (
        Probe((-1, 1, -1), 1),
        Probe((-2, -2, 1), 1),
        Probe((), 0),
    )
    hidden = (Probe((-2, 2, 1), 1), Probe((-1, -1, 2), 2))
    positive = search_with_pruning(public)
    if positive.status != "composed" or not independently_validate(positive, hidden):
        raise M052Error("positive episode failed")
    ambiguous = search_with_pruning((Probe((1,), 1), Probe((), 0)))
    manifest = {
        "schema": "m052-manifest-v1",
        "status": "development_pending_qualification",
        "finite_domain_size": len(FINITE_DOMAIN),
        "raw_candidate_count": len(FROZEN_CANDIDATES),
        "equivalence_class_count": len(CANONICAL_REPRESENTATIVES),
        "pruned_candidate_count": len(FROZEN_CANDIDATES) - len(CANONICAL_REPRESENTATIVES),
        "positive": positive.__dict__,
        "ambiguous_status": ambiguous.status,
        "arbitrary_code_generation": False,
        "grammar_widening": False,
        "unknown_runtime_discovery": False,
        "network_authority": False,
        "repository_authority": False,
        "credential_authority": False,
        "deployment_authority": False,
        "canonical": False,
    }
    return {**manifest, "digest": _digest(b"m052-manifest-v1\0", manifest)}


__all__ = [
    "CANONICAL_REPRESENTATIVES",
    "DOMAIN_VALUES",
    "EQUIVALENCE_CLASSES",
    "FINITE_DOMAIN",
    "MAX_DOMAIN_LENGTH",
    "M052Error",
    "PrunedSearchResult",
    "behavioral_signature",
    "independently_validate",
    "run_m052_behavioral_equivalence_pruning",
    "search_with_pruning",
]
