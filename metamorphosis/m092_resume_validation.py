"""Canonical resume validation for the frozen M092 criterion search.

Serialized M092 criterion states contain SHA-256 integrity checks, not signatures.  Canonical resume
therefore treats a supplied state only as a cache of a deterministic search prefix: the complete
claimed prefix is replayed from genesis under the frozen theorem and implementation bindings and
must reproduce the supplied serialized state exactly before search may continue.

This module imports no qualification material and never executes a candidate for selection.
"""
from __future__ import annotations

from typing import Mapping

from metamorphosis.m092_criterion_search import CriterionSearchState, advance_search


class ResumeValidationError(ValueError):
    """A supplied criterion state is not the exact deterministic prefix it claims to be."""


def verified_resume_state(
    raw_state: Mapping[str, object],
    requirement: Mapping[str, object],
) -> CriterionSearchState:
    """Validate internal integrity and replay the complete claimed prefix from genesis."""

    supplied = CriterionSearchState.from_dict(raw_state)
    replayed = advance_search(
        CriterionSearchState.fresh(requirement),
        requirement,
        program_limit=supplied.generated_programs,
    )
    if replayed.to_dict() != supplied.to_dict():
        raise ResumeValidationError(
            "resume state does not match deterministic replay from the frozen M092 criterion genesis"
        )
    return supplied


__all__ = ["ResumeValidationError", "verified_resume_state"]
