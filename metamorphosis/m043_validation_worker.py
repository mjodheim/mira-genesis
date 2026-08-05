"""One-shot disposable replay worker for M043 Q4.

The worker receives only the accepted parent and a candidate package. It does not import
Q3 task/evaluator code and never receives the hidden target body.
"""
from __future__ import annotations

import json
import os
import sys
from typing import Mapping

from metamorphosis.m043_adoption_codec import (
    CandidatePackage,
    WORKER_REQUEST_SCHEMA,
    WorkerResult,
)
from metamorphosis.m043_mealy import MealyMachine, mealy_digest
from metamorphosis.m043_rewrite import (
    exact_body_digest,
    replay_rewrite_trace,
    trace_digest,
)


def _rejected(reason: str) -> WorkerResult:
    return WorkerResult(
        replayed=False,
        reason=reason,
        worker_pid=os.getpid(),
        parent_body_digest=None,
        candidate_body_digest=None,
        candidate_behaviour_digest=None,
        candidate_state_count=None,
        trace_digest=None,
        candidate=None,
    )


def replay_request(payload: bytes | str) -> WorkerResult:
    try:
        raw = json.loads(payload)
        if not isinstance(raw, Mapping) or set(raw) != {
            "schema",
            "parent",
            "candidate_package",
        }:
            return _rejected("invalid worker request fields")
        if raw["schema"] != WORKER_REQUEST_SCHEMA:
            return _rejected("unsupported worker request schema")
        if not isinstance(raw["parent"], Mapping):
            return _rejected("parent must be an object")
        parent = MealyMachine.from_dict(raw["parent"])
        package = CandidatePackage.from_bytes(
            json.dumps(
                raw["candidate_package"],
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        if exact_body_digest(parent) != package.parent_body_digest:
            return _rejected("worker parent identity mismatch")
        if len(package.trace.steps) > package.search_budget.max_depth:
            return _rejected("worker trace exceeds the depth budget")
        candidate = replay_rewrite_trace(parent, package.trace)
        if candidate.n_states > package.search_budget.max_states:
            return _rejected("worker candidate exceeds the state budget")
        if exact_body_digest(candidate) != package.expected_final_body_digest:
            return _rejected("worker candidate final identity mismatch")
        return WorkerResult(
            replayed=True,
            reason="replayed",
            worker_pid=os.getpid(),
            parent_body_digest=exact_body_digest(parent),
            candidate_body_digest=exact_body_digest(candidate),
            candidate_behaviour_digest=mealy_digest(candidate, minimise=True),
            candidate_state_count=candidate.n_states,
            trace_digest=trace_digest(package.trace),
            candidate=candidate,
        )
    except Exception as exc:  # fail closed at the process boundary
        return _rejected(f"worker rejected request: {type(exc).__name__}")


def main() -> int:
    result = replay_request(sys.stdin.buffer.read())
    sys.stdout.buffer.write(result.to_bytes())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
