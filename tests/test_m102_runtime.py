from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from metamorphosis import m101_runtime
from metamorphosis import m102_runtime as runtime


ROOT = Path(__file__).resolve().parents[1]


def _m101_t2_bytes() -> bytes:
    result = json.loads((ROOT / "experiments/M101/RESULT.json").read_text(encoding="utf-8"))
    record = result["scientific_evidence"]["states"]["T2"]
    raw = m101_runtime.canonical_json(record["definitions"])
    state = {
        "schema": m101_runtime.STATE_SCHEMA,
        "m100_sha256": record["m100_sha256"],
        "m100_ascii": result["scientific_evidence"]["states"]["T0"]["definitions"] and "",
        "definitions": record["definitions"],
    }
    # Reconstruct through the exact embedded predecessor carried by any canonical M101 process.
    chronology = result["scientific_evidence"]["state_chronology"]["acquire_and_register_b"]
    canonical = chronology["runtime"]["acquisition"]["next_state"]
    encoded = m101_runtime.canonical_json(canonical).encode("ascii")
    assert hashlib.sha256(encoded).hexdigest() == record["raw_sha256"]
    assert raw  # The test also makes the canonical definition payload explicit.
    assert state["schema"] == "m101-lineage-state-v1"
    return encoded


def _prior_events() -> list[dict[str, object]]:
    return [
        runtime.registry_event(
            "record_alpha", "prepare", {"kind": "rename_key", "old": "raw", "new": "value"}
        ),
        runtime.registry_event("record_alpha", "finish", {"kind": "sort_list", "key": "values"}),
    ]


def _incoming_events() -> list[dict[str, object]]:
    return [
        runtime.registry_event("record_beta", "prepare", {"kind": "drop_key", "key": "trash"}),
        runtime.registry_event(
            "record_beta", "finish", {"kind": "set_default", "key": "status", "value": "ready"}
        ),
    ]


def _policy_demand(state: dict[str, object]) -> dict[str, object]:
    events = _incoming_events()
    all_events = list(state["journal"]) + events
    lookups = [
        {
            "case_id": f"development-policy-{index}",
            "carrier": event["carrier"],
            "slot": event["slot"],
            "expected_descriptor": copy.deepcopy(event["descriptor"]),
        }
        for index, event in enumerate(all_events, start=1)
    ]
    return runtime.policy_demand("development_policy_collision", events, lookups)


def _sqlite_events() -> list[dict[str, object]]:
    return [
        runtime.registry_event(
            "sqlite",
            "prepare",
            {
                "kind": "add_column",
                "table": "items",
                "column": "priority",
                "type": "INTEGER",
                "default": 0,
            },
        ),
        runtime.registry_event(
            "sqlite",
            "derive",
            {
                "kind": "backfill_length",
                "table": "items",
                "source": "name",
                "target": "priority",
            },
        ),
        runtime.registry_event(
            "sqlite",
            "rename",
            {
                "kind": "rename_column",
                "table": "items",
                "old": "name",
                "new": "label",
            },
        ),
        runtime.registry_event(
            "sqlite",
            "index",
            {
                "kind": "create_index",
                "table": "items",
                "name": "idx_items_label_priority",
                "columns": ["label", "priority"],
            },
        ),
    ]


def _sqlite_case(case_id: str, rows: list[dict[str, object]]) -> dict[str, object]:
    expected_rows = [
        {"id": row["id"], "label": row["name"], "priority": len(str(row["name"]))}
        for row in rows
    ]
    return {
        "case_id": case_id,
        "input": {
            "table": "items",
            "columns": [
                {"name": "id", "type": "INTEGER"},
                {"name": "name", "type": "TEXT"},
            ],
            "rows": rows,
            "indexes": [],
        },
        "expected": {
            "table": "items",
            "columns": [
                {"name": "id", "type": "INTEGER"},
                {"name": "label", "type": "TEXT"},
                {"name": "priority", "type": "INTEGER"},
            ],
            "rows": expected_rows,
            "indexes": [
                {"name": "idx_items_label_priority", "columns": ["label", "priority"]}
            ],
        },
    }


