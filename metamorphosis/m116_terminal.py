"""Deterministic terminal-failure classification for a future H61 attempt.

M115 diagnosed its own terminal failure by matching the text of a Python exception. That worked in
the sense that it produced a label, and failed in the sense that the label carried no information:
`invalid_json` meant "`json.loads` raised", which a truncated completion, a prose-prefixed
completion and a fenced completion all produce identically. The frozen M115 plan even enumerated
`truncated_completion` as a distinct class -- and no code path in the repository could ever assign
it.

This classifier is a pure function of preserved, non-carrier structured evidence. It is
independently replayable from the committed record, it never reads carrier content, and it refuses
to guess: every class requires affirmative evidence, and anything else falls closed into
`unclassified_terminal` rather than being rounded to the nearest plausible story.

In particular `truncated_completion` requires a finish reason in the frozen output-budget set. A
parse failure on its own is *never* enough to conclude truncation -- that inference is exactly the
one M115's record cannot support, and this module must not make it easy to make.
"""

from __future__ import annotations

from typing import Any, Mapping

from metamorphosis import m116_telemetry as telemetry

CLASSIFIER_VERSION = "m116-terminal-classifier-v1"
CLASSIFICATION_SCHEMA = "m116-terminal-classification-v1"

# Ordered by precedence. The first class whose affirmative evidence is present wins, and the order
# is part of the frozen contract: an attempt that is both a transport ambiguity and a 429 is an
# ambiguity, because the conservative reading is the one that forbids a retry.
TERMINAL_CLASSES = (
    "ambiguous_transport",
    "pre_generation_429",
    "provider_or_route_failure",
    "runtime_identity_failure",
    "missing_completion",
    "refused_completion",
    "truncated_completion",
    "invalid_json",
    "output_schema_violation",
    "post_validation_failure",
    "unclassified_terminal",
)

# The one class that is not an observation but a verdict about our own machinery: the pre-seal
# admission record and the post-reveal recomputation disagreed.
BINDING_FAILURE = "post_validation_failure"

# Classes from which a physical retry may be permitted, subject to the inherited delivery rule.
# Deliberately a single member: an explicit capacity rejection carrying no completion and no
# evidence that the model ran. Everything else is terminal on its first outcome.
RETRYABLE_CLASSES = frozenset({"pre_generation_429"})


class ClassificationError(RuntimeError):
    """The evidence offered is not the frozen evidence shape."""


def _bool(value: Any) -> bool:
    return value is True


def classify(
    record: Mapping[str, Any],
    *,
    admission: Mapping[str, Any] | None = None,
    binding_mismatch: bool = False,
) -> dict[str, Any]:
    """Classify one terminal attempt from telemetry plus, if it got that far, the admission record.

    `record` is a validated telemetry projection. `admission` is the pre-seal admission record when
    a completion reached the validator, and None when it did not. Neither carries carrier content.
    """
    telemetry.validate(record)
    if admission is not None and not isinstance(admission, Mapping):
        raise ClassificationError("admission evidence is not an object")

    reasons: list[str] = []

    def decide(name: str, why: str) -> dict[str, Any]:
        if name not in TERMINAL_CLASSES:
            raise ClassificationError("unknown terminal class %r" % name)
        return {
            "schema": CLASSIFICATION_SCHEMA,
            "classifier_version": CLASSIFIER_VERSION,
            "terminal_class": name,
            "because": why,
            "retry_permitted_by_class": name in RETRYABLE_CLASSES,
            "evidence_considered": sorted(reasons),
        }

    status = record.get("http_status")
    finish = record.get("finish_reason")
    execution = _bool(record.get("model_execution_evidence"))
    reasons += ["http_status", "finish_reason", "model_execution_evidence"]

    # 1. The binding verdict outranks every observation: if pre-seal and post-reveal disagree, what
    #    the endpoint did stops being the question.
    if binding_mismatch:
        return decide(BINDING_FAILURE,
                      "the pre-seal admission record and the post-reveal recomputation disagree")

    # 2. Transport ambiguity. We could not establish what the endpoint did, so we must not retry.
    if record.get("transport_failure_class") is not None or status is None:
        reasons.append("transport_failure_class")
        return decide("ambiguous_transport",
                      "the attempt did not establish a response from the endpoint")

    # 3. The single retryable class, and it requires all three of its conditions affirmatively.
    if int(status) == 429 and not execution and not _bool(record.get("content_present")):
        return decide("pre_generation_429",
                      "explicit capacity rejection carrying no completion and no execution evidence")

    # 4. Any other non-success status is the route or provider failing, terminally.
    if int(status) != 200:
        return decide("provider_or_route_failure",
                      "the endpoint returned a terminal non-success status")

    # 5. A 200 whose attested identity does not hold is not an observation about carriers.
    identity_checks = (
        "canonical_checkpoint_attested", "router_direct", "router_no_fallback",
        "router_one_endpoint", "router_one_attempt", "router_no_pipeline_intervention",
    )
    reasons += list(identity_checks)
    if not all(_bool(record.get(name)) for name in identity_checks):
        return decide("runtime_identity_failure",
                      "the served route or checkpoint did not match the frozen identity")

    # 6. A structurally reported refusal, before any question about parsing.
    reasons.append("refusal_present")
    if _bool(record.get("refusal_present")):
        return decide("refused_completion",
                      "the endpoint structurally reported a refusal or content filter")

    # 7. No completion at all.
    reasons.append("content_present")
    if not _bool(record.get("content_present")):
        return decide("missing_completion", "the response carried no completion content")

    # 8. Output-budget termination, and only on affirmative finish-reason evidence. This must be
    #    decided BEFORE parsing, because a truncated completion also fails to parse and the parse
    #    failure would otherwise absorb it -- which is precisely M115's defect.
    if finish is not None and finish in telemetry.BUDGET_FINISH_REASONS:
        return decide("truncated_completion",
                      "the frozen finish-reason semantics report output-budget termination")

    # 9. From here on the completion exists and did not stop for budget, so admission evidence is
    #    required. Without it we cannot say anything, and we say so.
    if admission is None:
        return decide("unclassified_terminal",
                      "a completion exists but no admission evidence was preserved")
    reasons += ["admission.parsed", "admission.schema_valid"]

    if not _bool(admission.get("parsed")):
        # A parse failure at a completed finish reason is genuinely invalid JSON: prose, a fence,
        # a stray prefix. At an unknown finish reason it is not attributable, and falls closed.
        if finish is not None and finish in telemetry.COMPLETED_FINISH_REASONS:
            return decide("invalid_json",
                          "the endpoint reported a completed generation whose content is not JSON")
        return decide("unclassified_terminal",
                      "content did not parse and no frozen finish-reason semantics apply")

    if not _bool(admission.get("schema_valid")):
        return decide("output_schema_violation",
                      "the completion parsed but does not satisfy the frozen carrier schema")

    if not _bool(admission.get("payload_admissible")):
        return decide("output_schema_violation",
                      "the enveloped payload was refused by the frozen carrier host contract")

    return decide("unclassified_terminal",
                  "no frozen terminal condition matched the preserved evidence")


__all__ = [
    "BINDING_FAILURE",
    "CLASSIFICATION_SCHEMA",
    "CLASSIFIER_VERSION",
    "ClassificationError",
    "RETRYABLE_CLASSES",
    "TERMINAL_CLASSES",
    "classify",
]
