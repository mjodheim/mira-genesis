"""M116 DEVELOPMENT-only large structured-output capacity audit.

This harness exists only to decide whether the prospective H61 generator route can safely be frozen.
It NEVER sends the M113/M114/M115 qualifying input and it never creates, seals, reveals, qualifies or
scores a carrier bank.

The acceptance rule is intentionally committed before the first network call:

* exact DeepSeek alias -> canonical checkpoint identity on Alibaba;
* direct routing, one selected endpoint, one router attempt, no fallback/pipeline intervention;
* HTTP 200 and finish_reason=stop;
* candidate M116 output controls: max_tokens=131072 and reasoning effort=none;
* a synthetic strict-schema payload with exactly 1536 rows and eight bounded integer fields;
* strict parsing of that payload;
* observed completion_tokens > 32000, proving completion beyond M115's old ceiling;
* positive reasoning telemetry showing zero reasoning tokens.

At most three physical DEVELOPMENT attempts are permitted, and only an explicit HTTP 429 carrying no
completion and no evidence of model execution may be retried after 60 seconds. The first materialized
or otherwise terminal response ends the audit.

The attempt budget is crash-safe. A process lock prevents concurrent execution in one repository
workspace, every physical slot is durably reserved before the request begins, and every retryable 429
is durably recorded before the wait starts. If a process disappears while an attempt is in flight,
the reserved slot becomes an ambiguous terminal observation on restart rather than being redrawn.
Any response generation identifier is also execution evidence and therefore forbids a retry.
Raw completion content is never written.
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
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from metamorphosis import m115_identity as model_identity  # noqa: E402
from metamorphosis.blind_bank_protocol import canonical_bytes, sha256_hex  # noqa: E402

MODEL = "deepseek/deepseek-v4-flash-0731"
CANONICAL_CHECKPOINT = "deepseek/deepseek-v4-flash-20260731"
PROVIDER = "Alibaba"
ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
SECRET_VARIABLE = "OPENROUTER_API_KEY"
REPORT_PATH = ROOT / "experiments" / "M116" / "CAPACITY_STRESS_DEVELOPMENT.json"
LEDGER_PATH = ROOT / "experiments" / "M116" / "CAPACITY_STRESS_DEVELOPMENT_LEDGER.json"
_GIT_DIRECTORY = ROOT / ".git"
LOCK_PATH = (
    _GIT_DIRECTORY / "m116-capacity-stress.lock"
    if _GIT_DIRECTORY.is_dir()
    else ROOT / ".m116-capacity-stress.lock"
)
MAX_TOKENS = 131072
OLD_M115_MAX_TOKENS = 32000
ROWS = 1536
RETRY_WAIT_SECONDS = 60
MAX_PHYSICAL_ATTEMPTS = 3
LEDGER_SCHEMA = "m116-capacity-stress-development-ledger-v1"

STRESS_INPUT = (
    "Return a JSON object with exactly one key named rows. Its value must contain exactly 1536 "
    "objects. Every object must contain exactly the eight integer keys a,b,c,d,e,f,g,h. Every "
    "integer must be between 10000000 and 99999999 inclusive. No prose or other keys."
)

_ROW_PROPERTIES = {
    key: {"type": "integer", "minimum": 10000000, "maximum": 99999999}
    for key in "abcdefgh"
}
STRESS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "rows": {
            "type": "array",
            "minItems": ROWS,
            "maxItems": ROWS,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": _ROW_PROPERTIES,
                "required": list("abcdefgh"),
            },
        }
    },
    "required": ["rows"],
}

REQUEST_BODY: dict[str, Any] = {
    "model": MODEL,
    "messages": [{"role": "user", "content": STRESS_INPUT}],
    "provider": {
        "only": [PROVIDER],
        "allow_fallbacks": False,
        "require_parameters": True,
    },
    "reasoning": {"effort": "none"},
    "response_format": {
        "type": "json_schema",
        "json_schema": {
            "name": "m116_capacity_rows",
            "strict": True,
            "schema": STRESS_SCHEMA,
        },
    },
    "max_tokens": MAX_TOKENS,
    "seed": 0,
    "stream": False,
    "temperature": 1.0,
}

QUALIFYING_INPUT_PATHS = (
    ROOT / "experiments" / "M113" / "QUALIFYING_INPUT.txt",
    ROOT / "experiments" / "M114" / "QUALIFYING_INPUT.txt",
    ROOT / "experiments" / "M115" / "QUALIFYING_INPUT.txt",
)
CARRIER_SCHEMA_VOCABULARY = frozenset(
    {"machines", "surface", "cells", "initial", "visible", "errors", "actions"}
)


class CapacityAuditError(RuntimeError):
    """M116 capacity readiness cannot be established without guessing or crossing a boundary."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _secret() -> str:
    secret = os.environ.get(SECRET_VARIABLE)
    if not secret:
        raise CapacityAuditError(f"{SECRET_VARIABLE} is not set; no network request was made")
    return secret


