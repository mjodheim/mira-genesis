#!/usr/bin/env python3
"""M116 DEVELOPMENT-only structured-output capability matrix on the fixed H61 route.

The first DEVELOPMENT stress attempt established that the route returns HTTP 200, stops
voluntarily at 18 % of the output budget with zero reasoning tokens, and emits output that does not
satisfy a census-dominating strict schema. It could not say *which* constraint was ignored: the
audit collapsed every outcome into one boolean and persisted no discriminating evidence.

This harness answers that question and nothing else. It sends small synthetic probes, each
isolating one schema feature class that the frozen carrier census proves the real schema relies
upon, and records for each one whether content arrived, whether it parsed, whether the top-level
shape was right, whether it satisfied the schema, and -- when it did not -- the first failing
keyword with its schema and instance locations.

It is not a scientific observation:

* the H61 qualifying input is never sent, and is checked against before any request;
* no probe carries carrier vocabulary;
* no probe result can advance a generality gate;
* the qualifying invocation count stays at zero.

Rules fixed before the first call, and not adjustable afterwards:

* the probe sequence, its order and its length are derived from the committed census;
* per probe, at most three physical attempts, and attempt 2 or 3 only after an explicit HTTP 429
  carrying no completion and no evidence that the model executed;
* the first materialized response is the observation for that probe -- never redrawn because it
  violated the schema, never repaired, never regenerated;
* the combined probe is reached only if every isolated probe passed;
* the decision rule below is evaluated mechanically from the recorded outcomes.

    python scripts/audit_m116_capability_matrix.py --plan     # print the frozen plan, no network
    python scripts/audit_m116_capability_matrix.py --execute  # run it once
"""

from __future__ import annotations

import argparse
import fcntl
import http.client
import json
import os
import ssl
import sys
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from metamorphosis import m116_capability_probes as probes  # noqa: E402
from metamorphosis import m116_schema as schema_tools  # noqa: E402
from metamorphosis import m116_telemetry as telemetry  # noqa: E402
from metamorphosis.blind_bank_protocol import canonical_bytes, sha256_hex  # noqa: E402

MODEL = "deepseek/deepseek-v4-flash-0731"
CANONICAL_CHECKPOINT = "deepseek/deepseek-v4-flash-20260731"
PROVIDER = "Alibaba"
ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
SECRET_VARIABLE = "OPENROUTER_API_KEY"

MAX_TOKENS = 131072
MAX_PHYSICAL_ATTEMPTS = 3
RETRY_WAIT_SECONDS = 60

CENSUS_PATH = ROOT / "experiments" / "M116" / "CARRIER_SCHEMA_CENSUS.json"
REPORT_PATH = ROOT / "experiments" / "M116" / "CAPABILITY_MATRIX_DEVELOPMENT.json"
LEDGER_PATH = ROOT / "experiments" / "M116" / "CAPABILITY_MATRIX_DEVELOPMENT_LEDGER.json"
_GIT = ROOT / ".git"
LOCK_PATH = (_GIT / "m116-capability-matrix.lock") if _GIT.is_dir() else ROOT / ".m116-matrix.lock"

QUALIFYING_INPUT_PATHS = (
    ROOT / "experiments" / "M113" / "QUALIFYING_INPUT.txt",
    ROOT / "experiments" / "M114" / "QUALIFYING_INPUT.txt",
    ROOT / "experiments" / "M115" / "QUALIFYING_INPUT.txt",
)

REPORT_SCHEMA = "m116-capability-matrix-development-v1"
LEDGER_SCHEMA = "m116-capability-matrix-development-ledger-v1"

# The outcome vocabulary. Every probe lands in exactly one, and every one is reachable.
OUTCOMES = (
    "conforming",
    "truncated_completion",
    "invalid_json",
    "wrong_top_level_type",
    "enum_violation",
    "pattern_violation",
    "min_items_violation",
    "max_items_violation",
    "required_violation",
    "additional_properties_violation",
    "bounds_violation",
    "type_violation",
    "nesting_violation",
    "other_schema_violation",
    "missing_completion",
    "transport_or_provider_failure",
    "not_attempted",
)

