from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from metamorphosis import m103_runtime as runtime


VALIDATED_S_PRIME_FEATURES = {
    "OBSERVE_CONTEXT",
    "PARTITION_EQUAL",
    "SYNTHESIZE_PARTITIONS",
    "EMIT_GUARDED",
}


ROOT = Path(__file__).resolve().parents[1]
M102_RESULT = ROOT / "experiments" / "M102" / "RESULT.json"
M102_U2_RAW_SHA256 = "3bad4d5400e8d9a11b15ba596336925823ffb4064a5bbe38f93f64b7384a198d"


def m102_u2_bytes() -> bytes:
    result = json.loads(M102_RESULT.read_text(encoding="utf-8"))
    state = result["scientific_evidence"]["states"]["U2"]["state"]
    raw = runtime.canonical_json(state).encode("ascii")
    assert runtime.sha256_bytes(raw) == M102_U2_RAW_SHA256
    return raw


def action(descriptor: dict[str, object]) -> dict[str, object]:
    return runtime.action_definition(descriptor)


def development_demand() -> dict[str, object]:
    amber = action({"kind": "set_value", "key": "outcome", "value": "amber"})
    violet = action({"kind": "set_value", "key": "outcome", "value": "violet"})
    return runtime.acquisition_demand(
        "development-constructor-trigger",
        "development_record",
        [amber, violet],
        [
            {
                "case_id": "development-left",
                "context": ["north"],
                "initial": {"seed": "same"},
                "expected": {"seed": "same", "outcome": "amber"},
            },
            {
                "case_id": "development-right",
                "context": ["south"],
                "initial": {"seed": "same"},
                "expected": {"seed": "same", "outcome": "violet"},
            },
        ],
        [
            {"probe_id": "development-probe-left", "context": ["north"], "initial": {}},
            {"probe_id": "development-probe-right", "context": ["south"], "initial": {}},
        ],
        max_trace=1,
    )


def configuration_demand() -> dict[str, object]:
    harden = action(
        {"kind": "set_option", "section": "service", "option": "mode", "value": "hardened"}
    )
    remove_debug = action(
        {"kind": "remove_option", "section": "service", "option": "debug"}
    )
    initial = "[service]\nmode=base\ndebug=true\n"
    return runtime.acquisition_demand(
        "configuration-consumer",
        "configuration",
        [harden, remove_debug],
        [
            {
                "case_id": "configuration-production",
                "context": ["production"],
                "initial": initial,
                "expected": {"service": {"debug": "true", "mode": "hardened"}},
            },
            {
                "case_id": "configuration-lean",
                "context": ["lean"],
                "initial": initial,
                "expected": {"service": {"mode": "base"}},
            },
        ],
        [
            {
                "probe_id": "configuration-probe-production",
                "context": ["production"],
                "initial": "[service]\nmode=probe\ndebug=false\n",
            },
            {
                "probe_id": "configuration-probe-lean",
                "context": ["lean"],
                "initial": "[service]\nmode=probe\ndebug=false\n",
            },
        ],
        max_trace=1,
    )


def filesystem_demand() -> dict[str, object]:
    deploy = action({"kind": "write_text", "path": "deploy.flag", "content": "ready"})
    verify = action({"kind": "write_text", "path": "verify.flag", "content": "ready"})
    return runtime.acquisition_demand(
        "filesystem-consumer",
        "filesystem",
        [deploy, verify],
        [
            {
                "case_id": "filesystem-release",
                "context": ["release"],
                "initial": {"base.txt": "seed"},
                "expected": {"base.txt": "seed", "deploy.flag": "ready"},
            },
            {
                "case_id": "filesystem-verify",
                "context": ["verify"],
                "initial": {"base.txt": "seed"},
                "expected": {"base.txt": "seed", "verify.flag": "ready"},
            },
        ],
        [
            {
                "probe_id": "filesystem-probe-release",
                "context": ["release"],
                "initial": {"probe.txt": "x"},
            },
            {
                "probe_id": "filesystem-probe-verify",
                "context": ["verify"],
                "initial": {"probe.txt": "x"},
            },
        ],
        max_trace=1,
    )


def acquire_v1() -> tuple[dict[str, object], dict[str, object]]:
    v0 = runtime.create_state(m102_u2_bytes())
    acquisition = runtime.acquire_constructor(v0, development_demand(), register_result=True)
    assert acquisition["confirmed"] is True
    return v0, acquisition["next_state"]


def test_s0_closure_and_constructor_acquisition_change_reach() -> None:
    v0, v1 = acquire_v1()
    closure = runtime.s0_closure(development_demand())
    assert closure["finite_image_size"] == 2
    assert closure["demand_outside_complete_image"] is True
    assert closure["budget_independent"] is True
    assert runtime.construct_hypothesis(v0["constructor"], development_demand())["confirmed"] is False
    assert set(v1["constructor"]["features"]) == VALIDATED_S_PRIME_FEATURES
    assert runtime.construct_hypothesis(v1["constructor"], development_demand())["confirmed"] is True
    assert v1["m102_ascii"] == v0["m102_ascii"]