def _assert_nonqualifying() -> None:
    stress = STRESS_INPUT.encode("utf-8")
    stress_digest = sha256_hex(stress)
    serialized_schema = canonical_bytes(STRESS_SCHEMA)
    for forbidden in CARRIER_SCHEMA_VOCABULARY:
        if ('"%s"' % forbidden).encode("utf-8") in serialized_schema:
            raise CapacityAuditError("the M116 stress schema contains carrier-schema vocabulary")
    for path in QUALIFYING_INPUT_PATHS:
        if not path.is_file():
            continue
        qualifying = path.read_bytes()
        if stress_digest == sha256_hex(qualifying):
            raise CapacityAuditError("the M116 stress input equals a qualifying carrier input")
        decoded = qualifying.decode("utf-8", "replace")
        if STRESS_INPUT.strip() in decoded or decoded.strip() in STRESS_INPUT:
            raise CapacityAuditError("the M116 stress input overlaps a qualifying carrier input")


def request_body_digest() -> str:
    _assert_nonqualifying()
    return sha256_hex(canonical_bytes(REQUEST_BODY))


def _connection(
    url: str, timeout: int
) -> tuple[http.client.HTTPSConnection, urllib.parse.SplitResult]:
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise CapacityAuditError("capacity audit endpoint must use https")
    context = ssl.create_default_context()
    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    if proxy:
        via = urllib.parse.urlsplit(proxy if "://" in proxy else "http://" + proxy)
        conn = http.client.HTTPSConnection(
            via.hostname, via.port or 80, timeout=timeout, context=context
        )
        conn.set_tunnel(parsed.hostname, parsed.port or 443)
    else:
        conn = http.client.HTTPSConnection(
            parsed.hostname, parsed.port or 443, timeout=timeout, context=context
        )
    return conn, parsed


def _transport_failure_observation(
    *,
    started_at: str,
    request_call_began: bool,
) -> dict[str, Any]:
    return {
        "started_at": started_at,
        "finished_at": _now(),
        "status": None,
        "headers": {},
        "body": {},
        "response_sha256": None,
        "response_bytes": None,
        "transport_failure_class": (
            "ambiguous_transport_failure"
            if request_call_began
            else "pretransmission_transport_failure"
        ),
        "model_execution_cannot_be_excluded": request_call_began,
    }


def _request(*, timeout: int = 1200) -> dict[str, Any]:
    # Missing owner credential is checked before a physical attempt is reserved by execute().
    secret = _secret()
    payload = canonical_bytes(REQUEST_BODY)
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {secret}",
        "Content-Type": "application/json",
        "X-OpenRouter-Metadata": "enabled",
        "X-OpenRouter-Cache": "false",
    }
    started = _now()
    conn: http.client.HTTPSConnection | None = None
    request_call_began = False
    try:
        conn, parsed = _connection(ENDPOINT, timeout)
        # Once conn.request is invoked, partial transmission cannot be excluded even if it raises.
        request_call_began = True
        conn.request("POST", parsed.path or "/", body=payload, headers=headers)
        response = conn.getresponse()
        raw = response.read()
        status = response.status
        observed_headers = {
            key.lower(): value
            for key, value in response.getheaders()
            if key.lower() in {"date", "server", "retry-after", "x-generation-id"}
        }
    except Exception:  # network/HTTP failure is deliberately converted to safe terminal evidence
        return _transport_failure_observation(
            started_at=started,
            request_call_began=request_call_began,
        )
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
    try:
        decoded = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        decoded = None
    return {
        "started_at": started,
        "finished_at": _now(),
        "status": status,
        "headers": observed_headers,
        "body": decoded,
        "response_sha256": sha256_hex(raw),
        "response_bytes": len(raw),
        "transport_failure_class": None,
        "model_execution_cannot_be_excluded": False,
    }


