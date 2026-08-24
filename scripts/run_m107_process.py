"""M107 isolated capsule entry point.

Runs exactly one M107 action inside a process whose import path contains only the capsule. The
capsule carries the runtime module and the inputs that action is allowed to see, and nothing else,
so a later stage cannot reach an earlier stage's material through an import, a relative path or an
exception. The report records the interpreter's own view of its isolation.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

PROCESS_SCHEMA = "m107-isolated-process-v1"

CAPSULE = Path(__file__).resolve().parent
if str(CAPSULE) not in sys.path:
    sys.path.insert(0, str(CAPSULE))

import m107_runtime as runtime  # noqa: E402


def _imported_project_modules() -> list[str]:
    """Any Genesis module reachable from here other than the capsule's own runtime is a leak."""
    leaked = []
    for name, module in sorted(sys.modules.items()):
        if module is None or name in {"m107_runtime", "__main__"}:
            continue
        origin = getattr(getattr(module, "__spec__", None), "origin", None) or getattr(
            module, "__file__", None
        )
        # "built-in" and "frozen" are not paths. Resolving them would make them relative to the
        # working directory, which is the capsule, and mark the whole standard library as a leak.
        if not origin or origin in {"built-in", "frozen"} or not os.path.isabs(origin):
            continue
        resolved = Path(origin).resolve()
        if resolved.parent == CAPSULE and resolved.name != "m107_runtime.py":
            leaked.append(name)
    return leaked


def _runtime_report() -> dict[str, object]:
    return {
        "schema": PROCESS_SCHEMA,
        "pid": os.getpid(),
        "isolated_mode": True,
        "search_path": [str(Path(item).resolve()) for item in sys.path if item],
        "capsule_only_path": all(
            Path(item).resolve() == CAPSULE
            for item in sys.path
            if item and Path(item).exists() and Path(item).is_dir()
            and not str(Path(item).resolve()).lower().startswith(sys.base_prefix.lower())
        ),
        "imported_project_modules": _imported_project_modules(),
        "python_version": ".".join(str(part) for part in sys.version_info[:3]),
        "model_calls": 0,
        "network_calls": 0,
        "remote_execution_calls": 0,
    }


def _read(name: str):
    path = CAPSULE / name
    return json.loads(path.read_text(encoding="ascii"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--action", required=True)
    parser.add_argument("--bound", type=int, default=None)
    arguments = parser.parse_args()

    report: dict[str, object] = {"action": arguments.action}
    try:
        if arguments.action == "acquire":
            state = _read("STATE.json")
            demand = _read("DEMAND.json")
            report["acquisition"] = runtime.acquire_operator(
                state, demand, register_result=True
            )
        elif arguments.action == "acquire_refuse_only":
            state = _read("STATE.json")
            demand = _read("DEMAND.json")
            report["acquisition"] = runtime.acquire_operator(
                state, demand, register_result=False
            )
        elif arguments.action == "construct":
            state = _read("STATE.json")
            targets = _read("TARGETS.json")
            bound = arguments.bound or runtime.MAX_EXPRESSION_NODES
            constructions = []
            for target in targets["targets"]:
                built = runtime.construct(state, target)
                witness = built.get("expression")
                if witness is not None:
                    operators = runtime.operator_map(runtime.decode_state(state)["operators"])
                    built["executed_truth_table"] = [
                        bool(value) for value in runtime.truth_table(operators, witness)
                    ]
                    built["executes_to_target"] = built["executed_truth_table"] == list(target)
                constructions.append(built)
            report["constructions"] = constructions
            report["bound"] = bound
        elif arguments.action == "certificate":
            state = _read("STATE.json")
            targets = _read("TARGETS.json")
            decoded = runtime.decode_state(state)
            report["certificates"] = [
                runtime.insufficiency_certificate(decoded["operators"], tuple(target))
                for target in targets["targets"]
            ]
        elif arguments.action == "image":
            state = _read("STATE.json")
            decoded = runtime.decode_state(state)
            bound = arguments.bound or runtime.MAX_EXPRESSION_NODES
            image = runtime.complete_image(decoded["operators"], bound)
            report["image"] = {
                "bound": bound,
                "size": len(image),
                "tables": sorted(
                    "".join("1" if bit else "0" for bit in table) for table in image
                ),
                "operator_names": sorted(item["name"] for item in decoded["operators"]),
            }
        else:
            raise ValueError("M107 capsule action is unknown")
        report["confirmed"] = True
    except Exception as error:  # noqa: BLE001 - the report is the observation
        report["confirmed"] = False
        report["error"] = "%s: %s" % (type(error).__name__, error)

    report["runtime"] = _runtime_report()
    sys.stdout.write(runtime.canonical_json(report))
    return 0 if report.get("confirmed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
