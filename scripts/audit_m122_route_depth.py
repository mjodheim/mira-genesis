#!/usr/bin/env python3
"""DEVELOPMENT diagnostic: does this route enforce the nesting the M122 contract needs?

M120 closed because its candidate schema needed eight array-of-object levels and the route
enforces fewer. Its outcome records what a successor must do about that:

> The carrier contract must fit inside what the route enforces. A successor should either flatten
> the representation until its census sits at or below the five levels this route has been observed
> to enforce, or establish a higher depth on the route *before* adopting a schema that needs it.

M122 flattens to five. Five is backed by inheritance -- M115's schema sat there, M116 and M119 ran
under it, M118's readiness gate certified that census -- but inheritance across a schema change is
exactly the reasoning M120 was built to stop doing. So this asks the route directly, for the price
of two requests, **before** the rest of the milestone is built.

This is a diagnostic, not a gate. It is not M122's readiness run, it consumes no single-use
budget, it is repeatable, and its result is design evidence rather than scientific evidence. It
sends no qualifying input and produces no carrier. What it can establish is one thing: whether the
class that closed M120 holds at the depth M122 asks for.

The API key is read from `OPENROUTER_API_KEY` and is never written or printed.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from metamorphosis import m116_capability_probes as probes  # noqa: E402
from metamorphosis import m116_schema as schema_tools  # noqa: E402
from metamorphosis import m118_route as fixed  # noqa: E402
from metamorphosis import m122_carrier_contract as contract  # noqa: E402
from metamorphosis.blind_bank_protocol import canonical_bytes, sha256_hex  # noqa: E402
from scripts.run_m120_readiness import _http  # noqa: E402

DIAGNOSTIC_SCHEMA = "m122-route-depth-diagnostic-v1"
MAX_TOKENS = 131072

# The two probes that matter here. `nested_arrays` is the class M120 lost; `combined` is the one
# that exercises every class at once and was never reached on M120's run because the runaway probe
# before it had already provoked rate limiting.
PROBES_OF_INTEREST = ("nested_arrays", "combined")


def _request_body(prompt: str, schema: dict[str, Any], name: str) -> dict[str, Any]:
    fixed.assert_is_the_fixed_route(fixed.REQUESTED_MODEL, fixed.PROVIDER)
    return {
        "model": fixed.REQUESTED_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "provider": fixed.provider_block(),
        "response_format": {"type": "json_schema", "json_schema": {
            "name": name, "strict": True, "schema": schema}},
        "max_tokens": MAX_TOKENS,
        "seed": 0, "stream": False, "temperature": 1.0,
        "reasoning": {"effort": "none"},
    }


def run() -> dict[str, Any]:
    census = schema_tools.census(contract.candidate_schema())
    matrix = {probe["name"]: probe for probe in probes.build_matrix(census)}
    observations = []
    for name in PROBES_OF_INTEREST:
        probe = matrix.get(name)
        if probe is None:
            continue
        body = _request_body(probe["prompt"], probe["schema"], "m122_depth_%s" % name)
        observed = _http("https://openrouter.ai/api/v1/chat/completions",
                         method="POST", body=canonical_bytes(body), timeout=900)
        payload = observed.get("body") or {}
        choices = payload.get("choices") if isinstance(payload.get("choices"), list) else []
        first = choices[0] if choices and isinstance(choices[0], dict) else {}
        message = first.get("message") if isinstance(first.get("message"), dict) else {}
        usage = payload.get("usage") if isinstance(payload.get("usage"), dict) else {}
        content = message.get("content")
        conforms = False
        if isinstance(content, str):
            try:
                conforms, _, _ = schema_tools.instance_is_valid(
                    json.loads(content), probe["schema"])
            except ValueError:
                conforms = False
        observations.append({
            "probe": name,
            "feature_class": probe["feature_class"],
            "http_status": observed.get("status"),
            "finish_reason": first.get("finish_reason"),
            "completion_tokens": usage.get("completion_tokens"),
            "schema_conforms": bool(conforms),
            "identity_holds": fixed.identity_holds(payload)["holds"] if payload else False,
            "transport_failure_class": observed.get("transport_failure_class"),
            "raw_completion_persisted": False,
        })
    record = {
        "schema": DIAGNOSTIC_SCHEMA,
        "milestone": "M122", "development": True,
        "is_a_qualifying_call": False,
        "is_a_readiness_gate": False,
        "consumes_no_single_use_budget": True,
        "repeatable": True,
        "sends_the_qualifying_input": False,
        "array_of_object_levels_requested": int(census["array_of_object_levels"]),
        "m120_requested_and_was_refused_at": 8,
        "candidate_schema_sha256": sha256_hex(canonical_bytes(contract.candidate_schema())),
        "route": fixed.route()["route_version"],
        "observations": observations,
        "every_probe_conformed": all(o["schema_conforms"] for o in observations),
        "result_sha256": "",
    }
    record["result_sha256"] = sha256_hex(canonical_bytes(
        {k: v for k, v in record.items() if k != "result_sha256"}))
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true", required=True)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    record = run()
    # Printed before it is written, and the directory is created rather than assumed. The first
    # run of this script paid for two requests and then lost both to a missing parent directory --
    # the same shape as M118 revision 1, which discarded every observation it had already bought
    # when it aborted. Evidence is cheapest to keep at the moment it exists.
    print(json.dumps({k: record[k] for k in (
        "array_of_object_levels_requested", "every_probe_conformed", "result_sha256")},
        indent=2, sort_keys=True))
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_bytes(canonical_bytes(record) + b"\n")
    for observation in record["observations"]:
        print("  %-14s http=%-5s finish=%-8s conforms=%-6s tokens=%s"
              % (observation["probe"], observation["http_status"],
                 observation["finish_reason"], observation["schema_conforms"],
                 observation["completion_tokens"]))
    return 0 if record["every_probe_conformed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
