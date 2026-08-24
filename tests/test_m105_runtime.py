from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from metamorphosis import m105_runtime as runtime


ROOT = Path(__file__).resolve().parents[1]
M104_RESULT = ROOT / "experiments" / "M104" / "RESULT.json"


def m104_v3_bytes() -> bytes:
    result = json.loads(M104_RESULT.read_text(encoding="utf-8"))
    state = result["scientific_evidence"]["states"]["V3"]["state"]
    raw = runtime.canonical_json(state).encode("ascii")
    assert runtime.sha256_bytes(raw) == runtime.M104_V3_RAW_SHA256
    return raw


def feature_demand() -> dict[str, object]:
    observations = []
    expected = {
        (False, False): False,
        (False, True): True,
        (True, False): True,
        (True, True): False,
    }
    for index, (signals, value) in enumerate(expected.items()):
        for nonce_index in range(2):
            observations.append(
                {
                    "case_id": f"development_{index}_{nonce_index}",
                    "signals": list(signals),
                    "nonce": f"development-nonce-{index}-{nonce_index}",
                    "expected": value,
                }
            )
    return runtime.feature_demand("development_feature", observations)


def json_demand() -> dict[str, object]:
    amber = runtime.action_definition(
        {"kind": "set_field", "key": "route", "value": "amber"}
    )
    violet = runtime.action_definition(
        {"kind": "set_field", "key": "route", "value": "violet"}
    )
    return runtime.consumer_demand(
        "json_consumer",
        "json_document",
        [amber, violet],
        [
            {
                "case_id": "json_false",
                "context": {"signals": [False, False], "nonce": "json-public-a"},
                "initial": {"seed": 1},
                "expected": {"seed": 1, "route": "amber"},
            },
            {
                "case_id": "json_true",
                "context": {"signals": [False, True], "nonce": "json-public-b"},
                "initial": {"seed": 1},
                "expected": {"seed": 1, "route": "violet"},
            },
        ],
        [
            {
                "probe_id": "json_probe_10",
                "context": {"signals": [True, False], "nonce": "json-probe-new"},
                "initial": {"probe": 2},
            },
            {
                "probe_id": "json_probe_11",
                "context": {"signals": [True, True], "nonce": "json-probe-newer"},
                "initial": {"probe": 3},
            },
        ],
        max_trace=1,
    )


def sqlite_demand() -> dict[str, object]:
    amber = runtime.action_definition(
        {"kind": "set_status", "id": 1, "status": "amber"}
    )
    violet = runtime.action_definition(
        {"kind": "set_status", "id": 1, "status": "violet"}
    )
    initial = {"rows": [{"id": 1, "value": "seed", "status": "base"}]}
    return runtime.consumer_demand(
        "sqlite_consumer",
        "sqlite",
        [amber, violet],
        [
            {
                "case_id": "sqlite_false",
                "context": {"signals": [False, False], "nonce": "sqlite-public-a"},
                "initial": initial,
                "expected": {"rows": [{"id": 1, "value": "seed", "status": "amber"}]},
            },
            {
                "case_id": "sqlite_true",
                "context": {"signals": [False, True], "nonce": "sqlite-public-b"},
                "initial": initial,
                "expected": {"rows": [{"id": 1, "value": "seed", "status": "violet"}]},
            },
        ],
        [
            {
                "probe_id": "sqlite_probe_10",
                "context": {"signals": [True, False], "nonce": "sqlite-probe-new"},
                "initial": initial,
            },
            {
                "probe_id": "sqlite_probe_11",
                "context": {"signals": [True, True], "nonce": "sqlite-probe-newer"},
                "initial": initial,
            },
        ],
        max_trace=1,
    )


def acquired_feature_state() -> tuple[dict[str, object], dict[str, object]]:
    w0 = runtime.create_state(m104_v3_bytes())
    result = runtime.acquire_feature(w0, feature_demand(), register_result=True)
    assert result["confirmed"] is True
    return w0, result["next_state"]


def test_complete_boolean_census_has_all_sixteen_semantics() -> None:
    census = runtime.semantic_census()
    assert census["semantic_count"] == 16
    assert census["complete_two_input_boolean_image"] is True
    assert len({tuple(row["truth_table"]) for row in census["representatives"]}) == 16
    assert max(row["nodes"] for row in census["representatives"]) <= 8


def test_exact_m104_migration_and_empty_registry() -> None:
    raw = m104_v3_bytes()
    w0 = runtime.create_state(raw)
    assert w0["m104_ascii"].encode("ascii") == raw
    assert w0["features"] == []
    assert w0["definitions"] == []
    assert runtime.predecessor_conservation(w0)["all_conserved"] is True


def test_feature_acquisition_is_unique_persistent_and_build_only_is_transactional() -> None:
    w0 = runtime.create_state(m104_v3_bytes())
    before = runtime.encode_state(w0)
    built = runtime.acquire_feature(w0, feature_demand(), register_result=False)
    assert built["confirmed"] is True
    assert built["accepted_semantic_classes"] == 1
    assert built["semantic_image_exhausted"] is True
    assert built["next_state"] is None
    assert runtime.encode_state(w0) == before
    adopted = runtime.acquire_feature(w0, feature_demand(), register_result=True)
    w1_raw = runtime.encode_state(adopted["next_state"])
    w1 = runtime.decode_state(w1_raw)
    assert w1["features"][0] == adopted["feature"]
    serialized = runtime.canonical_json(w1["features"][0]).lower()
    assert "development-nonce" not in serialized
    assert "json" not in serialized
    assert "sqlite" not in serialized


