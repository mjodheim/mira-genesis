"""M050: bounded composition of frozen migration primitives.

This development experiment composes a small admissible pipeline from independent
input, reduction, and empty-input primitives using public evidence only. A separate
validator owns hidden evidence. The construction is finite, deterministic, and has
no authority over repositories, networks, credentials, deployment, or production.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import itertools
import json
from typing import Iterable, Mapping, Sequence


class M050Error(ValueError):
    """Raised when an M050 artifact violates the frozen protocol."""


def _digest(domain: bytes, value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(domain + payload).hexdigest()


@dataclass(frozen=True)
class Primitive:
    family: str
    name: str

    def artifact(self) -> dict[str, str]:
        body = {"schema": "m050-primitive-v1", "family": self.family, "name": self.name}
        return {**body, "digest": _digest(b"m050-primitive-v1\0", body)}


INPUT_PRIMITIVES: tuple[Primitive, ...] = (
    Primitive("input", "identity"),
    Primitive("input", "absolute"),
    Primitive("input", "unique"),
)
REDUCTION_PRIMITIVES: tuple[Primitive, ...] = (
    Primitive("reduction", "maximum"),
    Primitive("reduction", "minimum"),
    Primitive("reduction", "sum"),
    Primitive("reduction", "mean_floor"),
)
EMPTY_PRIMITIVES: tuple[Primitive, ...] = (
    Primitive("empty", "zero"),
    Primitive("empty", "reject"),
)

COMPOSITION_BUDGET = len(INPUT_PRIMITIVES) * len(REDUCTION_PRIMITIVES) * len(EMPTY_PRIMITIVES)


@dataclass(frozen=True)
class Pipeline:
    input_primitive: Primitive
    reduction_primitive: Primitive
    empty_primitive: Primitive

    def apply(self, values: Sequence[int]) -> int:
        if not values:
            if self.empty_primitive.name == "zero":
                return 0
            raise M050Error("pipeline rejects empty input")

        transformed = list(values)
        if self.input_primitive.name == "absolute":
            transformed = [abs(value) for value in transformed]
        elif self.input_primitive.name == "unique":
            transformed = list(dict.fromkeys(transformed))
        elif self.input_primitive.name != "identity":
            raise M050Error("unknown input primitive")

        reduction = self.reduction_primitive.name
        if reduction == "maximum":
            return max(transformed)
        if reduction == "minimum":
            return min(transformed)
        if reduction == "sum":
            return sum(transformed)
        if reduction == "mean_floor":
            return sum(transformed) // len(transformed)
        raise M050Error("unknown reduction primitive")

    def artifact(self) -> dict[str, object]:
        body = {
            "schema": "m050-pipeline-v1",
            "runtime": "node-esm",
            "primitives": [
                self.input_primitive.artifact(),
                self.reduction_primitive.artifact(),
                self.empty_primitive.artifact(),
            ],
        }
        return {**body, "digest": _digest(b"m050-pipeline-v1\0", body)}


FROZEN_PIPELINES: tuple[Pipeline, ...] = tuple(
    Pipeline(input_primitive, reduction_primitive, empty_primitive)
    for input_primitive, reduction_primitive, empty_primitive in itertools.product(
        INPUT_PRIMITIVES, REDUCTION_PRIMITIVES, EMPTY_PRIMITIVES
    )
)


@dataclass(frozen=True)
class Probe:
    values: tuple[int, ...]
    expected: int | None
    expects_error: bool = False


@dataclass(frozen=True)
class Composition:
    status: str
    pipeline: Mapping[str, object] | None
    public_evidence_digest: str
    surviving_pipeline_digests: tuple[str, ...]
    explored_compositions: int

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": "m050-composition-v1",
            "status": self.status,
            "pipeline": dict(self.pipeline) if self.pipeline is not None else None,
            "public_evidence_digest": self.public_evidence_digest,
            "surviving_pipeline_digests": list(self.surviving_pipeline_digests),
            "explored_compositions": self.explored_compositions,
        }


def _matches(pipeline: Pipeline, probe: Probe) -> bool:
    try:
        result = pipeline.apply(probe.values)
    except M050Error:
        return probe.expects_error
    return not probe.expects_error and result == probe.expected


def compose_pipeline(public_probes: Iterable[Probe]) -> Composition:
    """Compose exactly one frozen pipeline from public evidence, otherwise fail closed."""
    probes = tuple(public_probes)
    if not probes:
        raise M050Error("at least one public probe is required")
    evidence = [
        {
            "values": list(probe.values),
            "expected": probe.expected,
            "expects_error": probe.expects_error,
        }
        for probe in probes
    ]
    survivors = [
        pipeline for pipeline in FROZEN_PIPELINES if all(_matches(pipeline, probe) for probe in probes)
    ]
    survivor_digests = tuple(pipeline.artifact()["digest"] for pipeline in survivors)
    status = "composed" if len(survivors) == 1 else "insufficient_evidence"
    return Composition(
        status=status,
        pipeline=survivors[0].artifact() if len(survivors) == 1 else None,
        public_evidence_digest=_digest(b"m050-public-evidence-v1\0", evidence),
        surviving_pipeline_digests=survivor_digests,
        explored_compositions=len(FROZEN_PIPELINES),
    )


@dataclass(frozen=True)
class Validation:
    accepted: bool
    composition_digest: str
    hidden_evidence_digest: str
    verdict_digest: str

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": "m050-validation-v1",
            "accepted": self.accepted,
            "composition_digest": self.composition_digest,
            "hidden_evidence_digest": self.hidden_evidence_digest,
            "verdict_digest": self.verdict_digest,
        }


def _pipeline_from_artifact(artifact: Mapping[str, object]) -> Pipeline:
    candidate = dict(artifact)
    supplied_digest = candidate.pop("digest", None)
    if supplied_digest != _digest(b"m050-pipeline-v1\0", candidate):
        raise M050Error("pipeline artifact digest mismatch")
    if candidate.get("schema") != "m050-pipeline-v1" or candidate.get("runtime") != "node-esm":
        raise M050Error("pipeline artifact metadata mismatch")
    primitive_artifacts = candidate.get("primitives")
    if not isinstance(primitive_artifacts, list) or len(primitive_artifacts) != 3:
        raise M050Error("pipeline must contain exactly three primitives")

    resolved: list[Primitive] = []
    frozen = INPUT_PRIMITIVES + REDUCTION_PRIMITIVES + EMPTY_PRIMITIVES
    for primitive_artifact in primitive_artifacts:
        if not isinstance(primitive_artifact, dict):
            raise M050Error("malformed primitive artifact")
        primitive_body = dict(primitive_artifact)
        primitive_digest = primitive_body.pop("digest", None)
        if primitive_digest != _digest(b"m050-primitive-v1\0", primitive_body):
            raise M050Error("primitive artifact digest mismatch")
        matches = [
            primitive for primitive in frozen
            if primitive.family == primitive_body.get("family") and primitive.name == primitive_body.get("name")
        ]
        if len(matches) != 1:
            raise M050Error("primitive is outside the frozen admissible family")
        resolved.append(matches[0])
    pipeline = Pipeline(resolved[0], resolved[1], resolved[2])
    if pipeline not in FROZEN_PIPELINES:
        raise M050Error("pipeline is outside the frozen composition family")
    return pipeline


def independently_validate(composition: Composition, hidden_probes: Iterable[Probe]) -> Validation:
    """Validate a public composition against hidden evidence without adoption authority."""
    hidden = tuple(hidden_probes)
    if composition.status != "composed" or composition.pipeline is None:
        raise M050Error("only a unique composition may be validated")
    if not hidden:
        raise M050Error("independent validation requires hidden probes")
    pipeline = _pipeline_from_artifact(composition.pipeline)
    accepted = all(_matches(pipeline, probe) for probe in hidden)
    hidden_payload = [
        {
            "values": list(probe.values),
            "expected": probe.expected,
            "expects_error": probe.expects_error,
        }
        for probe in hidden
    ]
    composition_digest = _digest(b"m050-composition-v1\0", composition.to_dict())
    hidden_digest = _digest(b"m050-hidden-evidence-v1\0", hidden_payload)
    verdict = {
        "accepted": accepted,
        "composition_digest": composition_digest,
        "hidden_evidence_digest": hidden_digest,
    }
    return Validation(
        accepted=accepted,
        composition_digest=composition_digest,
        hidden_evidence_digest=hidden_digest,
        verdict_digest=_digest(b"m050-validation-v1\0", verdict),
    )


def run_m050_bounded_primitive_composition() -> dict[str, object]:
    """Run positive, ambiguous, and hidden-rejection development episodes."""
    positive_public = (
        Probe((-7, 2, -7), 9),
        Probe((-3, -4), 7),
        Probe((), 0),
    )
    positive_hidden = (
        Probe((-5, 1, -5, 2), 8),
        Probe((0, -2), 2),
    )
    composed = compose_pipeline(positive_public)
    validated = independently_validate(composed, positive_hidden)
    if not validated.accepted:
        raise M050Error("frozen positive episode failed independent validation")

    ambiguous = compose_pipeline((Probe((5,), 5), Probe((), 0)))
    if ambiguous.status != "insufficient_evidence":
        raise M050Error("ambiguous episode did not fail closed")

    misleading = compose_pipeline((Probe((1, 2, 3), 3), Probe((), 0)))
    if misleading.status != "composed":
        raise M050Error("misleading public episode did not produce a unique candidate")
    rejected = independently_validate(misleading, (Probe((-5, -2), -2),))
    if rejected.accepted:
        raise M050Error("hidden contradiction was not rejected")

    manifest = {
        "schema": "m050-manifest-v1",
        "status": "passed_in_development",
        "composition": composed.to_dict(),
        "validation": validated.to_dict(),
        "ambiguous": ambiguous.to_dict(),
        "hidden_rejection": rejected.to_dict(),
        "composition_budget": COMPOSITION_BUDGET,
        "arbitrary_code_generation": False,
        "unknown_runtime_discovery": False,
        "repository_authority": False,
        "network_authority": False,
        "credential_authority": False,
        "deployment_authority": False,
        "canonical": False,
    }
    return {**manifest, "digest": _digest(b"m050-manifest-v1\0", manifest)}


__all__ = [
    "COMPOSITION_BUDGET",
    "Composition",
    "EMPTY_PRIMITIVES",
    "FROZEN_PIPELINES",
    "INPUT_PRIMITIVES",
    "M050Error",
    "Pipeline",
    "Primitive",
    "Probe",
    "REDUCTION_PRIMITIVES",
    "Validation",
    "compose_pipeline",
    "independently_validate",
    "run_m050_bounded_primitive_composition",
]
