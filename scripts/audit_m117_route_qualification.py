#!/usr/bin/env python3
"""M117 Stage 1: qualify a generation route by measurement, before any H62 specification exists.

M116 closed because its fixed route enforced none of the nine schema feature classes the frozen
carrier schema relies upon -- while the catalogue advertised `supports_structured_outputs: true`
for it. Stage 1 is built around that fact: **a catalogue claim is not evidence, only measured
enforcement is.** Declared capability bounds which candidates are worth spending budget on, and
decides nothing.

The order of operations is the whole safeguard:

    1. the apparatus is frozen and committed          (before any request)
    2. the catalogue is read and snapshotted          (metadata only; no generation)
    3. the candidate universe is derived and committed with its digest and its total order
    4. candidates are probed in that order, using the M116 capability matrix unchanged
    5. the first qualifier in the frozen order is the selection

Nothing observed at step 4 can change the order fixed at step 3, the thresholds fixed at step 1, or
which candidate comes next. No provider may be added once probing begins.

Stage 1 is DEVELOPMENT. It is not evidence for H62, it sends no qualifying input, and it cannot
advance a generality gate.

    python scripts/audit_m117_route_qualification.py --plan       # frozen rules, no network
    python scripts/audit_m117_route_qualification.py --catalogue  # snapshot + commit the universe
    python scripts/audit_m117_route_qualification.py --execute    # probe and select
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
from metamorphosis import m116_stress_schema as stress  # noqa: E402
from metamorphosis import m117_route_qualification as rule  # noqa: E402
from metamorphosis.blind_bank_protocol import canonical_bytes, sha256_hex  # noqa: E402
from scripts import audit_m116_capability_matrix as m116  # noqa: E402

SECRET_VARIABLE = "OPENROUTER_API_KEY"
MODELS_ENDPOINT = "https://openrouter.ai/api/v1/models"
COMPLETIONS_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"

DIRECTORY = ROOT / "experiments" / "M117"
UNIVERSE_PATH = DIRECTORY / "STAGE1_CANDIDATE_UNIVERSE.json"
CATALOGUE_PATH = DIRECTORY / "STAGE1_CATALOGUE_SNAPSHOT.json"
REPORT_PATH = DIRECTORY / "STAGE1_ROUTE_QUALIFICATION.json"
LEDGER_PATH = DIRECTORY / "STAGE1_ROUTE_QUALIFICATION_LEDGER.json"
_GIT = ROOT / ".git"
LOCK_PATH = (_GIT / "m117-stage1.lock") if _GIT.is_dir() else ROOT / ".m117-stage1.lock"

# Catalogue reads are metadata GETs: no generation, no completion tokens, no carrier. They are
# bounded anyway, in a deterministic alphabetical order fixed here, so that the universe cannot
# depend on the order the catalogue happens to return.
CATALOGUE_MODEL_CEILING = 60

# The inherited matrix sends this budget, so M117 sends it too. A smaller cap would make any
# truncation this harness's artifact rather than the route's behaviour.
PROBE_MAX_TOKENS = 131072

# Token-capacity stress, run only for a candidate that has already enforced every feature class.
STRESS_MAX_TOKENS = 131072
STRESS_MIN_COMPLETION_TOKENS = 32000

PLAN_SCHEMA = "m117-stage1-plan-v1"

# Attempt 01 read three catalogue fields out of places this API does not populate. It reached no
# candidate, sent no generation request and produced no selection; it is preserved verbatim under
# experiments/M117/ATTEMPT_01_INSTRUMENT_ABORT/ as an instrument abort, not as a result.
#
# This revision changes extraction only. Every threshold, ordering key, tie-break, qualification
# clause and budget bound is the frozen value attempt 01 carried, and the decision rule module is
# byte-for-byte unchanged -- tests/test_m117_apparatus_revision.py pins both. The repair is forced
# by the API's response shape rather than by any candidate's values: the defect nulled the metric
# for 282/282 endpoints uniformly, so it could not have favoured or disfavoured any candidate, and
# the corrected checkpoint field reproduces the checkpoint M116 independently recorded.
APPARATUS_REVISION = 5
SUPERSEDED_PLAN_SHA256 = "47ff587ff36e994a498ae8d63b6cc185ded94a7b1c9f429290a754b3a1181564"
REVISION_RATIONALE = (
    "two data-flow defects, both derivable from the request body without any observation and both "
    "present since attempt 01: derive_universe dropped supported_parameters, so declares_reasoning "
    "read a field the candidate did not carry, always answered False, and the reasoning-off control "
    "the plan promises was never sent on any request in any attempt while 58 observations recorded "
    "reasoning tokens being consumed; and eligible rows agreeing on model, provider and reasoning "
    "declaration produce an identical request, so 15 of 90 rows reserved budget for an experiment "
    "already run -- attempt 03 spent its final slot re-probing a route it had probed at position 3. "
    "Parameters are now carried and duplicates are marked rather than dropped, keeping every "
    "eligible endpoint in the record. No threshold, ordering key, tie-break, budget bound or "
    "qualification clause changed"
)
REPORT_SCHEMA = "m117-stage1-route-qualification-v1"
LEDGER_SCHEMA = "m117-stage1-ledger-v1"


class Stage1Error(RuntimeError):
    """Stage 1 cannot proceed without guessing or crossing a boundary."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _secret() -> str:
    secret = os.environ.get(SECRET_VARIABLE)
    if not secret:
        raise Stage1Error(f"{SECRET_VARIABLE} is not set; no network request was made")
    return secret


