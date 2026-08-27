"""M114 generator phase -- the M113 instrument, driven by the M114 delivery rule.

M113 is closed. Nothing here reads, writes, repairs or re-freezes it. What it does import is the
transport: `run_m113_generation.request` opens one connection through the configured egress proxy,
sends one request with `http.client` from the standard library, follows no redirect, reuses no
connection and retries at no layer. That property is exactly what M114 needs, and importing it is
what makes "the transport is unchanged" checkable rather than a claim about two files that look
alike.

What is different is above the transport, and it is only this. M113 spent its single budget on a
capacity rejection that never reached the model, because one predicate stood for two quantities.
`m114_delivery` separates them:

    delivery_attempt      one physical request carrying the frozen body
    bank_materialization  a response that actually carries a model completion

Up to three delivery attempts are permitted to obtain at most one materialization, each attempt
sends the byte-identical frozen body, and an attempt may follow another only after an explicit HTTP
429 that carries no completion and no evidence the model executed, after a fixed 60-second wait.
Three capacity rejections end the milestone as `instrument-aborted`, which is not a result about the
hypothesis. **This rule was decided after M113's failure, before any M114 bank existed, and with no
observation of H59 or H58 whatsoever. It was never part of M113.**

Where the doubt goes. `classify_attempt` decides an outcome from what was observed, and every
ambiguity resolves to a terminal outcome rather than a retryable one. This program feeds it
evidence on the same principle: a transport exception is recorded as "the model may have executed"
even when it almost certainly did not, because the cost of that mistake is one unused attempt,
while the opposite mistake would permit a second draw against a model that may already have
produced one.

Modes:

`--smoke`    DEVELOPMENT. One structured-output probe on a throwaway input, written into M114's own
             directory. Consumes no gate and no delivery attempt.
`--freeze`   Promotes the candidate plan and spec to the frozen names, once.
`--deliver`  The qualifying delivery sequence, against the frozen spec, under the frozen budget.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from metamorphosis import m114_carrier_bank as bank  # noqa: E402
from metamorphosis import m114_delivery as delivery  # noqa: E402
from metamorphosis.blind_bank_protocol import (  # noqa: E402
    canonical_bytes,
    contamination_hits,
    sha256_hex,
)
from scripts.run_m113_generation import (  # noqa: E402
    GenerationError,
    _now,
    request,
    smoke as m113_smoke,
)

EXPERIMENT = ROOT / bank.EXPERIMENT_DIRECTORY
PLAN_PATH = ROOT / bank.ANALYSIS_PLAN_PATH
PLAN_CANDIDATE_PATH = ROOT / bank.ANALYSIS_PLAN_CANDIDATE_PATH
SPEC_PATH = ROOT / bank.GENERATOR_SPEC_PATH
SPEC_CANDIDATE_PATH = ROOT / bank.GENERATOR_SPEC_CANDIDATE_PATH
LEDGER_PATH = ROOT / bank.DELIVERY_LEDGER_PATH
RESPONSE_PATH = EXPERIMENT / "GENERATION_RESPONSE.json"
SMOKE_PATH = EXPERIMENT / "TRANSPORT_SMOKE_DEVELOPMENT.json"


def _shown(path: Path) -> str:
    """Name a path in a message without assuming it sits under the repository root.

    `Path.relative_to` raises when it does not, and every use of it here is inside the text of an
    error or a confirmation. A refusal that crashes while explaining itself is worse than the
    condition it was refusing.
    """
    try:
        return str(Path(path).relative_to(ROOT))
    except ValueError:
        return str(path)


# ----------------------------------------------------------------------------------------
# Loading what has been frozen
# ----------------------------------------------------------------------------------------


def load_plan(*, frozen_required: bool) -> dict[str, Any]:
    path = PLAN_PATH if (frozen_required or PLAN_PATH.is_file()) else PLAN_CANDIDATE_PATH
    if not path.is_file():
        raise GenerationError("no analysis plan at %s" % _shown(path))
    plan = json.loads(path.read_text(encoding="utf-8"))
    bank.validate_analysis_plan(plan)
    return plan


def load_spec(*, frozen_required: bool) -> dict[str, Any]:
    path = SPEC_PATH if (frozen_required or SPEC_PATH.is_file()) else SPEC_CANDIDATE_PATH
    if not path.is_file():
        raise GenerationError("no generator spec at %s" % _shown(path))
    spec = json.loads(path.read_text(encoding="utf-8"))
    if frozen_required:
        plan = load_plan(frozen_required=True)
        bank.validate_generator_spec(
            spec, root=ROOT, plan_commitment_sha256=plan["plan_commitment_sha256"]
        )
        if spec.get("frozen_before_generation") is not True:
            raise GenerationError("the generator spec is not frozen")
    return spec


# ----------------------------------------------------------------------------------------
# DEVELOPMENT: the transport probe
# ----------------------------------------------------------------------------------------


def smoke(*, write: bool) -> dict[str, Any]:
    """M113's probe, on M114's spec, written into M114's directory.

    The probe itself is imported rather than restated: it builds a throwaway request, refuses an
    input that is the qualifying one by digest, and reports what was served. Called with
    `write=False` it touches no file, so the only thing written here is M114's own report.
    """
    report = dict(m113_smoke(load_spec(frozen_required=False), write=False))
    report["schema"] = "m114-transport-smoke-development-v1"
    report["milestone"] = bank.MILESTONE
    report["probe_is_m113s_imported_unchanged"] = True
    report["consumes_a_delivery_attempt"] = False
    if write:
        SMOKE_PATH.write_bytes(canonical_bytes(report) + b"\n")
    return report


# ----------------------------------------------------------------------------------------
# The freeze
# ----------------------------------------------------------------------------------------


def freeze() -> dict[str, Any]:
    """Promote the candidates to the frozen names, once, and never over an existing freeze."""
    for path in (PLAN_PATH, SPEC_PATH):
        if path.is_file():
            raise GenerationError(
                "%s already exists; a freeze is consumed once and is not rewritten"
                % _shown(path)
            )
    if LEDGER_PATH.is_file():
        raise GenerationError(
            "a delivery ledger already exists; freezing behind a delivery history would be "
            "freezing a spec the instrument has already acted on"
        )

    plan = json.loads(PLAN_CANDIDATE_PATH.read_text(encoding="utf-8"))
    bank.validate_analysis_plan(plan)

    spec = json.loads(SPEC_CANDIDATE_PATH.read_text(encoding="utf-8"))
    # The freeze is what these two fields were waiting for, and it is the only edit it makes.
    for key in spec.pop("unset_before_freeze", []):
        if key != "frozen_before_generation":
            raise GenerationError("the freeze does not know how to set %r" % key)
    spec["frozen_before_generation"] = True
    spec["frozen_at"] = _now()
    spec["spec_commitment_sha256"] = bank.generator_spec_commitment(spec)
    bank.validate_generator_spec(
        spec, root=ROOT, plan_commitment_sha256=plan["plan_commitment_sha256"]
    )

    PLAN_PATH.write_bytes(canonical_bytes(plan) + b"\n")
    SPEC_PATH.write_bytes(canonical_bytes(spec) + b"\n")
    return {
        "schema": "m114-freeze-v1",
        "milestone": bank.MILESTONE,
        "hypothesis": bank.HYPOTHESIS,
        "frozen_at": spec["frozen_at"],
        "plan_commitment_sha256": plan["plan_commitment_sha256"],
        "spec_commitment_sha256": spec["spec_commitment_sha256"],
        "canonical_request_body_sha256": spec["canonical_request_body_sha256"],
        "generator_inputs_are_m113s": bank.generator_inputs_are_m113s(ROOT),
        "delivery_semantics": spec["delivery_semantics"],
        "max_delivery_attempts": delivery.MAX_DELIVERY_ATTEMPTS,
        "max_bank_materializations": delivery.MAX_BANK_MATERIALIZATIONS,
    }


# ----------------------------------------------------------------------------------------
# The delivery sequence
# ----------------------------------------------------------------------------------------


def _evidence(observed: dict[str, Any] | None, failure: str | None) -> dict[str, Any]:
    """What the response says about whether the model ran, and whether it produced anything.

    Two booleans, and both are read by `classify_attempt` rather than by anything here. The
    asymmetry between them is the safeguard: `completion_present` is claimed only on a completion
    that is actually there, and `model_execution_cannot_be_excluded` is *not* cleared unless the
    evidence positively rules execution out.
    """
    if observed is None:
        # A transport failure. Whether the request reached the provider, whether the provider
        # reached the model, and whether the model produced anything are all unknown from here --
        # a read timeout looks exactly like a connection refused once the exception is caught. So
        # execution is not excluded. This costs an attempt when the connection never opened, and
        # that is the cheap side of the mistake.
        return {
            "completion_present": False,
            "model_execution_cannot_be_excluded": True,
            "why": "the transport raised before a response was read: %s" % failure,
        }

    decoded = observed.get("body")
    # A response that decoded to something other than an object is not a completion and is not
    # evidence of one. It must not raise here either: this function runs after the request has been
    # sent, so an exception would lose the very attempt the ledger exists to record.
    body = decoded if isinstance(decoded, dict) else {}
    choices = body.get("choices") or []
    message = (choices[0].get("message") or {}) if choices else {}
    content = message.get("content")
    completion = isinstance(content, str) and content.strip() != ""

    usage = body.get("usage") or {}
    tokens = usage.get("completion_tokens") or 0
    # Any of these means something downstream of the queue did work: a choices array, billed
    # completion tokens, or a finish reason. A capacity rejection carries none of them.
    executed = bool(choices) or bool(tokens) or bool(body.get("finish_reason"))

    return {
        "completion_present": completion,
        "model_execution_cannot_be_excluded": bool(executed) and not completion,
        "why": (
            "a completion is present" if completion
            else "the response carries evidence the model executed" if executed
            else "HTTP %s carrying no completion and no evidence of execution"
            % observed.get("status")
        ),
    }


# Fields a provider's error envelope may carry that identify the account rather than the failure.
# The 429 body is evidence and is preserved in full -- that is the whole repair over M113, whose
# client discarded it. But "in full" means the failure, not the caller: an account identifier says
# nothing about why the request was rejected and everything about who sent it, and this record is
# published. Stripped at capture, so it never reaches a ledger, a digest or a commit.
IDENTIFYING_RESPONSE_KEYS = ("user_id", "user", "account_id", "organization", "org_id", "key")
REDACTED = "[redacted: identifies the account, not the failure]"


def _without_identity(value: Any) -> Any:
    """Recursively replace account-identifying fields, preserving the document's shape."""
    if isinstance(value, dict):
        return {
            key: (REDACTED if key in IDENTIFYING_RESPONSE_KEYS else _without_identity(item))
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_without_identity(item) for item in value]
    return value