def _c_demand() -> dict[str, object]:
    cases = [
        _sqlite_case("development-sqlite-1", [{"id": 1, "name": "amber"}]),
        _sqlite_case(
            "development-sqlite-2",
            [{"id": 1, "name": "zinc"}, {"id": 2, "name": "quartz"}],
        ),
        _sqlite_case("development-sqlite-3", [{"id": 9, "name": "iron"}]),
        _sqlite_case(
            "development-sqlite-4",
            [{"id": 4, "name": "a"}, {"id": 7, "name": "long-name"}],
        ),
    ]
    return runtime.c_demand(
        "development_sqlite_trigger", ["prepare", "derive", "rename", "index"], cases
    )


@pytest.fixture(scope="module")
def u0() -> dict[str, object]:
    return runtime.create_state(_m101_t2_bytes(), _prior_events())


@pytest.fixture(scope="module")
def policy_acquisition(u0: dict[str, object]) -> dict[str, object]:
    return runtime.acquire_policy(u0, _policy_demand(u0), register_result=True)


@pytest.fixture(scope="module")
def u1(policy_acquisition: dict[str, object]) -> dict[str, object]:
    return policy_acquisition["next_state"]


@pytest.fixture(scope="module")
def pre_c(u1: dict[str, object]) -> dict[str, object]:
    return runtime.register_events(u1, _sqlite_events())


@pytest.fixture(scope="module")
def c_acquisition(pre_c: dict[str, object]) -> dict[str, object]:
    return runtime.acquire_c(pre_c, _c_demand(), register_result=True)


@pytest.fixture(scope="module")
def u2(c_acquisition: dict[str, object]) -> dict[str, object]:
    return c_acquisition["next_state"]


def test_exact_m101_t2_is_embedded_unchanged(u0: dict[str, object]) -> None:
    assert u0["m101_sha256"] == "cd5b5994e5a252599807e9ddc2b5733efaf176fe23dd05055b50d883bde0b7a0"
    assert hashlib.sha256(u0["m101_ascii"].encode("ascii")).hexdigest() == u0["m101_sha256"]
    predecessor = m101_runtime.decode_state(u0["m101_ascii"].encode("ascii"))
    assert len(predecessor["definitions"]) == 2


def test_flat_policy_has_a_structural_collision(u0: dict[str, object]) -> None:
    closure = runtime.flat_collision_report(u0, _incoming_events())
    assert closure["budget_independent"] is True
    assert closure["joint_relation_representable"] is False
    assert len(closure["collision_witnesses"]) == 2


def test_policy_is_exhaustively_acquired_without_target_identity(
    policy_acquisition: dict[str, object],
) -> None:
    assert policy_acquisition["confirmed"] is True
    assert policy_acquisition["assembled"] == sum(
        len(runtime.POLICY_TOKENS) ** length
        for length in range(1, runtime.POLICY_MAX_BODY + 1)
    )
    adopted = policy_acquisition["adopted"]
    assert adopted["origin"] == runtime.ACQUIRED_POLICY_ORIGIN
    assert len(adopted["body"]) == 4
    text = runtime.canonical_json(adopted).lower()
    assert not any(term in text for term in runtime.FORBIDDEN_POLICY_SUBSTRINGS)


def test_building_policy_without_registration_leaves_u0_exact(u0: dict[str, object]) -> None:
    before = runtime.encode_state(u0)
    result = runtime.acquire_policy(u0, _policy_demand(u0), register_result=False)
    assert result["confirmed"] is True
    assert result["registered"] is False
    assert result["next_state"] is None
    assert runtime.encode_state(u0) == before


def test_no_upgrade_last_write_genuinely_forgets_the_old_record_capability(
    u0: dict[str, object],
) -> None:
    destructive = runtime.force_last_write_events(u0, _incoming_events())
    value = {"raw": "kept", "values": [3, 1], "trash": True}
    retained = runtime.execute_registry_sequence(
        u0, "record_alpha", ["prepare", "finish"], value
    )
    forgotten = runtime.execute_registry_sequence(
        destructive, "record_alpha", ["prepare", "finish"], value, last_write=True
    )
    assert retained == {"value": "kept", "values": [1, 3], "trash": True}
    assert forgotten != retained
    with pytest.raises(ValueError, match="unequal descriptors"):
        runtime.registry_index(destructive)


def test_registered_policy_prevents_forgetting(u1: dict[str, object]) -> None:
    value = {"raw": "kept", "values": [3, 1], "trash": True}
    assert runtime.execute_registry_sequence(
        u1, "record_alpha", ["prepare", "finish"], value
    ) == {"value": "kept", "values": [1, 3], "trash": True}
    assert runtime.execute_registry_sequence(
        u1, "record_beta", ["prepare", "finish"], value
    ) == {"raw": "kept", "values": [3, 1], "status": "ready"}


