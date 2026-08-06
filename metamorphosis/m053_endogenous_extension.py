"""M053: bounded endogenous extension of the accepted transformation language."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import itertools
import json
from typing import Iterable, Sequence

from metamorphosis.m051_variable_composition import FROZEN_CANDIDATES, M051Error


class M053Error(ValueError):
    """Raised when an M053 artifact violates the bounded protocol."""


def _digest(domain: bytes, value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(domain + payload).hexdigest()


ATOMS = ("current", "previous")
OPERATORS = ("add", "subtract", "minimum", "maximum")
EXTENSION_BUDGET = len(ATOMS) * len(OPERATORS) * len(ATOMS)


@dataclass(frozen=True)
class Probe:
    values: tuple[int, ...]
    reduction: str
    expected: int


@dataclass(frozen=True)
class PairProgram:
    left: str
    operator: str
    right: str

    def evaluate_pair(self, previous: int, current: int) -> int:
        env = {"previous": previous, "current": current}
        left, right = env[self.left], env[self.right]
        if self.operator == "add":
            return left + right
        if self.operator == "subtract":
            return left - right
        if self.operator == "minimum":
            return min(left, right)
        if self.operator == "maximum":
            return max(left, right)
        raise M053Error("unknown operator")

    def transform(self, values: Sequence[int]) -> tuple[int, ...]:
        if len(values) < 2:
            raise M053Error("pair extension requires at least two values")
        return tuple(self.evaluate_pair(previous, current) for previous, current in zip(values, values[1:]))

    def apply(self, values: Sequence[int], reduction: str) -> int:
        transformed = self.transform(values)
        if reduction == "sum":
            return sum(transformed)
        if reduction == "maximum":
            return max(transformed)
        raise M053Error("unsupported reuse reduction")

    def artifact(self) -> dict[str, object]:
        body = {
            "schema": "m053-pair-extension-v1",
            "left": self.left,
            "operator": self.operator,
            "right": self.right,
        }
        return {**body, "digest": _digest(b"m053-pair-extension-v1\0", body)}


META_PROGRAMS = tuple(PairProgram(*parts) for parts in itertools.product(ATOMS, OPERATORS, ATOMS))


def founder_matches(probe: Probe) -> bool:
    if probe.reduction not in {"sum", "maximum"}:
        raise M053Error("unsupported founder comparison")
    for candidate in FROZEN_CANDIDATES:
        try:
            if candidate.apply(probe.values) == probe.expected:
                return True
        except M051Error:
            pass
    return False


def certify_founder_insufficiency(public_probes: Iterable[Probe]) -> dict[str, object]:
    probes = tuple(public_probes)
    if not probes:
        raise M053Error("public probes are required")
    survivors = []
    for candidate in FROZEN_CANDIDATES:
        matched = True
        for probe in probes:
            if candidate.reduction != probe.reduction:
                matched = False
                break
            try:
                if candidate.apply(probe.values) != probe.expected:
                    matched = False
                    break
            except M051Error:
                matched = False
                break
        if matched:
            survivors.append(candidate.artifact()["digest"])
    evidence = [probe.__dict__ for probe in probes]
    return {
        "founder_candidate_count": len(FROZEN_CANDIDATES),
        "survivor_count": len(survivors),
        "insufficient": not survivors,
        "evidence_digest": _digest(b"m053-founder-insufficiency-v1\0", evidence),
    }


def synthesize_extension(public_probes: Iterable[Probe]) -> dict[str, object]:
    probes = tuple(public_probes)
    if not probes:
        raise M053Error("public probes are required")
    certificate = certify_founder_insufficiency(probes)
    if not certificate["insufficient"]:
        raise M053Error("founder language is not demonstrably insufficient")
    survivors = [
        program for program in META_PROGRAMS
        if all(program.apply(probe.values, probe.reduction) == probe.expected for probe in probes)
    ]
    evidence = [probe.__dict__ for probe in probes]
    return {
        "status": "synthesized" if len(survivors) == 1 else "insufficient_evidence",
        "extension": survivors[0].artifact() if len(survivors) == 1 else None,
        "explored_meta_programs": len(META_PROGRAMS),
        "surviving_digests": tuple(program.artifact()["digest"] for program in survivors),
        "evidence_digest": _digest(b"m053-public-extension-evidence-v1\0", evidence),
        "founder_certificate": certificate,
    }


def _load_extension(artifact: dict[str, object]) -> PairProgram:
    body = dict(artifact)
    supplied = body.pop("digest", None)
    if supplied != _digest(b"m053-pair-extension-v1\0", body):
        raise M053Error("extension digest mismatch")
    program = PairProgram(str(body["left"]), str(body["operator"]), str(body["right"]))
    if program not in META_PROGRAMS:
        raise M053Error("extension is outside the bounded meta-language")
    return program


def independently_validate(result: dict[str, object], hidden_probes: Iterable[Probe]) -> bool:
    hidden = tuple(hidden_probes)
    if result.get("status") != "synthesized" or not isinstance(result.get("extension"), dict):
        raise M053Error("only a unique synthesized extension may be validated")
    if not hidden:
        raise M053Error("hidden probes are required")
    program = _load_extension(result["extension"])
    return all(program.apply(probe.values, probe.reduction) == probe.expected for probe in hidden)


@dataclass(frozen=True)
class Registry:
    accepted: tuple[dict[str, object], ...] = ()

    def checkpoint(self) -> str:
        return _digest(b"m053-registry-v1\0", self.accepted)

    def adopt(self, artifact: dict[str, object], validated: bool) -> "Registry":
        if not validated:
            raise M053Error("unvalidated extensions cannot be adopted")
        _load_extension(artifact)
        return Registry(self.accepted + (artifact,))


def run_m053_endogenous_extension() -> dict[str, object]:
    public = (
        Probe((1, 4, 2), "sum", 1),
        Probe((5, 2, 8), "sum", 3),
        Probe((0, 3, 7), "sum", 7),
    )
    hidden = (Probe((-2, 3, 1), "sum", 3), Probe((9, 4, -1), "sum", -10))
    result = synthesize_extension(public)
    validated = independently_validate(result, hidden)
    if not validated:
        raise M053Error("positive extension failed hidden validation")
    founder = Registry()
    founder_checkpoint = founder.checkpoint()
    adopted = founder.adopt(result["extension"], validated)
    program = _load_extension(adopted.accepted[-1])
    reuse_probe = Probe((1, 4, 2, 9), "maximum", 7)
    reuse_passed = program.apply(reuse_probe.values, reuse_probe.reduction) == reuse_probe.expected
    if not reuse_passed or founder_matches(reuse_probe):
        raise M053Error("extension did not demonstrate bounded reusable capability gain")
    ambiguous = synthesize_extension((Probe((1, 2), "sum", 1),))
    before_fault = adopted.checkpoint()
    restored = founder
    rollback_exact = restored.checkpoint() == founder_checkpoint and before_fault != founder_checkpoint
    manifest = {
        "schema": "m053-manifest-v1",
        "status": "development_pending_qualification",
        "founder_candidate_count": len(FROZEN_CANDIDATES),
        "meta_program_budget": EXTENSION_BUDGET,
        "positive": result,
        "hidden_validated": validated,
        "reuse_family": "maximum_adjacent_transition",
        "reuse_passed": reuse_passed,
        "negative_status": ambiguous["status"],
        "rollback_exact": rollback_exact,
        "arbitrary_code_generation": False,
        "network_authority": False,
        "repository_authority": False,
        "credential_authority": False,
        "deployment_authority": False,
        "canonical": False,
    }
    return {**manifest, "digest": _digest(b"m053-manifest-v1\0", manifest)}


__all__ = [
    "EXTENSION_BUDGET", "META_PROGRAMS", "M053Error", "PairProgram", "Probe", "Registry",
    "certify_founder_insufficiency", "founder_matches", "independently_validate",
    "run_m053_endogenous_extension", "synthesize_extension",
]
