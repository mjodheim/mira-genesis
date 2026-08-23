"""Independently validate a development M101 lineage state.

This checker intentionally does not import either M101 implementation module.  It
recomputes the state and definition addresses from canonical bytes, then evaluates the
registered definitions over symbolic slot traces.  It validates apparatus structure;
it does not inspect a qualification population and cannot issue a scientific verdict.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

STATE_SCHEMA = "m101-lineage-state-v1"
DEFINITION_SCHEMA = "m101-definition-v1"
REPORT_SCHEMA = "m101-definition-validation-v1"
A_ORIGIN = "m101-a"
B_ORIGIN = "m101-b"
M100_STATE_SCHEMA = "m100-cumulative-operation-language-v1"
M100_DEFINITION_SCHEMA = "m100-cumulative-operation-v1"
M097_DEFINITION_SCHEMA = "m097-expression-operation-v1"

FORBIDDEN_A_SUBSTRINGS = (
    "text",
    "record",
    "mapping",
    "dict",
    "python",
    "syntax",
    "ast",
    "compose",
    "composition",
    "chain",
)


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("ascii")).hexdigest()


def _closed(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError(f"{label} is not a closed record")
    return value


def _definition_id(origin: str, body: list[str], dependencies: list[str]) -> str:
    payload = {
        "schema": DEFINITION_SCHEMA,
        "origin": origin,
        "body": body,
        "dependencies": dependencies,
    }
    prefix = "generic-combinator" if origin == A_ORIGIN else "syntax-successor"
    return f"{prefix}-{digest(payload)[:16]}"


def _m100_id(body: list[str], dependencies: list[str], origin: str) -> str:
    if origin == "m097":
        return "derived-expression-" + digest(
            {"schema": M097_DEFINITION_SCHEMA, "body": body}
        )[:16]
    return "cumulative-expression-" + digest(
        {
            "schema": M100_DEFINITION_SCHEMA,
            "body": body,
            "dependency_ids": dependencies,
        }
    )[:16]


def _m100_signature(
    body: list[str], known: dict[str, tuple[int, int]]
) -> tuple[int, int] | None:
    stack: list[tuple[int, int]] = []
    for token in body:
        if token == "PUSH_LEFT":
            stack.append((1, 0))
        elif token == "PUSH_RIGHT":
            stack.append((0, 1))
        elif token == "NEG":
            if not stack:
                return None
            left, right = stack.pop()
            stack.append((-left, -right))
        elif token == "SWAP":
            if len(stack) < 2:
                return None
            stack[-1], stack[-2] = stack[-2], stack[-1]
        else:
            if len(stack) < 2:
                return None
            right = stack.pop()
            left = stack.pop()
            if token == "ADD":
                stack.append((left[0] + right[0], left[1] + right[1]))
            elif token == "SUB":
                stack.append((left[0] - right[0], left[1] - right[1]))
            elif token == "MUL":
                return None
            elif token.startswith("CALL:") and token[5:] in known:
                signature = known[token[5:]]
                stack.append(
                    (
                        signature[0] * left[0] + signature[1] * right[0],
                        signature[0] * left[1] + signature[1] * right[1],
                    )
                )
            else:
                return None
    return stack[0] if len(stack) == 1 else None


def _validate_m100(raw: bytes) -> list[dict[str, Any]]:
    try:
        state = json.loads(raw.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"embedded M100 state is not canonical ASCII JSON: {error}") from error
    if canonical_json(state).encode("ascii") != raw:
        raise ValueError("embedded M100 state bytes are not canonical JSON")
    state = _closed(
        state,
        {
            "schema",
            "inherited_digest",
            "origin_m097_state_digest",
            "operations",
            "state_digest",
        },
        "embedded M100 state",
    )
    payload = {key: value for key, value in state.items() if key != "state_digest"}
    if state["schema"] != M100_STATE_SCHEMA or state["state_digest"] != digest(payload):
        raise ValueError("embedded M100 state binding is invalid")
    operations = state["operations"]
    if not isinstance(operations, list) or len(operations) != 3:
        raise ValueError("embedded M100 state is not the complete S3 lineage")
    known: dict[str, tuple[int, int]] = {}
    reports: list[dict[str, Any]] = []
    for index, raw_operation in enumerate(operations):
        operation = _closed(
            raw_operation,
            {"schema", "operation_id", "origin", "body", "dependency_ids"},
            "embedded M100 operation",
        )
        body = operation["body"]
        dependencies = operation["dependency_ids"]
        origin = operation["origin"]
        operation_id = operation["operation_id"]
        if operation["schema"] != M100_DEFINITION_SCHEMA:
            raise ValueError("embedded M100 operation schema mismatch")
        if not isinstance(operation_id, str) or origin not in {"m097", "m100-cycle"}:
            raise ValueError("embedded M100 operation identity is invalid")
        if not isinstance(body, list) or not 0 < len(body) <= 6 or not all(
            isinstance(token, str) for token in body
        ):
            raise ValueError("embedded M100 operation body is invalid")
        if not isinstance(dependencies, list) or not all(
            isinstance(dependency, str) for dependency in dependencies
        ):
            raise ValueError("embedded M100 dependency list is invalid")
        observed_dependencies: list[str] = []
        for token in body:
            if token.startswith("CALL:") and token[5:] not in observed_dependencies:
                observed_dependencies.append(token[5:])
        if dependencies != observed_dependencies or any(
            dependency not in known for dependency in dependencies
        ):
            raise ValueError("embedded M100 live dependency graph changed")
        if operation_id != _m100_id(body, dependencies, str(origin)):
            raise ValueError("embedded M100 operation address changed")
        if (index == 0 and (origin != "m097" or dependencies)) or (
            index > 0 and origin != "m100-cycle"
        ):
            raise ValueError("embedded M100 operation chronology changed")
        signature = _m100_signature(body, known)
        if signature is None:
            raise ValueError("embedded M100 operation has no independent affine signature")
        known[operation_id] = signature
        reports.append(
            {"operation_id": operation_id, "signature": list(signature), "origin": origin}
        )
    if [item["signature"] for item in reports] != [[1, -1], [1, 1], [1, 2]]:
        raise ValueError("embedded M100 A/B/C semantics changed")
    return reports


def _symbolic_a(
    body: list[str],
    *,
    initial: tuple[int, ...] = (),
    slots: tuple[int, int] = (0, 1),
) -> tuple[int, ...] | None:
    """Evaluate A independently as a trace transformer over opaque slot labels."""
    stack: list[tuple[int, ...]] = []
    result: tuple[int, ...] | None = None
    for token in body:
        if result is not None:
            return None
        if token == "LOAD_INPUT":
            stack.append(initial)
        elif token == "APPLY_SLOT:0":
            if not stack:
                return None
            stack.append(stack.pop() + (slots[0],))
        elif token == "APPLY_SLOT:1":
            if not stack:
                return None
            stack.append(stack.pop() + (slots[1],))
        elif token == "DUP":
            if not stack:
                return None
            stack.append(stack[-1])
        elif token == "SWAP":
            if len(stack) < 2:
                return None
            stack[-1], stack[-2] = stack[-2], stack[-1]
        elif token == "RETURN":
            if len(stack) != 1:
                return None
            result = stack.pop()
        else:
            return None
    return result if result is not None and not stack else None


def _symbolic_b(
    body: list[str], a_id: str, a_body: list[str]
) -> tuple[tuple[int, ...] | None, int, int]:
    """Evaluate B without sharing the runtime parser or executor."""
    current: tuple[int, ...] | None = None
    loaded = False
    returned = False
    calls = 0
    direct_applications = 0
    for token in body:
        if returned:
            return None, calls, direct_applications
        if token == "LOAD_INPUT":
            if loaded:
                return None, calls, direct_applications
            current = ()
            loaded = True
            continue
        if token == "RETURN":
            if not loaded or current is None:
                return None, calls, direct_applications
            returned = True
            continue
        if token.startswith("CALL:"):
            parts = token.split(":")
            if len(parts) != 4 or not loaded or current is None:
                return None, calls, direct_applications
            try:
                left, right = int(parts[2]), int(parts[3])
            except ValueError:
                return None, calls, direct_applications
            if (
                parts[1] != a_id
                or calls
                or direct_applications
                or left not in {0, 1, 2}
                or right not in {0, 1, 2}
            ):
                return None, calls, direct_applications
            calls += 1
            current = _symbolic_a(a_body, initial=current, slots=(left, right))
            if current is None:
                return None, calls, direct_applications
            continue
        if token.startswith("APPLY_SLOT:"):
            if not loaded or current is None or calls != 1:
                return None, calls, direct_applications
            try:
                slot = int(token.split(":", 1)[1])
            except ValueError:
                return None, calls, direct_applications
            if slot not in {0, 1, 2} or direct_applications:
                return None, calls, direct_applications
            direct_applications += 1
            current += (slot,)
            continue
        return None, calls, direct_applications
    if not returned or calls != 1 or direct_applications != 1:
        return None, calls, direct_applications
    return current, calls, direct_applications


def validate(raw: bytes, *, expected_m100_sha256: str | None = None) -> dict[str, Any]:
    try:
        decoded = raw.decode("ascii")
        state = json.loads(decoded)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"M101 state is not canonical ASCII JSON: {error}") from error
    if canonical_json(state).encode("ascii") != raw:
        raise ValueError("M101 state bytes are not canonical JSON")

    state = _closed(
        state,
        {"schema", "m100_sha256", "m100_ascii", "definitions", "state_digest"},
        "M101 state",
    )
    payload = {key: value for key, value in state.items() if key != "state_digest"}
    if state["schema"] != STATE_SCHEMA:
        raise ValueError("M101 state schema mismatch")
    if state["state_digest"] != digest(payload):
        raise ValueError("M101 state digest mismatch")
    if not isinstance(state["m100_ascii"], str) or not isinstance(state["m100_sha256"], str):
        raise ValueError("M101 predecessor binding is invalid")
    measured_m100 = hashlib.sha256(state["m100_ascii"].encode("ascii")).hexdigest()
    if measured_m100 != state["m100_sha256"]:
        raise ValueError("M100 predecessor bytes changed")
    if expected_m100_sha256 is not None and measured_m100 != expected_m100_sha256:
        raise ValueError("M100 predecessor differs from the independently expected digest")
    m100_reports = _validate_m100(state["m100_ascii"].encode("ascii"))

    definitions = state["definitions"]
    if not isinstance(definitions, list) or len(definitions) > 2:
        raise ValueError("M101 definition census is invalid")
    seen: set[str] = set()
    definition_reports: list[dict[str, Any]] = []
    a_id: str | None = None
    a_body: list[str] | None = None
    for index, raw_definition in enumerate(definitions):
        item = _closed(
            raw_definition,
            {"schema", "definition_id", "origin", "body", "dependencies"},
            "M101 definition",
        )
        if item["schema"] != DEFINITION_SCHEMA:
            raise ValueError("M101 definition schema mismatch")
        if item["origin"] not in {A_ORIGIN, B_ORIGIN}:
            raise ValueError("M101 definition origin is invalid")
        if not isinstance(item["body"], list) or not all(
            isinstance(token, str) for token in item["body"]
        ):
            raise ValueError("M101 definition body is invalid")
        if not isinstance(item["dependencies"], list) or not all(
            isinstance(dependency, str) for dependency in item["dependencies"]
        ):
            raise ValueError("M101 dependency list is invalid")
        body = list(item["body"])
        dependencies = list(item["dependencies"])
        expected_id = _definition_id(str(item["origin"]), body, dependencies)
        if item["definition_id"] != expected_id:
            raise ValueError("M101 content-addressed definition id mismatch")
        if item["definition_id"] in seen or any(dependency not in seen for dependency in dependencies):
            raise ValueError("M101 definition dependency order is invalid")

        if index == 0:
            if item["origin"] != A_ORIGIN or dependencies:
                raise ValueError("the first M101 definition must be dependency-free A")
            trace = _symbolic_a(body)
            if trace is None or sorted(trace) != [0, 1]:
                raise ValueError("A symbolic semantics do not compose two distinct opaque slots")
            text = canonical_json(item).lower()
            if any(term in text for term in FORBIDDEN_A_SUBSTRINGS):
                raise ValueError("A contains a forbidden carrier or shortcut identifier")
            a_id = str(item["definition_id"])
            a_body = body
            definition_reports.append(
                {
                    "definition_id": a_id,
                    "origin": A_ORIGIN,
                    "symbolic_trace": list(trace),
                    "dependency_count": 0,
                }
            )
        else:
            if item["origin"] != B_ORIGIN or a_id is None or a_body is None:
                raise ValueError("only B may follow A")
            if dependencies != [a_id]:
                raise ValueError("B does not retain exactly one live A dependency")
            trace, call_count, direct_count = _symbolic_b(body, a_id, a_body)
            if (
                trace is None
                or sorted(trace) != [0, 1, 2]
                or call_count != 1
                or direct_count != 1
            ):
                raise ValueError("B symbolic semantics do not extend A with slot 2")
            definition_reports.append(
                {
                    "definition_id": str(item["definition_id"]),
                    "origin": B_ORIGIN,
                    "symbolic_trace": list(trace),
                    "dependency_count": 1,
                    "live_a_calls": call_count,
                    "direct_applications": direct_count,
                }
            )
        seen.add(str(item["definition_id"]))

    report: dict[str, Any] = {
        "schema": REPORT_SCHEMA,
        "scientific_verdict": False,
        "confirmed": True,
        "state_raw_sha256": hashlib.sha256(raw).hexdigest(),
        "state_digest": state["state_digest"],
        "m100_sha256": measured_m100,
        "m100_operations": m100_reports,
        "definition_count": len(definitions),
        "definitions": definition_reports,
        "independent_of_runtime_modules": True,
    }
    report["report_digest"] = digest(report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", required=True)
    parser.add_argument("--expected-m100-sha256")
    arguments = parser.parse_args()
    try:
        report = validate(
            Path(arguments.state).read_bytes(),
            expected_m100_sha256=arguments.expected_m100_sha256,
        )
    except Exception as error:
        report = {
            "schema": REPORT_SCHEMA,
            "scientific_verdict": False,
            "confirmed": False,
            "failed_closed": True,
            "error": f"{type(error).__name__}: {error}",
        }
        report["report_digest"] = digest(report)
        print(json.dumps(report, sort_keys=True))
        return 3
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
