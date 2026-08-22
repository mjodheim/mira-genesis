"""M097 endogenous acquisition from the frozen symbolic assembly substrate."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Mapping, Sequence

from metamorphosis.m097_language import (
    ExpressionDefinition,
    candidate_definitions,
    digest,
)
from metamorphosis.m097_validator import validate

ACQUISITION_SCHEMA = "m097-acquisition-v1"


@dataclass(frozen=True)
class Acquisition:
    candidates_assembled: int
    candidates_well_formed: int
    accepted_candidates: int
    rejection_counts: dict[str, int]
    adopted: ExpressionDefinition | None

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": ACQUISITION_SCHEMA,
            "candidates_assembled": self.candidates_assembled,
            "candidates_well_formed": self.candidates_well_formed,
            "accepted_candidates": self.accepted_candidates,
            "rejection_counts": dict(sorted(self.rejection_counts.items())),
            "adopted": self.adopted.to_dict() if self.adopted else None,
            "adopted_operation_id": self.adopted.operation_id if self.adopted else None,
        }


def acquire(public_cases: Sequence[Mapping[str, int | float]]) -> Acquisition:
    assembled = 0
    well_formed = 0
    rejected: Counter[str] = Counter()
    accepted: list[ExpressionDefinition] = []
    for definition in candidate_definitions():
        assembled += 1
        validation = validate(definition, public_cases)
        if validation.expression is not None:
            well_formed += 1
        if validation.accepted:
            accepted.append(definition)
        else:
            rejected[validation.reason] += 1
    # Minimal accepted construction first; digest is a content-addressed tie-break, not a
    # target-specific preference. The full accepted set is still counted.
    accepted.sort(key=lambda item: (len(item.body), digest(item.to_dict())))
    return Acquisition(
        candidates_assembled=assembled,
        candidates_well_formed=well_formed,
        accepted_candidates=len(accepted),
        rejection_counts=dict(rejected),
        adopted=accepted[0] if accepted else None,
    )


__all__ = ["ACQUISITION_SCHEMA", "Acquisition", "acquire"]
