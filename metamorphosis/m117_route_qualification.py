"""M117 Stage 1: which endpoint, if any, may generate the H62 carrier bank.

M116 ended because its fixed route enforced none of the nine schema feature classes the frozen
carrier schema relies upon, while the provider catalogue declared `supports_structured_outputs:
true` for it. That is the fact this module is built around:

    **A catalogue claim is not evidence. Only measured enforcement is.**

So eligibility here is a filter on what a candidate *claims*, used only to bound a budget, and
qualification is decided exclusively by what a candidate *does* under the inherited M116 capability
matrix. A route that advertises everything and enforces nothing fails, exactly as M116's did.

Everything in this module is a pure function of committed evidence. It performs no I/O, makes no
network request, and cannot select a route by any input other than the frozen rule.

## Why "first qualifier in the frozen order" is the whole selection algorithm

Candidates are totally ordered before any is probed, by the reliability ordering inherited from
M115 and fixed since before that milestone's first matrix. Selection is then: probe in that order,
and take the first candidate that qualifies. Because the order is fixed in advance and independent
of every observation, the first qualifier *is* the best-ordered qualifier -- there is no version of
this rule under which continuing to probe could produce a better answer, and none under which an
observation can change who is next. It also spends the smallest budget consistent with the rule.

The property that matters: nothing observed about a candidate can change the order, the threshold,
or which candidate is considered next.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence

QUALIFICATION_SCHEMA = "m117-route-qualification-v1"
UNIVERSE_SCHEMA = "m117-candidate-universe-v1"
SELECTION_SCHEMA = "m117-route-selection-v1"

# Inherited from M115 unchanged, where it was committed before that milestone's first matrix and
# has never been re-derived. Reusing it verbatim is deliberate: an ordering rewritten for M117
# could be rewritten to put a preferred provider first.
RELIABILITY_ORDERING = (
    "uptime_last_1d_desc",
    "uptime_last_30m_desc",
    "latency_last_30m_p50_asc",
    "provider_name_asc",
)

# Metrics every candidate must report completely. A candidate missing any of them is ineligible
# rather than ranked with a default, because a default would be a value we chose.
REQUIRED_METRICS = ("uptime_last_1d", "uptime_last_30m", "latency_last_30m_p50")

# Eligibility bounds a budget; it never qualifies anything.
MINIMUM_UPTIME_LAST_1D = 99.0
MINIMUM_UPTIME_LAST_30M = 95.0
MINIMUM_MAX_COMPLETION_TOKENS = 32768
REQUIRED_SUPPORTED_PARAMETERS = ("response_format", "structured_outputs", "seed")

# Budget. Fixed before the first request; exceeding it ends Stage 1 without a selection rather
# than being widened.
MAX_REQUESTS_PER_PROBE = 3
MAX_REQUESTS_PER_CANDIDATE = 40
GLOBAL_REQUEST_CEILING = 160

EXCLUSION_REASONS = (
    "missing_required_metric",
    "uptime_last_1d_below_minimum",
    "uptime_last_30m_below_minimum",
    "max_completion_tokens_below_minimum",
    "missing_supported_parameter",
    "no_canonical_checkpoint_declared",
    "endpoint_not_available",
)


class RouteQualificationError(RuntimeError):
    """Stage 1 cannot proceed without guessing. Every path fails closed."""


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def metrics_of(candidate: Mapping[str, Any]) -> dict[str, float | None]:
    latency = candidate.get("latency_last_30m")
    latency = latency if isinstance(latency, Mapping) else {}
    return {
        "uptime_last_1d": _number(candidate.get("uptime_last_1d")),
        "uptime_last_30m": _number(candidate.get("uptime_last_30m")),
        "latency_last_30m_p50": _number(latency.get("p50")),
    }


def eligibility(candidate: Mapping[str, Any]) -> dict[str, Any]:
    """Is this catalogue entry eligible to *spend budget on*? Never whether it qualifies."""
    reasons: list[str] = []
    observed = metrics_of(candidate)

    if candidate.get("provider_found") is not True or candidate.get("endpoint_available") is not True:
        reasons.append("endpoint_not_available")
    for name in REQUIRED_METRICS:
        if observed[name] is None:
            reasons.append("missing_required_metric")
            break
    if observed["uptime_last_1d"] is not None and observed["uptime_last_1d"] < MINIMUM_UPTIME_LAST_1D:
        reasons.append("uptime_last_1d_below_minimum")
    if observed["uptime_last_30m"] is not None and observed["uptime_last_30m"] < MINIMUM_UPTIME_LAST_30M:
        reasons.append("uptime_last_30m_below_minimum")

    tokens = _number(candidate.get("max_completion_tokens"))
    if tokens is None or tokens < MINIMUM_MAX_COMPLETION_TOKENS:
        reasons.append("max_completion_tokens_below_minimum")

    supported = candidate.get("supported_parameters")
    supported = set(supported) if isinstance(supported, Sequence) and not isinstance(
        supported, (str, bytes)) else set()
    if not set(REQUIRED_SUPPORTED_PARAMETERS) <= supported:
        reasons.append("missing_supported_parameter")

    # The identity rule, generalized from M115 without special-casing its model: the catalogue must
    # declare the exact checkpoint the endpoint serves, so a runtime substitution is detectable.
    if not isinstance(candidate.get("canonical_checkpoint"), str) or not candidate["canonical_checkpoint"]:
        reasons.append("no_canonical_checkpoint_declared")

    ordered = sorted(set(reasons))
    for reason in ordered:
        if reason not in EXCLUSION_REASONS:
            raise RouteQualificationError("unknown exclusion reason %r" % reason)
    return {"eligible": not ordered, "exclusions": ordered, "metrics": observed}


def rank_key(candidate: Mapping[str, Any]) -> tuple[float, float, float, str, str]:
    """The frozen total order. Fixed before any candidate is probed."""
    observed = metrics_of(candidate)
    missing = [name for name in REQUIRED_METRICS if observed[name] is None]
    if missing:
        raise RouteQualificationError(
            "cannot rank a candidate missing %s" % ", ".join(missing))
    return (
        -observed["uptime_last_1d"],       # uptime_last_1d_desc
        -observed["uptime_last_30m"],      # uptime_last_30m_desc
        observed["latency_last_30m_p50"],  # latency_last_30m_p50_asc
        str(candidate.get("provider") or ""),   # provider_name_asc  (tie-break)
        str(candidate.get("model") or ""),      # total order even on identical providers
    )


def derive_universe(catalogue: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """The complete candidate universe and its frozen order, from the catalogue snapshot alone."""
    entries = list(catalogue)
    assessed: list[dict[str, Any]] = []
    for entry in entries:
        verdict = eligibility(entry)
        assessed.append({
            "model": entry.get("model"),
            "provider": entry.get("provider"),
            "canonical_checkpoint": entry.get("canonical_checkpoint"),
            "eligible": verdict["eligible"],
            "exclusions": verdict["exclusions"],
            "metrics": verdict["metrics"],
            "max_completion_tokens": entry.get("max_completion_tokens"),
        })
    eligible = [item for item in assessed if item["eligible"]]
    ordered = sorted(eligible, key=lambda item: rank_key(
        {**item, "latency_last_30m": {"p50": item["metrics"]["latency_last_30m_p50"]},
         "uptime_last_1d": item["metrics"]["uptime_last_1d"],
         "uptime_last_30m": item["metrics"]["uptime_last_30m"]}))
    for position, item in enumerate(ordered, start=1):
        item["order"] = position
    return {
        "schema": UNIVERSE_SCHEMA,
        "catalogue_entries": len(entries),
        "assessed": assessed,
        "eligible_count": len(eligible),
        "ordered_candidates": ordered,
        "ordering": list(RELIABILITY_ORDERING),
        "eligibility_bounds_budget_never_qualifies": True,
        "minimum_uptime_last_1d": MINIMUM_UPTIME_LAST_1D,
        "minimum_uptime_last_30m": MINIMUM_UPTIME_LAST_30M,
        "minimum_max_completion_tokens": MINIMUM_MAX_COMPLETION_TOKENS,
        "required_supported_parameters": list(REQUIRED_SUPPORTED_PARAMETERS),
    }


def qualifies(profile: Mapping[str, Any]) -> dict[str, Any]:
    """Does one probed candidate qualify? Every clause must hold; partial capability is not
    qualification."""
    required = list(profile.get("required_feature_classes") or ())
    unenforced = sorted(profile.get("unenforced_feature_classes") or ())
    checks = {
        "every_required_feature_class_enforced": bool(required) and not unenforced,
        "combined_structural_test_holds": profile.get("combined_probe_conforms") is True,
        "token_capacity_stress_holds": profile.get("token_capacity_holds") is True,
        "requested_model_identity_exact": profile.get("requested_model_exact") is True,
        "canonical_checkpoint_exact": profile.get("canonical_checkpoint_exact") is True,
        "provider_exact": profile.get("provider_exact") is True,
        "direct_route": profile.get("router_direct") is True,
        "no_fallback": profile.get("router_no_fallback") is True,
        "one_selected_endpoint": profile.get("router_one_endpoint") is True,
        "one_router_attempt": profile.get("router_one_attempt") is True,
        "no_pipeline_intervention": profile.get("router_no_pipeline_intervention") is True,
        "reliability_minimum_holds": profile.get("reliability_minimum_holds") is True,
    }
    return {
        "schema": QUALIFICATION_SCHEMA,
        "qualifies": all(checks.values()),
        "checks": checks,
        "unenforced_feature_classes": unenforced,
        "failed_checks": sorted(name for name, held in checks.items() if not held),
    }


def select(universe: Mapping[str, Any], profiles: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Compute the selection from the frozen order and the recorded qualifications alone.

    The first qualifier in the frozen order is the selection, because the order was fixed before
    any observation and no observation can change it.
    """
    ordered = list(universe.get("ordered_candidates") or [])
    by_key = {(p.get("model"), p.get("provider")): p for p in profiles}
    selected = None
    for item in ordered:
        profile = by_key.get((item.get("model"), item.get("provider")))
        if profile is None:
            break  # not reached under the frozen budget; nothing after it was probed either
        if profile.get("incomplete"):
            continue
        # Recomputed here rather than read from the profile. A recorded verdict is a claim, and the
        # point of decision should rest on the evidence rather than on what the record says about
        # it -- otherwise a profile asserting `qualifies: true` would select a route that never
        # passed a single check.
        if qualifies(profile)["qualifies"] is True:
            selected = item
            break
    return {
        "schema": SELECTION_SCHEMA,
        "ordering": list(RELIABILITY_ORDERING),
        "selection_rule": "first qualifying candidate in the frozen reliability order",
        "candidates_probed": len(profiles),
        "selected": ({"model": selected.get("model"), "provider": selected.get("provider"),
                      "canonical_checkpoint": selected.get("canonical_checkpoint"),
                      "order": selected.get("order")} if selected else None),
        "route_selected": selected is not None,
        "carrier_quality_was_an_input": False,
        "qualification_recomputed_at_selection": True,
        "selection_depends_only_on_frozen_order_and_qualification": True,
    }


__all__ = [
    "EXCLUSION_REASONS",
    "GLOBAL_REQUEST_CEILING",
    "MAX_REQUESTS_PER_CANDIDATE",
    "MAX_REQUESTS_PER_PROBE",
    "MINIMUM_MAX_COMPLETION_TOKENS",
    "MINIMUM_UPTIME_LAST_1D",
    "MINIMUM_UPTIME_LAST_30M",
    "QUALIFICATION_SCHEMA",
    "RELIABILITY_ORDERING",
    "REQUIRED_METRICS",
    "REQUIRED_SUPPORTED_PARAMETERS",
    "RouteQualificationError",
    "SELECTION_SCHEMA",
    "UNIVERSE_SCHEMA",
    "derive_universe",
    "eligibility",
    "metrics_of",
    "qualifies",
    "rank_key",
    "select",
]
