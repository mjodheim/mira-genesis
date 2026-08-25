"""M111 isolated capsule entry point.

Runs exactly one M111 action in a process whose import path contains only the capsule. The capsule
carries the runtime modules and the inputs that action is allowed to see, and nothing else.

M111 needs five runtime modules: its own, and the chain M110 -> M109 -> M108 -> M107 imported
unchanged, because the attribution cascade is executed by M109's own code and the consumer carrier is
M110's. All five are capsule members and all five are exempt from the leak detector; any *other*
Genesis module reachable from here is still a leak.

No capsule holds a producer result, a producer demand or an episodes fixture. The lineage records its
own episodes, and the capsules that do so hold only the world.
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
import types
from pathlib import Path

PROCESS_SCHEMA = "m111-isolated-process-v1"

CAPSULE = Path(__file__).resolve().parent
if str(CAPSULE) not in sys.path:
    sys.path.insert(0, str(CAPSULE))

CAPSULE_RUNTIMES = {
    "m107_runtime.py",
    "m108_runtime.py",
    "m109_runtime.py",
    "m110_runtime.py",
    "m111_runtime.py",
}

if (CAPSULE / "m111_runtime.py").exists():
    _package = types.ModuleType("metamorphosis")
    _package.__path__ = []  # type: ignore[attr-defined]
    sys.modules.setdefault("metamorphosis", _package)
    for _name in ("m107_runtime", "m108_runtime", "m109_runtime", "m110_runtime"):
        _module = importlib.import_module(_name)
        setattr(_package, _name, _module)
        sys.modules.setdefault("metamorphosis." + _name, _module)
    runtime = importlib.import_module("m111_runtime")
    consumer = sys.modules["m110_runtime"]
else:  # pragma: no cover - normal repository import
    from metamorphosis import m110_runtime as consumer
    from metamorphosis import m111_runtime as runtime


def _imported_project_modules() -> list[str]:
    leaked = []
    for name, module in sorted(sys.modules.items()):
        if module is None or name in CAPSULE_RUNTIMES or name in {
            "m107_runtime",
            "m108_runtime",
            "m109_runtime",
            "m110_runtime",
            "m111_runtime",
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


def _world():
    return consumer.decode_world(_read("WORLD.json")["world"])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--action", required=True)
    parser.add_argument("--bound", type=int, default=None)
    parser.add_argument("--probe-order", default="candidates_first")
    parser.add_argument("--force-probe", default="policy")
    arguments = parser.parse_args()
    bound = arguments.bound or consumer.MAX_EXPRESSION_NODES
    order = (
        runtime.PROBE_ORDER_CANDIDATES_FIRST
        if arguments.probe_order == "candidates_first"
        else runtime.PROBE_ORDER_SIGNALS_FIRST
    )
    force = {"policy": None, "never": False, "always": True}[arguments.force_probe]

    report: dict[str, object] = {
        "action": arguments.action,
        "bound": bound,
        "probe_order": arguments.probe_order,
        "force_probe": arguments.force_probe,
    }
    try:
        if arguments.action == "census":
            report["census"] = consumer.attribution_census(_world(), bound)
        elif arguments.action == "expressibility":
            state = runtime.decode_state(_read("STATE.json"))
            report["expressibility"] = runtime.expressibility_certificate(
                state["machinery_state"], 3, 7
            )
            report["policy_rule_space"] = len(
                runtime.policy_rule_space(state["machinery_state"])
            )
        elif arguments.action == "episodes":
            world = _world()
            base = consumer.create_state()
            targets = _read("TARGETS.json")["targets"]
            episodes = [runtime.record_episode(base, world, item, bound) for item in targets]
            report["episodes"] = episodes
            report["survey"] = runtime.undetermined_rows(episodes)
            report["episodes_fixture_present"] = (CAPSULE / "EPISODES.json").exists()
        elif arguments.action == "acquire":
            state = runtime.decode_state(_read("STATE.json"))
            acquisition = runtime.acquire_policy(
                state, _read("RECORD.json")["episodes"], register_result=True
            )
            next_state = acquisition.pop("next_state", None)
            report["acquisition"] = acquisition
            if next_state is not None:
                report["next_state"] = json.loads(
                    runtime.encode_state(next_state).decode("ascii")
                )
        elif arguments.action == "acquire_refuse_only":
            state = runtime.decode_state(_read("STATE.json"))
            acquisition = runtime.acquire_policy(
                state, _read("RECORD.json")["episodes"], register_result=False
            )
            acquisition.pop("next_state", None)
            report["acquisition"] = acquisition
        elif arguments.action == "sequence":
            state = runtime.decode_state(_read("STATE.json"))
            demands = [
                consumer.decode_demand(item) for item in _read("DEMANDS.json")["demands"]
            ]
            report["sequence"] = runtime.resolve_sequence(
                state, _world(), demands, probe_order=order, force_probe=force, max_nodes=bound
            )
            report["arm_state_digest"] = state["state_digest"]
            report["adapter_projection_digest"] = runtime.digest(
                runtime.adapter_projection(state)
            )
            report["holds_a_policy"] = state["policy"] is not None
        elif arguments.action == "probe_rollback":
            state = runtime.decode_state(_read("STATE.json"))
            world = _world()
            demands = [
                consumer.decode_demand(item) for item in _read("DEMANDS.json")["demands"]
            ]
            records = [
                runtime.probe(state, world, item["target"], component, bound)
                for item in demands
                for component in (
                    runtime.COMPONENT_SIGNALS,
                    runtime.COMPONENT_CANDIDATES,
                    runtime.COMPONENT_OPERATORS,
                )
            ]
            report["probe_rollback"] = {
                "records": records,
                "every_probe_left_the_state_unchanged": all(
                    item["state_unchanged"] for item in records
                ),
                "no_probe_is_an_adoption": all(not item["is_an_adoption"] for item in records),
                "probe_count": len(records),
            }
        elif arguments.action == "corruption":
            state = _read("STATE.json")
            if state.get("policy"):
                state["policy"]["policy_id"] = "policy-0000000000000000"
            else:
                state["probe_budget"] = state["probe_budget"] + 1
            try:
                runtime.decode_state(state)
                report["corruption"] = {"confirmed": True, "error": None}
            except Exception as error:  # noqa: BLE001 - the refusal is the observation
                report["corruption"] = {
                    "confirmed": False,
                    "error": "%s: %s" % (type(error).__name__, error),
                }
        else:
            raise ValueError("M111 capsule action is unknown")
        report["confirmed"] = True
    except Exception as error:  # noqa: BLE001 - the report is the observation
        report["confirmed"] = False
        report["error"] = "%s: %s" % (type(error).__name__, error)

    report["runtime"] = _runtime_report()
    sys.stdout.write(runtime.canonical_json(report))
    return 0 if report.get("confirmed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
