#!/usr/bin/env python3
"""M117 DEVELOPMENT diagnostic: why does the token-capacity stress request return HTTP 400?

Stage 1 attempt 03 recorded four candidates that enforced every required schema feature class on
the capability probes -- HTTP 200 on all ten, conforming output -- and then answered HTTP 400 to
the token-capacity stress. The apparatus could not say why. That is M115's failure mode returning:
a terminal observation whose cause the record cannot state.

Two explanations were ruled out by attempt 03's own evidence before this diagnostic was written:

  * It is not the token budget. The probes sent max_tokens = 131072 to an endpoint declaring 65536
    and every one returned 200; capping the stress at exactly the declared ceiling still returned
    400.
  * It is not the route being incapable of structured output. The same endpoints conformed to all
    ten probe schemas.

So the difference lies in the stress request itself. This bisects it one dimension at a time.

Nothing here qualifies, selects, or scores anything. It sends no carrier and no qualifying input,
it cannot advance a generality gate, and it writes no selection. It exists so the record can state
a cause instead of recording a bare 400.

    python scripts/audit_m117_stress_rejection.py --plan
    python scripts/audit_m117_stress_rejection.py --execute
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from metamorphosis import m116_capability_probes as probes  # noqa: E402
from metamorphosis import m116_stress_schema as stress  # noqa: E402
from metamorphosis.blind_bank_protocol import canonical_bytes, sha256_hex  # noqa: E402
from scripts import audit_m116_capability_matrix as m116  # noqa: E402
from scripts import audit_m117_route_qualification as stage1  # noqa: E402

REPORT_PATH = ROOT / "experiments" / "M117" / "STRESS_REJECTION_DIAGNOSIS.json"

# One endpoint, chosen mechanically: the first candidate in attempt 03's frozen order that
# enforced every feature class and then answered 400. Not a preference -- a reproduction.
UNIVERSE_PATH = stage1.UNIVERSE_PATH

MAX_REQUESTS = 12

# Provider error text is free text and is never committed. Each message is classified against this
# fixed vocabulary and only the matched class is recorded, alongside a digest so that two identical
# errors are comparable without disclosing either.
# Ordered most specific first. A generic word decided ahead of a specific one gives a confident
# wrong cause, which is worse for the record than "unclassified": "exceeds" once matched
# schema_too_large before "max_tokens" could reach token_budget_rejected.
ERROR_CLASSES = (
    ("rate_limited", ("rate limit", "quota", "resource exhausted")),
    ("token_budget_rejected", ("max_tokens", "maxoutputtokens", "max output tokens",
                               "output token")),
    ("schema_too_deep", ("too deep", "deeply nested", "nesting", "depth", "recursion")),
    ("schema_unsupported_keyword", ("unsupported", "not supported", "unknown field",
                                    "invalid schema", "unrecognized")),
    ("schema_too_large", ("too large", "too long", "size limit", "too many", "exceeds")),
    ("parameter_rejected", ("parameter", "reasoning", "seed", "temperature")),
)


def classify_error(message: str) -> str:
    lowered = message.lower()
    for name, needles in ERROR_CLASSES:
        if any(n in lowered for n in needles):
            return name
    return "unclassified"


def _shrink(schema: Mapping[str, Any], *, max_items: int) -> dict[str, Any]:
    """The stress schema with every array cardinality reduced. Structure is untouched."""
    out = copy.deepcopy(dict(schema))

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for key in ("minItems", "maxItems"):
                if isinstance(node.get(key), int):
                    node[key] = min(node[key], max_items)
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(out)
    return out


def _truncate_depth(schema: Mapping[str, Any], *, limit: int) -> dict[str, Any]:
    """The stress schema truncated below a nesting limit, so depth alone varies."""

    def walk(node: Any, depth: int) -> Any:
        if not isinstance(node, dict):
            return node
        out = {}
        for key, value in node.items():
            if key in ("properties", "items") and depth >= limit:
                continue
            if key == "properties" and isinstance(value, dict):
                out[key] = {k: walk(v, depth + 1) for k, v in value.items()}
            elif key == "items":
                out[key] = walk(value, depth + 1)
            elif key == "required" and depth >= limit:
                continue
            else:
                out[key] = value
        if "properties" not in out and out.get("type") == "object":
            out.pop("required", None)
            out.pop("additionalProperties", None)
        return out

    return walk(dict(schema), 0)


def cases() -> list[dict[str, Any]]:
    """Each case differs from the stress request in exactly one dimension."""
    full = stress.build_stress_schema()
    matrix = probes.build_matrix(m116._census())
    small = next(p for p in matrix if p["name"] == "combined")
    return [
        {"case": "probe_schema_probe_budget", "schema": small["schema"],
         "prompt": small["prompt"], "max_tokens": 65536, "reasoning": True,
         "isolates": "baseline: the request shape attempt 03 recorded as HTTP 200"},
        {"case": "stress_schema_small_budget", "schema": full, "prompt": stress.STRESS_PROMPT,
         "max_tokens": 1024, "reasoning": True,
         "isolates": "the schema, with the token budget removed as a factor"},
        {"case": "stress_schema_no_reasoning_control", "schema": full,
         "prompt": stress.STRESS_PROMPT, "max_tokens": 65536, "reasoning": False,
         "isolates": "the reasoning parameter"},
        {"case": "stress_prompt_probe_schema", "schema": small["schema"],
         "prompt": stress.STRESS_PROMPT, "max_tokens": 65536, "reasoning": True,
         "isolates": "the prompt"},
        {"case": "stress_schema_cardinality_4", "schema": _shrink(full, max_items=4),
         "prompt": stress.STRESS_PROMPT, "max_tokens": 65536, "reasoning": True,
         "isolates": "array cardinality, structure unchanged"},
        {"case": "stress_schema_depth_6", "schema": _truncate_depth(full, limit=6),
         "prompt": stress.STRESS_PROMPT, "max_tokens": 65536, "reasoning": True,
         "isolates": "nesting depth"},
    ]


def plan() -> dict[str, Any]:
    record = {
        "schema": "m117-stress-rejection-plan-v1",
        "milestone": "M117", "development": True,
        "is_a_qualifying_call": False, "qualifying_input_was_sent": False,
        "selects_nothing": True, "scores_nothing": True,
        "purpose": "establish why the token-capacity stress returns HTTP 400 on a route that "
                   "conformed to all ten capability probes",
        "ruled_out_before_this_diagnostic": [
            "the token budget: probes sent 131072 to an endpoint declaring 65536 and returned 200, "
            "and capping at the declared ceiling still returned 400",
            "incapacity for structured output: the same endpoints conformed to all ten probes",
        ],
        "max_requests": MAX_REQUESTS,
        "error_text_is_never_committed": True,
        "also_records_router_metadata_key_names": True,
        "error_classes": [name for name, _ in ERROR_CLASSES],
        "cases": [{"case": c["case"], "isolates": c["isolates"], "max_tokens": c["max_tokens"],
                   "reasoning_control": c["reasoning"],
                   "schema_sha256": sha256_hex(canonical_bytes(c["schema"]))} for c in cases()],
        "plan_sha256": "",
    }
    record["plan_sha256"] = sha256_hex(
        canonical_bytes({k: v for k, v in record.items() if k != "plan_sha256"}))
    return record


def _target() -> dict[str, Any]:
    """The first candidate in the frozen order that enforced everything and then answered 400."""
    ledger = json.loads(
        (ROOT / "experiments" / "M117" / "STAGE1_ROUTE_QUALIFICATION_LEDGER.json")
        .read_text(encoding="utf-8"))
    for profile in sorted(ledger["profiles"], key=lambda p: p.get("order") or 0):
        stress_record = profile.get("token_capacity_stress") or {}
        if not profile.get("unenforced_feature_classes") and stress_record.get("http_status") == 400:
            return profile
    raise stage1.Stage1Error("no candidate reproduced the stress rejection; nothing to diagnose")


def execute() -> dict[str, Any]:
    target = _target()
    candidate = {"model": target["model"], "provider": target["provider"],
                 "max_completion_tokens": (target.get("token_capacity_stress") or {})
                 .get("declared_max_completion_tokens"),
                 "supported_parameters": ["reasoning"] if target.get("reasoning_control_applied")
                 else []}
    results = []
    for case in cases():
        body = {
            "model": candidate["model"],
            "messages": [{"role": "user", "content": case["prompt"]}],
            "provider": {"only": [candidate["provider"]], "allow_fallbacks": False,
                         "require_parameters": True},
            "response_format": {"type": "json_schema", "json_schema": {
                "name": "m117_stress_diagnostic", "strict": True, "schema": case["schema"]}},
            "max_tokens": case["max_tokens"], "seed": 0, "stream": False, "temperature": 1.0,
        }
        if case["reasoning"] and target.get("reasoning_control_applied"):
            body["reasoning"] = {"effort": "none"}
        observed = stage1._http(stage1.COMPLETIONS_ENDPOINT, method="POST",
                                body=canonical_bytes(body), timeout=600)
        payload = observed.get("body") if isinstance(observed.get("body"), Mapping) else {}
        error = payload.get("error") if isinstance(payload.get("error"), Mapping) else {}
        # Second open question, answered by the same requests: `attempts` and `pipeline` were
        # absent on 11 of 11 Stage 1 candidates while `strategy` -- read from the same object --
        # was present on all 11, and M116 recorded both as [] on this same provider. Recording the
        # metadata's key set settles whether the fields are gone from the response or are being
        # lost somewhere in this code path. Key names only; no values, no free text.
        metadata = payload.get("openrouter_metadata")
        metadata_keys = sorted(metadata) if isinstance(metadata, Mapping) else None
        message = error.get("message")
        message = message if isinstance(message, str) else ""
        results.append({
            "case": case["case"], "isolates": case["isolates"],
            "http_status": observed.get("status"),
            "max_tokens": case["max_tokens"],
            "schema_sha256": sha256_hex(canonical_bytes(case["schema"])),
            "error_class": classify_error(message) if message else None,
            "error_code": error.get("code") if isinstance(error.get("code"), (int, str)) else None,
            "error_message_sha256": sha256_hex(message.encode("utf-8")) if message else None,
            "error_message_bytes": len(message.encode("utf-8")) if message else 0,
            "error_text_persisted": False,
            "raw_completion_persisted": False,
            "router_metadata_keys": metadata_keys,
            "router_metadata_present": metadata_keys is not None,
        })

    report = {
        "schema": "m117-stress-rejection-diagnosis-v1",
        "milestone": "M117", "development": True,
        "is_a_qualifying_call": False, "qualifying_input_was_sent": False,
        "plan_sha256": plan()["plan_sha256"],
        "target_model": candidate["model"], "target_provider": candidate["provider"],
        "target_declared_max_completion_tokens": candidate["max_completion_tokens"],
        "results": results,
        "requests_spent": len(results),
        "report_sha256": "",
    }
    report["report_sha256"] = sha256_hex(
        canonical_bytes({k: v for k, v in report.items() if k != "report_sha256"}))
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_bytes(canonical_bytes(report) + b"\n")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", action="store_true")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if args.plan:
        print(json.dumps(plan(), indent=2, sort_keys=True))
        return 0
    if args.execute:
        report = execute()
        print(json.dumps({r["case"]: {"status": r["http_status"], "error": r["error_class"]}
                          for r in report["results"]}, indent=2, sort_keys=True))
        return 0
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