def _first_message(
    body: Mapping[str, Any],
) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    choices = body.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], Mapping):
        return {}, {}
    first = choices[0]
    message = first.get("message")
    return first, message if isinstance(message, Mapping) else {}


def _execution_evidence(body: Mapping[str, Any]) -> dict[str, bool]:
    first, message = _first_message(body)
    content = message.get("content")
    completion_present = isinstance(content, str) and bool(content.strip())
    usage = body.get("usage") if isinstance(body.get("usage"), Mapping) else {}
    completion_tokens = usage.get("completion_tokens") if isinstance(usage, Mapping) else None
    executed = bool(first) or (
        isinstance(completion_tokens, int)
        and not isinstance(completion_tokens, bool)
        and completion_tokens > 0
    )
    return {
        "completion_present": completion_present,
        "model_execution_cannot_be_excluded": executed and not completion_present,
    }


def _strict_payload_holds(content: Any) -> tuple[bool, str | None]:
    if not isinstance(content, str):
        return False, None
    try:
        value = json.loads(content)
    except ValueError:
        return False, None
    if not isinstance(value, dict) or set(value) != {"rows"}:
        return False, None
    rows = value.get("rows")
    if not isinstance(rows, list) or len(rows) != ROWS:
        return False, None
    expected = set("abcdefgh")
    for row in rows:
        if not isinstance(row, dict) or set(row) != expected:
            return False, None
        for number in row.values():
            if (
                not isinstance(number, int)
                or isinstance(number, bool)
                or not 10000000 <= number <= 99999999
            ):
                return False, None
    return True, sha256_hex(canonical_bytes(value))


def _reasoning_tokens(usage: Mapping[str, Any]) -> int | None:
    details = usage.get("completion_tokens_details")
    if not isinstance(details, Mapping):
        return None
    value = details.get("reasoning_tokens")
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _observed_selected_checkpoint(identity: Mapping[str, Any] | None) -> str | None:
    if not isinstance(identity, Mapping):
        return None
    metadata = identity.get("safe_router_metadata")
    if not isinstance(metadata, Mapping):
        return None
    endpoints = metadata.get("endpoints")
    available = endpoints.get("available") if isinstance(endpoints, Mapping) else None
    if not isinstance(available, list):
        return None
    selected = [
        item
        for item in available
        if isinstance(item, Mapping) and item.get("selected") is True
    ]
    if len(selected) != 1:
        return None
    value = selected[0].get("model")
    return value if isinstance(value, str) else None


def evaluate_terminal_observation(observed: Mapping[str, Any]) -> dict[str, Any]:
    body = observed.get("body") if isinstance(observed.get("body"), Mapping) else {}
    first, message = _first_message(body)
    content = message.get("content")
    strict_output, payload_digest = _strict_payload_holds(content)
    usage = body.get("usage") if isinstance(body.get("usage"), Mapping) else {}
    completion_tokens = usage.get("completion_tokens")
    if not isinstance(completion_tokens, int) or isinstance(completion_tokens, bool):
        completion_tokens = None
    reasoning_tokens = _reasoning_tokens(usage)
    reasoning_fields_empty = all(
        message.get(key) in (None, "", [], {})
        for key in ("reasoning", "reasoning_content", "reasoning_details")
    )
    # The preregistered gate requires positive evidence, not absence of evidence.
    reasoning_observation_holds = reasoning_fields_empty and reasoning_tokens == 0

    identity = (
        model_identity.attest_completion_response(body)
        if isinstance(content, str) and content.strip()
        else None
    )
    identity_holds = isinstance(identity, Mapping) and identity.get("holds") is True
    observed_checkpoint = _observed_selected_checkpoint(identity)

    checks = {
        "http_200": observed.get("status") == 200,
        "finish_reason_stop": first.get("finish_reason") == "stop",
        "strict_output_parsed": strict_output,
        "completion_exceeds_m115_ceiling": completion_tokens is not None
        and completion_tokens > OLD_M115_MAX_TOKENS,
        "reasoning_request_is_explicitly_off": REQUEST_BODY.get("reasoning")
        == {"effort": "none"},
        "reasoning_response_has_zero_tokens": reasoning_observation_holds,
        "runtime_identity_holds": identity_holds,
        "canonical_checkpoint_exact": observed_checkpoint == CANONICAL_CHECKPOINT,
        "served_provider_exact": body.get("provider") == PROVIDER,
        "served_model_alias_exact": body.get("model") == MODEL,
    }
    gate_holds = all(checks.values())
    return {
        "schema": "m116-capacity-stress-observation-v1",
        "development": True,
        "is_a_qualifying_call": False,
        "qualifying_input_was_sent": False,
        "observed_at": observed.get("finished_at") or _now(),
        "status": observed.get("status"),
        "finish_reason": first.get("finish_reason"),
        "request_body_sha256": request_body_digest(),
        "response_sha256": observed.get("response_sha256"),
        "response_bytes": observed.get("response_bytes"),
        "completion_tokens": completion_tokens,
        "reasoning_tokens": reasoning_tokens,
        "observed_selected_checkpoint": observed_checkpoint,
        "synthetic_rows": ROWS if strict_output else 0,
        "synthetic_payload_sha256": payload_digest,
        "identity_attestation": identity,
        "checks": checks,
        "gate_holds": gate_holds,
        "raw_completion_persisted": False,
    }


