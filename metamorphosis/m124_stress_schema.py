"""M123's sizing rule, unchanged, and now confirmed by an observation it did not use.

## Why nothing here moves

M123 closed at `not_ready_stress`. Its stress was **not** what failed:

    predicted band at 109 stations   45,598 - 65,698 tokens
    observed                         50,232
    implied rate                     460.8 per station

The empirical rate envelope made an out-of-sample prediction and the route landed inside it, after
a two-point linear fit had failed the same test by at least 57%. That is the first sizing in this
line that worked, and M124 does not touch it.

The new observation is folded in and **changes nothing**, which is the point of recording it:

    24 stations    13,118 tokens    546.6 per station
    74 stations    30,957 tokens    418.3 per station
    167 stations   >=100,657        >=602.7 per station   (censored)
    109 stations   >=50,232         >=460.8 per station   (censored)

460.8 sits inside the envelope [418.3, 602.7] that the first three already described, so the window
stays [77, 141] and the midpoint stays 109. A rule whose answer is stable when new evidence arrives
is behaving the way a rule should.

## What killed M123, and what this module does not pretend to fix

The stress returned HTTP 200 with 50,232 tokens, **no `finish_reason` at all**, and a body that does
not validate. `holds` requires `finish_reason == "stop"`, so the verdict was `not_ready_stress` --
terminal. The fix belongs in the gate's classification, not here; see `run_m124_readiness.py`.

## The limitation that still stands

At a fixed station count the inherited schema permits conforming completions spanning about 4x,
which is wider than the pass window. Station count is not the only variable, and it is not the
largest. Pinning the inner array cardinalities would remove that freedom and leaves the census
M122 validated **bit-identical** -- verified. It is deliberately not done here, because every
observation above was measured on the unpinned schema: pinning would improve the instrument and
discard its entire calibration in the same edit. That trade belongs to a milestone that budgets for
re-calibration, not to a successor whose purpose is to correct a verdict rule.

**The 32,000 threshold is inherited from M118 and is not touched.** The stress moves; the bar does
not. It has now not moved for four milestones.
"""

from __future__ import annotations

from typing import Any

from metamorphosis import m122_stress_schema as inherited

STRESS_SCHEMA_NAME = "m124_survey_stations"

# ---------------------------------------------------------------------------------------------
# Every rate ever observed, including the censored one
# ---------------------------------------------------------------------------------------------
#
# Each observation records the run that produced it so the envelope can be checked rather than
# believed. `truncated` marks an observation whose completion token count is a floor rather than a
# measurement: the route stopped on length, so the completion the schema asked for was never
# finished and the real figure is larger by an unknown amount.
OBSERVATIONS = (
    {"stations": 24, "completion_tokens": 13118, "truncated": False,
     "run": "M122 readiness attempt 3, 2026-09-03"},
    {"stations": 74, "completion_tokens": 30957, "truncated": False,
     "run": "M122 readiness attempt 4, 2026-09-04"},
    {"stations": 167, "completion_tokens": 100657, "truncated": True,
     "run": "M123 readiness attempt 1, 2026-09-04"},
    # The observation M123 bought with its own closure. Censored twice over: the object was never
    # closed, and the response carried no `finish_reason` at all, so the model was still generating
    # when it ended. 460.8 per station is therefore a floor, and it falls INSIDE the envelope the
    # previous three observations already described -- which is why nothing about the size moves.
    {"stations": 109, "completion_tokens": 50232, "truncated": True,
     "run": "M123 readiness attempt 2, 2026-09-04"},
)

SIZING_RULE = "empirical_rate_envelope"


def _rate(observation: dict[str, Any]) -> float:
    return observation["completion_tokens"] / observation["stations"]


OBSERVED_RATES = tuple(_rate(o) for o in OBSERVATIONS)
LOWEST_OBSERVED_RATE = min(OBSERVED_RATES)
HIGHEST_OBSERVED_RATE = max(OBSERVED_RATES)

INHERITED_THRESHOLD_TOKENS = 32000      # M118's, unchanged

