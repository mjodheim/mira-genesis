"""Pinned DEVELOPMENT stress and fresh sizing machinery for M125/H70.

M125 deliberately does not reuse M122/M123/M124 token rates. Historical observations motivated
this redesign but are excluded from calibration. The only inherited object is the M122 non-carrier
stress *shape*. All inner array cardinalities are pinned by a deterministic rule, the structural
census is proved identical, and sizing uses only the fresh 8/16/32 M125 calibration queue.
"""

from __future__ import annotations

import copy
import math
from fractions import Fraction
from typing import Any

from metamorphosis import m116_schema as schema_tools
from metamorphosis import m122_stress_schema as inherited

STRESS_SCHEMA_VERSION = "m125-pinned-stress-v1"
STRESS_SCHEMA_NAME_PREFIX = "m125_survey_stations"
CALIBRATION_QUEUE = (8, 16, 32)

REQUEST_MAX_TOKENS = 65536
MIN_COMPLETION_TOKENS = 32000
MAX_COMPLETION_TOKENS = (REQUEST_MAX_TOKENS * 4) // 5
PINNING_RULE = "upper_midpoint_inclusive"


class StressError(RuntimeError):
    """The pinned stress or fresh sizing protocol cannot certify the route."""


def upper_midpoint(minimum: int, maximum: int) -> int:
    if minimum > maximum:
        raise StressError("invalid cardinality interval %d..%d" % (minimum, maximum))
    return (minimum + maximum + 1) // 2


def _pin_array_ranges(node: Any, *, path: tuple[str, ...] = ()) -> None:
    if isinstance(node, dict):
        if node.get("type") == "array" and path != ("properties", "stations"):
            low, high = node.get("minItems"), node.get("maxItems")
            if isinstance(low, int) and isinstance(high, int):
                pinned = upper_midpoint(low, high)
                node["minItems"] = pinned
                node["maxItems"] = pinned
        for key, value in node.items():
            _pin_array_ranges(value, path=path + (str(key),))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            _pin_array_ranges(value, path=path + (str(index),))


def build_stress_schema(stations: int) -> dict[str, Any]:
    if not isinstance(stations, int) or stations <= 0:
        raise StressError("stations must be a positive integer")
    schema = copy.deepcopy(inherited.build_stress_schema())
    _pin_array_ranges(schema)
    station_array = schema["properties"]["stations"]
    station_array["minItems"] = stations
    station_array["maxItems"] = stations
    return schema


def pinning_proof(stations: int = CALIBRATION_QUEUE[0]) -> dict[str, Any]:
    before = copy.deepcopy(inherited.build_stress_schema())
    before["properties"]["stations"]["minItems"] = stations
    before["properties"]["stations"]["maxItems"] = stations
    after = build_stress_schema(stations)
    census_before = schema_tools.census(before)
    census_after = schema_tools.census(after)
    if census_before != census_after:
        raise StressError("pinning changed the structural census")
    return {
        "schema": "m125-pinning-proof-v1",
        "pinning_rule": PINNING_RULE,
        "stations": stations,
        "census_before": census_before,
        "census_after": census_after,
        "census_bit_identical": True,
        "historical_token_observations_used": False,
    }


def assert_certifies(candidate_schema: dict[str, Any], stations: int,
                    certified_levels: int) -> dict[str, Any]:
    stressed = schema_tools.census(build_stress_schema(stations))
    candidate = schema_tools.census(candidate_schema)
    dominates, shortfalls = schema_tools.census_dominates(stressed, candidate)
    if not dominates:
        raise StressError(
            "pinned stress does not dominate candidate census: %s" % ", ".join(shortfalls)
        )
    levels = int(stressed["array_of_object_levels"])
    if levels > int(certified_levels):
        raise StressError(
            "pinned stress needs %d array-of-object levels but route is certified for %d"
            % (levels, certified_levels)
        )
    pin = pinning_proof(stations)
    return {
        "stress_schema_census": stressed,
        "candidate_schema_census": candidate,
        "stress_dominates_candidate": True,
        "within_certified_nesting": True,
        "pinning_census_bit_identical": pin["census_bit_identical"],
        "historical_token_observations_used": False,
    }


def stress_prompt(stations: int) -> str:
    return (
        "Return a JSON object with exactly one key named stations. Its value must be a list of "
        "exactly %d survey stations. Every station records its docket, terrain, masts, offline "
        "indices, fault codes and instruments. Follow the JSON schema exactly. Vary values across "
        "stations. Emit no prose, commentary or extra keys."
    ) % stations


