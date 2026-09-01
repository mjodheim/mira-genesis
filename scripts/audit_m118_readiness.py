#!/usr/bin/env python3
"""M118 readiness gate: does the fixed H63 route still provide the calibrated instrument properties?

M117 observed that structured-output behaviour is not stable run to run -- one model returned every
required feature class enforced in one attempt and none in another. A single historical calibration
therefore cannot be trusted indefinitely, so H63 re-establishes the instrument immediately before
its scientific freeze.

This gate answers exactly one question:

    Does the fixed H63 route still provide the instrument properties already established during
    M117 calibration?

It does **not** select among providers -- there is one route and no second one. It does **not**
compare carrier quality. It does **not** send the H63 qualifying input, which does not exist when
this runs. It cannot advance a generality gate and is not evidence for H63.

Everything it does is fixed before it executes: the schemas, the prompts, the request body, the
reasoning control, the identity requirements, the feature requirements, the stress requirement, the
completion-token threshold, the retry rule, the stopping rule and the result classifier. The plan
digest binds them, and the result records that digest.

    python scripts/audit_m118_readiness.py --plan      # frozen rules, no network
    python scripts/audit_m118_readiness.py --execute    # DEVELOPMENT run against the fixed route
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from metamorphosis import m116_capability_probes as probes  # noqa: E402
from metamorphosis import m116_schema as schema_tools  # noqa: E402
from metamorphosis import m116_stress_schema as stress  # noqa: E402
from metamorphosis import m118_chronology as chronology  # noqa: E402
from metamorphosis import m118_route as fixed  # noqa: E402
from metamorphosis.blind_bank_protocol import canonical_bytes, sha256_hex  # noqa: E402
from scripts import audit_m116_capability_matrix as m116  # noqa: E402
from scripts import audit_m117_route_qualification as stage1  # noqa: E402

DIRECTORY = ROOT / "experiments" / "M118"
RESULT_PATH = DIRECTORY / "READINESS_RESULT.json"
LEDGER_PATH = DIRECTORY / "READINESS_LEDGER.json"

PLAN_SCHEMA = "m118-readiness-plan-v1"
RESULT_SCHEMA = "m118-readiness-result-v1"

# Inherited from the calibration unchanged, so the gate measures the route rather than a new
# instrument. A threshold rewritten for M118 could be rewritten to let the route through.
PROBE_MAX_TOKENS = 131072
STRESS_MAX_TOKENS = 131072
STRESS_MIN_COMPLETION_TOKENS = 32000

# The reasoning state H63 intends: the control is sent, and no reasoning tokens are consumed.
# M117 calibration observed exactly this on the fixed route -- 0 reasoning tokens on all ten probes
# with the control applied -- so the requirement is achievable and is not a bar invented here.
REASONING_EFFORT = "none"
MAX_REASONING_TOKENS = 0

# The only retry permitted, inherited verbatim: an explicit pre-generation 429 carrying no
# completion and no evidence of model execution. Nothing content-dependent, ever.
RETRYABLE = ("pre_generation_429",)
MAX_RETRIES = 2

# Mandatory requests: one per capability probe, plus the token-capacity stress.
MANDATORY_REQUESTS = 11

# The budget is derived from the retry rule rather than chosen. Revision 1 fixed it at 12 while
# granting up to two retries on each of eleven mandatory requests -- a contradiction visible in
# the constants alone, and one that duly aborted the gate at the stress after two pre-generation
# 429s consumed the slack. A budget that cannot accommodate the retries its own plan grants makes
# the gate fail for its own arithmetic rather than for anything about the route.
MAX_REQUESTS = MANDATORY_REQUESTS * (MAX_RETRIES + 1)


class ReadinessError(RuntimeError):
    """Fail closed. A readiness gate that guesses is not a gate."""


def _assert_budget_admits_the_retry_rule() -> None:
    """An admitted retry must be affordable, or the gate fails on its own arithmetic."""
    needed = MANDATORY_REQUESTS * (MAX_RETRIES + 1)
    if MAX_REQUESTS < needed:
        raise ReadinessError(
            "the frozen budget cannot accommodate the retries the plan grants: %d < %d"
            % (MAX_REQUESTS, needed))


def required_feature_classes() -> list[str]:
    return sorted(probes.required_feature_classes(m116._census()))


def feature_coverage() -> dict[str, Any]:
    """Which census-required keywords each probe actually exercises.

    The census requires eleven keywords; the inherited matrix carries nine named probes. The two
    without a probe of their own -- `items` and `maximum` -- are not unassessed: `items` is
    structurally present in every array probe, and `maximum` is exercised by the integer-bounds
    probe, which is labelled for `minimum`. A gate that reported "eleven required" beside nine
    probes would misdescribe its own coverage, so the mapping is computed from the probe schemas
    rather than asserted, and any keyword that reached no probe at all is named explicitly.
    """
    matrix = probes.build_matrix(m116._census())
    required = required_feature_classes()
    covered: dict[str, list[str]] = {}
    for keyword in required:
        needle = '"%s"' % keyword.replace("_false", "")
        covered[keyword] = sorted(
            probe["name"] for probe in matrix
            if probe["feature_class"] == keyword or needle in json.dumps(probe["schema"]))
    return {
        "required_by_census": required,
        "probes_with_their_own_named_class": sorted(
            {p["feature_class"] for p in matrix if p["name"] != "combined"}),
        "exercised_by": covered,
        "required_keywords_reaching_no_probe": sorted(k for k, v in covered.items() if not v),
    }


def plan() -> dict[str, Any]:
    matrix = probes.build_matrix(m116._census())
    record = {
        "schema": PLAN_SCHEMA,
        "milestone": "M118", "hypothesis": "H63", "development": True,
        "purpose": "does the fixed H63 route still provide the instrument properties established "
                   "during M117 calibration",
        "selects_among_providers": False,
        "compares_carrier_quality": False,
        "uses_the_h63_qualifying_input": False,
        "is_a_qualifying_call": False,
        "qualifying_input_was_sent": False,
        "can_advance_a_generality_gate": False,
        "is_evidence_for_h63": False,
        "route": fixed.route(),
        "identity_requirements": [
            "served model exactly the fixed requested model",
            "served provider exactly the fixed provider",
            "selected endpoint checkpoint exactly the fixed canonical checkpoint",
            "direct routing strategy",
            "routing attempt 1",
            "exactly one selected endpoint",
            "no fallback",
            "no pipeline intervention",
        ],
        "feature_requirements": {
            "required_feature_classes": required_feature_classes(),
            "coverage": feature_coverage(),
            "every_probed_class_must_be_enforced": True,
            "classes_without_their_own_probe_are_exercised_within_others": True,
            "combined_structural_probe_must_conform": True,
            "probe_count": len(matrix),
            "probe_max_tokens": PROBE_MAX_TOKENS,
            "matrix_plan_sha256": matrix and m116.plan()["plan_sha256"],
            "matrix_inherited_unchanged_from": "M116",
        },
        "stress_requirement": {
            "schema_sha256": sha256_hex(canonical_bytes(stress.build_stress_schema())),
            "schema_is_census_dominating": True,
            "http_status": 200,
            "finish_reason": "stop",
            "output_must_conform": True,
            "minimum_completion_tokens": STRESS_MIN_COMPLETION_TOKENS,
            "max_tokens": STRESS_MAX_TOKENS,
        },
        "reasoning_control": {
            "effort": REASONING_EFFORT,
            "sent_on_every_request": True,
            "maximum_observed_reasoning_tokens": MAX_REASONING_TOKENS,
            "calibration_observed": "0 reasoning tokens on all ten probes with the control applied",
        },
        "retry": {
            "permitted_only_for": list(RETRYABLE),
            "max_retries": MAX_RETRIES,
            "content_dependent_redraw_permitted": False,
            "repair_permitted": False,
            "resend_of_a_materialized_observation_permitted": False,
        },
        "budget": {
            "max_requests": MAX_REQUESTS,
            "mandatory_requests": MANDATORY_REQUESTS,
            "derived_as": "mandatory_requests * (max_retries + 1)",
            "chosen_rather_than_derived": False,
        },
        "stopping_rule": "every requirement must hold on this run; the first requirement that fails "
                         "ends the gate as not ready, and H63 stops before scientific generation "
                         "rather than changing provider, model, threshold or schema",
        "failure_rule": "record H63 untested / instrument unavailable at execution time; do not "
                        "change provider, change model, weaken the stress, remove a schema "
                        "requirement, rerun until it passes, or create a carrier bank",
        "result_classifier": [
            "ready: every identity, feature, stress and reasoning requirement held",
            "not_ready_identity: the response did not come from exactly the fixed route",
            "not_ready_features: a required schema feature class was not enforced",
            "not_ready_stress: the stress did not return a conforming full-scale completion",
            "not_ready_reasoning: the reasoning state was not the intended one",
            "not_ready_transport: the route could not be reached within the frozen budget",
        ],
        "plan_sha256": "",
    }
    _assert_budget_admits_the_retry_rule()
    record["plan_sha256"] = sha256_hex(
        canonical_bytes({k: v for k, v in record.items() if k != "plan_sha256"}))
    return record


def _request_body(prompt: str, schema: Mapping[str, Any], name: str,
                  max_tokens: int) -> dict[str, Any]:
    """One shape, for every request this gate sends."""
    fixed.assert_is_the_fixed_route(fixed.REQUESTED_MODEL, fixed.PROVIDER)
    return {
        "model": fixed.REQUESTED_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "provider": fixed.provider_block(),
        "response_format": {"type": "json_schema", "json_schema": {
            "name": name, "strict": True, "schema": schema}},
        "max_tokens": max_tokens,
        "seed": 0, "stream": False, "temperature": 1.0,
        "reasoning": {"effort": REASONING_EFFORT},
    }


def _send(prompt: str, schema: Mapping[str, Any], name: str, max_tokens: int,
          budget: dict[str, int]) -> dict[str, Any]:
    body = _request_body(prompt, schema, name, max_tokens)
    for attempt in range(MAX_RETRIES + 1):
        if budget["spent"] >= MAX_REQUESTS:
            raise ReadinessError("the frozen request budget is exhausted")
        budget["spent"] += 1
        observed = stage1._http(stage1.COMPLETIONS_ENDPOINT, method="POST",
                                body=canonical_bytes(body), timeout=900)
        if observed.get("status") == 429 and not (observed.get("body") or {}).get("choices"):
            if attempt < MAX_RETRIES:
                continue  # explicit pre-generation 429, no completion, no execution evidence
        return observed
    raise ReadinessError("pre-generation 429 persisted beyond the frozen retry allowance")


def _reasoning_tokens(body: Mapping[str, Any]) -> int | None:
    usage = body.get("usage") if isinstance(body.get("usage"), Mapping) else {}
    detail = usage.get("completion_tokens_details")
    if isinstance(detail, Mapping) and isinstance(detail.get("reasoning_tokens"), int):
        return detail["reasoning_tokens"]
    return usage.get("reasoning_tokens") if isinstance(usage.get("reasoning_tokens"), int) else None


def execute() -> dict[str, Any]:
    if RESULT_PATH.exists():
        raise ReadinessError("a readiness result already exists; this gate is not redrawn")
    # The gate may only run once its predecessors are commits at HEAD: M117's calibration and
    # closure, this milestone's preregistration, the fixed route and this apparatus itself. A
    # freeze written moments earlier is not a freeze, so nothing here accepts an in-memory record.
    permission = chronology.assert_stage_permitted("readiness_run")
    frozen = plan()
    budget = {"spent": 0}
    observations: list[dict[str, Any]] = []
    identity: dict[str, Any] | None = None
    verdict = "ready"
    DIRECTORY.mkdir(parents=True, exist_ok=True)

    def _persist_ledger(state: str, note: str = "") -> None:
        """Write what has been measured so far.

        Revision 1 persisted nothing until the end, so when it aborted on its own budget
        arithmetic it lost every observation it had already paid for -- the record could not say
        what the route had done. That is M115's failure mode, and an abort is exactly when the
        evidence matters most.
        """
        LEDGER_PATH.write_bytes(canonical_bytes({
            "schema": "m118-readiness-ledger-v1",
            "milestone": "M118", "hypothesis": "H63", "development": True,
            "state": state, "note": note,
            "plan_sha256": frozen["plan_sha256"],
            "route": fixed.route(),
            "identity": identity,
            "observations": observations,
            "requests_spent": budget["spent"],
            "budget": frozen["budget"],
            "raw_completion_persisted": False,
        }) + b"\n")

    _persist_ledger("started")
    for probe in probes.build_matrix(m116._census()):
        try:
            observed = _send(probe["prompt"], probe["schema"],
                             "m118_readiness_%s" % probe["name"], PROBE_MAX_TOKENS, budget)
        except ReadinessError as exc:
            _persist_ledger("instrument_aborted", "probing %s: %s" % (probe["name"], exc))
            raise
        body = observed.get("body") if isinstance(observed.get("body"), Mapping) else {}
        if identity is None:
            identity = fixed.identity_holds(body)
        diagnosis = m116.diagnose(probe, observed,
                                  requested_model=fixed.REQUESTED_MODEL,
                                  requested_provider=fixed.PROVIDER)
        diagnosis["reasoning_tokens"] = _reasoning_tokens(body)
        observations.append(diagnosis)
        _persist_ledger("probing")

    unenforced = sorted({o["feature_class"] for o in observations
                         if o["probe"] != "combined" and o["outcome"] not in m116.ENFORCED})
    combined = next((o for o in observations if o["probe"] == "combined"), None)
    combined_conforms = bool(combined and combined.get("outcome") == "conforming")
    reasoning_intended = all(
        o.get("reasoning_tokens") is not None and o["reasoning_tokens"] <= MAX_REASONING_TOKENS
        for o in observations)

    stress_record: dict[str, Any] = {"ran": False}
    if identity and identity["holds"] and not unenforced and combined_conforms:
        try:
            observed = _send(stress.STRESS_PROMPT, stress.build_stress_schema(),
                             "m118_readiness_stress", STRESS_MAX_TOKENS, budget)
        except ReadinessError as exc:
            _persist_ledger("instrument_aborted", "stress: %s" % exc)
            raise
        body = observed.get("body") if isinstance(observed.get("body"), Mapping) else {}
        choices = body.get("choices") if isinstance(body.get("choices"), list) else []
        first = choices[0] if choices and isinstance(choices[0], Mapping) else {}
        message = first.get("message") if isinstance(first.get("message"), Mapping) else {}
        usage = body.get("usage") if isinstance(body.get("usage"), Mapping) else {}
        tokens = usage.get("completion_tokens")
        conforms = False
        content = message.get("content")
        if isinstance(content, str):
            try:
                conforms = schema_tools.instance_is_valid(
                    json.loads(content), stress.build_stress_schema())[0]
            except ValueError:
                conforms = False
        stress_record = {
            "ran": True,
            "http_status": observed.get("status"),
            "finish_reason": first.get("finish_reason") if isinstance(
                first.get("finish_reason"), str) else None,
            "completion_tokens": tokens if isinstance(tokens, int) else None,
            "reasoning_tokens": _reasoning_tokens(body),
            "schema_conforms": conforms,
            "raw_completion_persisted": False,
        }
        stress_record["holds"] = bool(
            stress_record["http_status"] == 200
            and stress_record["finish_reason"] == "stop"
            and conforms
            and isinstance(tokens, int) and tokens > STRESS_MIN_COMPLETION_TOKENS)

    if identity is None or not identity["holds"]:
        verdict = "not_ready_identity"
    elif unenforced or not combined_conforms:
        verdict = "not_ready_features"
    elif not reasoning_intended:
        verdict = "not_ready_reasoning"
    elif not stress_record.get("holds"):
        verdict = "not_ready_stress"

    result = {
        "schema": RESULT_SCHEMA,
        "milestone": "M118", "hypothesis": "H63", "development": True,
        "is_a_qualifying_call": False, "qualifying_input_was_sent": False,
        "is_evidence_for_h63": False, "advances_a_generality_gate": False,
        "plan_sha256": frozen["plan_sha256"],
        "chronology": permission,
        "route": fixed.route(),
        "observed_at": stage1._now(),
        "identity": identity or {"holds": False, "failed_checks": ["no_response"]},
        "required_feature_classes": required_feature_classes(),
        "unenforced_feature_classes": unenforced,
        "combined_probe_conforms": combined_conforms,
        "reasoning_state_as_intended": reasoning_intended,
        "token_capacity_stress": stress_record,
        "observations": observations,
        "requests_spent": budget["spent"],
        "raw_completion_persisted": False,
        "verdict": verdict,
        "ready": verdict == "ready",
        "result_sha256": "",
    }
    result["result_sha256"] = sha256_hex(
        canonical_bytes({k: v for k, v in result.items() if k != "result_sha256"}))
    LEDGER_PATH.write_bytes(canonical_bytes(result) + b"\n")
    RESULT_PATH.write_bytes(canonical_bytes(result) + b"\n")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", action="store_true")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if args.plan:
        print(json.dumps(plan(), indent=2, sort_keys=True))
        return 0
    if args.execute:
        result = execute()
        print(json.dumps({"verdict": result["verdict"], "ready": result["ready"],
                          "requests_spent": result["requests_spent"],
                          "result_sha256": result["result_sha256"]}, indent=2, sort_keys=True))
        return 0 if result["ready"] else 1
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
