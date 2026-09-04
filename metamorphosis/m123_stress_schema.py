"""M122's stress schema, unchanged in shape, sized from two measurements instead of one.

M122 closed at `not_ready_stress` on a completion that conformed: 30,957 tokens against a 32,000
threshold, short by 3.3%. Nine of nine capability probes had passed. The contract was fine. The
stress size was not, and it was wrong twice for two different reasons:

* **inherited** — `STATIONS = 24` came from M120 while the schema underneath was being flattened
  from eight array-of-object levels to five, and a shallower station serialises smaller;
* **extrapolated** — the replacement was derived from a *single* observation, 546.6 tokens per
  station at 24 stations, on the assumption that the rate is constant.

It is not constant. At 74 stations the observed rate was 418.3, and the single-point model
overshot its own prediction by 31%. The model grows terser as the list lengthens.

## What changed here, and what deliberately did not

**The shape is inherited byte-for-byte from M122** and rebuilt through its own builders, because
that shape is the one this route has been *observed* to enforce: nine of nine classes conforming,
five array-of-object levels, zero enforcement failures. Re-authoring a validated schema to change a
count would throw away the only thing M122 established.

**Only the station count changes**, and it is now fit from two observations at different scales
rather than extrapolated from one:

    tokens = 356.8 x stations + 4555

The intercept is the point. A single-point model is a line through the origin, and this one is not
through the origin -- there is a fixed cost per completion that a proportional model charges to
every station. That is precisely the error that closed M122.

## Why the margin is what it is

Two closures in a row came from a stress that was too small, and the risk is asymmetric: a stress
that is too small kills the milestone, while a stress that is too large only takes longer and makes
the gate *harder* to pass. So the sizing errs large, deliberately, and says by how much:

    target            1.5 x the larger of the threshold and the contract ceiling
    model allowance   the fit may run 25% low, because the previous model was 31% out
    stations          167, predicted at 64,137 tokens

Even if the fit runs a quarter low the stress still clears 48,000 tokens, which is 1.5x the
threshold. If the yield instead returned to the old high rate the completion would be about 91,000
tokens, still well under the 131,072 cap, so over-sizing cannot cause a truncation failure either.

**The 32,000 threshold is inherited from M118 and is not touched.** A threshold rewritten to fit a
stress is a gate tuned to pass itself, which is the failure this whole line of records exists to
prevent. The stress moves; the bar does not.
"""

from __future__ import annotations

import math
from typing import Any

from metamorphosis import m122_stress_schema as inherited

STRESS_SCHEMA_NAME = "m123_survey_stations"

# ---------------------------------------------------------------------------------------------
# The two-point fit
# ---------------------------------------------------------------------------------------------
#
# Both observations are of the same schema shape on the same route, at different scales. They are
# recorded with the run that produced them so the fit can be checked rather than believed.
OBSERVATIONS = (
    {"stations": 24, "completion_tokens": 13118, "run": "M122 readiness attempt 3, 2026-09-03"},
    {"stations": 74, "completion_tokens": 30957, "run": "M122 readiness attempt 4, 2026-09-04"},
)

_LOW, _HIGH = OBSERVATIONS
TOKENS_PER_STATION = ((_HIGH["completion_tokens"] - _LOW["completion_tokens"])
                      / (_HIGH["stations"] - _LOW["stations"]))
FIXED_COMPLETION_COST = _LOW["completion_tokens"] - TOKENS_PER_STATION * _LOW["stations"]

INHERITED_THRESHOLD_TOKENS = 32000      # M118's, unchanged
CONTRACT_CEILING_TOKENS = 29520         # 48 machines at the contract's ceiling
TARGET_MARGIN = 1.5                     # the risk is asymmetric; err large
MODEL_SHORTFALL_ALLOWANCE = 0.25        # the single-point model was 31% out

TARGET_COMPLETION_TOKENS = TARGET_MARGIN * max(INHERITED_THRESHOLD_TOKENS,
                                               CONTRACT_CEILING_TOKENS)
_FIT_TARGET = TARGET_COMPLETION_TOKENS / (1 - MODEL_SHORTFALL_ALLOWANCE)
STATIONS = math.ceil((_FIT_TARGET - FIXED_COMPLETION_COST) / TOKENS_PER_STATION)

# The endpoint's own ceiling. Over-sizing must not create a truncation failure, so the sizing is
# checked against the cap under the *most* generous yield ever observed rather than under the fit.
MAX_OUTPUT_TOKENS = 131072
_HIGHEST_RATE_EVER_OBSERVED = _LOW["completion_tokens"] / _LOW["stations"]


class StressError(RuntimeError):
    """The stress schema cannot certify the contract. Every path fails closed."""


def predicted_completion_tokens(stations: int = None) -> float:
    """The fit, applied. Two parameters from two points, so it reproduces both exactly."""
    count = STATIONS if stations is None else stations
    return TOKENS_PER_STATION * count + FIXED_COMPLETION_COST


