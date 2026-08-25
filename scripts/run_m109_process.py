"""M109 isolated capsule entry point.

Runs exactly one M109 action inside a process whose import path contains only the capsule. The
capsule carries the runtime modules and the inputs that action is allowed to see, and nothing else,
so a later stage cannot reach an earlier stage's material through an import, a relative path or an
exception. The report records the interpreter's own view of its isolation.

M109 needs three runtime modules, because its substrate is M108's imported unchanged, which is
M107's imported unchanged in turn. All three are capsule members and all three are exempt from the
leak detector for that reason; any *other* Genesis module reachable from here is still a leak.
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
import types
from pathlib import Path

PROCESS_SCHEMA = "m109-isolated-process-v1"

CAPSULE = Path(__file__).resolve().parent
if str(CAPSULE) not in sys.path:
    sys.path.insert(0, str(CAPSULE))

CAPSULE_RUNTIMES = {"m107_runtime.py", "m108_runtime.py", "m109_runtime.py"}

# Inside a capsule the runtimes sit beside this file under their copied names; in the repository they
# stay namespaced under ``metamorphosis``. The same dual import M105, M107 and M108 use. M108 and
# M109 import their predecessors by the package path, so that package name is aliased to the flat
# copies before M109 is imported.
if (CAPSULE / "m109_runtime.py").exists():
    _m107 = importlib.import_module("m107_runtime")
    _package = types.ModuleType("metamorphosis")
    _package.__path__ = []  # type: ignore[attr-defined]
    _package.m107_runtime = _m107  # type: ignore[attr-defined]
    sys.modules.setdefault("metamorphosis", _package)
    sys.modules.setdefault("metamorphosis.m107_runtime", _m107)
    _m108 = importlib.import_module("m108_runtime")
    _package.m108_runtime = _m108  # type: ignore[attr-defined]
    sys.modules.setdefault("metamorphosis.m108_runtime", _m108)
    runtime = importlib.import_module("m109_runtime")
else:  # pragma: no cover - normal repository import
    from metamorphosis import m109_runtime as runtime


def _imported_project_modules() -> list[str]:
    """Any Genesis module reachable from here other than the capsule's own runtimes is a leak."""
    leaked = []
    for name, module in sorted(sys.modules.items()):
        if module is None or name in {
            "m107_runtime",
            "m108_runtime",
            "m109_runtime",
            "__main__",
        }:
            continue
        origin = getattr(getattr(module, "__spec__", None), "origin", None) or getattr(
            module, "__file__", None
        )
        # "built-in" and "frozen" are not paths. Resolving them would make them relative to the
        # working directory, which is the capsule, and mark the whole standard library as a leak.
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


def _staged_demand() -> dict:
    for name in ("DEMAND_STAGE1.json", "DEMAND_STAGE2.json"):
        if (CAPSULE / name).exists():
            return _read(name)["demand"]
    raise ValueError("M109 capsule holds no staged demand")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--action", required=True)
    parser.add_argument("--bound", type=int, default=None)
    parser.add_argument("--budget", type=int, default=2)
    arguments = parser.parse_args()
    bound = arguments.bound or runtime.MAX_EXPRESSION_NODES

    report: dict[str, object] = {"action": arguments.action, "bound": bound}
    try:
        if arguments.action == "domain":
            report["domain"] = runtime.attribution_domain(max_nodes=bound)
        elif arguments.action == "closure":
            state = runtime.decode_state(_read("STATE.json"))
            report["closure"] = runtime.candidate_space_closure_certificate(
                state["operators"], state["signal_width"], runtime.MONOTONE_SPACE, bound
            )
        elif arguments.action == "image":
            state = runtime.decode_state(_read("STATE.json"))
            image = runtime.state_image(state, bound)
            report["image"] = {
                "bound": bound,
                "size": len(image),
                "signal_width": state["signal_width"],
                "candidate_space": state["candidate_space"],
                "generations": len(state["rules"]),
                "operator_names": sorted(item["name"] for item in state["operators"]),
                "tables": sorted(
                    "".join("1" if bit else "0" for bit in table) for table in image
                ),
            }
        elif arguments.action == "episode":
            state = runtime.decode_state(_read("STATE.json"))
            report["episode"] = runtime.record_episode(state, _staged_demand(), bound)
        elif arguments.action == "acquire":
            state = runtime.decode_state(_read("STATE.json"))
            acquisition = runtime.acquire_rule(
                state,
                _read("EPISODES.json")["episodes"],
                _read("DOMAIN.json")["domain"],
                register_result=True,
                max_nodes=bound,
            )
            next_state = acquisition.pop("next_state", None)
            report["acquisition"] = acquisition
            if next_state is not None:
                report["next_state"] = json.loads(
                    runtime.encode_state(next_state).decode("ascii")
                )
        elif arguments.action == "acquire_refuse_only":
            state = runtime.decode_state(_read("STATE.json"))
            acquisition = runtime.acquire_rule(
                state,
                _read("EPISODES.json")["episodes"],
                _read("DOMAIN.json")["domain"],
                register_result=False,
                max_nodes=bound,
            )
            acquisition.pop("next_state", None)
            report["acquisition"] = acquisition
        elif arguments.action == "resolve":
            state = runtime.decode_state(_read("STATE.json"))
            report["resolution"] = runtime.resolve(state, _staged_demand(), bound)
        elif arguments.action == "reach_improve":
            state = runtime.decode_state(_read("STATE.json"))
            report["reach_improve"] = runtime.reach_improve(state, arguments.budget, bound)
        elif arguments.action == "corruption":
            state = _read("STATE.json")
            state["rules"][-1]["rule_id"] = "rule-0000000000000000"
            try:
                runtime.decode_state(state)
                report["corruption"] = {"confirmed": True, "error": None}
            except Exception as error:  # noqa: BLE001 - the refusal is the observation
                report["corruption"] = {
                    "confirmed": False,
                    "error": "%s: %s" % (type(error).__name__, error),
                }
        else:
            raise ValueError("M109 capsule action is unknown")
        report["confirmed"] = True
    except Exception as error:  # noqa: BLE001 - the report is the observation
        report["confirmed"] = False
        report["error"] = "%s: %s" % (type(error).__name__, error)

    report["runtime"] = _runtime_report()
    sys.stdout.write(runtime.canonical_json(report))
    return 0 if report.get("confirmed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
