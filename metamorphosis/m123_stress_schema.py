"""M122's stress schema, sized by the empirical envelope of every rate ever observed.

## Why there is no model here any more

Three sizings, three failures, and the third one falsified the method rather than the number:

* **M120's 24 stations, inherited** while the schema underneath was being flattened. 13,118 tokens.
* **M122's 74 stations, extrapolated from one observation** on the assumption that the rate is
  constant. 30,957 tokens against a 32,000 threshold -- short by 3.3%.
* **M123's 167 stations, fit from two observations.** The fit predicted 64,137 tokens. The route
  produced **at least 100,657** and truncated.

Each replacement was a better model than the one before, and each was wrong. The rates say why:

    24 stations   13,118 tokens     546.6 per station
    74 stations   30,957 tokens     418.3 per station
    167 stations  >=100,657 tokens  >=602.7 per station   (censored -- see below)

**Down, then up.** The relationship is not linear, not monotonic, and not something three points
identify. Fitting a fourth model to three points would repeat the mistake with more arithmetic, so
this module does not fit anything. It takes the *envelope* of the rates actually observed and
requires the stress to sit inside the admissible window under **every** one of them.

## The censored observation, stated as such

100,657 is **a truncation that was observed, not a ceiling that is specified.** The request asked
for 131,072 tokens and the route stopped at 100,657 with `finish_reason: "length"`. What that
establishes, stated in the right direction:

* the route serves **at least** 100,657 completion tokens in one response, because it emitted
  exactly that many. The effective limit is not below 100,657, and since generation stopped there
  rather than at the 131,072 requested, roughly 100,657 is where the cap sits;
* the true rate at 167 stations is **at least** 602.7 per station, because the object was cut off
  before it closed. The upper edge of the envelope is therefore itself a lower bound, and the real
  worst case can be worse than the worst case this module can see.

Only the second of those is a weakness, and it is the reason for the margin below. The first is
supporting evidence and was previously written backwards -- an earlier draft of this module claimed
the limit was "at most about 100,657, and could be anywhere below it", which cannot be true of a
completion that was actually produced.

A fourth observation, from M117's route calibration on this same route and checkpoint, is recorded
here because it bears directly on serviceability: **68,368 completion tokens, `finish_reason:
"stop"`, schema conforming.** The worst case at 109 stations is 65,698 tokens, below a completion
this route has already delivered cleanly.

## The operational bound

    observed truncation      100,657 tokens   (an observation, not a specification)
    operational ceiling       85,000 tokens   (a choice, ~15.6% below the observation)

85,000 is **chosen, not derived.** It buys roughly 15% of headroom against three things this
project cannot measure from here: that the true limit may sit below the one truncation ever seen,
that the censored rate under-states the real rate, and that a route's yield has already moved by
44% between two sizings without anything in the schema changing.

## The window, and the deterministic choice inside it

    floor    > 32,000 tokens at the LOWEST rate ever observed (418.3)  ->  >= 77 stations
    ceiling  < 85,000 tokens at the HIGHEST rate ever observed (602.7) ->  <= 141 stations
    chosen   the midpoint of [77, 141], which is 109

The midpoint is taken because it is the one point in the window that no observation argues for --
it is maximally far from both edges, and it is computed rather than picked. A size chosen because
it looked likely to pass would be the gate tuned to itself, which is the failure this whole line of
records exists to prevent.

At 109 stations the prediction is a range, not a number: **45,599 tokens at the lowest observed
rate, 65,698 at the highest.** Both sit inside the window with room on each side.

**The 32,000 threshold is inherited from M118 and is not touched.** The stress moves; the bar does
not.

## What is deliberately unchanged

The schema's *shape* is M122's, rebuilt through M122's own builders. That shape is what this route
has been observed to enforce -- nine of nine capability classes conforming at five array-of-object
levels. Only the station count moves.
"""

from __future__ import annotations

from typing import Any

from metamorphosis import m122_stress_schema as inherited

STRESS_SCHEMA_NAME = "m123_survey_stations"

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
            "M123 attempt 1"
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