def sizing_derivation() -> dict[str, Any]:
    """The arithmetic above, reported so it is checkable rather than believed."""
    predicted = predicted_completion_tokens()
    return {
        "observations": list(OBSERVATIONS),
        "observation_count": len(OBSERVATIONS),
        "fit": "tokens = %.1f * stations + %.0f" % (TOKENS_PER_STATION, FIXED_COMPLETION_COST),
        "tokens_per_station": TOKENS_PER_STATION,
        "fixed_completion_cost": FIXED_COMPLETION_COST,
        "why_the_intercept_matters": (
            "a single-point model is a line through the origin. This one is not: there is a fixed "
            "cost per completion that a proportional model charges to every station, which is the "
            "error that closed M122."),
        "inherited_threshold_tokens": INHERITED_THRESHOLD_TOKENS,
        "inherited_threshold_was_not_changed": True,
        "contract_ceiling_tokens": CONTRACT_CEILING_TOKENS,
        "target_margin": TARGET_MARGIN,
        "model_shortfall_allowance": MODEL_SHORTFALL_ALLOWANCE,
        "target_completion_tokens": TARGET_COMPLETION_TOKENS,
        "stations": STATIONS,
        "predicted_completion_tokens": predicted,
        "predicted_if_the_fit_runs_low": predicted * (1 - MODEL_SHORTFALL_ALLOWANCE),
        "still_clears_the_threshold_if_the_fit_runs_low":
            predicted * (1 - MODEL_SHORTFALL_ALLOWANCE) > INHERITED_THRESHOLD_TOKENS,
        "worst_case_if_yield_returned_to_the_highest_rate_observed":
            _HIGHEST_RATE_EVER_OBSERVED * STATIONS,
        "stays_under_the_output_cap":
            _HIGHEST_RATE_EVER_OBSERVED * STATIONS < MAX_OUTPUT_TOKENS,
        "the_shape_is_inherited_unchanged_only_the_size_moved": True,
    }


def _assert_the_sizing_is_safe_in_both_directions() -> None:
    """Too small kills the milestone; too large risks a truncation the cap would cause."""
    derivation = sizing_derivation()
    if not derivation["still_clears_the_threshold_if_the_fit_runs_low"]:
        raise StressError(
            "the stress would not clear the threshold if the fit ran %d%% low, which is less "
            "margin than the model that closed M122 was out by"
            % (100 * MODEL_SHORTFALL_ALLOWANCE))
    if not derivation["stays_under_the_output_cap"]:
        raise StressError(
            "at the highest yield ever observed this stress would exceed the %d token cap and "
            "truncate, which would read as enforcement failing open"% MAX_OUTPUT_TOKENS)


_assert_the_sizing_is_safe_in_both_directions()


def build_stress_schema() -> dict[str, Any]:
    """M122's schema, rebuilt through its own builders, with only the station count moved.

    The shape is what this route was observed to enforce. Re-authoring it to change a count would
    discard the one thing M122 did establish.
    """
    schema = inherited.build_stress_schema()
    stations = schema["properties"]["stations"]
    stations["minItems"] = STATIONS
    stations["maxItems"] = STATIONS
    return schema


STRESS_PROMPT = inherited.STRESS_PROMPT.replace(
    "exactly %d survey stations" % inherited.STATIONS,
    "exactly %d survey stations" % STATIONS)


def assert_certifies(candidate_schema: dict[str, Any], certified_levels: int) -> dict[str, Any]:
    """Dominance and serviceability together, inherited from M122 and re-checked on this size."""
    from metamorphosis import m116_schema as schema_tools  # noqa: PLC0415

    stressed = schema_tools.census(build_stress_schema())
    candidate = schema_tools.census(candidate_schema)
    dominates, shortfalls = schema_tools.census_dominates(stressed, candidate)
    if not dominates:
        raise StressError(
            "the stress schema does not dominate the candidate census, so it cannot certify it: %s"
            % ", ".join(shortfalls))
    levels = int(stressed["array_of_object_levels"])
    if levels > certified_levels:
        raise StressError(
            "the stress schema needs %d array-of-object levels and this route has been observed to "
            "enforce %d" % (levels, certified_levels))
    return {
        "stress_schema_census": stressed,
        "candidate_schema_census": candidate,
        "stress_dominates_the_candidate_schema": True,
        "stress_is_within_the_certified_nesting": True,
        "stress_schema_is_not_the_candidate_schema": True,
        "stress_sizing_derivation": sizing_derivation(),
    }


__all__ = ["OBSERVATIONS", "STATIONS", "STRESS_PROMPT", "STRESS_SCHEMA_NAME", "StressError",
           "assert_certifies", "build_stress_schema", "predicted_completion_tokens",
           "sizing_derivation"]
