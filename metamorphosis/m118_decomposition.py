"""What a positive H63 may actually be said to show, from the factorial arms.

A verdict is not a mechanism. The 2x2 exists so that "the descendant beat the comparator" can be
resolved into *which part* of the acquired machinery carried it:

                     policy absent        policy present
    rules absent      fresh_uniform        probe_only
    rules present     M2                   M3

The rules below are the owner's claim-discipline specification, implemented rather than left to
prose, so the strongest supportable statement is computed from the arms instead of chosen by
whoever writes the summary.
"""

from __future__ import annotations

from typing import Any, Mapping

DECOMPOSITION_VERSION = "m118-decomposition-v1"

# A difference smaller than this is not treated as a contribution. It is the same margin the
# primary endpoint uses, so "adds nothing" means the same thing everywhere.
CONTRIBUTION_MARGIN = 0.10


def _rate(successes: int, total: int) -> float | None:
    return None if not total else successes / total


def decompose(rates: Mapping[str, float | None], *, positive: bool,
              margin: float = CONTRIBUTION_MARGIN) -> dict[str, Any]:
    """The strongest causal statement the arms support, and the ones they do not.

    `rates` maps arm name to primary-endpoint success rate.
    """
    m3 = rates.get("M3")
    m2 = rates.get("M2")
    probe_only = rates.get("probe_only")
    fresh = rates.get("fresh_uniform")
    t0 = rates.get("T0")
    probe_budget = rates.get("probe_only_budget_plus")

    def better(a: float | None, b: float | None) -> bool | None:
        return None if a is None or b is None else (a - b) >= margin

    beats_fresh = better(m3, fresh)
    beats_t0 = better(m3, t0)
    beats_probe_only = better(m3, probe_only)
    beats_m2 = better(m3, m2)
    probe_alone_beats_fresh = better(probe_only, fresh)
    rules_alone_beat_fresh = better(m2, fresh)
    budget_rescues_probe = better(probe_budget, probe_only)

    if not positive:
        statement = ("H63 is negative: the primary criterion or a no-harm guard did not hold. "
                     "No causal claim about acquired machinery is supported.")
    elif beats_fresh is False:
        statement = ("H63 is negative against the designated comparator, whatever the legacy "
                     "arm shows.")
    elif beats_probe_only is False and probe_alone_beats_fresh:
        statement = ("Evidence favours the diagnostic policy and probe pathway, NOT the acquired "
                     "rule cascade: probe_only reproduces the descendant's advantage.")
    elif beats_probe_only and beats_m2:
        statement = ("Evidence supports an additional contribution from the combined acquired "
                     "machinery: the descendant exceeds both the rules-only and the probe-only "
                     "ablation.")
    elif rules_alone_beat_fresh and beats_m2 is False:
        statement = ("Evidence supports the acquired cascade but not an incremental benefit from "
                     "the diagnostic policy: the descendant does not exceed the rules-only arm.")
    else:
        statement = ("The advantage is not resolved to a component by these arms; report the "
                     "decomposition rather than a mechanism.")

    return {
        "schema": "m118-decomposition-v1",
        "version": DECOMPOSITION_VERSION,
        "margin": margin,
        "rates": dict(rates),
        "descendant_beats_designated_fresh_comparator": beats_fresh,
        "descendant_beats_legacy_t0": beats_t0,
        "descendant_beats_probe_only": beats_probe_only,
        "descendant_beats_rules_only_m2": beats_m2,
        "probe_only_beats_fresh": probe_alone_beats_fresh,
        "rules_only_beats_fresh": rules_alone_beat_fresh,
        "extra_budget_rescues_probe_only": budget_rescues_probe,
        "beating_t0_alone_is_not_evidence": True,
        "strongest_supported_statement": statement,
        "unsupported_without_further_arms": [
            "any claim that the acquired rule cascade carried the result when probe_only "
            "reproduces it",
            "any claim of an incremental diagnostic-policy benefit when the descendant does not "
            "exceed the rules-only arm",
            "any claim of provider invariance: H63 runs one fixed route",
        ],
    }


def rates_from_outcomes(outcomes: Mapping[str, list[bool]]) -> dict[str, float | None]:
    return {arm: _rate(sum(1 for x in series if x), len(series))
            for arm, series in outcomes.items()}
