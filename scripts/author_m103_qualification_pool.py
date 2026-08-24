"""Author and validate the frozen-shape M103 qualification-only population."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from metamorphosis import m103_runtime as runtime  # noqa: E402


OUTPUT = ROOT / "experiments" / "M103" / "QUALIFICATION_POOL.json"
DEVELOPMENT = ROOT / "experiments" / "M103" / "DEVELOPMENT_FIXTURE.json"
RESULT = ROOT / "experiments" / "M103" / "RESULT.json"
VALIDATED_S_PRIME_FEATURES = {
    "OBSERVE_CONTEXT",
    "PARTITION_EQUAL",
    "SYNTHESIZE_PARTITIONS",
    "EMIT_GUARDED",
}


def _action(descriptor: dict[str, Any]) -> dict[str, Any]:
    return runtime.action_definition(descriptor)


def _configuration_family() -> dict[str, Any]:
    harden = _action(
        {"kind": "set_option", "section": "service", "option": "tier", "value": "hardened"}
    )
    remove_trace = _action(
        {"kind": "remove_option", "section": "service", "option": "trace"}
    )
    actions = [harden, remove_trace]
    initial = "[service]\ntier=base\ntrace=on\n"
    acquisition = runtime.acquisition_demand(
        "qualification-configuration-acquisition",
        "configuration",
        actions,
        [
            {
                "case_id": "configuration-public-facet-7",
                "context": ["facet-7"],
                "initial": initial,
                "expected": {"service": {"tier": "hardened", "trace": "on"}},
            },
            {
                "case_id": "configuration-public-facet-2",
                "context": ["facet-2"],
                "initial": initial,
                "expected": {"service": {"tier": "base"}},
            },
        ],
        [
            {
                "probe_id": "configuration-diagnostic-facet-7",
                "context": ["facet-7"],
                "initial": "[service]\ntier=probe\ntrace=off\n",
            },
            {
                "probe_id": "configuration-diagnostic-facet-2",
                "context": ["facet-2"],
                "initial": "[service]\ntier=probe\ntrace=off\n",
            },
        ],
        max_trace=1,
    )
    hidden_initials = (
        "[service]\ntier=bronze\ntrace=verbose\nregion=west\n",
        "[service]\ntier=silver\ntrace=quiet\nregion=east\n",
        "[service]\ntier=gold\ntrace=audit\nregion=delta\n",
        "[service]\ntier=platinum\ntrace=debug\nregion=omega\n",
    )
    hidden_worlds: list[dict[str, Any]] = []
    for index, source in enumerate(hidden_initials):
        before = runtime.execute_trace("configuration", actions, [], source)
        hardened = runtime.execute_trace(
            "configuration", actions, [harden["action_id"]], source
        )
        lean = runtime.execute_trace(
            "configuration", actions, [remove_trace["action_id"]], source
        )
        assert before != hardened and before != lean and hardened != lean
        hidden_worlds.append(
            {
                "world_id": f"configuration-hidden-{index}",
                "family": "configuration",
                "cases": [
                    {
                        "case_id": f"configuration-hidden-{index}-facet-7",
                        "context": ["facet-7"],
                        "initial": source,
                        "expected": hardened,
                    },
                    {
                        "case_id": f"configuration-hidden-{index}-facet-2",
                        "context": ["facet-2"],
                        "initial": source,
                        "expected": lean,
                    },
                ],
            }
        )
    return {"acquisition": acquisition, "hidden_worlds": hidden_worlds}


def _filesystem_family() -> dict[str, Any]:
    rename = _action({"kind": "rename_path", "old": "draft.txt", "new": "final.txt"})
    stamp = _action({"kind": "write_text", "path": "stamp.txt", "content": "sealed"})
    actions = [rename, stamp]
    initial = {"draft.txt": "payload", "keep.txt": "stable"}
    acquisition = runtime.acquisition_demand(
        "qualification-filesystem-acquisition",
        "filesystem",
        actions,
        [
            {
                "case_id": "filesystem-public-facet-9",
                "context": ["facet-9"],
                "initial": initial,
                "expected": {"final.txt": "payload", "keep.txt": "stable"},
            },
            {
                "case_id": "filesystem-public-facet-4",
                "context": ["facet-4"],
                "initial": initial,
                "expected": {
                    "draft.txt": "payload",
                    "keep.txt": "stable",
                    "stamp.txt": "sealed",
                },
            },
        ],
        [
            {
                "probe_id": "filesystem-diagnostic-facet-9",
                "context": ["facet-9"],
                "initial": {"draft.txt": "probe", "other.txt": "one"},
            },
            {
                "probe_id": "filesystem-diagnostic-facet-4",
                "context": ["facet-4"],
                "initial": {"draft.txt": "probe", "other.txt": "one"},
            },
        ],
        max_trace=1,
    )
    hidden_initials = (
        {"draft.txt": "alpha", "keep.txt": "k1"},
        {"draft.txt": "beta", "notes.txt": "n2"},
        {"draft.txt": "gamma", "nested/item.txt": "n3"},
        {"draft.txt": "delta", "keep.txt": "k4", "notes.txt": "n4"},
    )
    hidden_worlds: list[dict[str, Any]] = []
    for index, source in enumerate(hidden_initials):
        before = runtime.execute_trace("filesystem", actions, [], source)
        renamed = runtime.execute_trace("filesystem", actions, [rename["action_id"]], source)
        stamped = runtime.execute_trace("filesystem", actions, [stamp["action_id"]], source)
        assert before != renamed and before != stamped and renamed != stamped
        hidden_worlds.append(
            {
                "world_id": f"filesystem-hidden-{index}",
                "family": "filesystem",
                "cases": [
                    {
                        "case_id": f"filesystem-hidden-{index}-facet-9",
                        "context": ["facet-9"],
                        "initial": source,
                        "expected": renamed,
                    },
                    {
                        "case_id": f"filesystem-hidden-{index}-facet-4",
                        "context": ["facet-4"],
                        "initial": source,
                        "expected": stamped,
                    },
                ],
            }
        )
    return {"acquisition": acquisition, "hidden_worlds": hidden_worlds}


def _ambiguous_control() -> dict[str, Any]:
    keep_base = _action(
        {"kind": "set_option", "section": "service", "option": "mode", "value": "base"}
    )
    remove_debug = _action(
        {"kind": "remove_option", "section": "service", "option": "debug"}
    )
    return runtime.acquisition_demand(
        "qualification-ambiguity-control",
        "configuration",
        [keep_base, remove_debug],
        [
            {
                "case_id": "qualification-ambiguity-fit",
                "context": ["facet-ambiguous"],
                "initial": "[service]\nmode=base\n",
                "expected": {"service": {"mode": "base"}},
            }
        ],
        [
            {
                "probe_id": "qualification-ambiguity-separator",
                "context": ["facet-ambiguous"],
                "initial": "[service]\nmode=probe\ndebug=true\n",
            }
        ],
        max_trace=1,
    )


def build_pool() -> dict[str, Any]:
    if RESULT.exists():
        raise RuntimeError("M103 qualification pool cannot be authored after a result exists")
    development = json.loads(DEVELOPMENT.read_text(encoding="ascii"))
    configuration = _configuration_family()
    filesystem = _filesystem_family()
    ambiguity = _ambiguous_control()

    # Verify the ambiguity control really has multiple observationally distinct accepted traces.
    s_prime = runtime.constructor_definition(runtime.S_PRIME_ORIGIN, VALIDATED_S_PRIME_FEATURES)
    ambiguity_attempt = runtime.construct_hypothesis(s_prime, ambiguity)
    if ambiguity_attempt["reason"] != "ambiguous_public_semantics":
        raise RuntimeError("M103 ambiguity control does not refuse for semantic ambiguity")

    payload: dict[str, Any] = {
        "schema": "m103-qualification-pool-v1",
        "milestone": "M103",
        "authored_after_runtime_and_boundary_audit": True,
        "development_fixture_digest": development["fixture_digest"],
        "development_fixture_raw_sha256": runtime.sha256_bytes(DEVELOPMENT.read_bytes()),
        "qualification_only": True,
        "producer_fixture_included": False,
        "configuration": configuration,
        "filesystem": filesystem,
        "ambiguous_control": ambiguity,
        "record_count": 11,
        "hidden_case_count": 16,
        "selection": "complete population; no draw, replacement, retry or post-result addition",
    }
    payload["pool_digest"] = runtime.digest(payload)
    return payload


def main() -> int:
    expected = runtime.canonical_json(build_pool()).encode("ascii")
    if OUTPUT.exists() and OUTPUT.read_bytes() != expected:
        raise SystemExit("existing M103 qualification pool differs from deterministic authoring")
    OUTPUT.write_bytes(expected)
    pool = json.loads(expected)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "pool_digest": pool["pool_digest"],
                "record_count": pool["record_count"],
                "hidden_case_count": pool["hidden_case_count"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