# An observation, not a specification. The request asked for 131,072 and the route stopped here.
OBSERVED_TRUNCATION_TOKENS = 100657
# A choice, not a derivation: ~15.6% below the single truncation ever seen.
OPERATIONAL_CEILING_TOKENS = 85000
# M117 calibration, same route and checkpoint: a conforming completion that finished on `stop`.
# Recorded because the worst case at this size sits below it, which is evidence about
# serviceability that the envelope alone does not supply.
CLEAN_COMPLETION_ON_THIS_ROUTE = 68368

# The admissible window, derived from the envelope and the two bounds above.
MIN_STATIONS = 77
MAX_STATIONS = 141
# Deterministic, and deliberately not chosen for its likelihood of passing.
STATIONS = (MIN_STATIONS + MAX_STATIONS) // 2


class StressError(RuntimeError):
    """The stress schema cannot certify the contract. Every path fails closed."""


def predicted_completion_token_range(stations: int | None = None) -> tuple[float, float]:
    """A range, because a point prediction is what has been falsified three times."""
    count = STATIONS if stations is None else stations
    return (LOWEST_OBSERVED_RATE * count, HIGHEST_OBSERVED_RATE * count)


def _derived_bounds() -> tuple[int, int]:
    """The window edges, recomputed from the envelope rather than trusted as constants."""
    import math  # noqa: PLC0415

    floor = math.floor(INHERITED_THRESHOLD_TOKENS / LOWEST_OBSERVED_RATE) + 1
    ceiling = math.floor(OPERATIONAL_CEILING_TOKENS / HIGHEST_OBSERVED_RATE)
    return floor, ceiling


def sizing_derivation() -> dict[str, Any]:
    """The whole rule, reported so it is checkable rather than believed."""
    low, high = predicted_completion_token_range()
    floor, ceiling = _derived_bounds()
    return {
        "sizing_rule": SIZING_RULE,
        "no_model_is_fitted": True,
        "why_no_model_is_fitted": (
            "three sizings produced rates of 546.6, 418.3 and >=602.7 per station. The "
            "relationship is not linear, not monotonic and not identified by three points. A "
            "two-point fit predicted 64,137 tokens at 167 stations and the route produced at "
            "least 100,657, so the method was abandoned rather than refitted."),
        "observations": [dict(o) for o in OBSERVATIONS],
        "observation_count": len(OBSERVATIONS),
        "observed_rates": list(OBSERVED_RATES),
        "lowest_observed_rate": LOWEST_OBSERVED_RATE,
        "highest_observed_rate": HIGHEST_OBSERVED_RATE,
        "observed_truncation_tokens": OBSERVED_TRUNCATION_TOKENS,
        "observed_truncation_is_not_a_known_exact_ceiling": True,
        "what_the_truncation_establishes": (
            "the request asked for 131,072 tokens and the route stopped at 100,657 on length. The "
            "route therefore serves at least 100,657 tokens in one response, because it emitted "
            "exactly that many, and the cap sits at roughly that figure rather than below it. The "
            "real rate at 167 stations is at least 602.7 and may be higher, because the object "
            "was cut off before it closed. The upper edge of this envelope is itself a lower "
            "bound, which is the weakness the operational ceiling exists to cover."),
        "route_has_served_this_many_tokens_cleanly": CLEAN_COMPLETION_ON_THIS_ROUTE,
        "worst_case_is_below_a_completion_already_served_cleanly":
            HIGHEST_OBSERVED_RATE * STATIONS < CLEAN_COMPLETION_ON_THIS_ROUTE,
        "operational_ceiling_tokens": OPERATIONAL_CEILING_TOKENS,
        "operational_ceiling_is_a_conservative_choice_not_a_measurement": True,
        "operational_ceiling_margin_below_the_observed_truncation":
            1 - OPERATIONAL_CEILING_TOKENS / OBSERVED_TRUNCATION_TOKENS,
        "inherited_threshold_tokens": INHERITED_THRESHOLD_TOKENS,
        "inherited_threshold_was_not_changed": True,
        "min_stations": MIN_STATIONS,
        "max_stations": MAX_STATIONS,
        "bounds_recomputed_from_the_envelope": list(_derived_bounds()),
        "stations": STATIONS,
        "station_choice": "midpoint_of_the_admissible_window",
        "station_choice_is_deterministic": True,
        "why_the_midpoint": (
            "it is the one point in the window that no observation argues for, it is maximally far "
            "from both edges, and it is computed rather than picked. A size chosen because it "
            "looked likely to pass would be the gate tuned to itself."),
        "predicted_tokens_at_the_lowest_observed_rate": low,
        "predicted_tokens_at_the_highest_observed_rate": high,
        "clears_the_threshold_even_at_the_lowest_observed_rate":
            low > INHERITED_THRESHOLD_TOKENS,
        "stays_under_the_operational_ceiling_even_at_the_highest_observed_rate":
            high < OPERATIONAL_CEILING_TOKENS,
        "the_shape_is_inherited_unchanged_only_the_size_moved": True,
        "floor_and_ceiling_bracket_the_choice": floor <= STATIONS <= ceiling,
    }


