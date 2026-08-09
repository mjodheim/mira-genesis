"""Frozen evaluator-owned task bank for M069 governed terminal episodes.

This file is committed before the repair policy.  The later learner may execute it through its
command-line boundary but may not import it or read its source.  Public and hidden cases remain in
the evaluator process, outside each materialized governed workspace.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from typing import Mapping, Sequence


RESPONSE_SCHEMA = "m069-terminal-task-response-v1"
TASK_SCHEMA = "m069-terminal-task-bank-v1"
MODULE_SOURCE = """def solve(x, y):
    # MIRA_REPAIR_SLOT
    return None
"""
INCOMPATIBLE_SOURCE = """def solve(record):
    return {"value": record.get("value")}
"""


TASKS: tuple[dict[str, object], ...] = (
    {
        "handle": "workcell-13a9d2",
        "goal_id": "repair-opaque-a",
        "instruction": "Repair solve so the registered evaluator accepts numeric-pair behavior.",
        "module": MODULE_SOURCE,
        "public": (((1, 2), 3), ((6, -3), 3), ((-4, 7), 3)),
        "hidden": (((100, 2), 102), ((-7, -8), -15), ((0, 0), 0)),
    },
    {
        "handle": "workcell-4c70be",
        "goal_id": "repair-opaque-b",
        "instruction": "Repair solve so the registered evaluator accepts text-normalization behavior.",
        "module": MODULE_SOURCE,
        "public": (((' Hello World ', None), "hello-world"), (("MIRA Genesis", 0), "mira-genesis"), (("already-clean", 1), "already-clean")),
        "hidden": (((' Two  Spaces ', None), "two--spaces"), (("CAPS", None), "caps"), ((" a b ", None), "a-b")),
    },
    {
        "handle": "workcell-806f41",
        "goal_id": "repair-opaque-c",
        "instruction": "Repair solve so the registered evaluator accepts sequence-summary behavior.",
        "module": MODULE_SOURCE,
        "public": ((((1, 4, 2), None), 3), (((-2, 3, 10), None), 12), ((((5, 5), None), 0))),
        "hidden": ((((100, -100, 0), None), 200), (((9, 1), None), 8), ((((7, 2, 4, 6), None), 5))),
    },
    {
        "handle": "workcell-b5287f",
        "goal_id": "repair-opaque-d",
        "instruction": "Repair solve so the registered evaluator accepts bounded-value behavior.",
        "module": MODULE_SOURCE,
        "public": (((5, (0, 10)), 5), ((-2, (0, 10)), 0), ((12, (0, 10)), 10)),
        "hidden": (((3, (3, 3)), 3), ((100, (-5, 5)), 5), ((-9, (-4, 2)), -4)),
    },
    {
        "handle": "workcell-fde304",
        "goal_id": "incompatible-artifact-protocol",
        "instruction": "Produce a signed result.json artifact under an undisclosed external schema.",
        "module": INCOMPATIBLE_SOURCE,
        "public": (),
        "hidden": (),
        "incompatible": True,
    },
)


def _canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _digest(domain: bytes, value: object) -> str:
    return hashlib.sha256(domain + _canonical_json(value)).hexdigest()


def _task_digest(task: Mapping[str, object]) -> str:
    return _digest(b"m069-private-task-v1\0", task)


def _bank_commitment() -> str:
    return _digest(b"m069-private-task-bank-v1\0", [_task_digest(task) for task in TASKS])


def _find(handle: str) -> Mapping[str, object]:
    task = next((task for task in TASKS if task["handle"] == handle), None)
    if task is None:
        raise ValueError("unknown M069 task handle")
    return task


def attest() -> dict[str, object]:
    return {
        "task_schema": TASK_SCHEMA,
        "task_count": len(TASKS),
        "compatible_task_count": sum(not task.get("incompatible", False) for task in TASKS),
        "incompatible_task_count": sum(bool(task.get("incompatible", False)) for task in TASKS),
        "task_handles": [task["handle"] for task in TASKS],
        "task_digests": [_task_digest(task) for task in TASKS],
        "task_bank_commitment": _bank_commitment(),
        "hidden_cases_disclosed": False,
        "solutions_disclosed": False,
        "external_task_authorship_claimed": False,
    }


def materialize(handle: str) -> dict[str, object]:
    task = _find(handle)
    return {
        "task_handle": handle,
        "goal_id": task["goal_id"],
        "instruction": task["instruction"],
        "files": {"solution.py": task["module"]},
    }


def _load_solution(root: Path):
    path = (root / "solution.py").resolve(strict=True)
    if not path.is_relative_to(root.resolve(strict=True)) or not path.is_file():
        raise ValueError("M069 solution module escaped the evaluation workspace")
    spec = importlib.util.spec_from_file_location("m069_candidate_solution", path)
    if spec is None or spec.loader is None:
        raise ValueError("M069 candidate solution could not be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    solve = getattr(module, "solve", None)
    if not callable(solve):
        raise ValueError("M069 candidate solution has no callable solve")
    return solve


def evaluate(handle: str, domain: str, root: Path) -> tuple[dict[str, object], bool]:
    if domain not in {"public", "hidden"}:
        raise ValueError("M069 evaluator domain must be public or hidden")
    task = _find(handle)
    if task.get("incompatible", False):
        return {"task_handle": handle, "domain": domain, "status": "incompatible"}, False
    solve = _load_solution(root)
    cases = task[domain]
    if not isinstance(cases, Sequence) or not cases:
        raise ValueError("M069 evaluator case domain is empty")
    results: list[dict[str, object]] = []
    for index, case in enumerate(cases):
        arguments, expected = case
        try:
            actual = solve(*arguments)
            passed = actual == expected and type(actual) is type(expected)
            error = None
        except Exception as exc:  # noqa: BLE001 - candidate failure is an evaluator result
            actual = None
            passed = False
            error = type(exc).__name__
        results.append({
            "case": index,
            "passed": passed,
            "actual_type": type(actual).__name__ if error is None else None,
            "error_type": error,
        })
    all_passed = all(record["passed"] for record in results)
    return {
        "task_handle": handle,
        "domain": domain,
        "status": "passed" if all_passed else "failed",
        "passed": sum(bool(record["passed"]) for record in results),
        "total": len(results),
        "results": results if domain == "public" else None,
    }, all_passed


def _emit(mode: str, result: object, *, success: bool = True) -> int:
    print(json.dumps({"schema": RESPONSE_SCHEMA, "mode": mode, "result": result}, sort_keys=True))
    return 0 if success else 1


def main(argv: Sequence[str] | None = None) -> int:
    arguments = tuple(sys.argv[1:] if argv is None else argv)
    mode = arguments[0] if arguments else ""
    try:
        if mode == "attest" and len(arguments) == 1:
            return _emit(mode, attest())
        if mode == "materialize" and len(arguments) == 2:
            return _emit(mode, materialize(arguments[1]))
        if mode in {"public", "hidden"} and len(arguments) == 2:
            result, success = evaluate(arguments[1], mode, Path.cwd())
            return _emit(mode, result, success=success)
        raise ValueError("invalid M069 evaluator invocation")
    except Exception as exc:  # noqa: BLE001 - CLI boundary must return structured failure
        print(json.dumps({
            "schema": RESPONSE_SCHEMA,
            "mode": mode,
            "fatal_error": f"{type(exc).__name__}: {exc}",
        }, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