def calibration_step_name(stations: int) -> str:
    if stations not in CALIBRATION_QUEUE:
        raise StressError("calibration station count %d is not preregistered" % stations)
    return "calibration:%d" % stations


def _point_rate(point: dict[str, Any]) -> Fraction:
    stations = point.get("stations")
    tokens = point.get("completion_tokens")
    if stations not in CALIBRATION_QUEUE:
        raise StressError("calibration point uses an unregistered station count")
    if not isinstance(tokens, int) or tokens <= 0:
        raise StressError("calibration point lacks a positive completion token count")
    if point.get("answered") is not True:
        raise StressError("unanswered calibration point cannot size the final stress")
    if point.get("finish_reason") != "stop":
        raise StressError("non-stop calibration point cannot size the final stress")
    if point.get("schema_conforms") is not True:
        raise StressError("nonconforming calibration point cannot size the final stress")
    return Fraction(tokens, stations)


def derive_final_size(points: list[dict[str, Any]]) -> dict[str, Any]:
    """Derive one out-of-sample station count from exactly the fresh 8/16/32 points."""
    by_station = {point.get("stations"): point for point in points}
    if set(by_station) != set(CALIBRATION_QUEUE) or len(points) != len(CALIBRATION_QUEUE):
        raise StressError("final sizing requires exactly one fresh point at 8, 16 and 32 stations")
    rates = [_point_rate(by_station[size]) for size in CALIBRATION_QUEUE]
    low_rate, high_rate = min(rates), max(rates)
    minimum = math.floor(Fraction(MIN_COMPLETION_TOKENS, 1) / low_rate) + 1
    maximum = math.floor(Fraction(MAX_COMPLETION_TOKENS, 1) / high_rate)
    if minimum > maximum:
        raise StressError(
            "fresh calibration leaves no admissible final-size window (%d..%d)" % (minimum, maximum)
        )
    candidate = (minimum + maximum) // 2
    if candidate in CALIBRATION_QUEUE:
        if candidate + 1 <= maximum and candidate + 1 not in CALIBRATION_QUEUE:
            candidate += 1
        elif candidate - 1 >= minimum and candidate - 1 not in CALIBRATION_QUEUE:
            candidate -= 1
        else:
            raise StressError("admissible window contains no out-of-sample station count")
    predicted_low = low_rate * candidate
    predicted_high = high_rate * candidate
    return {
        "schema": "m125-fresh-sizing-v1",
        "calibration_queue": list(CALIBRATION_QUEUE),
        "historical_token_observations_used": False,
        "fresh_rates": [
            {"stations": size, "tokens_per_station_numerator": rates[index].numerator,
             "tokens_per_station_denominator": rates[index].denominator}
            for index, size in enumerate(CALIBRATION_QUEUE)
        ],
        "lowest_fresh_rate": [low_rate.numerator, low_rate.denominator],
        "highest_fresh_rate": [high_rate.numerator, high_rate.denominator],
        "minimum_final_stations": minimum,
        "maximum_final_stations": maximum,
        "final_stations": candidate,
        "final_is_out_of_sample": candidate not in CALIBRATION_QUEUE,
        "predicted_low_tokens": [predicted_low.numerator, predicted_low.denominator],
        "predicted_high_tokens": [predicted_high.numerator, predicted_high.denominator],
        "minimum_completion_tokens": MIN_COMPLETION_TOKENS,
        "maximum_completion_tokens": MAX_COMPLETION_TOKENS,
        "request_max_tokens": REQUEST_MAX_TOKENS,
        "selection_rule": "midpoint_then_plus_one_else_minus_one_if_midpoint_was_calibration_size",
        "refit_after_final_observation_permitted": False,
    }


def final_observation_holds(observation: dict[str, Any], derivation: dict[str, Any]) -> bool:
    tokens = observation.get("completion_tokens")
    return bool(
        observation.get("answered") is True
        and observation.get("finish_reason") == "stop"
        and observation.get("schema_conforms") is True
        and observation.get("stations") == derivation.get("final_stations")
        and isinstance(tokens, int)
        and MIN_COMPLETION_TOKENS < tokens <= MAX_COMPLETION_TOKENS
    )


__all__ = [
    "CALIBRATION_QUEUE", "MAX_COMPLETION_TOKENS", "MIN_COMPLETION_TOKENS",
    "PINNING_RULE", "REQUEST_MAX_TOKENS", "STRESS_SCHEMA_NAME_PREFIX", "STRESS_SCHEMA_VERSION",
    "StressError", "assert_certifies", "build_stress_schema", "calibration_step_name",
    "derive_final_size", "final_observation_holds", "pinning_proof", "stress_prompt",
    "upper_midpoint",
]
