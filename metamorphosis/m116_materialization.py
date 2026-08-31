"""The one-shot rule: when the H61 generation opportunity is consumed, and what may follow.

This module exists to make one sentence mechanical.

    The first completion carrying evidence of model execution consumes the scientific generation
    opportunity.

Everything else follows from it. If pre-seal admission then fails, there is no second completion,
no redraw, no repair and no bank: the milestone ends `instrument-aborted`. If admission succeeds,
that exact completion is the one admissible materialization, bound by digest and sealed before any
human sees it.

"First schema-valid completion wins" is forbidden, and the reason is not squeamishness. Whether a
completion parses is a function of its content: a long, varied, structurally rich carrier family is
the one that exhausts an output budget or stresses a constrained decoder, and a short, repetitive
one completes cleanly. Redrawing on a parse failure would therefore filter the carrier population
toward smaller and simpler families -- the very axis that decides how hard the derived demands are,
and it would do so with no human ever looking at anything. The bias runs toward the hypothesis.

A physical retry survives only where it is provably independent of content: an explicit
pre-generation capacity rejection carrying no completion and no evidence that the model ran.
"""

from __future__ import annotations

from typing import Any, Mapping

from metamorphosis import m116_admission as admission
from metamorphosis import m116_telemetry as telemetry
from metamorphosis import m116_terminal as terminal

DECISION_SCHEMA = "m116-materialization-decision-v1"
MAX_BANK_MATERIALIZATIONS = 1


class MaterializationError(RuntimeError):
    """The decision cannot be made from the evidence offered."""


def opportunity_consumed(record: Mapping[str, Any]) -> bool:
    """Did this attempt consume the one scientific generation opportunity?

    Any evidence that the model executed consumes it -- a completion, a token count, a finish
    reason, or a generation identifier. Absence of a completion is not absence of execution.
    """
    telemetry.validate(record)
    return bool(
        record.get("model_execution_evidence")
        or record.get("content_present")
        or record.get("generation_id") is not None
        or (record.get("completion_tokens") or 0) > 0
        or record.get("finish_reason") is not None
    )


def decide(
    record: Mapping[str, Any],
    admission_record: Mapping[str, Any] | None,
    *,
    binding_mismatch: bool = False,
) -> dict[str, Any]:
    """Decide what one delivery attempt means for the bank, the budget and any further attempt."""
    telemetry.validate(record)
    if admission_record is not None:
        admission.validate_record(admission_record)

    classification = terminal.classify(
        record, admission=admission_record, binding_mismatch=binding_mismatch
    )
    consumed = opportunity_consumed(record)
    terminal_class = classification["terminal_class"]

    # A retry is permitted only when the class allows it AND nothing suggests the model ran. The
    # conjunction is deliberate: the class is about what the endpoint said, and consumption is
    # about what it did. Either one alone is not enough to authorize a second physical attempt.
    physical_retry_permitted = bool(
        classification["retry_permitted_by_class"] and not consumed
    )
    admitted = bool(admission_record is not None and admission_record.get("admitted"))

    decision = {
        "schema": DECISION_SCHEMA,
        "terminal_class": terminal_class,
        "classifier_version": terminal.CLASSIFIER_VERSION,
        "scientific_opportunity_consumed": consumed,
        "physical_retry_permitted": physical_retry_permitted,
        # The three prohibitions, stated as data so a checker can read them off the record.
        "content_dependent_redraw_permitted": False,
        "repair_permitted": False,
        "selection_among_completions_permitted": False,
        "bank_materialized": admitted,
        "may_seal": admitted,
        "verdict": "materialized" if admitted else "instrument-aborted",
        "hypothesis_status": "pending" if admitted else "untested",
    }
    if admitted and consumed is False:
        raise MaterializationError(
            "a completion was admitted without evidence that the model executed"
        )
    return decision


def assert_no_redraw_after(decision: Mapping[str, Any]) -> None:
    """Fail closed if anything tries to draw again after a content-dependent failure."""
    if not isinstance(decision, Mapping) or decision.get("schema") != DECISION_SCHEMA:
        raise MaterializationError("decision record schema is not the declared one")
    if decision.get("scientific_opportunity_consumed") and decision.get(
        "physical_retry_permitted"
    ):
        raise MaterializationError(
            "the scientific opportunity is consumed; no further physical attempt is permitted"
        )


__all__ = [
    "DECISION_SCHEMA",
    "MAX_BANK_MATERIALIZATIONS",
    "MaterializationError",
    "assert_no_redraw_after",
    "decide",
    "opportunity_consumed",
]