def _safe_nonmaterialized_attempt(
    observed: Mapping[str, Any], position: int
) -> dict[str, Any]:
    body = observed.get("body") if isinstance(observed.get("body"), Mapping) else {}
    evidence = _execution_evidence(body)
    headers = observed.get("headers") if isinstance(observed.get("headers"), Mapping) else {}
    generation_id = headers.get("x-generation-id")
    generation_id_present = isinstance(generation_id, str) and bool(generation_id.strip())
    transport_ambiguous = observed.get("model_execution_cannot_be_excluded") is True
    execution_cannot_be_excluded = (
        transport_ambiguous
        or evidence["model_execution_cannot_be_excluded"]
        or generation_id_present
    )
    transport_failure = observed.get("transport_failure_class")
    return {
        "attempt_index": position,
        "started_at": observed.get("started_at"),
        "finished_at": observed.get("finished_at"),
        "status": observed.get("status"),
        "response_sha256": observed.get("response_sha256"),
        "response_bytes": observed.get("response_bytes"),
        "transport_failure_class": transport_failure,
        "generation_id_present": generation_id_present,
        "completion_present": evidence["completion_present"],
        "model_execution_cannot_be_excluded": execution_cannot_be_excluded,
        "retry_permitted": transport_failure is None
        and observed.get("status") == 429
        and not evidence["completion_present"]
        and not execution_cannot_be_excluded,
    }


def _terminal_nonmaterialized(safe: Mapping[str, Any]) -> dict[str, Any]:
    failure = safe.get("transport_failure_class") or "nonmaterialized_terminal_response"
    return {
        "schema": "m116-capacity-stress-observation-v1",
        "development": True,
        "is_a_qualifying_call": False,
        "qualifying_input_was_sent": False,
        "attempt_index": safe.get("attempt_index"),
        "status": safe.get("status"),
        "model_execution_cannot_be_excluded": safe.get(
            "model_execution_cannot_be_excluded"
        )
        is True,
        "gate_holds": False,
        "terminal_failure": failure,
        "raw_completion_persisted": False,
    }


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _timestamp_after(value: Any, seconds: int) -> str:
    parsed = _parse_timestamp(value) or datetime.now(timezone.utc)
    return (parsed + timedelta(seconds=seconds)).isoformat().replace("+00:00", "Z")


