"""M110 isolated capsule entry point.

Runs exactly one M110 action in a process whose import path contains only the capsule. The capsule
carries the runtime modules and the inputs that action is allowed to see, and nothing else.

M110 needs four runtime modules: its own, and the producer chain M109 -> M108 -> M107 imported
unchanged, because the attribution cascade is executed by the producer's own code. All four are
capsule members and all four are exempt from the leak detector; any *other* Genesis module reachable
from here is still a leak.

A capsule never holds the producer's result, the producer's demands or the producer's world. The arm
capsules differ from one another in `STATE.json` and in nothing else, and their membership lists are
recorded so that can be measured rather than asserted.
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
import types
from pathlib import Path

PROCESS_SCHEMA = "m110-isolated-process-v1"

CAPSULE = Path(__file__).resolve().parent
if str(CAPSULE) not in sys.path:
    sys.path.insert(0, str(CAPSULE))

CAPSULE_RUNTIMES = {
    "m107_runtime.py",
    "m108_runtime.py",
    "m109_runtime.py",
    "m110_runtime.py",
}

if (CAPSULE / "m110_runtime.py").exists():
    _m107 = importlib.import_module("m107_runtime")
    _package = types.ModuleType("metamorphosis")
    _package.__path__ = []  # type: ignore[attr-defined]
    _package.m107_runtime = _m107  # type: ignore[attr-defined]
    sys.modules.setdefault("metamorphosis", _package)
    sys.modules.setdefault("metamorphosis.m107_runtime", _m107)
    _m108 = importlib.import_module("m108_runtime")
    _package.m108_runtime = _m108  # type: ignore[attr-defined]
    sys.modules.setdefault("metamorphosis.m108_runtime", _m108)
    _m109 = importlib.import_module("m109_runtime")
    _package.m109_runtime = _m109  # type: ignore[attr-defined]
    sys.modules.setdefault("metamorphosis.m109_runtime", _m109)
    runtime = importlib.import_module("m110_runtime")
else:  # pragma: no cover - normal repository import
    from metamorphosis import m110_runtime as runtime


def _imported_project_modules() -> list[str]:
    leaked = []
    for name, module in sorted(sys.modules.items()):
        if module is None or name in {
            "m107_runtime",
            "m108_runtime",
            "m109_runtime",
            "m110_runtime",
            "__main__",
        }:
            continue
        origin = getattr(getattr(module, "__spec__", None), "origin", None) or getattr(
            module, "__file__", None
        )
        if not origin or origin in {"built-in", "frozen"} or not os.path.isabs(origin):
            continue
        resolved = Path(origin).resolve()
        if resolved.parent == CAPSULE and resolved.name not in CAPSULE_RUNTIMES:
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
            if item
            and Path(item).exists()
            and Path(item).is_dir()
            and not str(Path(item).resolve()).lower().startswith(sys.base_prefix.lower())
        ),
        "imported_project_modules": _imported_project_modules(),
        "python_version": ".".join(str(part) for part in sys.version_info[:3]),
        "model_calls": 0,
        "network_calls": 0,
        "remote_execution_calls": 0,
    }


def _read(name: str):
    return json.loads((CAPSULE / name).read_text(encoding="ascii"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--action", required=True)
    parser.add_argument("--bound", type=int, default=None)
    parser.add_argument("--budget", type=int, default=2)
    arguments = parser.parse_args()
    bound = arguments.bound or runtime.MAX_EXPRESSION_NODES

    report: dict[str, object] = {"action": arguments.action, "bound": bound}
    try:
        if arguments.action == "census":
            world = runtime.decode_world(_read("WORLD.json")["world"])
            report["census"] = runtime.attribution_census(world, bound)
        elif arguments.action == "certificates":
            world = runtime.decode_world(_read("WORLD.json")["world"])
            state = runtime.decode_state(_read("STATE.json"))
            report["certificates"] = {
                "monotone_closure": runtime.monotone_closure_certificate(state, world, bound),
                "visible_function": runtime.visible_function_certificate(world, bound),
                "fixed_point": runtime.fixed_point_certificate(world),
            }
        elif arguments.action == "image":
            world = runtime.decode_world(_read("WORLD.json")["world"])
            state = runtime.decode_state(_read("STATE.json"))
            image = runtime.state_image(state, world, bound)
            report["image"] = {
                "bound": bound,
                "size": len(image),
                "interface_width": state["interface_width"],
                "candidate_space": state["candidate_space"],
                "generations": len(state["rules"]),
                "world_digest": world["world_digest"],
            }
        elif arguments.action == "resolve":
            world = runtime.decode_world(_read("WORLD.json")["world"])
            state = runtime.decode_state(_read("STATE.json"))
            demand = _read("DEMAND.json")["demand"]
            resolution = runtime.resolve(state, world, demand, bound)
            report["resolution"] = resolution
            report["arm_state_digest"] = state["state_digest"]
            report["generations"] = len(state["rules"])
            report["adapter_projection_digest"] = runtime.digest(
                runtime.adapter_projection(state)
            )
        elif arguments.action == "trial":
            world = runtime.decode_world(_read("WORLD.json")["world"])
            state = runtime.decode_state(_read("STATE.json"))
            demand = runtime.decode_demand(_read("DEMAND.json")["demand"])
            report["trial"] = runtime.component_trial(state, world, demand["target"], bound)
            report["features"] = runtime.failure_features(state, world, demand["target"], bound)
        elif arguments.action == "reach_improve":
            world = runtime.decode_world(_read("WORLD.json")["world"])
            state = runtime.decode_state(_read("STATE.json"))
            reach = runtime.reach_improve(state, world, arguments.budget, bound)
            report["reach_improve"] = reach
        elif arguments.action == "corruption":
            state = _read("STATE.json")
            if state.get("rules"):
                state["rules"][-1]["rule_id"] = "rule-0000000000000000"
            else:
                state["operators"][-1]["operator_id"] = "consumer-operator-0000000000000000"
            try:
                runtime.decode_state(state)
                report["corruption"] = {"confirmed": True, "error": None}
            except Exception as error:  # noqa: BLE001 - the refusal is the observation
                report["corruption"] = {
                    "confirmed": False,
                    "error": "%s: %s" % (type(error).__name__, error),
                }
        else:
            raise ValueError("M110 capsule action is unknown")
        report["confirmed"] = True
    except Exception as error:  # noqa: BLE001 - the report is the observation
        report["confirmed"] = False
        report["error"] = "%s: %s" % (type(error).__name__, error)

    report["runtime"] = _runtime_report()
    sys.stdout.write(runtime.canonical_json(report))
    return 0 if report.get("confirmed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
