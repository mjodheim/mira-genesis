"""Author the fresh, complete M104 qualification-only population."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from metamorphosis import m103_runtime as runtime  # noqa: E402


OUTPUT = ROOT / "experiments" / "M104" / "QUALIFICATION_POOL.json"
DEVELOPMENT = ROOT / "experiments" / "M103" / "DEVELOPMENT_FIXTURE.json"
M103_POOL = ROOT / "experiments" / "M103" / "QUALIFICATION_POOL.json"
RESULT = ROOT / "experiments" / "M104" / "RESULT.json"
VALIDATED_S_PRIME_FEATURES = {
    "OBSERVE_CONTEXT",
    "PARTITION_EQUAL",
    "SYNTHESIZE_PARTITIONS",
    "EMIT_GUARDED",
}


def _action(descriptor: dict[str, Any]) -> dict[str, Any]:
    return runtime.action_definition(descriptor)


def _configuration_family() -> dict[str, Any]:
    lock = _action(
        {"kind": "set_option", "section": "pipeline", "option": "profile", "value": "locked"}
    )
    remove_diagnostics = _action(
        {"kind": "remove_option", "section": "pipeline", "option": "diagnostics"}
    )
    actions = [lock, remove_diagnostics]
    initial = "[pipeline]\nprofile=standard\ndiagnostics=enabled\n"
    acquisition = runtime.acquisition_demand(
        "m104-qualification-configuration-acquisition",
        "configuration",
        actions,
        [
            {
                "case_id": "m104-configuration-public-channel-13",
                "context": ["channel-13"],
                "initial": initial,
                "expected": {"pipeline": {"profile": "locked", "diagnostics": "enabled"}},
            },
            {
                "case_id": "m104-configuration-public-channel-6",
                "context": ["channel-6"],
                "initial": initial,
                "expected": {"pipeline": {"profile": "standard"}},
            },
        ],
        [
            {
                "probe_id": "m104-configuration-diagnostic-channel-13",
                "context": ["channel-13"],
                "initial": "[pipeline]\nprofile=probe104\ndiagnostics=trace104\n",
            },
            {
                "probe_id": "m104-configuration-diagnostic-channel-6",
                "context": ["channel-6"],
                "initial": "[pipeline]\nprofile=probe104\ndiagnostics=trace104\n",
            },
        ],
        max_trace=1,
    )
    hidden_initials = (
        "[pipeline]\nprofile=cobalt\ndiagnostics=loud104\nzone=northwest104\n",
        "[pipeline]\nprofile=ivory\ndiagnostics=soft104\nzone=southeast104\n",
        "[pipeline]\nprofile=umber\ndiagnostics=scan104\nzone=central104\n",
        "[pipeline]\nprofile=jade\ndiagnostics=deep104\nzone=coastal104\n",
    )
    hidden_worlds: list[dict[str, Any]] = []
    for index, source in enumerate(hidden_initials):
        before = runtime.execute_trace("configuration", actions, [], source)
        locked = runtime.execute_trace("configuration", actions, [lock["action_id"]], source)
        lean = runtime.execute_trace(
            "configuration", actions, [remove_diagnostics["action_id"]], source
        )
        if len({runtime.digest(before), runtime.digest(locked), runtime.digest(lean)}) != 3:
            raise RuntimeError("M104 configuration world is not context-decisive")
        hidden_worlds.append(
            {
                "world_id": f"m104-configuration-hidden-{index}",
                "family": "configuration",
                "cases": [
                    {
                        "case_id": f"m104-configuration-hidden-{index}-channel-13",
                        "context": ["channel-13"],
                        "initial": source,
                        "expected": locked,
                    },
                    {
                        "case_id": f"m104-configuration-hidden-{index}-channel-6",
                        "context": ["channel-6"],
                        "initial": source,
                        "expected": lean,
                    },
                ],
            }
        )
    return {"acquisition": acquisition, "hidden_worlds": hidden_worlds}


def _filesystem_family() -> dict[str, Any]:
    rename = _action({"kind": "rename_path", "old": "input.dat", "new": "published.dat"})
    sign = _action({"kind": "write_text", "path": "proof.sig", "content": "verified104"})
    actions = [rename, sign]
    initial = {"input.dat": "payload104", "retain.cfg": "stable104"}
    acquisition = runtime.acquisition_demand(
        "m104-qualification-filesystem-acquisition",
        "filesystem",
        actions,
        [
            {
                "case_id": "m104-filesystem-public-channel-15",
                "context": ["channel-15"],
                "initial": initial,
                "expected": {"published.dat": "payload104", "retain.cfg": "stable104"},
            },
            {
                "case_id": "m104-filesystem-public-channel-8",
                "context": ["channel-8"],
                "initial": initial,
                "expected": {
                    "input.dat": "payload104",
                    "proof.sig": "verified104",
                    "retain.cfg": "stable104",
                },
            },
        ],
        [
            {
                "probe_id": "m104-filesystem-diagnostic-channel-15",
                "context": ["channel-15"],
                "initial": {"input.dat": "probe104", "aux.bin": "left104"},
            },
            {
                "probe_id": "m104-filesystem-diagnostic-channel-8",
                "context": ["channel-8"],
                "initial": {"input.dat": "probe104", "aux.bin": "left104"},
            },
        ],
        max_trace=1,
    )
    hidden_initials = (
        {"input.dat": "epsilon104", "retain.cfg": "r104a"},
        {"input.dat": "zeta104", "memo.log": "m104b"},
        {"input.dat": "eta104", "tree/node.bin": "t104c"},
        {"input.dat": "theta104", "retain.cfg": "r104d", "memo.log": "m104d"},
    )
    hidden_worlds: list[dict[str, Any]] = []
    for index, source in enumerate(hidden_initials):
        before = runtime.execute_trace("filesystem", actions, [], source)
        renamed = runtime.execute_trace("filesystem", actions, [rename["action_id"]], source)
        signed = runtime.execute_trace("filesystem", actions, [sign["action_id"]], source)
        if len({runtime.digest(before), runtime.digest(renamed), runtime.digest(signed)}) != 3:
            raise RuntimeError("M104 filesystem world is not context-decisive")
        hidden_worlds.append(
            {
                "world_id": f"m104-filesystem-hidden-{index}",
                "family": "filesystem",
                "cases": [
                    {
                        "case_id": f"m104-filesystem-hidden-{index}-channel-15",
                        "context": ["channel-15"],
                        "initial": source,
                        "expected": renamed,
                    },
                    {
                        "case_id": f"m104-filesystem-hidden-{index}-channel-8",
                        "context": ["channel-8"],
                        "initial": source,
                        "expected": signed,
                    },
                ],
            }
        )
    return {"acquisition": acquisition, "hidden_worlds": hidden_worlds}


def _ambiguous_control() -> dict[str, Any]:
    keep_default = _action(
        {"kind": "set_option", "section": "pipeline", "option": "policy", "value": "default104"}
    )
    remove_verbose = _action(
        {"kind": "remove_option", "section": "pipeline", "option": "verbose104"}
    )
    return runtime.acquisition_demand(
        "m104-qualification-ambiguity-control",
        "configuration",
        [keep_default, remove_verbose],
        [
            {
                "case_id": "m104-qualification-ambiguity-fit",
                "context": ["channel-ambiguous-104"],
                "initial": "[pipeline]\npolicy=default104\n",
                "expected": {"pipeline": {"policy": "default104"}},
            }
        ],
        [
            {
                "probe_id": "m104-qualification-ambiguity-separator",
                "context": ["channel-ambiguous-104"],
                "initial": "[pipeline]\npolicy=probe104\nverbose104=true\n",
            }
        ],
        max_trace=1,
    )


def build_pool() -> dict[str, Any]:
    if RESULT.exists():
        raise RuntimeError("M104 qualification pool cannot be authored after a result exists")
    development = json.loads(DEVELOPMENT.read_text(encoding="ascii"))
    ambiguity = _ambiguous_control()
    s_prime = runtime.constructor_definition(runtime.S_PRIME_ORIGIN, VALIDATED_S_PRIME_FEATURES)
    ambiguity_attempt = runtime.construct_hypothesis(s_prime, ambiguity)
    if ambiguity_attempt.get("reason") != "ambiguous_public_semantics":
        raise RuntimeError("M104 ambiguity control is not semantically ambiguous")
    payload: dict[str, Any] = {
        "schema": "m104-qualification-pool-v1",
        "milestone": "M104",
        "authored_after_m103_negative_before_m104_runner": True,
        "development_fixture_digest": development["fixture_digest"],
        "development_fixture_raw_sha256": runtime.sha256_bytes(DEVELOPMENT.read_bytes()),
        "m103_pool_raw_sha256": runtime.sha256_bytes(M103_POOL.read_bytes()),
        "fresh_from_m103": True,
        "qualification_only": True,
        "producer_fixture_included": False,
        "configuration": _configuration_family(),
        "filesystem": _filesystem_family(),
        "ambiguous_control": ambiguity,
        "record_count": 11,
        "hidden_case_count": 16,
        "selection": "complete fresh population; no draw, replacement, retry or post-result addition",
    }
    payload["pool_digest"] = runtime.digest(payload)
    return payload


def main() -> int:
    expected = runtime.canonical_json(build_pool()).encode("ascii") + b"\n"
    if OUTPUT.exists() and OUTPUT.read_bytes() != expected:
        raise SystemExit("existing M104 qualification pool differs from deterministic authoring")
    OUTPUT.write_bytes(expected)
    pool = json.loads(expected)
    print(json.dumps({"path": str(OUTPUT), "pool_digest": pool["pool_digest"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