def _sleep_remaining(retry_not_before: Any) -> None:
    target = _parse_timestamp(retry_not_before)
    if target is None:
        raise CapacityAuditError("retry ledger lacks a valid retry_not_before timestamp")
    remaining = (target - datetime.now(timezone.utc)).total_seconds()
    if remaining > 0:
        time.sleep(remaining)


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _write_json_atomic(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = canonical_bytes(value) + b"\n"
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    descriptor = os.open(
        temporary,
        os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
        0o600,
    )
    try:
        with os.fdopen(descriptor, "wb", closefd=False) as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        os.close(descriptor)
    os.replace(temporary, path)
    _fsync_directory(path.parent)


def _write_json_exclusive(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = canonical_bytes(value) + b"\n"
    try:
        descriptor = os.open(
            path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o600,
        )
    except FileExistsError as exc:
        raise CapacityAuditError(
            f"{path.name} already exists; the audit is not redrawn"
        ) from exc
    try:
        with os.fdopen(descriptor, "wb", closefd=False) as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        os.close(descriptor)
    _fsync_directory(path.parent)


def _load_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise CapacityAuditError(f"cannot read {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise CapacityAuditError(f"{path} is not a JSON object")
    return value


@contextmanager
def _exclusive_audit_lock() -> Iterator[None]:
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOCK_PATH.open("a+b") as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise CapacityAuditError(
                "another M116 DEVELOPMENT capacity audit process already holds the execution lock"
            ) from exc
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _new_ledger() -> dict[str, Any]:
    return {
        "schema": LEDGER_SCHEMA,
        "milestone": "M116",
        "hypothesis": "H61",
        "development": True,
        "request_body_sha256": request_body_digest(),
        "candidate_max_tokens": MAX_TOKENS,
        "m115_max_tokens": OLD_M115_MAX_TOKENS,
        "reasoning_control": {"effort": "none"},
        "requested_provider": PROVIDER,
        "requested_model": MODEL,
        "required_canonical_checkpoint": CANONICAL_CHECKPOINT,
        "max_physical_attempts": MAX_PHYSICAL_ATTEMPTS,
        "retry_wait_seconds": RETRY_WAIT_SECONDS,
        "state": "ready",
        "attempts": [],
        "terminal_observation": None,
        "qualifying_calls": 0,
        "raw_completion_persisted": False,
    }


def _validate_ledger(ledger: Mapping[str, Any]) -> None:
    expected = {
        "schema": LEDGER_SCHEMA,
        "milestone": "M116",
        "hypothesis": "H61",
        "development": True,
        "request_body_sha256": request_body_digest(),
        "candidate_max_tokens": MAX_TOKENS,
        "m115_max_tokens": OLD_M115_MAX_TOKENS,
        "reasoning_control": {"effort": "none"},
        "requested_provider": PROVIDER,
        "requested_model": MODEL,
        "required_canonical_checkpoint": CANONICAL_CHECKPOINT,
        "max_physical_attempts": MAX_PHYSICAL_ATTEMPTS,
        "retry_wait_seconds": RETRY_WAIT_SECONDS,
        "qualifying_calls": 0,
        "raw_completion_persisted": False,
    }
    for key, value in expected.items():
        if ledger.get(key) != value:
            raise CapacityAuditError(f"M116 DEVELOPMENT ledger drift at {key}")
    attempts = ledger.get("attempts")
    if not isinstance(attempts, list) or len(attempts) > MAX_PHYSICAL_ATTEMPTS:
        raise CapacityAuditError("M116 DEVELOPMENT ledger has an invalid attempt list")
    for index, attempt in enumerate(attempts, start=1):
        if not isinstance(attempt, Mapping) or attempt.get("attempt_index") != index:
            raise CapacityAuditError("M116 DEVELOPMENT ledger attempt indices are not contiguous")
    if ledger.get("state") not in {"ready", "in_flight", "retry_wait", "terminal"}:
        raise CapacityAuditError("M116 DEVELOPMENT ledger has an unknown state")
    terminal = ledger.get("terminal_observation")
    if ledger.get("state") == "terminal":
        if not isinstance(terminal, Mapping):
            raise CapacityAuditError("terminal M116 DEVELOPMENT ledger lacks its observation")
    elif terminal is not None:
        raise CapacityAuditError("non-terminal M116 DEVELOPMENT ledger carries terminal evidence")


def _load_or_create_ledger() -> dict[str, Any]:
    if LEDGER_PATH.exists():
        ledger = _load_object(LEDGER_PATH)
        _validate_ledger(ledger)
        return ledger
    ledger = _new_ledger()
    _write_json_exclusive(LEDGER_PATH, ledger)
    return ledger


def _write_ledger(ledger: dict[str, Any]) -> None:
    _validate_ledger(ledger)
    _write_json_atomic(LEDGER_PATH, ledger)


def _reserve_attempt(ledger: dict[str, Any]) -> int:
    attempts = list(ledger.get("attempts") or [])
    position = len(attempts) + 1
    if position > MAX_PHYSICAL_ATTEMPTS:
        raise CapacityAuditError("M116 DEVELOPMENT physical-attempt budget is exhausted")
    attempts.append(
        {
            "attempt_index": position,
            "state": "in_flight",
            "reserved_at": _now(),
            "request_body_sha256": request_body_digest(),
            "model_execution_cannot_be_excluded": True,
            "retry_permitted": False,
        }
    )
    ledger["attempts"] = attempts
    ledger["state"] = "in_flight"
    # This fsynced write happens before _request() is allowed to begin.
    _write_ledger(ledger)
    return position


def _interrupted_in_flight_terminal(
    ledger: dict[str, Any], attempt: Mapping[str, Any]
) -> dict[str, Any]:
    replacement = dict(attempt)
    replacement["state"] = "interrupted_in_flight"
    replacement["finished_at"] = _now()
    replacement["model_execution_cannot_be_excluded"] = True
    replacement["retry_permitted"] = False
    ledger["attempts"][-1] = replacement
    return {
        "schema": "m116-capacity-stress-observation-v1",
        "development": True,
        "is_a_qualifying_call": False,
        "qualifying_input_was_sent": False,
        "attempt_index": replacement.get("attempt_index"),
        "status": None,
        "model_execution_cannot_be_excluded": True,
        "gate_holds": False,
        "terminal_failure": "interrupted_in_flight_attempt",
        "raw_completion_persisted": False,
    }


def _record_materialized_attempt(
    ledger: dict[str, Any],
    position: int,
    observed: Mapping[str, Any],
) -> dict[str, Any]:
    terminal = evaluate_terminal_observation(observed)
    terminal["attempt_index"] = position
    reserved_at = ledger["attempts"][-1].get("reserved_at")
    ledger["attempts"][-1] = {
        "attempt_index": position,
        "state": "materialized_stress_response",
        "reserved_at": reserved_at,
        "started_at": observed.get("started_at"),
        "finished_at": observed.get("finished_at"),
        "status": observed.get("status"),
        "response_sha256": observed.get("response_sha256"),
        "response_bytes": observed.get("response_bytes"),
        "outcome": "materialized_stress_response",
        "model_execution_cannot_be_excluded": False,
        "retry_permitted": False,
    }
    return terminal


def _record_nonmaterialized_attempt(
    ledger: dict[str, Any],
    safe: Mapping[str, Any],
) -> dict[str, Any]:
    record = dict(safe)
    record["reserved_at"] = ledger["attempts"][-1].get("reserved_at")
    if safe.get("retry_permitted") is True:
        record["state"] = "retryable_429"
        record["retry_not_before"] = _timestamp_after(
            safe.get("finished_at"), RETRY_WAIT_SECONDS
        )
    else:
        record["state"] = "terminal_nonmaterialized"
    ledger["attempts"][-1] = record
    return record


def _report_from_ledger(ledger: Mapping[str, Any]) -> dict[str, Any]:
    terminal = ledger.get("terminal_observation")
    if not isinstance(terminal, Mapping):
        raise CapacityAuditError("cannot build final M116 report without terminal observation")
    return {
        "schema": "m116-capacity-stress-development-v1",
        "milestone": "M116",
        "hypothesis": "H61",
        "development": True,
        "request_body_sha256": ledger["request_body_sha256"],
        "candidate_max_tokens": MAX_TOKENS,
        "m115_max_tokens": OLD_M115_MAX_TOKENS,
        "reasoning_control": {"effort": "none"},
        "requested_provider": PROVIDER,
        "requested_model": MODEL,
        "required_canonical_checkpoint": CANONICAL_CHECKPOINT,
        "max_physical_attempts": MAX_PHYSICAL_ATTEMPTS,
        "retry_wait_seconds": RETRY_WAIT_SECONDS,
        "attempts": list(ledger.get("attempts") or []),
        "terminal_observation": dict(terminal),
        "gate_holds": terminal.get("gate_holds") is True,
        "qualifying_calls": 0,
        "raw_completion_persisted": False,
    }


def _finalize(
    ledger: dict[str, Any], terminal: Mapping[str, Any]
) -> dict[str, Any]:
    ledger["terminal_observation"] = dict(terminal)
    ledger["state"] = "terminal"
    # Terminal evidence is durable before the public summary is created. If the process dies between
    # these writes, the next invocation reconstructs the same report without any network call.
    _write_ledger(ledger)
    report = _report_from_ledger(ledger)
    if REPORT_PATH.exists():
        raise CapacityAuditError(
            "M116 DEVELOPMENT capacity report already exists; the audit is not redrawn"
        )
    _write_json_exclusive(REPORT_PATH, report)
    return report


def _resume_terminal_ledger(ledger: dict[str, Any]) -> dict[str, Any]:
    report = _report_from_ledger(ledger)
    if REPORT_PATH.exists():
        raise CapacityAuditError(
            "M116 DEVELOPMENT capacity report already exists; the audit is not redrawn"
        )
    _write_json_exclusive(REPORT_PATH, report)
    return report


def _exhausted_429_terminal(attempts: list[Mapping[str, Any]]) -> dict[str, Any]:
    last = attempts[-1] if attempts else {}
    return {
        "schema": "m116-capacity-stress-observation-v1",
        "development": True,
        "is_a_qualifying_call": False,
        "qualifying_input_was_sent": False,
        "attempt_index": last.get("attempt_index"),
        "status": 429 if attempts else None,
        "model_execution_cannot_be_excluded": False,
        "gate_holds": False,
        "terminal_failure": "development_capacity_rejections_exhausted",
        "raw_completion_persisted": False,
    }


def execute() -> dict[str, Any]:
    _assert_nonqualifying()
    # Credential absence is known before any physical slot is reserved.
    _secret()

    with _exclusive_audit_lock():
        if REPORT_PATH.exists():
            raise CapacityAuditError(
                "M116 DEVELOPMENT capacity report already exists; the audit is not redrawn"
            )

        ledger = _load_or_create_ledger()
        _validate_ledger(ledger)

        if ledger.get("state") == "terminal":
            return _resume_terminal_ledger(ledger)

        attempts = list(ledger.get("attempts") or [])
        if attempts and attempts[-1].get("state") == "in_flight":
            terminal = _interrupted_in_flight_terminal(ledger, attempts[-1])
            return _finalize(ledger, terminal)

        # A restart after a persisted retryable 429 resumes the original wait/budget. It never starts
        # from attempt 1 again.
        if attempts and attempts[-1].get("state") == "retryable_429":
            if len(attempts) >= MAX_PHYSICAL_ATTEMPTS:
                return _finalize(ledger, _exhausted_429_terminal(attempts))
            _sleep_remaining(attempts[-1].get("retry_not_before"))

        while True:
            position = _reserve_attempt(ledger)
            observed = _request()
            body = observed.get("body") if isinstance(observed.get("body"), Mapping) else {}
            evidence = _execution_evidence(body)

            if evidence["completion_present"]:
                terminal = _record_materialized_attempt(ledger, position, observed)
                return _finalize(ledger, terminal)

            safe = _safe_nonmaterialized_attempt(observed, position)
            record = _record_nonmaterialized_attempt(ledger, safe)

            if record.get("retry_permitted") is not True:
                return _finalize(ledger, _terminal_nonmaterialized(record))

            # The retryable response itself is durable before entering the wait.
            ledger["state"] = "retry_wait"
            _write_ledger(ledger)

            if position >= MAX_PHYSICAL_ATTEMPTS:
                return _finalize(
                    ledger,
                    _exhausted_429_terminal(list(ledger["attempts"])),
                )

            # Fresh in-process retries wait the full frozen interval. If the process disappears during
            # this wait, the next invocation uses retry_not_before to wait only the remaining time.
            time.sleep(RETRY_WAIT_SECONDS)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="perform or safely resume the committed DEVELOPMENT audit",
    )
    parser.add_argument(
        "--request-digest",
        action="store_true",
        help="print the canonical DEVELOPMENT request digest",
    )
    args = parser.parse_args(argv)

    if args.execute == args.request_digest:
        parser.error("choose exactly one of --execute or --request-digest")
    if args.request_digest:
        print(request_body_digest())
        return 0

    report = execute()
    print(
        json.dumps(
            {
                "gate_holds": report["gate_holds"],
                "attempts": len(report["attempts"]),
                "report": str(REPORT_PATH.relative_to(ROOT)),
            },
            sort_keys=True,
        )
    )
    return 0 if report["gate_holds"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