def _connection(url: str, timeout: int):
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise Stage1Error("Stage 1 endpoints must use https")
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


def _http(url: str, *, method: str = "GET", body: bytes | None = None,
          timeout: int = 300) -> dict[str, Any]:
    secret = _secret()
    headers = {"Accept": "application/json", "Authorization": f"Bearer {secret}"}
    if body is not None:
        headers["Content-Type"] = "application/json"
        headers["X-OpenRouter-Metadata"] = "enabled"
        headers["X-OpenRouter-Cache"] = "false"
    started = _now()
    conn = None
    began = False
    try:
        conn, parsed = _connection(url, timeout)
        began = True
        path = parsed.path or "/"
        if parsed.query:
            path = "%s?%s" % (path, parsed.query)
        conn.request(method, path, body=body, headers=headers)
        response = conn.getresponse()
        raw = response.read()
        status = response.status
        safe_headers = {k.lower(): v for k, v in response.getheaders()
                        if k.lower() in {"date", "retry-after", "x-generation-id"}}
    except Exception as exc:  # noqa: BLE001 -- ambiguity is evidence, not a crash
        return {"status": None, "body": None, "response_bytes": None, "started_at": started,
                "finished_at": _now(), "response_headers": {},
                "transport_failure_class": type(exc).__name__,
                "model_execution_cannot_be_excluded": began and body is not None}
    finally:
        if conn is not None:
            conn.close()
    try:
        decoded = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        decoded = None
    return {"status": status, "body": decoded if isinstance(decoded, Mapping) else None,
            "response_bytes": len(raw), "started_at": started, "finished_at": _now(),
            "response_headers": safe_headers, "transport_failure_class": None,
            "model_execution_cannot_be_excluded": False}


# ---------------------------------------------------------------------------------------------
# The frozen plan
# ---------------------------------------------------------------------------------------------

