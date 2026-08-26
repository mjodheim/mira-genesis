"""Prove, mechanically, that M113's information boundaries are boundaries and not conventions.

Four claims in this milestone are load-bearing and are all of the form "X cannot see Y". A claim of
that shape is worth exactly as much as the check that enforces it, so each one is checked here and
each failure is decisive.

1. **The learner cannot read the carrier.** `m113_runtime` receives a `carrier_host.Channel` and
   never a carrier. The carrier lives in a closure inside the channel, so there is no attribute to
   reach for -- but a future edit could add one, or could import the host's own accessors and use
   them on a payload. So the module's source is parsed and refused if it names any carrier-internal
   key or calls any host function that reads carrier structure.

2. **The evaluator is outside the mutable body.** `m113_evaluator` must not import `m113_runtime`,
   directly or transitively, or the thing being scored would be scoring itself.

3. **The learner cannot read the evaluator.** `m113_runtime` must not import `m113_evaluator`: the
   ground-truth component, the qualification rule and the reachable set all live there.

4. **The host holds no carrier semantics.** `carrier_host` must not name a cell, an action, an error
   or a token from any particular carrier. It is checked against the devkit's own vocabulary, which
   is the only vocabulary that exists before a bank does.
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

RUNTIME = ROOT / "metamorphosis" / "m113_runtime.py"
EVALUATOR = ROOT / "metamorphosis" / "m113_evaluator.py"
HOST = ROOT / "metamorphosis" / "carrier_host.py"
BANK = ROOT / "metamorphosis" / "m113_carrier_bank.py"

# Keys that exist only inside a carrier. A learner naming one is reading something it was not given.
CARRIER_INTERNAL_KEYS = (
    "cells",
    "initial",
    "visible",
    "guard",
    "effect",
    "errors",
    "operand",
    "carrier_digest",
)

# Host functions that read carrier structure rather than drive a session. The learner may call none.
FORBIDDEN_HOST_CALLS = (
    "validate_carrier",
    "observation",
    "observed_cells",
    "guard_holds",
    "apply_effect",
    "find_action",
    "step",
    "initial_state",
    "action_alphabet",
    "reachable_states",
    "observation_closure",
    "witness_sequence",
    "carrier_facts",
    "structural_signature",
    "open_session",
    "meta_channel",
)


def _module(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _imported_modules(tree: ast.Module) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
            found.update("%s.%s" % (node.module, alias.name) for alias in node.names)
    return found


def _string_constants(tree: ast.Module, *, skip_docstrings: bool = True) -> list[str]:
    docstrings: set[int] = set()
    if skip_docstrings:
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                body = getattr(node, "body", None)
                if (
                    body
                    and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)
                    and isinstance(body[0].value.value, str)
                ):
                    docstrings.add(id(body[0].value))
    return [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and id(node) not in docstrings
    ]


def _host_calls(tree: ast.Module, alias: str) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == alias
        ):
            found.add(node.attr)
    return found


def _rename(carrier: dict[str, Any], mapping: dict[str, str]) -> dict[str, Any]:
    from metamorphosis import carrier_host as host  # noqa: PLC0415

    surface = dict(carrier["surface"])
    for key in ("ok_token", "error_token", "action_key", "argument_key", "status_key"):
        surface[key] = mapping[surface[key]]
    return host.validate_carrier(
        {
            "surface": surface,
            "cells": [
                {"name": mapping[item["name"]], "size": item["size"]} for item in carrier["cells"]
            ],
            "initial": list(carrier["initial"]),
            "visible": list(carrier["visible"]),
            "errors": [mapping[item] for item in carrier["errors"]],
            "actions": [
                {
                    "name": mapping[item["name"]],
                    "arity": item["arity"],
                    "arg_size": item["arg_size"],
                    "guard": item["guard"],
                    "effect": item["effect"],
                    "error": mapping[item["error"]],
                }
                for item in carrier["actions"]
            ],
        }
    )


def _translate(carrier: dict[str, Any], response: str, mapping: dict[str, str]) -> str:
    """Rewrite a response into a name-free canonical form, so the comparison is structural.

    A textual substitution cannot do this: on the JSON surface the keys are emitted in canonical
    order, and renaming reorders them, so two responses that say exactly the same thing differ as
    strings. Comparing decoded content is the only comparison that means what the check means.
    """
    surface = carrier["surface"]
    kind = surface["kind"]

    def swap(value: Any) -> Any:
        return mapping.get(value, value) if isinstance(value, str) else value

    if kind in ("json_object", "json_array"):
        parsed = json.loads(response)
        if isinstance(parsed, dict):
            rebuilt: Any = {swap(key): swap(value) for key, value in parsed.items()}
        else:
            rebuilt = [swap(item) for item in parsed]
        return json.dumps(rebuilt, sort_keys=True, separators=(",", ":"))
    if kind == "text_line":
        pieces = []
        for item in response.split(surface["field_separator"]):
            parts = item.split(surface["pair_separator"])
            pieces.append(surface["pair_separator"].join(swap(part) for part in parts))
        return json.dumps(sorted(pieces))
    # The packed surface carries no delimiter, so the leading status token has to be lifted off by
    # the only thing that knows how long it is: the carrier's own declaration.
    for token in (surface["ok_token"], surface["error_token"]):
        if response.startswith(token):
            return json.dumps([swap(token), response[len(token) :]])
    return json.dumps([None, response])


def renaming_equivariance(sample: int = 60) -> dict[str, Any]:
    """The property "the host holds no carrier semantics" is equivariance, and it is checkable.

    A scan for suspicious strings cannot decide this: any word a carrier might use is a word some
    report key might also use, and the collisions are noise. What the claim actually means is that
    renaming every cell, action, error and surface token consistently changes nothing the host
    computes except the names -- so the whole state graph, the reachable and unreachable observation
    sets, the structural signature and every response are compared across a bijection.

    A host with a preference for some particular carrier would fail this. Nothing else does.
    """
    from metamorphosis import carrier_host as host  # noqa: PLC0415
    from metamorphosis import m113_carrier_devkit as devkit  # noqa: PLC0415

    failures: list[dict[str, Any]] = []
    compared = 0
    for index in range(int(sample)):
        carrier = devkit.development_carrier("m113-equivariance:%d" % index)
        names = sorted(
            {item["name"] for item in carrier["cells"]}
            | {item["name"] for item in carrier["actions"]}
            | set(carrier["errors"])
            | {
                carrier["surface"][key]
                for key in ("ok_token", "error_token", "action_key", "argument_key", "status_key")
            }
        )
        mapping = {name: "z%03d" % position for position, name in enumerate(names)}
        try:
            renamed = _rename(carrier, mapping)
        except host.CarrierError as exc:
            failures.append({"index": index, "reason": "renaming rejected: %s" % exc})
            continue
        compared += 1

        left = host.observation_closure(carrier)
        right = host.observation_closure(renamed)
        problems: list[str] = []
        if host.structural_signature(carrier) != host.structural_signature(renamed):
            problems.append("structural signature is not name-free")
        if left["reachable_observations"] != right["reachable_observations"]:
            problems.append("reachable observations differ under renaming")
        if left["unreachable_observations"] != right["unreachable_observations"]:
            problems.append("unreachable observations differ under renaming")
        if (left["state_count"], left["max_depth"], left["iterations"]) != (
            right["state_count"],
            right["max_depth"],
            right["iterations"],
        ):
            problems.append("the state graph differs under renaming")

        alphabet = host.action_alphabet(carrier)
        left_session = host.open_session(carrier, "opaque-left", 4 * len(alphabet) + 4)
        right_session = host.open_session(renamed, "opaque-right", 4 * len(alphabet) + 4)
        for name, argument in alphabet:
            answer = left_session.send(host.encode_request(carrier, name, argument))
            mirrored = right_session.send(host.encode_request(renamed, mapping[name], argument))
            if _translate(carrier, answer, mapping) != _translate(renamed, mirrored, {}):
                problems.append("a response differs under renaming")
                break
        if problems:
            failures.append({"index": index, "problems": sorted(set(problems))})

    return {
        "carriers_compared": compared,
        "equivariant": not failures and compared > 0,
        "failures": failures[:5],
        "failure_count": len(failures),
    }


def audit() -> dict[str, Any]:
    runtime_tree = _module(RUNTIME)
    evaluator_tree = _module(EVALUATOR)
    host_tree = _module(HOST)

    runtime_strings = _string_constants(runtime_tree)
    named_internals = sorted(
        {key for key in CARRIER_INTERNAL_KEYS if key in runtime_strings}
    )
    runtime_host_calls = _host_calls(runtime_tree, "host")
    forbidden_calls = sorted(runtime_host_calls & set(FORBIDDEN_HOST_CALLS))

    evaluator_imports = _imported_modules(evaluator_tree)
    runtime_imports = _imported_modules(runtime_tree)

    equivariance = renaming_equivariance()

    checks = {
        "learner_names_no_carrier_internal_key": not named_internals,
        "learner_calls_no_host_structure_reader": not forbidden_calls,
        "evaluator_does_not_import_the_learner": not any(
            name.endswith("m113_runtime") for name in evaluator_imports
        ),
        "learner_does_not_import_the_evaluator": not any(
            name.endswith("m113_evaluator") for name in runtime_imports
        ),
        "host_is_equivariant_under_carrier_renaming": bool(equivariance["equivariant"]),
        "learner_imports_the_producer_unchanged": any(
            name.endswith("m109_runtime") for name in runtime_imports
        ),
        "learner_imports_the_diagnostic_predecessor_unchanged": any(
            name.endswith("m111_runtime") for name in runtime_imports
        ),
    }
    return {
        "schema": "m113-boundary-audit-v1",
        "milestone": "M113",
        "checks": checks,
        "passed": all(checks.values()),
        "failing_checks": sorted(name for name, ok in checks.items() if not ok),
        "detail": {
            "carrier_internal_keys_named_by_the_learner": named_internals,
            "host_structure_readers_called_by_the_learner": forbidden_calls,
            "renaming_equivariance": equivariance,
            "learner_host_attributes_used": sorted(runtime_host_calls),
        },
        "audited_files": [
            str(path.relative_to(ROOT)).replace("\\", "/")
            for path in (RUNTIME, EVALUATOR, HOST, BANK)
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="print the report as JSON")
    arguments = parser.parse_args()
    report = audit()
    if arguments.json:
        print(json.dumps(report, sort_keys=True, indent=2))
    else:
        for name, ok in sorted(report["checks"].items()):
            print("%s %s" % ("PASS" if ok else "FAIL", name))
        if not report["passed"]:
            print()
            print(json.dumps(report["detail"], sort_keys=True, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