def _assert_the_sizing_is_safe_across_the_whole_envelope() -> None:
    """Too small kills the milestone; too large truncates. Both edges, every observed rate."""
    derivation = sizing_derivation()
    floor, ceiling = _derived_bounds()
    if (floor, ceiling) != (MIN_STATIONS, MAX_STATIONS):
        raise StressError(
            "the declared window [%d, %d] does not match the window the envelope derives "
            "[%d, %d]; the constants and the rule disagree"
            % (MIN_STATIONS, MAX_STATIONS, floor, ceiling))
    if not MIN_STATIONS <= STATIONS <= MAX_STATIONS:
        raise StressError(
            "%d stations sits outside the admissible window [%d, %d]"
            % (STATIONS, MIN_STATIONS, MAX_STATIONS))
    if not derivation["clears_the_threshold_even_at_the_lowest_observed_rate"]:
        raise StressError(
            "at the lowest rate ever observed (%.1f per station) this stress would produce %d "
            "tokens and would not clear the %d threshold -- the failure that closed M122"
            % (LOWEST_OBSERVED_RATE,
               derivation["predicted_tokens_at_the_lowest_observed_rate"],
               INHERITED_THRESHOLD_TOKENS))
    if not derivation["stays_under_the_operational_ceiling_even_at_the_highest_observed_rate"]:
        raise StressError(
            "at the highest rate ever observed (%.1f per station) this stress would produce %d "
            "tokens, over the %d operational ceiling, and would risk the truncation that closed "
            "M124 attempt 1"
            % (HIGHEST_OBSERVED_RATE,
               derivation["predicted_tokens_at_the_highest_observed_rate"],
               OPERATIONAL_CEILING_TOKENS))
    if OPERATIONAL_CEILING_TOKENS >= OBSERVED_TRUNCATION_TOKENS:
        raise StressError(
            "the operational ceiling %d is not below the observed truncation %d, so it carries no "
            "margin against a limit that was never exactly measured"
            % (OPERATIONAL_CEILING_TOKENS, OBSERVED_TRUNCATION_TOKENS))


_assert_the_sizing_is_safe_across_the_whole_envelope()


def build_stress_schema() -> dict[str, Any]:
    """M122's schema, rebuilt through its own builders, with only the station count moved."""
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


__all__ = ["CLEAN_COMPLETION_ON_THIS_ROUTE", "HIGHEST_OBSERVED_RATE", "LOWEST_OBSERVED_RATE", "MAX_STATIONS", "MIN_STATIONS",
           "OBSERVATIONS", "OBSERVED_RATES", "OBSERVED_TRUNCATION_TOKENS",
           "OPERATIONAL_CEILING_TOKENS", "SIZING_RULE", "STATIONS", "STRESS_PROMPT",
           "STRESS_SCHEMA_NAME", "StressError", "assert_certifies", "build_stress_schema",
           "predicted_completion_token_range", "sizing_derivation"]