def plan() -> dict[str, Any]:
    """Every Stage 1 rule, as a pure function of committed code. No network, no side effects."""
    matrix = m116.plan()
    record = {
        "schema": PLAN_SCHEMA,
        "milestone": "M117", "hypothesis": "H62",
        "stage": 1, "development_only": True,
        "is_a_qualifying_call": False, "qualifying_input_was_sent": False,
        "apparatus_revision": APPARATUS_REVISION,
        "supersedes_plan_sha256": SUPERSEDED_PLAN_SHA256,
        "revision_rationale": REVISION_RATIONALE,
        "catalogue_source": MODELS_ENDPOINT,
        "catalogue_model_ceiling": CATALOGUE_MODEL_CEILING,
        "catalogue_order": "model id ascending, fixed here so the universe cannot depend on the "
                           "order the catalogue returns",
        "eligibility": {
            "bounds_budget_never_qualifies": True,
            "minimum_uptime_last_1d": rule.MINIMUM_UPTIME_LAST_1D,
            "minimum_uptime_last_30m": rule.MINIMUM_UPTIME_LAST_30M,
            "minimum_max_completion_tokens": rule.MINIMUM_MAX_COMPLETION_TOKENS,
            "required_supported_parameters": list(rule.REQUIRED_SUPPORTED_PARAMETERS),
            "required_metrics": list(rule.REQUIRED_METRICS),
            "requires_declared_canonical_checkpoint": True,
            "exclusion_reasons": list(rule.EXCLUSION_REASONS),
        },
        "ordering": list(rule.RELIABILITY_ORDERING),
        "tie_break": "provider name ascending, then model id ascending",
        "selection_rule": "first qualifying candidate in the frozen reliability order",
        "capability_matrix": {
            "inherited_unchanged_from": "M116",
            "plan_sha256": matrix["plan_sha256"],
            "probe_count": matrix["probe_count"],
            "required_feature_classes": matrix["required_feature_classes"],
            "outcome_vocabulary": matrix["outcome_vocabulary"],
        },
        "probe_max_tokens": PROBE_MAX_TOKENS,
        "reasoning_control_rule": "reasoning effort none is sent exactly when the catalogue "
                                  "declares the parameter, because require_parameters would "
                                  "otherwise exclude an endpoint that does not accept it",
        "token_capacity_stress": {
            "runs_only_after_full_structural_qualification": True,
            "max_tokens": STRESS_MAX_TOKENS,
            "max_tokens_is_capped_at_the_candidates_declared_ceiling": True,
            "minimum_completion_tokens": STRESS_MIN_COMPLETION_TOKENS,
            "schema_sha256": sha256_hex(canonical_bytes(stress.build_stress_schema())),
        },
        "budget": {
            "max_requests_per_probe": rule.MAX_REQUESTS_PER_PROBE,
            "max_requests_per_candidate": rule.MAX_REQUESTS_PER_CANDIDATE,
            "global_request_ceiling": rule.GLOBAL_REQUEST_CEILING,
            "exceeding_the_ceiling_ends_stage_1_without_a_selection": True,
        },
        "retry": {
            "permitted_only_for": "explicit HTTP 429 with no completion and no execution evidence",
            "content_dependent_redraw_permitted": False,
            "repair_permitted": False,
            "resend_of_a_materialized_observation_permitted": False,
        },
        "prohibited": [
            "adding a candidate after probing begins",
            "manually preferring a candidate",
            "carrier quality as a selection input",
            "weakening a threshold after an observation",
            "changing a prompt or schema after an observation",
            "substituting a route",
            "treating M116's previous route specially",
        ],
        "stopping_rule": "probe in frozen order until a candidate qualifies or the global ceiling "
                         "is reached; if none qualifies, Stage 1 ends with no selection and H62 "
                         "is not created",
        "plan_sha256": "",
    }
    _assert_stress_is_satisfiable()
    record["plan_sha256"] = sha256_hex(
        canonical_bytes({k: v for k, v in record.items() if k != "plan_sha256"}))
    return record


# ---------------------------------------------------------------------------------------------
# Catalogue snapshot and candidate universe
# ---------------------------------------------------------------------------------------------

def _declared_capable(model: Mapping[str, Any]) -> bool:
    supported = model.get("supported_parameters")
    supported = set(supported) if isinstance(supported, list) else set()
    return set(rule.REQUIRED_SUPPORTED_PARAMETERS) <= supported


def _metric(endpoint: Mapping[str, Any], stats: Mapping[str, Any], name: str) -> Any:
    """Read a reliability metric from where this API actually publishes it: the endpoint itself."""
    value = endpoint.get(name)
    if value is None and isinstance(stats, Mapping):
        value = stats.get(name)
    return value


