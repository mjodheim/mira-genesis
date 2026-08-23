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
            if trace != (0, 1):
                raise ValueError("A symbolic semantics are not slot 0 followed by slot 1")
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
            if trace != (0, 1, 2) or call_count != 1 or direct_count != 1:
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
