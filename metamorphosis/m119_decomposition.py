"""What a positive H64 may be said to show, computed from the four arms.

                     policy absent      policy present
    cascade absent    FRESH              POLICY_ONLY
    cascade present   CASCADE_ONLY       FULL

The interpretation is preregistered and computed, so the strongest supportable statement is decided
by the arms rather than by whoever writes the summary.
"""

from __future__ import annotations

from typing import Any, Mapping

from metamorphosis import m119_endpoint as endpoint

DECOMPOSITION_VERSION = "m119-decomposition-v1"
CONTRIBUTION_MARGIN = 0.10


def decompose(rates: Mapping[str, float | None], *, verdict: str,
              margin: float = CONTRIBUTION_MARGIN) -> dict[str, Any]:
    full, fresh = rates.get("FULL"), rates.get("FRESH")
    cascade_only, policy_only = rates.get("CASCADE_ONLY"), rates.get("POLICY_ONLY")

    def exceeds(a: float | None, b: float | None) -> bool | None:
        return None if a is None or b is None else (a - b) >= margin

    contrasts = {
        "full_over_fresh": exceeds(full, fresh),
        "cascade_only_over_fresh": exceeds(cascade_only, fresh),
        "policy_only_over_fresh": exceeds(policy_only, fresh),
        "full_over_cascade_only": exceeds(full, cascade_only),
        "full_over_policy_only": exceeds(full, policy_only),
    }

    if verdict not in endpoint.VERDICTS:
        # A verdict this module does not know is not a licence to describe the arms. The names are
        # imported from the endpoint rather than re-spelled here precisely so a rename cannot make
        # an aborted run fall through into a causal statement.
        raise ValueError("unknown H64 verdict %r" % verdict)
    if any(rate is None for rate in (full, fresh, cascade_only, policy_only)) and verdict in (
            endpoint.POSITIVE, endpoint.NEGATIVE):
        raise ValueError(
            "a %s verdict cannot be decomposed while an arm has no rate" % verdict)
    if verdict == endpoint.INSTRUMENT_ABORTED:
        statement = ("H64 was not validly tested. No causal claim is available, and this is not "
                     "evidence against the hypothesis.")
    elif verdict == endpoint.INCONCLUSIVE:
        statement = ("H64 is inconclusive: significance was not arithmetically attainable on this "
                     "bank. This is not evidence against the hypothesis.")
    elif verdict == endpoint.NEGATIVE:
        statement = ("H64 is negative: FULL did not exceed FRESH under the frozen criterion. No "
                     "causal claim about acquired machinery is supported.")
    elif not contrasts["full_over_policy_only"] and contrasts["policy_only_over_fresh"]:
        statement = ("The effect is not attributable to the acquired cascade: POLICY_ONLY "
                     "reproduces FULL's advantage over FRESH.")
    elif not contrasts["full_over_cascade_only"] and contrasts["cascade_only_over_fresh"]:
        statement = ("No incremental contribution from the diagnostic policy is supported: "
                     "CASCADE_ONLY reproduces FULL's advantage over FRESH.")
    elif contrasts["full_over_cascade_only"] and contrasts["full_over_policy_only"]:
        statement = ("FULL exceeds both single-factor arms, supporting a combined contribution "
                     "from the acquired cascade and the acquired diagnostic policy.")
    else:
        statement = ("FULL exceeds FRESH, but no factorial contrast isolates a unique mechanism. "
                     "Report the combined effect without attributing it to a component.")

    return {
        "schema": "m119-decomposition-v1",
        "version": DECOMPOSITION_VERSION,
        "margin": margin,
        "rates": dict(rates),
        "contrasts": contrasts,
        "strongest_supported_statement": statement,
        "never_supported_by_this_design": [
            "provider invariance: H64 runs one fixed route",
            "generality beyond the carrier family this project's meta-schema defines",
        ],
    }