def snapshot_catalogue() -> dict[str, Any]:
    """Read the catalogue and commit it. Metadata only: no generation, no completion tokens."""
    if CATALOGUE_PATH.exists() or UNIVERSE_PATH.exists():
        raise Stage1Error("the Stage 1 catalogue snapshot already exists; it is not redrawn")
    frozen = plan()
    observed = _http(MODELS_ENDPOINT, timeout=120)
    if observed["status"] != 200 or not isinstance(observed["body"], Mapping):
        raise Stage1Error("could not read the model catalogue (status %s)" % observed["status"])
    models = observed["body"].get("data")
    if not isinstance(models, list):
        raise Stage1Error("the model catalogue has no data array")

    declared = sorted(
        (m for m in models if isinstance(m, Mapping) and _declared_capable(m)),
        key=lambda m: str(m.get("id") or ""),
    )
    considered = declared[:CATALOGUE_MODEL_CEILING]

    entries: list[dict[str, Any]] = []
    for model in considered:
        model_id = str(model.get("id"))
        detail = _http("%s/%s/endpoints" % (MODELS_ENDPOINT, model_id), timeout=120)
        data = (detail.get("body") or {}).get("data") if isinstance(detail.get("body"), Mapping) else None
        endpoints = data.get("endpoints") if isinstance(data, Mapping) else None
        if not isinstance(endpoints, list):
            continue
        for endpoint in endpoints:
            if not isinstance(endpoint, Mapping):
                continue
            # Reliability metrics are top-level fields on the endpoint object. Attempt 01 read
            # them out of a `stats` sub-object that this API does not return, which nulled
            # `uptime_last_1d` and `latency_last_30m_p50` for 282/282 endpoints and excluded the
            # whole universe on `missing_required_metric`. `stats` is kept only as a fallback.
            stats = endpoint.get("stats") if isinstance(endpoint.get("stats"), Mapping) else {}
            entries.append({
                "model": model_id,
                "provider": endpoint.get("provider_name") or endpoint.get("name"),
                # The router attests the selected endpoint as the model's dated canonical slug,
                # not the requested slug, the endpoint display name, or the quantization tag.
                # `model_variant_slug`, which attempt 01 read, is not a field this API returns.
                "canonical_checkpoint": model.get("canonical_slug"),
                "endpoint_tag": endpoint.get("tag"),
                "provider_found": True,
                "endpoint_available": endpoint.get("status") in (None, 0),
                "max_completion_tokens": endpoint.get("max_completion_tokens")
                or model.get("top_provider", {}).get("max_completion_tokens"),
                "context_length": endpoint.get("context_length"),
                "supported_parameters": endpoint.get("supported_parameters")
                or model.get("supported_parameters"),
                "uptime_last_1d": _metric(endpoint, stats, "uptime_last_1d"),
                "uptime_last_30m": _metric(endpoint, stats, "uptime_last_30m"),
                "latency_last_30m": _metric(endpoint, stats, "latency_last_30m"),
                "quantization": endpoint.get("quantization"),
            })

    record = {
        "schema": "m117-stage1-catalogue-snapshot-v1",
        "milestone": "M117", "stage": 1, "development": True,
        "observed_at": _now(),
        "plan_sha256": frozen["plan_sha256"],
        "catalogue_source": MODELS_ENDPOINT,
        "models_in_catalogue": len(models),
        "models_declaring_required_parameters": len(declared),
        "catalogue_model_ceiling": CATALOGUE_MODEL_CEILING,
        "models_considered": [str(m.get("id")) for m in considered],
        "endpoint_entries": entries,
        "declared_capability_is_not_evidence": True,
        "snapshot_sha256": "",
    }
    record["snapshot_sha256"] = sha256_hex(
        canonical_bytes({k: v for k, v in record.items() if k != "snapshot_sha256"}))
    DIRECTORY.mkdir(parents=True, exist_ok=True)
    CATALOGUE_PATH.write_bytes(canonical_bytes(record) + b"\n")

    universe = rule.derive_universe(entries)
    universe.update({
        "milestone": "M117", "stage": 1, "development": True,
        "plan_sha256": frozen["plan_sha256"],
        "catalogue_snapshot_sha256": record["snapshot_sha256"],
        "derived_at": _now(),
        "no_candidate_may_be_added_after_probing_begins": True,
        "universe_sha256": "",
    })
    universe["universe_sha256"] = sha256_hex(
        canonical_bytes({k: v for k, v in universe.items() if k != "universe_sha256"}))
    UNIVERSE_PATH.write_bytes(canonical_bytes(universe) + b"\n")
    return universe


def _committed_universe() -> dict[str, Any]:
    if not UNIVERSE_PATH.is_file():
        raise Stage1Error("the candidate universe must be committed before any candidate is probed")
    universe = json.loads(UNIVERSE_PATH.read_text(encoding="utf-8"))
    expected = sha256_hex(canonical_bytes(
        {k: v for k, v in universe.items() if k != "universe_sha256"}))
    if universe.get("universe_sha256") != expected:
        raise Stage1Error("the committed candidate universe digest does not match its contents")
    if universe.get("plan_sha256") != plan()["plan_sha256"]:
        raise Stage1Error("the committed universe belongs to a different frozen plan")
    return universe


# ---------------------------------------------------------------------------------------------
# Probing one candidate
# ---------------------------------------------------------------------------------------------

# Identity attestations are short provider/model tokens, never carrier or free text. Anything
# longer or unstringlike is recorded as a refusal marker rather than pasted into the record.
_IDENTITY_MAX = 128


def _shape(value: Any) -> str:
    """Absent, empty or populated -- enough to tell a real fallback from missing metadata."""
    if value is None:
        return "absent"
    if not isinstance(value, list):
        return "not_a_list"
    return "empty_list" if not value else "non_empty_list"