# Which failing keyword maps to which outcome. Derived from the validator's vocabulary so that a
# new keyword cannot silently fall into "other".
_KEYWORD_OUTCOME = {
    "enum": "enum_violation",
    "pattern": "pattern_violation",
    "minItems": "min_items_violation",
    "maxItems": "max_items_violation",
    "required": "required_violation",
    "additionalProperties": "additional_properties_violation",
    "minimum": "bounds_violation",
    "maximum": "bounds_violation",
    "exclusiveMinimum": "bounds_violation",
    "exclusiveMaximum": "bounds_violation",
    "minLength": "bounds_violation",
    "maxLength": "bounds_violation",
    "type": "type_violation",
    "uniqueItems": "other_schema_violation",
}

# The two probes whose whole subject is structure. For these, a type or required failure *is* a
# nesting shortfall; for every other probe a wrong scalar type is a type violation and calling it
# "nesting" would corrupt the capability profile with a structural claim the evidence lacks.
_STRUCTURAL_FEATURES = ("max_nesting_depth", "array_of_object_levels")

# Outcomes that count as the feature being enforced.
ENFORCED = ("conforming",)


class CapabilityMatrixError(RuntimeError):
    """The matrix cannot be run or resumed without guessing or crossing a boundary."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _secret() -> str:
    secret = os.environ.get(SECRET_VARIABLE)
    if not secret:
        raise CapabilityMatrixError(f"{SECRET_VARIABLE} is not set; no network request was made")
    return secret


def _census() -> dict[str, Any]:
    try:
        return json.loads(CENSUS_PATH.read_text(encoding="utf-8"))["frozen_carrier_census"]
    except (OSError, ValueError, KeyError) as exc:
        raise CapabilityMatrixError("cannot read the committed carrier census: %s" % exc)


def matrix() -> list[dict[str, Any]]:
    built = probes.build_matrix(_census())
    probes.assert_non_carrier(built)
    _assert_non_qualifying(built)
    return built


def _assert_non_qualifying(built: list[dict[str, Any]]) -> None:
    """No probe may carry, resemble or overlap the H61 qualifying input."""
    for probe in built:
        prompt = probe["prompt"]
        for path in QUALIFYING_INPUT_PATHS:
            if not path.is_file():
                continue
            qualifying = path.read_text("utf-8", errors="replace")
            if sha256_hex(prompt.encode("utf-8")) == sha256_hex(qualifying.encode("utf-8")):
                raise CapabilityMatrixError("a probe prompt equals a qualifying carrier input")
            if prompt.strip() in qualifying or qualifying.strip() in prompt:
                raise CapabilityMatrixError("a probe prompt overlaps a qualifying carrier input")


def request_body(probe: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "model": MODEL,
        "messages": [{"role": "user", "content": probe["prompt"]}],
        "provider": {"only": [PROVIDER], "allow_fallbacks": False, "require_parameters": True},
        "reasoning": {"effort": "none"},
        "response_format": {"type": "json_schema", "json_schema": {
            "name": "m116_probe_%s" % probe["name"], "strict": True, "schema": probe["schema"]}},
        "max_tokens": MAX_TOKENS,
        "seed": 0,
        "stream": False,
        "temperature": 1.0,
    }


def plan() -> dict[str, Any]:
    """The frozen plan. A pure function of the committed census; no network, no side effects."""
    built = matrix()
    census = _census()
    entries = [{
        "index": index,
        "name": probe["name"],
        "feature_class": probe["feature_class"],
        "detects": probe["detects"],
        "isolated": probe["name"] != "combined",
        "schema_sha256": sha256_hex(canonical_bytes(probe["schema"])),
        "prompt_sha256": sha256_hex(probe["prompt"].encode("utf-8")),
        "request_body_sha256": sha256_hex(canonical_bytes(request_body(probe))),
    } for index, probe in enumerate(built, start=1)]
    record = {
        "schema": "m116-capability-matrix-plan-v1",
        "milestone": "M116",
        "hypothesis": "H61",
        "development_only": True,
        "is_a_qualifying_call": False,
        "qualifying_input_was_sent": False,
        "route": {"model": MODEL, "canonical_checkpoint": CANONICAL_CHECKPOINT,
                  "provider": PROVIDER, "route_is_unchanged_from_m116": True},
        "required_feature_classes": probes.required_feature_classes(census),
        "derived_from": "experiments/M116/CARRIER_SCHEMA_CENSUS.json",
        "probe_count": len(entries),
        "probes": entries,
        "max_physical_attempts_per_probe": MAX_PHYSICAL_ATTEMPTS,
        "retry_wait_seconds": RETRY_WAIT_SECONDS,
        "retry_is_permitted_only_for": "explicit HTTP 429 with no completion and no execution evidence",
        "content_dependent_redraw_permitted": False,
        "repair_permitted": False,
        "probe_adaptation_after_observation_permitted": False,
        "combined_probe_runs_only_if_every_isolated_probe_passes": True,
        "outcome_vocabulary": list(OUTCOMES),
        "decision_rule": {
            "case_a": "every required isolated capability enforced AND the combined probe conforms",
            "case_a_consequence": "route retained; prepare an explicitly reviewed revised M116 "
                                  "stress candidate; at most one further full stress audit",
            "case_b": "any required capability not enforced",
            "case_b_consequence": "classify the M116 instrument family unsuitable for H61; "
                                  "preserve H61 untested; close the corrective-replication path; "
                                  "propose M117/H62 with a prospective route-qualification rule",
            "weakening_the_carrier_schema_permitted": False,
            "changing_route_inside_h61_permitted": False,
        },
        "plan_sha256": "",
    }
    record["plan_sha256"] = sha256_hex(
        canonical_bytes({k: v for k, v in record.items() if k != "plan_sha256"}))
    return record


# ---------------------------------------------------------------------------------------------
# Transport
# ---------------------------------------------------------------------------------------------

def _connection(url: str, timeout: int):
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise CapabilityMatrixError("capability matrix endpoint must use https")
    context = ssl.create_default_context()
    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    if proxy:
        via = urllib.parse.urlsplit(proxy if "://" in proxy else "http://" + proxy)
        conn = http.client.HTTPSConnection(via.hostname, via.port or 80, timeout=timeout,
                                           context=context)
        conn.set_tunnel(parsed.hostname, parsed.port or 443)
    else:
        conn = http.client.HTTPSConnection(parsed.hostname, parsed.port or 443, timeout=timeout,
                                           context=context)
    return conn, parsed


def _request(probe: Mapping[str, Any], *, timeout: int = 900) -> dict[str, Any]:
    secret = _secret()
    payload = canonical_bytes(request_body(probe))
    headers = {"Accept": "application/json", "Authorization": f"Bearer {secret}",
               "Content-Type": "application/json", "X-OpenRouter-Metadata": "enabled",
               "X-OpenRouter-Cache": "false"}
    started = _now()
    conn = None
    began = False
    try:
        conn, parsed = _connection(ENDPOINT, timeout)
        began = True
        conn.request("POST", parsed.path or "/", body=payload, headers=headers)
        response = conn.getresponse()
        raw = response.read()
        status = response.status
        safe_headers = {k.lower(): v for k, v in response.getheaders()
                        if k.lower() in {"date", "retry-after", "x-generation-id"}}
    except Exception as exc:  # noqa: BLE001 -- ambiguity is evidence, not a crash
        return {"status": None, "body": None, "response_bytes": None,
                "started_at": started, "finished_at": _now(), "response_headers": {},
                "transport_failure_class": type(exc).__name__,
                "model_execution_cannot_be_excluded": began}
    finally:
        if conn is not None:
            conn.close()
    try:
        body = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        body = None
    return {"status": status, "body": body if isinstance(body, Mapping) else None,
            "response_bytes": len(raw), "started_at": started, "finished_at": _now(),
            "response_headers": safe_headers, "transport_failure_class": None,
            "model_execution_cannot_be_excluded": False}


# ---------------------------------------------------------------------------------------------
# Diagnosis: what happened to one probe, without disclosing what the model said
# ---------------------------------------------------------------------------------------------

def diagnose(probe: Mapping[str, Any], observed: Mapping[str, Any]) -> dict[str, Any]:
    """Classify one probe observation into the frozen outcome vocabulary."""
    body = observed.get("body") if isinstance(observed.get("body"), Mapping) else {}
    record = telemetry.extract(
        status=observed.get("status"), body=body,
        response_bytes=observed.get("response_bytes"),
        headers=observed.get("response_headers"),
        requested_model=MODEL, requested_provider=PROVIDER,
        transport_failure_class=observed.get("transport_failure_class"),
    )
    telemetry.assert_no_carrier_content(record)

    result: dict[str, Any] = {
        "schema": "m116-capability-probe-observation-v1",
        "probe": probe["name"],
        "feature_class": probe["feature_class"],
        "development": True,
        "is_a_qualifying_call": False,
        "http_status": record["http_status"],
        "finish_reason": record["finish_reason"],
        "completion_tokens": record["completion_tokens"],
        "reasoning_tokens": record["reasoning_tokens"],
        "response_bytes": record["response_bytes"],
        "content_present": record["content_present"],
        "content_bytes": record["content_bytes"],
        "served_model": record["served_model"],
        "served_provider": record["served_provider"],
        "content_parses_as_json": False,
        "top_level_type_correct": False,
        "schema_conforms": False,
        "first_failing_keyword": "",
        "failing_schema_location": "",
        "failing_instance_path": "",
        "observed_top_level_keys": 0,
        "observed_depth": 0,
        "raw_completion_persisted": False,
        "outcome": "not_attempted",
    }

    if observed.get("transport_failure_class") or record["http_status"] != 200:
        result["outcome"] = "transport_or_provider_failure"
        return result
    if not record["content_present"]:
        result["outcome"] = "missing_completion"
        return result

    # Output-budget termination is decided BEFORE parsing, on affirmative finish-reason evidence.
    # A truncated completion also fails to parse, and letting the parse failure absorb it would
    # reproduce exactly the M115 defect this milestone exists to correct: a probe that ran out of
    # budget would be recorded as "the route emitted invalid JSON", which is a different and much
    # stronger claim than the evidence supports.
    if record["finish_reason"] in telemetry.BUDGET_FINISH_REASONS:
        result["outcome"] = "truncated_completion"
        return result

    choices = body.get("choices") or []
    content = choices[0]["message"]["content"] if choices else ""
    try:
        parsed = json.loads(content)
    except ValueError:
        result["outcome"] = "invalid_json"
        return result
    result["content_parses_as_json"] = True

    expected_type = probe["schema"].get("type")
    if expected_type == "object" and not isinstance(parsed, dict):
        result["outcome"] = "wrong_top_level_type"
        return result
    result["top_level_type_correct"] = True
    if isinstance(parsed, dict):
        result["observed_top_level_keys"] = len(parsed)
    result["observed_depth"] = _depth(parsed)

    verdict = schema_tools.describe_violation(parsed, probe["schema"])
    if verdict["conforms"]:
        result["schema_conforms"] = True
        result["outcome"] = "conforming"
        return result
    result["first_failing_keyword"] = verdict["keyword"]
    result["failing_schema_location"] = verdict["schema_location"]
    result["failing_instance_path"] = verdict["instance_path"]
    outcome = _KEYWORD_OUTCOME.get(verdict["keyword"], "other_schema_violation")
    if probe["feature_class"] in _STRUCTURAL_FEATURES and outcome in (
        "type_violation", "required_violation"
    ):
        # A structural probe that failed on type or a missing link did not reach the depth the
        # schema demands, which is precisely the capability under test.
        outcome = "nesting_violation"
    result["outcome"] = outcome
    return result


def _depth(value: Any, level: int = 0) -> int:
    if isinstance(value, dict):
        return max([level] + [_depth(v, level + 1) for v in value.values()])
    if isinstance(value, list):
        return max([level] + [_depth(v, level + 1) for v in value])
    return level


def decide(observations: list[dict[str, Any]]) -> dict[str, Any]:
    """Apply the precommitted decision rule. Pure function of the recorded outcomes."""
    isolated = [o for o in observations if o["probe"] != "combined"]
    combined = next((o for o in observations if o["probe"] == "combined"), None)
    unenforced = sorted({o["feature_class"] for o in isolated if o["outcome"] not in ENFORCED})
    every_isolated_passed = bool(isolated) and not unenforced
    # An entry exists for the combined probe even when it was never sent, so "ran" must mean the
    # request happened -- not merely that the record has a row for it.
    combined_ran = bool(combined and combined.get("outcome") != "not_attempted")
    combined_conforms = bool(combined and combined["outcome"] == "conforming")
    case_a = every_isolated_passed and combined_conforms
    return {
        "schema": "m116-capability-matrix-decision-v1",
        "every_isolated_capability_enforced": every_isolated_passed,
        "unenforced_feature_classes": unenforced,
        "combined_probe_ran": combined_ran,
        "combined_probe_conforms": combined_conforms,
        "case": "A" if case_a else "B",
        "route_validated_for_h61": case_a,
        "consequence": (
            "route retained; prepare an explicitly reviewed revised M116 stress candidate"
            if case_a else
            "the fixed M116 route does not enforce every required schema capability; classify the "
            "M116 instrument family unsuitable for H61, preserve H61 untested, close the "
            "corrective-replication path and propose M117/H62"
        ),
        "h61_remains_untested": True,
        "qualifying_calls": 0,
    }


# ---------------------------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------------------------

class _Lock:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._handle = None

    def __enter__(self):
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._handle = self._path.open("w")
        try:
            fcntl.flock(self._handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self._handle.close()
            raise CapabilityMatrixError("another capability-matrix run holds the lock")
        return self

    def __exit__(self, *exc):
        if self._handle is not None:
            fcntl.flock(self._handle.fileno(), fcntl.LOCK_UN)
            self._handle.close()


def _write(path: Path, record: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(record) + b"\n")


def _safe_diagnose(probe: Mapping[str, Any], observed: Mapping[str, Any]) -> dict[str, Any]:
    """Diagnose, converting an unexpected response shape into evidence instead of a crash.

    A crash mid-matrix would abort before the report is written, leaving the run resumable and the
    already-sent probes re-sendable. Failing closed here keeps one observation per probe.
    """
    try:
        return diagnose(probe, observed)
    except Exception as exc:  # noqa: BLE001 -- an unreadable response is an observation
        return {
            "schema": "m116-capability-probe-observation-v1",
            "probe": probe["name"], "feature_class": probe["feature_class"],
            "development": True, "is_a_qualifying_call": False,
            "outcome": "transport_or_provider_failure",
            "content_present": False, "completion_tokens": None,
            "raw_completion_persisted": False,
            "why": "the response could not be diagnosed: %s" % type(exc).__name__,
        }


def _run_probe(probe: Mapping[str, Any]) -> dict[str, Any]:
    """One probe, under the frozen per-probe delivery rule."""
    attempts = 0
    while True:
        attempts += 1
        observed = _request(probe)
        result = _safe_diagnose(probe, observed)
        result["physical_attempts"] = attempts

        retryable = (
            observed.get("status") == 429
            and not observed.get("model_execution_cannot_be_excluded")
            and not result.get("content_present")
            and result.get("completion_tokens") in (None, 0)
        )
        if not retryable or attempts >= MAX_PHYSICAL_ATTEMPTS:
            result["retry_permitted"] = False
            return result
        time.sleep(RETRY_WAIT_SECONDS)


def execute() -> dict[str, Any]:
    frozen = plan()
    _secret()
    with _Lock(LOCK_PATH):
        if REPORT_PATH.exists():
            raise CapabilityMatrixError(
                "the M116 capability matrix already has a report; it is not redrawn")
        built = matrix()
        # Resume rather than re-send. A probe that already has an observation in the ledger keeps
        # it: its one permitted delivery is spent, and repeating it would be a redraw.
        observations: list[dict[str, Any]] = []
        started = _now()
        if LEDGER_PATH.is_file():
            try:
                previous = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                raise CapabilityMatrixError("cannot read the capability-matrix ledger: %s" % exc)
            if previous.get("plan_sha256") != frozen["plan_sha256"]:
                raise CapabilityMatrixError(
                    "the existing ledger belongs to a different frozen plan")
            observations = list(previous.get("observations") or [])
            started = previous.get("started_at") or started
        already = {o["probe"] for o in observations}
        ledger = {"schema": LEDGER_SCHEMA, "milestone": "M116", "hypothesis": "H61",
                  "development": True, "plan_sha256": frozen["plan_sha256"],
                  "started_at": started, "observations": observations}

        for probe in built:
            if probe["name"] in already:
                continue
            if probe["name"] == "combined":
                unenforced = [o for o in observations if o["outcome"] not in ENFORCED]
                if unenforced:
                    observations.append({
                        "schema": "m116-capability-probe-observation-v1",
                        "probe": "combined", "feature_class": "combined", "development": True,
                        "is_a_qualifying_call": False, "outcome": "not_attempted",
                        "raw_completion_persisted": False,
                        "why": "an isolated prerequisite did not pass, so the combined probe is "
                               "not reached under the frozen rule",
                    })
                    _write(LEDGER_PATH, ledger)
                    break
            observations.append(_run_probe(probe))
            _write(LEDGER_PATH, ledger)

        ledger["finished_at"] = _now()
        _write(LEDGER_PATH, ledger)

        report = {
            "schema": REPORT_SCHEMA,
            "milestone": "M116", "hypothesis": "H61", "development": True,
            "is_a_qualifying_call": False, "qualifying_input_was_sent": False,
            "qualifying_calls": 0, "h61_frozen": False, "h61_bank_exists": False,
            "route": frozen["route"],
            "plan_sha256": frozen["plan_sha256"],
            "required_feature_classes": frozen["required_feature_classes"],
            "observations": observations,
            "decision": decide(observations),
            "raw_completion_persisted": False,
            "report_sha256": "",
        }
        report["report_sha256"] = sha256_hex(
            canonical_bytes({k: v for k, v in report.items() if k != "report_sha256"}))
        _write(REPORT_PATH, report)
        return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", action="store_true", help="print the frozen plan; no network")
    parser.add_argument("--execute", action="store_true", help="run the matrix once")
    args = parser.parse_args(argv)
    if args.plan == args.execute:
        parser.error("choose exactly one of --plan or --execute")
    if args.plan:
        print(json.dumps(plan(), indent=2, sort_keys=True))
        return 0
    report = execute()
    print(json.dumps({"case": report["decision"]["case"],
                      "route_validated_for_h61": report["decision"]["route_validated_for_h61"],
                      "unenforced": report["decision"]["unenforced_feature_classes"],
                      "report": str(REPORT_PATH.relative_to(ROOT))}, sort_keys=True))
    return 0 if report["decision"]["route_validated_for_h61"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
