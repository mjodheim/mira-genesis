"""Fail-closed intake for the human baseline G9 requires.

G9 asks that protocols, exclusions, budgets, **human baselines** and decision rules be committed
before private evaluation. The repository has every part of that except the baseline, and a baseline
cannot be written by the project: a system compared against its own author's estimate of human
performance has been compared against nothing.

So this module does for the baseline what `m085_cross_domain_intake` does for the sealed bank. It
refuses until real people have attempted the frozen tasks under a protocol committed beforehand, and
it makes the ways that could go wrong mechanical rather than remembered:

* participants and the coordinator may not be project identities;
* the protocol binds the exact task set by digest, so a baseline cannot be retrofitted to an easier
  set after the system's own numbers are known;
* the result binds the exact protocol digest, so the protocol cannot be edited after the sessions;
* participants must be attested uncoached and free of prior exposure, for the same reason the bank
  forbids supplying a decomposition;
* the cost of the human side must be declared, because G9 asks for cost on both sides of a
  comparison and a baseline whose cost is unstated flatters whichever side omitted it.

Nothing here computes a significance test. A human baseline is a **reference point reported as a
range**, not a hypothesis test, and this module refuses a result that claims otherwise.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from metamorphosis.m075_private_readiness import PROJECT_IDENTITIES

PROTOCOL_SCHEMA = "mira-human-baseline-protocol-v1"
RESULT_SCHEMA = "mira-human-baseline-result-v1"

# Five is not a power calculation and must never be presented as one. It is the smallest number for
# which reporting a minimum, a median and a maximum says more than one anecdote does. A baseline
# here is descriptive; if a later experiment wants an inferential claim about human performance it
# needs its own design, not a larger number bolted onto this one.
MINIMUM_PARTICIPANTS = 5

PROTOCOL_PATH = Path("experiments/G9/HUMAN_BASELINE_PROTOCOL.json")
RESULT_PATH = Path("experiments/G9/HUMAN_BASELINE_RESULT.json")

REQUIRED_ATTESTATIONS = (
    "evaluator_owned_success_attested",
    "no_decomposition_supplied_attested",
    "participants_uncoached_attested",
)


class HumanBaselineError(ValueError):
    """Raised when a baseline claims more independence or more inference than it has."""


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _is_project_identity(value: object) -> bool:
    return isinstance(value, str) and value.strip().casefold() in PROJECT_IDENTITIES


def validate_baseline_protocol(protocol: Mapping[str, Any]) -> None:
    """Validate the pre-commitment. No result may exist when this is written."""

    if protocol.get("schema") != PROTOCOL_SCHEMA:
        raise HumanBaselineError("human baseline protocol uses an unrecognized schema")
    if protocol.get("committed_before_system_evaluation") is not True:
        raise HumanBaselineError(
            "a baseline committed after the system's own numbers are known is not a baseline"
        )
    if not _is_sha256(protocol.get("task_set_sha256")):
        raise HumanBaselineError("protocol does not bind a task set by digest")

    coordinator = protocol.get("coordinator_identity")
    if not isinstance(coordinator, str) or not coordinator.strip():
        raise HumanBaselineError("protocol names no coordinator")
    if _is_project_identity(coordinator):
        raise HumanBaselineError("a project identity may not coordinate the human baseline")

    participants = protocol.get("participants")
    if not isinstance(participants, list) or len(participants) < MINIMUM_PARTICIPANTS:
        raise HumanBaselineError(
            "at least %d participants are required" % MINIMUM_PARTICIPANTS
        )
    seen: set[str] = set()
    for entry in participants:
        if not isinstance(entry, Mapping):
            raise HumanBaselineError("each participant must be a record")
        identifier = entry.get("participant_id")
        if not isinstance(identifier, str) or not identifier.strip():
            raise HumanBaselineError("a participant carries no identifier")
        if identifier in seen:
            raise HumanBaselineError("participant %r is listed twice" % identifier)
        seen.add(identifier)
        if _is_project_identity(identifier):
            raise HumanBaselineError("a project identity may not be a baseline participant")
        if entry.get("prior_exposure_to_tasks") is not False:
            raise HumanBaselineError(
                "participant %r has prior exposure to the tasks" % identifier
            )
        if not isinstance(entry.get("compensation_basis"), str) or not entry["compensation_basis"]:
            raise HumanBaselineError(
                "participant %r declares no compensation basis; state 'unpaid' if unpaid"
                % identifier
            )
        if entry.get("compensation_contingent_on_outcome") is not False:
            raise HumanBaselineError(
                "participant %r is paid contingently on the outcome" % identifier
            )

    for flag in REQUIRED_ATTESTATIONS:
        if protocol.get(flag) is not True:
            raise HumanBaselineError("protocol does not assert %s" % flag)
    if protocol.get("makes_a_significance_claim") is not False:
        raise HumanBaselineError(
            "a human baseline is a reported range, not a significance test"
        )


def validate_baseline_result(
    result: Mapping[str, Any], *, protocol_sha256: str, protocol: Mapping[str, Any]
) -> None:
    """Validate the outcome against the exact protocol it claims to follow."""

    if result.get("schema") != RESULT_SCHEMA:
        raise HumanBaselineError("human baseline result uses an unrecognized schema")
    if result.get("protocol_sha256") != protocol_sha256:
        raise HumanBaselineError("result does not bind the committed protocol")
    if result.get("task_set_sha256") != protocol.get("task_set_sha256"):
        raise HumanBaselineError("result was measured on a different task set")

    per_participant = result.get("per_participant")
    if not isinstance(per_participant, list) or not per_participant:
        raise HumanBaselineError("result records no per-participant outcome")
    expected = {entry["participant_id"] for entry in protocol["participants"]}
    reported = set()
    for entry in per_participant:
        if not isinstance(entry, Mapping):
            raise HumanBaselineError("each per-participant outcome must be a record")
        identifier = entry.get("participant_id")
        if identifier not in expected:
            raise HumanBaselineError("outcome names unlisted participant %r" % identifier)
        reported.add(identifier)
        for field in ("tasks_attempted", "tasks_solved"):
            value = entry.get(field)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise HumanBaselineError(
                    "participant %r reports a malformed %s" % (identifier, field)
                )
        if entry["tasks_solved"] > entry["tasks_attempted"]:
            raise HumanBaselineError(
                "participant %r solved more tasks than attempted" % identifier
            )
        seconds = entry.get("wall_clock_seconds")
        if not isinstance(seconds, (int, float)) or isinstance(seconds, bool) or seconds < 0:
            raise HumanBaselineError("participant %r declares no time cost" % identifier)
    missing = sorted(expected - reported)
    if missing:
        raise HumanBaselineError(
            "committed participants are absent from the result: %s" % ", ".join(missing)
        )

    cost = result.get("cost")
    if not isinstance(cost, Mapping):
        raise HumanBaselineError("result declares no cost for the human side")
    if cost.get("amount") is None and not cost.get("reason"):
        raise HumanBaselineError("an unpriced baseline must state why it is unpriced")
    if not isinstance(cost.get("total_wall_clock_seconds"), (int, float)):
        raise HumanBaselineError("result declares no total human time")
    if result.get("makes_a_significance_claim") is not False:
        raise HumanBaselineError(
            "a human baseline is a reported range, not a significance test"
        )


def summarize(result: Mapping[str, Any]) -> dict[str, Any]:
    """Report the baseline as a range. This deliberately computes no p-value."""

    rates = []
    for entry in result["per_participant"]:
        attempted = entry["tasks_attempted"]
        rates.append(entry["tasks_solved"] / attempted if attempted else 0.0)
    rates.sort()
    middle = len(rates) // 2
    median = rates[middle] if len(rates) % 2 else (rates[middle - 1] + rates[middle]) / 2
    return {
        "participants": len(rates),
        "solved_fraction_min": rates[0],
        "solved_fraction_median": median,
        "solved_fraction_max": rates[-1],
        "is_a_significance_test": False,
        "total_wall_clock_seconds": result["cost"]["total_wall_clock_seconds"],
        "monetary_cost": dict(result["cost"]),
    }


def _load(path: Path) -> tuple[dict[str, Any] | None, bytes | None, str | None]:
    if not path.exists():
        return None, None, "missing %s" % path.name
    try:
        raw = path.read_bytes()
        value = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return None, None, "malformed %s: %s" % (path.name, exc)
    if not isinstance(value, dict):
        return None, None, "malformed %s: expected one JSON object" % path.name
    return value, raw, None


def assess_readiness(root: Path) -> dict[str, Any]:
    """Report whether a usable human baseline exists. It does not, and says so."""

    resolved = Path(root).resolve()
    blockers: list[str] = []

    protocol, protocol_raw, error = _load(resolved / PROTOCOL_PATH)
    if error:
        blockers.append(error)
    if protocol is not None:
        try:
            validate_baseline_protocol(protocol)
        except HumanBaselineError as exc:
            blockers.append(str(exc))

    result, _, error = _load(resolved / RESULT_PATH)
    if error:
        blockers.append(error)
    if result is not None and protocol is not None and protocol_raw is not None:
        try:
            validate_baseline_result(
                result,
                protocol_sha256=_sha256_bytes(protocol_raw),
                protocol=protocol,
            )
        except HumanBaselineError as exc:
            blockers.append(str(exc))

    summary = None
    if not blockers and result is not None:
        summary = summarize(result)

    return {
        "schema": "mira-human-baseline-readiness-v1",
        "human_baseline_available": not blockers,
        "blockers": blockers,
        "required_minimum_participants": MINIMUM_PARTICIPANTS,
        "summary": summary,
        "g9_cost_reporting_required_on_both_sides": True,
        "baseline_is_a_range_not_a_significance_test": True,
    }