def _stress_max_tokens(candidate: Mapping[str, Any]) -> int:
    """Never ask a candidate for more than it declares it can produce.

    Attempt 02 asked every structurally qualified candidate for STRESS_MAX_TOKENS regardless of
    what that candidate declared. Eligibility admits anything at or above
    MINIMUM_MAX_COMPLETION_TOKENS (32768), so an admitted candidate could be sent a request for
    four times its own declared ceiling and answer HTTP 400 -- a malformed request of ours, not a
    capacity limit of theirs. The contradiction is visible in the frozen constants alone and did
    not need an observation to find.

    The threshold the stress must clear is unchanged; only the request is bounded.
    """
    declared = candidate.get("max_completion_tokens")
    if not isinstance(declared, int) or declared <= 0:
        return STRESS_MAX_TOKENS
    return min(STRESS_MAX_TOKENS, declared)


def _assert_stress_is_satisfiable() -> None:
    """A candidate admitted by eligibility must be able to clear the stress it will be given."""
    if STRESS_MIN_COMPLETION_TOKENS >= rule.MINIMUM_MAX_COMPLETION_TOKENS:
        raise Stage1Error(
            "the stress demands more completion tokens than eligibility guarantees: %d >= %d"
            % (STRESS_MIN_COMPLETION_TOKENS, rule.MINIMUM_MAX_COMPLETION_TOKENS))


def _identity_token(value: Any) -> Any:
    if value is None:
        return None
    if not isinstance(value, str) or len(value) > _IDENTITY_MAX or "\n" in value:
        return "<refused: not an identity token>"
    return value


def declares_reasoning(candidate: Mapping[str, Any]) -> bool:
    """Does the catalogue say this endpoint accepts the reasoning control?"""
    declared = candidate.get("supported_parameters")
    return isinstance(declared, list) and "reasoning" in declared


def _request_body(candidate: Mapping[str, Any], prompt: str, schema: Mapping[str, Any],
                  name: str, max_tokens: int) -> dict[str, Any]:
    body = {
        "model": candidate["model"],
        "messages": [{"role": "user", "content": prompt}],
        "provider": {"only": [candidate["provider"]], "allow_fallbacks": False,
                     "require_parameters": True},
        "response_format": {"type": "json_schema", "json_schema": {
            "name": name, "strict": True, "schema": schema}},
        "max_tokens": max_tokens,
        "seed": 0, "stream": False, "temperature": 1.0,
    }
    # The inherited matrix disables reasoning. `require_parameters: true` would exclude an endpoint
    # that does not accept the parameter at all, so the control is applied exactly when the
    # catalogue declares support -- a mechanical rule fixed here, not a per-candidate judgement.
    if declares_reasoning(candidate):
        body["reasoning"] = {"effort": "none"}
    return body


def _no_fallback(metadata: Mapping[str, Any], attempts: Any,
                 selected: list[Any]) -> bool:
    """Exactly one routing attempt, established from evidence this API emits.

    A reported attempt list is judged on its contents: at most one record, and any record present
    must be a success, so a retry after a failure can never read as a single clean attempt. Where no list is reported -- this API reports none, on success as much
    as on failure -- the same fact rests on a direct strategy, routing attempt 1 and exactly one
    selected endpoint, alongside the `allow_fallbacks: false` this harness sends on every request.

    The clause it replaces required the field to be present AND empty, which no observed route
    could satisfy.
    """
    if isinstance(attempts, list):
        return len(attempts) <= 1 and all(
            isinstance(a, Mapping) and a.get("status") == 200 for a in attempts)
    return (metadata.get("strategy") == "direct"
            and metadata.get("attempt") == 1
            and len(selected) == 1)


