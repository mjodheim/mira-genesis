"""Strict Q4 candidate, worker and validation-report contracts."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
from typing import Mapping, Sequence

from metamorphosis.m043_mealy import MealyMachine, Word
from metamorphosis.m043_rewrite import RewriteTrace, trace_digest, trace_from_bytes
from metamorphosis.m043_task_model import SearchBudget

CANDIDATE_SCHEMA = "m043-q4-candidate-v1"
WORKER_REQUEST_SCHEMA = "m043-q4-worker-request-v1"
WORKER_RESULT_SCHEMA = "m043-q4-worker-result-v1"
SNAPSHOT_SCHEMA = "m043-q4-lineage-snapshot-v1"
VALIDATION_REPORT_SCHEMA = "m043-q4-validation-report-v1"
MAX_CANDIDATE_BYTES = 131_072
VALIDATION_TIMEOUT_SECONDS = 10.0


class AdoptionError(ValueError):
    """Raised when a Q4 package, report, snapshot or transaction fails closed."""


class ValidationStatus(str, Enum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    SANDBOX_ERROR = "sandbox_error"


class FaultKind(str, Enum):
    BODY = "body"
    REGISTRY = "registry"
    LEARNING_STATE = "learning_state"
    JOURNAL = "journal"


def _mapping(value: object, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or any(not isinstance(key, str) for key in value):
        raise AdoptionError(f"{field} must be an object")
    return value


def _sequence(value: object, field: str) -> Sequence[object]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise AdoptionError(f"{field} must be a sequence")
    return value


def _integer(value: object, field: str, *, minimum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise AdoptionError(f"{field} must be an integer")
    if minimum is not None and value < minimum:
        raise AdoptionError(f"{field} must be at least {minimum}")
    return value


def _boolean(value: object, field: str) -> bool:
    if not isinstance(value, bool):
        raise AdoptionError(f"{field} must be a boolean")
    return value


def _string(value: object, field: str, *, nonempty: bool = True) -> str:
    if not isinstance(value, str) or (nonempty and not value):
        raise AdoptionError(f"{field} must be a string")
    return value


def _digest(value: object, field: str) -> str:
    text = _string(value, field)
    if len(text) != 64 or any(character not in "0123456789abcdef" for character in text):
        raise AdoptionError(f"{field} must be a lowercase SHA-256 digest")
    return text


def _fields(data: Mapping[str, object], expected: set[str], field: str) -> None:
    if set(data) != expected:
        missing = sorted(expected - set(data))
        extra = sorted(set(data) - expected)
        raise AdoptionError(f"invalid {field} fields: missing={missing}, extra={extra}")


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")


def _domain_digest(domain: bytes, value: object) -> str:
    return hashlib.sha256(domain + _canonical_json(value)).hexdigest()


def _parse_json(payload: bytes | str, field: str) -> Mapping[str, object]:
    try:
        return _mapping(json.loads(payload), field)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise AdoptionError(f"{field} is not valid JSON") from exc


def _budget_from_dict(value: object) -> SearchBudget:
    raw = _mapping(value, "search_budget")
    _fields(raw, {"max_depth", "max_nodes", "max_states"}, "search_budget")
    return SearchBudget(
        max_depth=_integer(raw["max_depth"], "max_depth", minimum=1),
        max_nodes=_integer(raw["max_nodes"], "max_nodes", minimum=1),
        max_states=_integer(raw["max_states"], "max_states", minimum=1),
    )


@dataclass(frozen=True)
class CandidatePackage:
    task_id: str
    parent_lineage_digest: str
    parent_body_digest: str
    target_commitment: str
    trace: RewriteTrace
    search_budget: SearchBudget
    expected_final_body_digest: str
    schema: str = CANDIDATE_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != CANDIDATE_SCHEMA:
            raise AdoptionError("unsupported candidate schema")
        _string(self.task_id, "task_id")
        _digest(self.parent_lineage_digest, "parent_lineage_digest")
        _digest(self.parent_body_digest, "parent_body_digest")
        _digest(self.target_commitment, "target_commitment")
        _digest(self.expected_final_body_digest, "expected_final_body_digest")
        if not isinstance(self.trace, RewriteTrace):
            raise AdoptionError("trace must be a RewriteTrace")
        if not isinstance(self.search_budget, SearchBudget):
            raise AdoptionError("search_budget must be a SearchBudget")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "task_id": self.task_id,
            "parent_lineage_digest": self.parent_lineage_digest,
            "parent_body_digest": self.parent_body_digest,
            "target_commitment": self.target_commitment,
            "trace": self.trace.to_dict(),
            "search_budget": self.search_budget.to_dict(),
            "expected_final_body_digest": self.expected_final_body_digest,
        }

    def to_bytes(self) -> bytes:
        payload = _canonical_json(self.to_dict())
        if len(payload) > MAX_CANDIDATE_BYTES:
            raise AdoptionError("candidate package exceeds the fixed payload limit")
        return payload

    def digest(self) -> str:
        return hashlib.sha256(b"m043-q4-candidate-v1\x00" + self.to_bytes()).hexdigest()

    @staticmethod
    def from_bytes(payload: bytes | str) -> "CandidatePackage":
        raw = _parse_json(payload, "candidate package")
        expected = {
            "schema",
            "task_id",
            "parent_lineage_digest",
            "parent_body_digest",
            "target_commitment",
            "trace",
            "search_budget",
            "expected_final_body_digest",
        }
        _fields(raw, expected, "candidate package")
        if raw["schema"] != CANDIDATE_SCHEMA:
            raise AdoptionError("unsupported candidate schema")
        trace_payload = _canonical_json(_mapping(raw["trace"], "trace"))
        try:
            trace = trace_from_bytes(trace_payload)
        except ValueError as exc:
            raise AdoptionError("candidate trace is malformed") from exc
        candidate = CandidatePackage(
            task_id=_string(raw["task_id"], "task_id"),
            parent_lineage_digest=_digest(
                raw["parent_lineage_digest"], "parent_lineage_digest"
            ),
            parent_body_digest=_digest(raw["parent_body_digest"], "parent_body_digest"),
            target_commitment=_digest(raw["target_commitment"], "target_commitment"),
            trace=trace,
            search_budget=_budget_from_dict(raw["search_budget"]),
            expected_final_body_digest=_digest(
                raw["expected_final_body_digest"], "expected_final_body_digest"
            ),
        )
        if len(candidate.to_bytes()) > MAX_CANDIDATE_BYTES:
            raise AdoptionError("candidate package exceeds the fixed payload limit")
        return candidate


@dataclass(frozen=True)
class WorkerResult:
    replayed: bool
    reason: str
    worker_pid: int
    parent_body_digest: str | None
    candidate_body_digest: str | None
    candidate_behaviour_digest: str | None
    candidate_state_count: int | None
    trace_digest: str | None
    candidate: MealyMachine | None
    schema: str = WORKER_RESULT_SCHEMA

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "replayed": self.replayed,
            "reason": self.reason,
            "worker_pid": self.worker_pid,
            "parent_body_digest": self.parent_body_digest,
            "candidate_body_digest": self.candidate_body_digest,
            "candidate_behaviour_digest": self.candidate_behaviour_digest,
            "candidate_state_count": self.candidate_state_count,
            "trace_digest": self.trace_digest,
            "candidate": None if self.candidate is None else self.candidate.to_dict(),
        }

    def to_bytes(self) -> bytes:
        return _canonical_json(self.to_dict())

    @staticmethod
    def from_bytes(payload: bytes | str) -> "WorkerResult":
        raw = _parse_json(payload, "worker result")
        expected = {
            "schema",
            "replayed",
            "reason",
            "worker_pid",
            "parent_body_digest",
            "candidate_body_digest",
            "candidate_behaviour_digest",
            "candidate_state_count",
            "trace_digest",
            "candidate",
        }
        _fields(raw, expected, "worker result")
        if raw["schema"] != WORKER_RESULT_SCHEMA:
            raise AdoptionError("unsupported worker-result schema")
        replayed = _boolean(raw["replayed"], "replayed")
        candidate_raw = raw["candidate"]
        candidate: MealyMachine | None = None
        if candidate_raw is not None:
            try:
                candidate = MealyMachine.from_dict(_mapping(candidate_raw, "candidate"))
            except ValueError as exc:
                raise AdoptionError("worker candidate is malformed") from exc
        optional_digest_fields = (
            "parent_body_digest",
            "candidate_body_digest",
            "candidate_behaviour_digest",
            "trace_digest",
        )
        parsed: dict[str, str | None] = {}
        for field in optional_digest_fields:
            parsed[field] = None if raw[field] is None else _digest(raw[field], field)
        state_count = raw["candidate_state_count"]
        parsed_state_count = (
            None
            if state_count is None
            else _integer(state_count, "candidate_state_count", minimum=1)
        )
        result = WorkerResult(
            replayed=replayed,
            reason=_string(raw["reason"], "reason", nonempty=False),
            worker_pid=_integer(raw["worker_pid"], "worker_pid", minimum=1),
            parent_body_digest=parsed["parent_body_digest"],
            candidate_body_digest=parsed["candidate_body_digest"],
            candidate_behaviour_digest=parsed["candidate_behaviour_digest"],
            candidate_state_count=parsed_state_count,
            trace_digest=parsed["trace_digest"],
            candidate=candidate,
        )
        if replayed and (
            candidate is None
            or result.parent_body_digest is None
            or result.candidate_body_digest is None
            or result.candidate_behaviour_digest is None
            or result.candidate_state_count is None
            or result.trace_digest is None
        ):
            raise AdoptionError("successful worker result is incomplete")
        return result


@dataclass(frozen=True)
class ValidationReport:
    status: ValidationStatus
    reason: str
    parent_lineage_digest: str
    package_digest: str
    task_id: str
    target_commitment: str
    trace_digest: str
    worker_pid: int | None
    disposable_process: bool
    candidate_body_digest: str | None
    candidate_behaviour_digest: str | None
    candidate_state_count: int | None
    exact_target_match: bool
    parent_was_incapable: bool
    resource_limits_respected: bool
    parent_distinguishing_word: Word | None
    schema: str = VALIDATION_REPORT_SCHEMA

    @property
    def accepted(self) -> bool:
        return self.status is ValidationStatus.ACCEPTED

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "status": self.status.value,
            "reason": self.reason,
            "parent_lineage_digest": self.parent_lineage_digest,
            "package_digest": self.package_digest,
            "task_id": self.task_id,
            "target_commitment": self.target_commitment,
            "trace_digest": self.trace_digest,
            "worker_pid": self.worker_pid,
            "disposable_process": self.disposable_process,
            "candidate_body_digest": self.candidate_body_digest,
            "candidate_behaviour_digest": self.candidate_behaviour_digest,
            "candidate_state_count": self.candidate_state_count,
            "exact_target_match": self.exact_target_match,
            "parent_was_incapable": self.parent_was_incapable,
            "resource_limits_respected": self.resource_limits_respected,
            "parent_distinguishing_word": (
                None
                if self.parent_distinguishing_word is None
                else list(self.parent_distinguishing_word)
            ),
            "accepted": self.accepted,
        }

    def identity_dict(self) -> dict[str, object]:
        """Return the deterministic report identity, excluding the runtime process id."""
        value = self.to_dict()
        value["worker_pid"] = None
        return value

    def digest(self) -> str:
        return _domain_digest(
            b"m043-q4-validation-report-v1\x00", self.identity_dict()
        )


@dataclass(frozen=True)
class ValidationDecision:
    report: ValidationReport
    candidate: MealyMachine | None


@dataclass(frozen=True)
class AdoptionReceipt:
    adopted: bool
    rolled_back: bool
    reason: str
    before_snapshot_digest: str
    after_snapshot_digest: str
    before_snapshot_bytes: bytes
    after_snapshot_bytes: bytes
    attempted_version: int
    committed_version: int
    fault_kind: FaultKind | None

    @property
    def exact_restoration(self) -> bool:
        return (
            self.rolled_back
            and self.before_snapshot_digest == self.after_snapshot_digest
            and self.before_snapshot_bytes == self.after_snapshot_bytes
        )


__all__ = [
    "AdoptionError",
    "AdoptionReceipt",
    "CandidatePackage",
    "FaultKind",
    "MAX_CANDIDATE_BYTES",
    "VALIDATION_TIMEOUT_SECONDS",
    "ValidationDecision",
    "ValidationReport",
    "ValidationStatus",
    "WORKER_REQUEST_SCHEMA",
    "WORKER_RESULT_SCHEMA",
    "WorkerResult",
]
