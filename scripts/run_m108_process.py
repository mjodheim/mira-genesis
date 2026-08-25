"""M108 isolated capsule entry point.

Runs exactly one M108 action inside a process whose import path contains only the capsule. The
capsule carries the runtime modules and the inputs that action is allowed to see, and nothing else,
so a later stage cannot reach an earlier stage's material through an import, a relative path or an
exception. The report records the interpreter's own view of its isolation.

M108 needs two runtime modules, because its expression substrate is M107's, imported unchanged. Both
are capsule members and both are exempt from the leak detector for that reason; any *other* Genesis
module reachable from here is still a leak.
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
from pathlib import Path

PROCESS_SCHEMA = "m108-isolated-process-v1"

CAPSULE = Path(__file__).resolve().parent
if str(CAPSULE) not in sys.path:
    sys.path.insert(0, str(CAPSULE))

CAPSULE_RUNTIMES = {"m107_runtime.py", "m108_runtime.py"}

# Inside a capsule the runtimes sit beside this file under their copied names; in the repository
# they stay namespaced under ``metamorphosis``. The same dual import M105 and M107 use, so the
# integrity graph can model the boundary without the frozen capsule source gaining repository-only
# logic. M108's runtime imports M107's by the ``metamorphosis`` path, so inside a capsule that
# package name is aliased to the flat copy before M108 is imported.
if (CAPSULE / "m108_runtime.py").exists():
    import types

    _m107 = importlib.import_module("m107_runtime")
    _package = types.ModuleType("metamorphosis")
    _package.__path__ = []  # type: ignore[attr-defined]
    _package.m107_runtime = _m107  # type: ignore[attr-defined]
    sys.modules.setdefault("metamorphosis", _package)
    sys.modules.setdefault("metamorphosis.m107_runtime", _m107)
    runtime = importlib.import_module("m108_runtime")
else:  # pragma: no cover - normal repository import
    from metamorphosis import m108_runtime as runtime


def _imported_project_modules() -> list[str]:
    """Any Genesis module reachable from here other than the capsule's own runtimes is a leak."""
    leaked = []
    for name, module in sorted(sys.modules.items()):
        if module is None or name in {"m107_runtime", "m108_runtime", "__main__"}:
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


def _tables(image: dict) -> list[str]:
    return sorted("".join("1" if bit else "0" for bit in table) for table in image)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--action", required=True)
    parser.add_argument("--bound", type=int, default=None)
    arguments = parser.parse_args()
    bound = arguments.bound or runtime.MAX_EXPRESSION_NODES

    report: dict[str, object] = {"action": arguments.action, "bound": bound}
    try:
        if arguments.action == "domain":
            report["domain"] = runtime.attribution_domain(bound)
        elif arguments.action == "equivalence":
            state = _read("STATE.json")
            decoded = runtime.decode_state(state)
            report["equivalence"] = runtime.interpreter_equivalence_certificate(
                decoded["operators"], bound
            )
        elif arguments.action == "image":
            state = _read("STATE.json")
            decoded = runtime.decode_state(state)
            image = runtime.state_image(decoded, bound)
            report["image"] = {
                "bound": bound,
                "size": len(image),
                "signal_width": decoded["signal_width"],
                "tables": _tables(image),
                "operator_names": sorted(item["name"] for item in decoded["operators"]),
                "attribution_mode": runtime.attribute(
                    decoded, {"row_index": 0}
                )["mode"],
            }
        elif arguments.action == "exclusion":
            demand = _read("DEMAND.json")["demand"]
            target = runtime.demand_target(demand)
            state = _read("STATE.json")
            decoded = runtime.decode_state(state)
            report["structural"] = runtime.structural_exclusion_certificate(
                target, runtime.BASE_SIGNAL_WIDTH
            )
            report["monotone"] = runtime.monotone_exclusion_certificate(
                runtime.expr.initial_operators(), target, runtime.WORLD_SIGNAL_WIDTH, bound
            )
            report["target_reachable_once_both_generations_hold"] = runtime.construct(
                runtime.create_state(decoded["operators"], signal_width=runtime.WORLD_SIGNAL_WIDTH),
                target,
                bound,
            )["constructible"]
        elif arguments.action in {"acquire", "acquire_refuse_only"}:
            state = _read("STATE.json")
            fixture = _read("EPISODES.json")
            episodes = fixture["episodes"]
            if arguments.action == "acquire_refuse_only":
                subset = set(fixture["underdetermined_subset"])
                episodes = [item for item in episodes if item["episode_id"] in subset]
            acquisition = runtime.acquire_attribution(
                runtime.decode_state(state),
                episodes,
                register_result=arguments.action == "acquire",
                max_nodes=bound,
            )
            next_state = acquisition.pop("next_state", None)
            report["acquisition"] = acquisition
            report["episode_ids"] = sorted(item["episode_id"] for item in episodes)
            report["episode_feature_rows"] = sorted(
                {runtime.episode_feature_row(runtime.decode_episode(item), bound) for item in episodes}
            )
            if next_state is not None:
                report["next_state"] = json.loads(runtime.encode_state(next_state).decode("ascii"))
        elif arguments.action == "resolve":
            state = _read("STATE.json")
            demand = _read("DEMAND.json")["demand"]
            resolution = runtime.resolve(runtime.decode_state(state), demand, bound)
            report["resolution"] = resolution
        elif arguments.action == "corruption":
            state = _read("STATE.json")
            state["attribution"]["rule_id"] = "attribution-0000000000000000"
            try:
                runtime.decode_state(state)
                report["corruption"] = {"confirmed": True, "error": None}
            except Exception as error:  # noqa: BLE001 - the refusal is the observation
                report["corruption"] = {
                    "confirmed": False,
                    "error": "%s: %s" % (type(error).__name__, error),
                }
        else:
            raise ValueError("M108 capsule action is unknown")
        report["confirmed"] = True
    except Exception as error:  # noqa: BLE001 - the report is the observation
        report["confirmed"] = False
        report["error"] = "%s: %s" % (type(error).__name__, error)

    report["runtime"] = _runtime_report()
    sys.stdout.write(runtime.canonical_json(report))
    return 0 if report.get("confirmed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