def test_policy_transfers_to_sqlite_registry_without_changing_m101(
    u1: dict[str, object], pre_c: dict[str, object]
) -> None:
    assert pre_c["m101_ascii"] == u1["m101_ascii"]
    assert pre_c["policy"] == u1["policy"]
    assert len(pre_c["journal"]) == len(u1["journal"]) + 4
    assert len(runtime.registry_index(pre_c)) == len(pre_c["journal"])


def test_c_is_demand_derived_and_depends_on_live_m101_b(
    c_acquisition: dict[str, object], pre_c: dict[str, object]
) -> None:
    assert c_acquisition["confirmed"] is True
    assert c_acquisition["assembled"] > 7_000
    assert c_acquisition["well_formed"] > 0
    assert c_acquisition["accepted"] > 0
    assert c_acquisition["shortest_accepted_length"] == 4
    assert sorted(c_acquisition["symbolic_trace"]) == [0, 1, 2, 3]
    adopted = c_acquisition["adopted"]
    predecessor = m101_runtime.decode_state(pre_c["m101_ascii"].encode("ascii"))
    assert adopted["definition_dependencies"] == [predecessor["definitions"][1]["definition_id"]]
    assert adopted["policy_dependency"] == pre_c["policy"]["policy_id"]
    assert any(
        token.startswith(f"CALL:{predecessor['definitions'][1]['definition_id']}:")
        for token in adopted["body"]
    )


def test_c_executes_against_actual_sqlite_state(u2: dict[str, object]) -> None:
    execution = runtime.execute_c_world(u2, _c_demand())
    assert execution["confirmed"] is True
    assert execution["passed"] == execution["total"] == 4
    for outcome in execution["outcomes"]:
        assert outcome["snapshot"] == outcome["expected"]


def test_c_build_without_registration_leaves_pre_c_exact(pre_c: dict[str, object]) -> None:
    before = runtime.encode_state(pre_c)
    result = runtime.acquire_c(pre_c, _c_demand(), register_result=False)
    assert result["confirmed"] is True
    assert result["next_state"] is None
    assert runtime.encode_state(pre_c) == before


def test_policy_and_c_mutations_break_only_the_predicted_capability(
    u2: dict[str, object]
) -> None:
    flat_fault = runtime.mutate_policy_to_flat(u2)
    assert runtime.execute_c_world(flat_fault, _c_demand())["confirmed"] is False

    c_fault = runtime.mutate_c_duplicate_effect(u2)
    assert runtime.execute_c_world(c_fault, _c_demand())["confirmed"] is False
    value = {"raw": "still-live", "values": [2, 1]}
    assert runtime.execute_registry_sequence(
        c_fault, "record_alpha", ["prepare", "finish"], value
    ) == {"value": "still-live", "values": [1, 2]}


def test_c_ablation_and_corruption_fail_closed(u2: dict[str, object]) -> None:
    assert runtime.execute_c_world(runtime.ablate_c(u2), _c_demand())["confirmed"] is False
    with pytest.raises(ValueError, match="state digest mismatch"):
        runtime.decode_state(runtime.corrupt_state_digest(u2))


def test_exact_u2_rollback_restores_every_capability(u2: dict[str, object]) -> None:
    original = runtime.encode_state(u2)
    faulted = runtime.mutate_c_duplicate_effect(u2)
    assert runtime.execute_c_world(faulted, _c_demand())["confirmed"] is False
    restored = runtime.decode_state(original)
    assert runtime.encode_state(restored) == original
    assert runtime.execute_c_world(restored, _c_demand())["confirmed"] is True
    assert runtime.execute_registry_sequence(
        restored,
        "record_alpha",
        ["prepare", "finish"],
        {"raw": "rollback", "values": [9, 4]},
    ) == {"value": "rollback", "values": [4, 9]}


def test_sqlite_identifiers_are_fail_closed() -> None:
    with pytest.raises(ValueError, match="safe SQLite identifier"):
        runtime._sqlite_model_atomic(
            {
                "kind": "add_column",
                "table": "items; DROP TABLE items",
                "column": "x",
                "type": "INTEGER",
                "default": 0,
            }
        )
