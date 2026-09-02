"""The pre-seal scientific-adequacy gate: is this bank one the frozen plan can actually be run on?

M116 moved carrier admission ahead of the seal so that an instrument failure could be described
without spending the reveal. It worked, and it asked the wrong question. M119's completion was
genuinely admissible -- it parsed, it conformed to the frozen output schema, and the frozen host
accepted the enveloped payload -- and it still could not be tested, because *admissible* and
*adequate for the plan's minimum* are different properties and only the first was checked before
the seal. Three carriers cleared the host, none cleared qualification, and the one authorized
reveal was consumed proving it.

This module asks the second question at the same point in the chronology as the first.

## What it computes

Exactly the properties the frozen analysis plan needs before a scientific statistic is possible:

    qualifying carriers                     against the plan's minimum
    distinct qualifying structures          against the plan's minimum
    paired demands the qualifying carriers  against the arithmetic minimum the endpoint's exact
    would yield                             test needs for significance to be attainable at all

If any of them is short, the milestone closes as an instrument failure **before** the seal is
broken. The bank is not filtered, repaired, resampled or regenerated, and no second generation is
drawn: an inadequate bank is a terminal outcome, and the hypothesis stays untested.

## The information boundary, stated so it can be tested

Running the frozen evaluator over carrier content before the seal is only safe if nothing about
that content escapes. Two rules make that mechanical rather than promised:

* **the output allowlist.** `ADEQUACY_FIELDS` is exhaustive and every member is a boolean, a count
  or a name from a fixed vocabulary. `validate_record` refuses a record carrying anything else, so
  a carrier value cannot reach a file, a terminal or a reviewer through this gate.
* **no selection channel.** The gate returns one verdict about the whole bank. It cannot name,
  rank, order, exclude or prefer a carrier, and the caller receives no per-carrier structure to
  act on. `blocking_clause_counts` is a histogram over the frozen clause names, which is the same
  instrument diagnosis M119 published after its reveal -- counts of a fixed vocabulary, with no
  index attached to any of them.

The gate is a predicate over a bank that already exists. It runs once, on the whole bank, and its
only two outcomes are "seal it" and "close the milestone".
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from metamorphosis import carrier_host as host
from metamorphosis import m113_evaluator as evaluator
from metamorphosis import m119_endpoint as endpoint

ADEQUACY_SCHEMA = "m120-preseal-adequacy-v1"
GATE_VERSION = "m120-preseal-adequacy-gate-v1"

# The whole of what this gate may say. Every entry is a boolean, a count, or a histogram over the
# frozen qualification-clause names. No carrier value, digest of a carrier value, index, ordering
# or excerpt appears anywhere in it.
ADEQUACY_FIELDS = (
    "schema",
    "gate_version",
    "adequate",
    "carriers_seen",
    "carriers_accepted_by_the_frozen_host",
    "carriers_refused_by_the_frozen_host",
    "qualifying_carriers",
    "distinct_qualifying_structures",
    "paired_demands_available",
    "minimum_qualifying_carriers",
    "minimum_distinct_qualifying_structures",
    "minimum_paired_demands_for_attainable_significance",
    "blocking_clause_counts",
    "host_refusal_counts",
    "shortfalls",
    "no_carrier_was_selected_filtered_or_reordered",
    "the_gate_returns_one_verdict_over_the_whole_bank",
    "an_inadequate_bank_is_terminal_and_is_never_redrawn",
)

SHORTFALL_QUALIFYING = "fewer qualifying carriers than the plan requires"
SHORTFALL_STRUCTURES = "fewer distinct qualifying structures than the plan requires"
SHORTFALL_DEMANDS = "too few paired demands for the frozen test to attain significance"
SHORTFALLS = (SHORTFALL_QUALIFYING, SHORTFALL_STRUCTURES, SHORTFALL_DEMANDS)


class AdequacyError(RuntimeError):
    """The gate could not be evaluated. Distinct from the gate returning `adequate=False`."""


def evaluate(carriers: Sequence[Any], plan: Mapping[str, Any]) -> dict[str, Any]:
    """One verdict over the whole bank, from the frozen host, evaluator and plan.

    `carriers` are the decoded machines in their original positions. Nothing is skipped: a carrier
    the host would somehow still refuse is counted, exactly as the runner counts it after the
    reveal, so the pre-seal and post-reveal numbers are the same numbers.
    """
    if not isinstance(carriers, Sequence) or isinstance(carriers, (str, bytes)):
        raise AdequacyError("the bank is not a sequence of carriers")
    minimum_carriers = _positive_int(plan, "minimum_qualifying_carriers")
    minimum_structures = _positive_int(plan, "minimum_distinct_qualifying_structures")
    session_budget = _positive_int(plan, "session_budget")

    accepted = 0
    qualifying = 0
    pairs = 0
    signatures: set[str] = set()
    blocking: dict[str, int] = {}
    refusals: dict[str, int] = {}

    for carrier in carriers:
        try:
            validated = host.validate_carrier(carrier)
        except host.CarrierError as exc:
            refusals[str(exc)] = refusals.get(str(exc), 0) + 1
            continue
        accepted += 1
        report = evaluator.qualification_report(validated)
        for clause in report["blocking_clauses"]:
            blocking[clause] = blocking.get(clause, 0) + 1
        if not report["qualifies"]:
            continue
        qualifying += 1
        signatures.add(host.structural_signature(validated))
        # The pair count is a function of the carrier's own attribution census and not of the
        # reference, but the carrier's committed opaque reference is used anyway when it is
        # present, so the count taken here and the count taken after the reveal are taken from
        # exactly the same inputs.
        reference = carrier.get("carrier_ref") if isinstance(carrier, Mapping) else None
        pairs += len(evaluator.derive_demand_pairs(
            validated, str(reference or "opaque-preseal-adequacy"), session_budget))

    # Each demand pair is posed to every arm in both classes, so the paired series the endpoint
    # scores is one entry per pair per class. Derived from the endpoint rather than restated.
    paired_demands = pairs * len(evaluator.DEMAND_CLASSES)
    minimum_paired = endpoint.required_paired_demands()

    shortfalls = []
    if qualifying < minimum_carriers:
        shortfalls.append(SHORTFALL_QUALIFYING)
    if len(signatures) < minimum_structures:
        shortfalls.append(SHORTFALL_STRUCTURES)
    if paired_demands < minimum_paired:
        shortfalls.append(SHORTFALL_DEMANDS)

    return {
        "schema": ADEQUACY_SCHEMA,
        "gate_version": GATE_VERSION,
        "adequate": not shortfalls,
        "carriers_seen": len(carriers),
        "carriers_accepted_by_the_frozen_host": accepted,
        "carriers_refused_by_the_frozen_host": len(carriers) - accepted,
        "qualifying_carriers": qualifying,
        "distinct_qualifying_structures": len(signatures),
        "paired_demands_available": paired_demands,
        "minimum_qualifying_carriers": minimum_carriers,
        "minimum_distinct_qualifying_structures": minimum_structures,
        "minimum_paired_demands_for_attainable_significance": minimum_paired,
        "blocking_clause_counts": dict(sorted(blocking.items())),
        "host_refusal_counts": dict(sorted(refusals.items())),
        "shortfalls": shortfalls,
        "no_carrier_was_selected_filtered_or_reordered": True,
        "the_gate_returns_one_verdict_over_the_whole_bank": True,
        "an_inadequate_bank_is_terminal_and_is_never_redrawn": True,
    }


def _positive_int(plan: Mapping[str, Any], key: str) -> int:
    value = plan.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise AdequacyError("the analysis plan does not carry a usable %s" % key)
    return int(value)


def validate_record(record: Mapping[str, Any]) -> None:
    """Fail closed on an adequacy record that is not the frozen shape.

    This is the enforcement of the information boundary, not a description of it: a record that has
    grown a field is refused rather than published, whatever that field turned out to hold.
    """
    if not isinstance(record, Mapping) or record.get("schema") != ADEQUACY_SCHEMA:
        raise AdequacyError("adequacy record schema is not the declared one")
    unexpected = sorted(set(record) - set(ADEQUACY_FIELDS))
    if unexpected:
        raise AdequacyError("adequacy record carries fields outside the allowlist: %s"
                            % ", ".join(unexpected))
    missing = sorted(set(ADEQUACY_FIELDS) - set(record))
    if missing:
        raise AdequacyError("adequacy record omits allowlisted fields: %s" % ", ".join(missing))
    unknown = sorted(set(record.get("shortfalls") or ()) - set(SHORTFALLS))
    if unknown:
        raise AdequacyError("adequacy record names a shortfall outside the frozen vocabulary: %s"
                            % ", ".join(unknown))
    if bool(record.get("adequate")) == bool(record.get("shortfalls")):
        raise AdequacyError("the adequacy verdict disagrees with its own shortfall list")
    clauses = record.get("blocking_clause_counts")
    if not isinstance(clauses, Mapping):
        raise AdequacyError("the blocking-clause histogram is not an object")
    for name, count in clauses.items():
        if not isinstance(name, str) or isinstance(count, bool) or not isinstance(count, int):
            raise AdequacyError("the blocking-clause histogram is not a name-to-count mapping")


def binding_matches(preseal: Mapping[str, Any],
                    postreveal: Mapping[str, Any]) -> tuple[bool, list[str]]:
    """Do the pre-seal gate and the post-reveal recomputation agree on every counted field?

    The gate runs on the bank before the seal and the runner measures the same bank after the
    reveal. If those two disagree, something between them changed the bank, and that is a terminal
    instrument failure rather than a discrepancy to reconcile.
    """
    validate_record(preseal)
    validate_record(postreveal)
    bound = ("gate_version", "adequate", "carriers_seen",
             "carriers_accepted_by_the_frozen_host", "carriers_refused_by_the_frozen_host",
             "qualifying_carriers", "distinct_qualifying_structures",
             "paired_demands_available", "minimum_qualifying_carriers",
             "minimum_distinct_qualifying_structures",
             "minimum_paired_demands_for_attainable_significance")
    differences = [name for name in bound if preseal.get(name) != postreveal.get(name)]
    return not differences, differences


__all__ = [
    "ADEQUACY_FIELDS",
    "ADEQUACY_SCHEMA",
    "GATE_VERSION",
    "SHORTFALLS",
    "AdequacyError",
    "binding_matches",
    "evaluate",
    "validate_record",
]