def _identity(candidate: Mapping[str, Any], body: Mapping[str, Any]) -> dict[str, Any]:
    metadata = body.get("openrouter_metadata") if isinstance(
        body.get("openrouter_metadata"), Mapping) else {}
    endpoints = metadata.get("endpoints") if isinstance(metadata.get("endpoints"), Mapping) else {}
    available = endpoints.get("available") if isinstance(endpoints.get("available"), list) else []
    selected = [e for e in available if isinstance(e, Mapping) and e.get("selected")]
    pipeline = metadata.get("pipeline")
    attempts = metadata.get("attempts")
    # M115's record could not say why it failed. An identity clause that fails for every candidate
    # is far more likely to be this harness reading the wrong field than a fact about every route,
    # so the observed value is recorded beside the declared one and a systematic mismatch stays
    # diagnosable as an instrument abort instead of being reported as "no route qualifies".
    return {
        "declared_model": candidate["model"],
        "observed_model": _identity_token(body.get("model")),
        "declared_provider": candidate["provider"],
        "observed_provider": _identity_token(body.get("provider")),
        "declared_canonical_checkpoint": candidate.get("canonical_checkpoint"),
        "observed_canonical_checkpoint": _identity_token(
            selected[0].get("model") if selected else None),
        "requested_model_exact": body.get("model") == candidate["model"],
        "provider_exact": body.get("provider") == candidate["provider"],
        "canonical_checkpoint_exact": bool(selected) and selected[0].get("model")
        == candidate.get("canonical_checkpoint"),
        "observed_attempts_shape": _shape(attempts),
        "observed_pipeline_shape": _shape(pipeline),
        "observed_selected_endpoints": len(selected),
        "router_direct": metadata.get("strategy") == "direct",
        # Revision 4. Where the router reports these fields they are judged on their contents; an
        # absent field is established from what the API does emit -- a direct strategy, routing
        # attempt 1, exactly one selected endpoint -- together with allow_fallbacks: false on the
        # request itself. Absence never overrides a positive report to the contrary.
        "router_no_fallback": _no_fallback(metadata, attempts, selected),
        "router_one_endpoint": len(selected) == 1,
        "router_one_attempt": metadata.get("attempt") == 1,
        "router_no_pipeline_intervention": pipeline is None or (
            isinstance(pipeline, list) and len(pipeline) == 0),
    }


def _send(candidate: Mapping[str, Any], prompt: str, schema: Mapping[str, Any], name: str,
          max_tokens: int, budget: dict[str, int]) -> dict[str, Any]:
    """One probe under the frozen per-probe rule. Returns the observation and spends budget."""
    attempts = 0
    while True:
        if budget["global"] >= rule.GLOBAL_REQUEST_CEILING:
            raise Stage1Error("the global DEVELOPMENT request ceiling is reached")
        attempts += 1
        budget["global"] += 1
        budget["candidate"] += 1
        observed = _http(COMPLETIONS_ENDPOINT, method="POST",
                         body=canonical_bytes(_request_body(candidate, prompt, schema, name,
                                                            max_tokens)))
        body = observed.get("body") if isinstance(observed.get("body"), Mapping) else {}
        choices = body.get("choices") if isinstance(body.get("choices"), list) else []
        usage = body.get("usage") if isinstance(body.get("usage"), Mapping) else {}
        executed = bool(choices) or bool(usage.get("completion_tokens"))
        retryable = (observed.get("status") == 429 and not executed
                     and not observed.get("model_execution_cannot_be_excluded"))
        if not retryable or attempts >= rule.MAX_REQUESTS_PER_PROBE \
                or budget["candidate"] >= rule.MAX_REQUESTS_PER_CANDIDATE:
            return observed
        time.sleep(60)