def test_ambiguous_development_refuses_without_state_change() -> None:
    w0 = runtime.create_state(m104_v3_bytes())
    before = runtime.encode_state(w0)
    demand = runtime.feature_demand(
        "ambiguous_feature",
        [
            {
                "case_id": "ambiguous_00_a",
                "signals": [False, False],
                "nonce": "a",
                "expected": False,
            },
            {
                "case_id": "ambiguous_00_b",
                "signals": [False, False],
                "nonce": "b",
                "expected": False,
            },
        ],
    )
    result = runtime.acquire_feature(w0, demand, register_result=True)
    assert result["confirmed"] is False
    assert result["next_state"] is None
    assert runtime.encode_state(w0) == before


def test_live_feature_enables_json_and_sqlite_while_fresh_is_ambiguous() -> None:
    w0, w1 = acquired_feature_state()
    fresh_json = runtime.acquire_consumer(w0, json_demand(), register_result=False)
    assert fresh_json["confirmed"] is False
    assert fresh_json["reason"] == "ambiguous_public_semantics"
    assert fresh_json["semantic_image_exhausted"] is True
    assert fresh_json["enumerated_feature_semantics"] == 16
    assert fresh_json["semantic_classes"] > 1
    json_result = runtime.acquire_consumer(w1, json_demand(), register_result=True)
    assert json_result["confirmed"] is True
    w2 = runtime.decode_state(runtime.encode_state(json_result["next_state"]))
    fresh_sqlite = runtime.acquire_consumer(w0, sqlite_demand(), register_result=False)
    assert fresh_sqlite["confirmed"] is False
    assert fresh_sqlite["semantic_image_exhausted"] is True
    assert fresh_sqlite["semantic_classes"] > 1
    sqlite_result = runtime.acquire_consumer(w2, sqlite_demand(), register_result=True)
    assert sqlite_result["confirmed"] is True
    w3 = sqlite_result["next_state"]
    assert runtime.state_summary(w3)["definition_families"] == ["json_document", "sqlite"]


def test_unseen_signal_nonce_generalization_and_real_sqlite_execution() -> None:
    _w0, w1 = acquired_feature_state()
    w2 = runtime.acquire_consumer(w1, json_demand(), register_result=True)["next_state"]
    w3 = runtime.acquire_consumer(w2, sqlite_demand(), register_result=True)["next_state"]
    json_definition = runtime.definition_for_family(w3, "json_document")
    assert runtime.execute_definition(
        w3,
        json_definition,
        {"signals": [True, False], "nonce": "qualification-never-seen"},
        {"hidden": 1},
    ) == {"hidden": 1, "route": "violet"}
    assert runtime.execute_definition(
        w3,
        json_definition,
        {"signals": [True, True], "nonce": "qualification-never-seen-2"},
        {"hidden": 2},
    ) == {"hidden": 2, "route": "amber"}
    sqlite_definition = runtime.definition_for_family(w3, "sqlite")
    initial = {"rows": [{"id": 1, "value": "hidden", "status": "base"}]}
    assert runtime.execute_definition(
        w3,
        sqlite_definition,
        {"signals": [True, False], "nonce": "sqlite-never-seen"},
        initial,
    ) == {"rows": [{"id": 1, "value": "hidden", "status": "violet"}]}


def test_ablation_mutation_corruption_and_exact_rollback() -> None:
    _w0, w1 = acquired_feature_state()
    w2 = runtime.acquire_consumer(w1, json_demand(), register_result=True)["next_state"]
    w3 = runtime.acquire_consumer(w2, sqlite_demand(), register_result=True)["next_state"]
    before = runtime.encode_state(w3)
    with pytest.raises(ValueError, match="live feature dependency is missing"):
        runtime.decode_state(runtime.remove_feature_without_rebinding(w3))
    mutated = runtime.mutate_feature_and_rebind(w3)
    assert runtime.encode_state(mutated) != before
    context = {"signals": [True, False], "nonce": "mutation-control"}
    original = runtime.execute_definition(
        w3, runtime.definition_for_family(w3, "json_document"), context, {}
    )
    changed = runtime.execute_definition(
        mutated, runtime.definition_for_family(mutated, "json_document"), context, {}
    )
    assert changed != original
    with pytest.raises(ValueError, match="schema or digest mismatch"):
        runtime.decode_state(runtime.corrupt_state_digest(w3))
    assert runtime.encode_state(runtime.decode_state(before)) == before


def test_definition_digest_rejects_semantic_mutation() -> None:
    _w0, w1 = acquired_feature_state()
    w2 = runtime.acquire_consumer(w1, json_demand(), register_result=True)["next_state"]
    broken = copy.deepcopy(w2)
    broken["definitions"][0]["branches"]["false"] = broken["definitions"][0]["branches"][
        "true"
    ]
    payload = {key: value for key, value in broken.items() if key != "state_digest"}
    broken["state_digest"] = runtime.digest(payload)
    with pytest.raises(ValueError, match="consumer content address mismatch"):
        runtime.decode_state(broken)