def _read_ledger() -> dict[str, Any] | None:
    if not LEDGER_PATH.is_file():
        return None
    try:
        ledger = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise GenerationError("the delivery ledger exists and cannot be read: %s" % exc)
    if not isinstance(ledger, dict):
        raise GenerationError("the delivery ledger is not an object")
    return ledger


def _write_ledger(ledger: dict[str, Any]) -> None:
    """Written after every attempt, before the next one is considered.

    A ledger written only at the end would be a ledger a crash could erase, and the attempt it
    erased would be the one nobody could see. Persisting each attempt as it completes is what makes
    the budget survive the process that spends it.
    """
    LEDGER_PATH.write_bytes(canonical_bytes(ledger) + b"\n")


def deliver(spec: dict[str, Any]) -> int:
    identity = spec["generator_identity"]
    commitment = spec["spec_commitment_sha256"]

    body = spec["canonical_request_body"]
    if sha256_hex(canonical_bytes(body)) != spec["canonical_request_body_sha256"]:
        raise GenerationError("the request body does not match the digest the spec froze")
    if contamination_hits(canonical_bytes(body).decode("utf-8")):
        raise GenerationError("the request body carries project context")
    if RESPONSE_PATH.is_file():
        raise GenerationError(
            "%s already exists; a materialized bank is not delivered twice"
            % _shown(RESPONSE_PATH)
        )

    ledger = _read_ledger() or {
        "schema": delivery.DELIVERY_LEDGER_SCHEMA,
        "milestone": bank.MILESTONE,
        "hypothesis": bank.HYPOTHESIS,
        "spec_commitment_sha256": commitment,
        "request_body_sha256": spec["canonical_request_body_sha256"],
        "delivery_rule_was_never_part_of_m113": True,
        "bank_materialization_index": None,
        "attempts": [],
    }
    if ledger.get("spec_commitment_sha256") != commitment:
        raise GenerationError(
            "the existing delivery ledger was opened against a different frozen spec"
        )

    attempts: list[dict[str, Any]] = list(ledger.get("attempts") or [])
    # Resuming is permitted only where the frozen rule already said another attempt was allowed.
    # The condition is recomputed here rather than read from the previous attempt's own claim.
    if attempts:
        last = attempts[-1]
        if not delivery.retry_permitted(last.get("outcome"), len(attempts)):
            raise GenerationError(
                "the delivery sequence is closed: attempt %d ended %r and the frozen rule permits "
                "no further attempt" % (len(attempts), last.get("outcome"))
            )

    while True:
        position = len(attempts) + 1
        waited = 0 if position == 1 else delivery.RETRY_WAIT_SECONDS
        if waited:
            print("waiting %d seconds before delivery attempt %d" % (waited, position))
            time.sleep(waited)

        started = _now()
        observed: dict[str, Any] | None = None
        failure: str | None = None
        try:
            observed = request(identity["endpoint"], body=body)
        except Exception as exc:  # noqa: BLE001 - a failed attempt is an outcome, not a crash
            failure = "%s: %s" % (type(exc).__name__, exc)

        decoded = (observed or {}).get("body")
        served = decoded if isinstance(decoded, dict) else {}
        evidence = _evidence(observed, failure)
        attempt = {
            "attempt_index": position,
            "started_at": started,
            "finished_at": (observed or {}).get("finished_at") or _now(),
            "status": (observed or {}).get("status"),
            "requested_provider": identity["provider"],
            "served_provider": served.get("provider"),
            "requested_model": identity["model"],
            "served_model": served.get("model"),
            "response_headers": (observed or {}).get("response_headers") or {},
            # The failure response is evidence, not noise. M113's first form recorded only a status
            # code and lost the body that explained it, at exactly the moment it mattered most.
            "error_body": None if evidence["completion_present"] else _without_identity(
                decoded if decoded is not None else ((observed or {}).get("raw_text") or failure)
            ),
            "response_sha256": (observed or {}).get("response_sha256"),
            "request_body_sha256": spec["canonical_request_body_sha256"],
            "completion_present": evidence["completion_present"],
            "model_execution_cannot_be_excluded": evidence["model_execution_cannot_be_excluded"],
            "classification_evidence": evidence["why"],
            "transport_failure": failure,
            "waited_seconds_before_this_attempt": waited,
        }
        attempt["outcome"] = delivery.classify_attempt(attempt)
        attempt["retry_permitted_by_the_frozen_rule"] = delivery.retry_permitted(
            attempt["outcome"], position
        )

        attempts.append(attempt)
        ledger["attempts"] = attempts
        ledger["bank_materialization_index"] = next(
            (a["attempt_index"] for a in attempts if a["outcome"] == "materialized"), None
        )
        _write_ledger(ledger)
        print("delivery attempt %d: %s (%s)" % (position, attempt["outcome"], evidence["why"]))

        if attempt["outcome"] == "materialized":
            break
        if not attempt["retry_permitted_by_the_frozen_rule"]:
            break

    final = attempts[-1]
    if final["outcome"] != "materialized":
        print()
        if all(a["outcome"] == "capacity_rejected" for a in attempts):
            print(
                "M114 = instrument-aborted. %d delivery attempts, %d capacity rejections, no bank."
                % (len(attempts), len(attempts))
            )
        else:
            print("M114 delivery ended %r without materializing a bank." % final["outcome"])
        print("The model was never reached, so this is a fact about transport capacity and not")
        print("a result about %s. Nothing is relaunched under M114." % bank.HYPOTHESIS)
        return 1

    # A materialization, and the served identity must be the frozen one. Fallbacks and automatic
    # routing are disabled in the spec precisely so that an answer from something else is a
    # refusal rather than a bank: if this fires, the payload did not come from the named generator.
    if final["served_model"] != identity["model"] or (
        final["served_provider"] is not None
        and final["served_provider"] != identity["provider"]
    ):
        # The body is deliberately not written. It may carry carriers, and a plaintext bank in this
        # public repository would destroy the experiment it belongs to -- and this one would not
        # even be M114's bank, since it came from a generator the record does not name. What the
        # ledger already holds is the tie to the evidence: the status, the response digest, the
        # served provider and the served model, all of which the contract then refuses.
        print("REFUSED: the served identity is not the frozen identity; the ledger records it")
        return 1

    RESPONSE_PATH.write_bytes(canonical_bytes({
        "schema": "m114-generation-response-v1",
        "milestone": bank.MILESTONE,
        "spec_commitment_sha256": commitment,
        "delivery_attempt_index": final["attempt_index"],
        "delivery_attempts_made": len(attempts),
        "request_body_sha256": spec["canonical_request_body_sha256"],
        "status": final["status"],
        "response_sha256": final["response_sha256"],
        "response_headers": final["response_headers"],
        "id": served.get("id"),
        "served_model": final["served_model"],
        "served_provider": final["served_provider"],
        "usage": served.get("usage"),
        "finish_reason": (
            (served.get("choices") or [{}])[0].get("finish_reason")
            if served.get("choices") else None
        ),
        "created": served.get("created"),
        "started_at": final["started_at"],
        "finished_at": final["finished_at"],
        "body": served,
    }) + b"\n")

    print()
    print("wrote %s" % _shown(RESPONSE_PATH))
    print("The response is preserved and unread. Seal it before anything reads it scientifically.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--smoke", action="store_true", help="DEVELOPMENT: one non-qualifying probe")
    mode.add_argument("--freeze", action="store_true", help="promote the candidate plan and spec")
    mode.add_argument("--deliver", action="store_true", help="the qualifying delivery sequence")
    parser.add_argument("--write", action="store_true", help="write the development report")
    arguments = parser.parse_args()

    try:
        if arguments.deliver:
            return deliver(load_spec(frozen_required=True))
        report = freeze() if arguments.freeze else smoke(write=arguments.write)
    except GenerationError as exc:
        print("REFUSED: %s" % exc)
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