def probe_candidate(candidate: Mapping[str, Any], budget: dict[str, int]) -> dict[str, Any]:
    """Run the inherited M116 matrix against one route, then the stress only if it fully holds."""
    budget["candidate"] = 0
    matrix_probes = probes.build_matrix(m116._census())
    probes.assert_non_carrier(matrix_probes)
    observations: list[dict[str, Any]] = []
    identity_holds: dict[str, bool] = {}

    for probe in matrix_probes:
        if probe["name"] == "combined" and any(
                o["outcome"] not in m116.ENFORCED for o in observations):
            observations.append({
                "schema": "m116-capability-probe-observation-v1", "probe": "combined",
                "feature_class": "combined", "development": True, "is_a_qualifying_call": False,
                "outcome": "not_attempted", "raw_completion_persisted": False,
                "why": "an isolated prerequisite did not pass"})
            break
        observed = _send(candidate, probe["prompt"], probe["schema"],
                         "m117_probe_%s" % probe["name"], PROBE_MAX_TOKENS, budget)
        result = m116._safe_diagnose(probe, observed)
        result.update({"requested_model": candidate["model"],
                       "requested_provider": candidate["provider"]})
        body = observed.get("body") if isinstance(observed.get("body"), Mapping) else {}
        if body:
            for key, held in _identity(candidate, body).items():
                identity_holds[key] = identity_holds.get(key, True) and held
        observations.append(result)

    unenforced = sorted({o["feature_class"] for o in observations
                         if o["probe"] != "combined" and o["outcome"] not in m116.ENFORCED})
    combined = next((o for o in observations if o["probe"] == "combined"), None)
    combined_conforms = bool(combined and combined.get("outcome") == "conforming")
    structural = not unenforced and combined_conforms

    # The stress is reached only after full structural qualification, so a route that enforces
    # nothing never spends budget proving it can emit volume.
    token_holds = False
    stress_record: dict[str, Any] | None = None
    if structural:
        stress_budget = _stress_max_tokens(candidate)
        observed = _send(candidate, stress.STRESS_PROMPT, stress.build_stress_schema(),
                         "m117_stress", stress_budget, budget)
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
        token_holds = bool(observed.get("status") == 200
                           and first.get("finish_reason") == "stop" and conforms
                           and isinstance(tokens, int) and tokens > STRESS_MIN_COMPLETION_TOKENS)
        stress_record = {"requested_max_tokens": stress_budget,
                         "declared_max_completion_tokens": candidate.get("max_completion_tokens"),
                         "http_status": observed.get("status"),
                         "finish_reason": first.get("finish_reason") if isinstance(
                             first.get("finish_reason"), str) else None,
                         "completion_tokens": tokens if isinstance(tokens, int) else None,
                         "schema_conforms": conforms, "holds": token_holds,
                         "raw_completion_persisted": False}

    metrics = candidate.get("metrics") or {}
    profile = {
        "schema": "m117-candidate-profile-v1",
        "model": candidate["model"], "provider": candidate["provider"],
        "canonical_checkpoint": candidate.get("canonical_checkpoint"),
        "order": candidate.get("order"),
        "required_feature_classes": probes.required_feature_classes(m116._census()),
        "unenforced_feature_classes": unenforced,
        "combined_probe_conforms": combined_conforms,
        "token_capacity_holds": token_holds,
        "token_capacity_stress": stress_record,
        "reasoning_control_applied": declares_reasoning(candidate),
        "probe_max_tokens": PROBE_MAX_TOKENS,
        "reliability_minimum_holds": bool(
            (metrics.get("uptime_last_1d") or 0) >= rule.MINIMUM_UPTIME_LAST_1D
            and (metrics.get("uptime_last_30m") or 0) >= rule.MINIMUM_UPTIME_LAST_30M),
        "requests_spent": budget["candidate"],
        "observations": observations,
        "raw_completion_persisted": False,
    }
    # Attempt 02 copied only the boolean verdicts here, so the declared/observed pairs added to
    # make an identity mismatch diagnosable never reached the record -- the diagnostic was itself
    # blind. Every field the attestation produces is carried through; the booleans are still
    # defaulted to False so a missing verdict can never read as a pass.
    _CLAUSES = ("requested_model_exact", "provider_exact", "canonical_checkpoint_exact",
                "router_direct", "router_no_fallback", "router_one_endpoint",
                "router_one_attempt", "router_no_pipeline_intervention")
    profile.update({k: v for k, v in identity_holds.items() if k not in _CLAUSES})
    profile.update({k: identity_holds.get(k, False) for k in _CLAUSES})
    profile["qualification"] = rule.qualifies(profile)
    return profile


# ---------------------------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------------------------