def test_built_not_registered_preserves_exact_v0() -> None:
    v0 = runtime.create_state(m102_u2_bytes())
    before = runtime.encode_state(v0)
    result = runtime.acquire_constructor(v0, development_demand(), register_result=False)
    assert result["confirmed"] is True
    assert result["registered"] is False
    assert result["next_state"] is None
    assert runtime.encode_state(v0) == before


def test_s_prime_acquires_two_consumers_and_s0_cannot() -> None:
    v0, v1 = acquire_v1()
    assert runtime.acquire_consumer(v0, configuration_demand(), register_result=False)[
        "confirmed"
    ] is False
    d_result = runtime.acquire_consumer(v1, configuration_demand(), register_result=True)
    assert d_result["confirmed"] is True
    v2 = d_result["next_state"]
    assert runtime.acquire_consumer(
        runtime.ablate_constructor(v2), filesystem_demand(), register_result=False
    )["confirmed"] is False
    e_result = runtime.acquire_consumer(v2, filesystem_demand(), register_result=True)
    assert e_result["confirmed"] is True
    v3 = e_result["next_state"]
    assert runtime.state_summary(v3)["definition_families"] == ["configuration", "filesystem"]


def test_compiled_definition_executes_but_future_acquisition_needs_s_prime() -> None:
    _v0, v1 = acquire_v1()
    v2 = runtime.acquire_consumer(v1, configuration_demand(), register_result=True)["next_state"]
    compiled_d = runtime.definition_for_family(v2, "configuration")
    assert runtime.execute_definition(
        compiled_d,
        ["production"],
        "[service]\nmode=base\ndebug=true\n",
    ) == {"service": {"debug": "true", "mode": "hardened"}}
    without_s_prime = runtime.ablate_constructor(v2)
    assert runtime.execute_definition(
        runtime.definition_for_family(without_s_prime, "configuration"),
        ["production"],
        "[service]\nmode=base\ndebug=true\n",
    ) == {"service": {"debug": "true", "mode": "hardened"}}
    assert runtime.acquire_consumer(without_s_prime, filesystem_demand(), register_result=False)[
        "confirmed"
    ] is False


def test_ambiguity_refuses_without_state_change() -> None:
    _v0, v1 = acquire_v1()
    set_flag = action({"kind": "set_value", "key": "flag", "value": True})
    drop_missing = action({"kind": "drop_value", "key": "missing"})
    demand = runtime.acquisition_demand(
        "ambiguous-development-control",
        "development_record",
        [set_flag, drop_missing],
        [
            {
                "case_id": "ambiguous-fit",
                "context": ["one"],
                "initial": {"flag": True},
                "expected": {"flag": True},
            }
        ],
        [
            {
                "probe_id": "ambiguous-probe",
                "context": ["one"],
                "initial": {"flag": False, "missing": 1},
            }
        ],
        max_trace=1,
    )
    before = runtime.encode_state(v1)
    result = runtime.acquire_consumer(v1, demand, register_result=True)
    assert result["confirmed"] is False
    assert result["reason"] == "ambiguous_public_semantics"
    assert result["semantic_classes"] == 2
    assert result["next_state"] is None
    assert runtime.encode_state(v1) == before


def test_feature_mutation_corruption_ablation_and_conservation() -> None:
    _v0, v1 = acquire_v1()
    for feature in VALIDATED_S_PRIME_FEATURES:
        mutated = runtime.mutate_constructor_without_feature(v1, feature)
        assert runtime.acquire_consumer(mutated, configuration_demand(), register_result=False)[
            "confirmed"
        ] is False
    with pytest.raises(ValueError, match="digest mismatch"):
        runtime.decode_state(runtime.corrupt_state_digest(v1))
    conservation = runtime.predecessor_conservation(v1)
    assert conservation["m100_live"] is True
    assert conservation["m101_a_live"] is True
    assert conservation["m101_b_live"] is True
    assert conservation["m102_k_live"] is True
    assert conservation["m102_c_live"] is True
    assert conservation["record_registry_live"] is True


def test_definition_digest_rejects_semantic_mutation() -> None:
    _v0, v1 = acquire_v1()
    v2 = runtime.acquire_consumer(v1, configuration_demand(), register_result=True)["next_state"]
    broken = copy.deepcopy(v2)
    broken["definitions"][0]["dispatch"][0]["body"] = broken["definitions"][0]["dispatch"][
        1
    ]["body"]
    payload = {key: value for key, value in broken.items() if key != "state_digest"}
    broken["state_digest"] = runtime.digest(payload)
    with pytest.raises(ValueError, match="consumer content address mismatch"):
        runtime.decode_state(broken)