class _Lock:
    def __init__(self, path: Path) -> None:
        self._path, self._handle = path, None

    def __enter__(self):
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._handle = self._path.open("w")
        try:
            fcntl.flock(self._handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self._handle.close()
            raise Stage1Error("another Stage 1 run holds the lock")
        return self

    def __exit__(self, *exc):
        if self._handle is not None:
            fcntl.flock(self._handle.fileno(), fcntl.LOCK_UN)
            self._handle.close()


def execute() -> dict[str, Any]:
    frozen = plan()
    _secret()
    with _Lock(LOCK_PATH):
        if REPORT_PATH.exists():
            raise Stage1Error("the Stage 1 report already exists; it is not redrawn")
        universe = _committed_universe()
        profiles: list[dict[str, Any]] = []
        budget = {"global": 0, "candidate": 0}

        if LEDGER_PATH.is_file():
            previous = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
            if previous.get("universe_sha256") != universe["universe_sha256"]:
                raise Stage1Error("the existing ledger belongs to a different candidate universe")
            profiles = list(previous.get("profiles") or [])
            budget["global"] = int(previous.get("requests_spent") or 0)
        done = {(p["model"], p["provider"]) for p in profiles}

        ledger = {"schema": LEDGER_SCHEMA, "milestone": "M117", "stage": 1, "development": True,
                  "plan_sha256": frozen["plan_sha256"],
                  "universe_sha256": universe["universe_sha256"],
                  "profiles": profiles, "requests_spent": budget["global"]}

        for candidate in universe["ordered_candidates"]:
            # A row the frozen order already reached as an identical request is not a second
            # experiment. It is skipped explicitly and recorded, so the record shows the position
            # was reached and why no budget was spent on it -- rather than the run appearing to
            # have probed more distinct routes than it did.
            if candidate.get("duplicate_of_order") is not None:
                profiles.append({
                    "schema": "m117-candidate-profile-v1",
                    "model": candidate["model"], "provider": candidate["provider"],
                    "order": candidate.get("order"),
                    "skipped": "identical_request_to_order_%s" % candidate["duplicate_of_order"],
                    "requests_spent": 0,
                    "qualification": {"qualifies": False,
                                      "failed_checks": ["candidate_not_probed_duplicate_request"]},
                })
                continue
            if (candidate["model"], candidate["provider"]) in done:
                continue
            if any(p.get("qualification", {}).get("qualifies") for p in profiles):
                break  # the first qualifier in the frozen order is the selection
            if budget["global"] >= rule.GLOBAL_REQUEST_CEILING:
                break
            try:
                profiles.append(probe_candidate(candidate, budget))
            except Stage1Error as exc:
                # The ceiling ended this candidate mid-way. An incomplete candidate cannot
                # qualify, but dropping it silently would hide budget consumed on its behalf.
                profiles.append({
                    "schema": "m117-candidate-profile-v1",
                    "model": candidate["model"], "provider": candidate["provider"],
                    "order": candidate.get("order"), "incomplete": True,
                    "why": str(exc), "requests_spent": budget["candidate"],
                    "raw_completion_persisted": False,
                    "qualification": {"schema": rule.QUALIFICATION_SCHEMA, "qualifies": False,
                                      "checks": {}, "unenforced_feature_classes": [],
                                      "failed_checks": ["candidate_probing_incomplete"]},
                })
                break
            ledger["requests_spent"] = budget["global"]
            LEDGER_PATH.write_bytes(canonical_bytes(ledger) + b"\n")

        ledger["requests_spent"] = budget["global"]
        LEDGER_PATH.write_bytes(canonical_bytes(ledger) + b"\n")

        selection = rule.select(universe, profiles)
        report = {
            "schema": REPORT_SCHEMA, "milestone": "M117", "hypothesis": "H62", "stage": 1,
            "development": True, "is_a_qualifying_call": False,
            "qualifying_input_was_sent": False, "qualifying_calls": 0,
            "h62_frozen": False, "h62_bank_exists": False,
            "plan_sha256": frozen["plan_sha256"],
            "universe_sha256": universe["universe_sha256"],
            "catalogue_snapshot_sha256": universe["catalogue_snapshot_sha256"],
            "eligible_candidates": universe["eligible_count"],
            "candidates_probed": len(profiles),
            "requests_spent": budget["global"],
            "global_request_ceiling": rule.GLOBAL_REQUEST_CEILING,
            "profiles": profiles,
            "selection": selection,
            "raw_completion_persisted": False,
            "report_sha256": "",
        }
        report["report_sha256"] = sha256_hex(
            canonical_bytes({k: v for k, v in report.items() if k != "report_sha256"}))
        REPORT_PATH.write_bytes(canonical_bytes(report) + b"\n")
        return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", action="store_true")
    parser.add_argument("--catalogue", action="store_true")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    chosen = [args.plan, args.catalogue, args.execute]
    if sum(1 for flag in chosen if flag) != 1:
        parser.error("choose exactly one of --plan, --catalogue or --execute")
    if args.plan:
        print(json.dumps(plan(), indent=2, sort_keys=True))
        return 0
    if args.catalogue:
        universe = snapshot_catalogue()
        print(json.dumps({"eligible": universe["eligible_count"],
                          "assessed": len(universe["assessed"]),
                          "universe_sha256": universe["universe_sha256"]}, sort_keys=True))
        return 0
    report = execute()
    print(json.dumps({"route_selected": report["selection"]["route_selected"],
                      "selected": report["selection"]["selected"],
                      "candidates_probed": report["candidates_probed"],
                      "requests_spent": report["requests_spent"]}, sort_keys=True))
    return 0 if report["selection"]["route_selected"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
