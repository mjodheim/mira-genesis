from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

from metamorphosis import m101_runtime
from metamorphosis import m102_runtime as runtime
from scripts import run_m102_development as development


ROOT = Path(__file__).resolve().parents[1]


def _m101_t2_bytes() -> bytes:
    result = json.loads((ROOT / "experiments/M101/RESULT.json").read_text(encoding="utf-8"))
    state = result["scientific_evidence"]["state_chronology"]["acquire_and_register_b"][
        "runtime"
    ]["acquisition"]["next_state"]
    raw = m101_runtime.canonical_json(state).encode("ascii")
    assert hashlib.sha256(raw).hexdigest() == (
        "cd5b5994e5a252599807e9ddc2b5733efaf176fe23dd05055b50d883bde0b7a0"
    )
    return raw


def _record_events() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    prior = [
        runtime.registry_event(
            "record_alpha", "prepare", {"kind": "rename_key", "old": "raw", "new": "value"}
        ),
        runtime.registry_event("record_alpha", "finish", {"kind": "sort_list", "key": "values"}),
    ]
    incoming = [
        runtime.registry_event("record_beta", "prepare", {"kind": "drop_key", "key": "trash"}),
        runtime.registry_event(
            "record_beta", "finish", {"kind": "set_default", "key": "status", "value": "ready"}
        ),
    ]
    return prior, incoming


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
            {"kind": "rename_column", "table": "items", "old": "name", "new": "label"},
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
    return {
        "case_id": case_id,
        "input": {
            "table": "items",
            "columns": [{"name": "id", "type": "INTEGER"}, {"name": "name", "type": "TEXT"}],
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
            "rows": [
                {"id": row["id"], "label": row["name"], "priority": len(str(row["name"]))}
                for row in rows
            ],
            "indexes": [
                {"name": "idx_items_label_priority", "columns": ["label", "priority"]}
            ],
        },
    }


def _write(path: Path, value: object) -> Path:
    path.write_bytes(runtime.canonical_json(value).encode("ascii"))
    return path


def _successful(invocation: dict[str, object]) -> dict[str, object]:
    assert invocation["returncode"] == 0, invocation
    payload = invocation["runtime"]
    assert payload["confirmed"] is True
    return payload


def test_development_lineage_crosses_fresh_isolated_processes(tmp_path: Path) -> None:
    capsules, reports = development.build_capsules(tmp_path / "capsules")
    predecessor = tmp_path / "m101.json"
    predecessor.write_bytes(_m101_t2_bytes())
    prior, incoming = _record_events()
    prior_path = _write(tmp_path / "prior.json", prior)
    incoming_path = _write(tmp_path / "incoming.json", incoming)

    u0_path = tmp_path / "u0.json"
    create = _successful(
        development.acquisition(
            capsules["acquisition"],
            "create-state",
            "--m101",
            str(predecessor),
            "--events",
            str(prior_path),
            "--out",
            str(u0_path),
        )
    )
    u0 = runtime.decode_state(u0_path.read_bytes())
    lookups = [
        {
            "case_id": f"development-process-policy-{index}",
            "carrier": event["carrier"],
            "slot": event["slot"],
            "expected_descriptor": copy.deepcopy(event["descriptor"]),
        }
        for index, event in enumerate([*prior, *incoming], start=1)
    ]
    demand_path = _write(
        tmp_path / "policy-demand.json",
        runtime.policy_demand("development_process_policy", incoming, lookups),
    )
    u1_path = tmp_path / "u1.json"
    acquire_policy = _successful(
        development.acquisition(
            capsules["acquisition"],
            "acquire-policy",
            "--state",
            str(u0_path),
            "--demand",
            str(demand_path),
            "--register",
            "--out",
            str(u1_path),
        )
    )
    assert acquire_policy["acquisition"]["adopted"]["body"] == [
        "LOAD_CARRIER",
        "LOAD_SLOT",
        "PAIR",
        "RETURN",
    ]

    sqlite_events_path = _write(tmp_path / "sqlite-events.json", _sqlite_events())
    pre_c_path = tmp_path / "pre-c.json"
    register = _successful(
        development.acquisition(
            capsules["acquisition"],
            "register-events",
            "--state",
            str(u1_path),
            "--events",
            str(sqlite_events_path),
            "--out",
            str(pre_c_path),
        )
    )
    cases = [
        _sqlite_case("development-process-sqlite-1", [{"id": 1, "name": "cobalt"}]),
        _sqlite_case(
            "development-process-sqlite-2",
            [{"id": 2, "name": "tin"}, {"id": 3, "name": "graphite"}],
        ),
    ]
    c_demand = runtime.c_demand(
        "development_process_c", ["prepare", "derive", "rename", "index"], cases
    )
    c_demand_path = _write(tmp_path / "c-demand.json", c_demand)
    u2_path = tmp_path / "u2.json"
    acquire_c = _successful(
        development.acquisition(
            capsules["acquisition"],
            "acquire-c",
            "--state",
            str(pre_c_path),
            "--demand",
            str(c_demand_path),
            "--register",
            "--out",
            str(u2_path),
        )
    )
    assert acquire_c["acquisition"]["symbolic_trace"]

    definition = _successful(
        development.definition_check(
            capsules["definition_checker"],
            "--state",
            str(u2_path),
            "--expected-m101-sha256",
            u0["m101_sha256"],
        )
    )
    assert definition["independent_of_m102_runtime_and_search"] is True
    sqlite_world_path = _write(
        tmp_path / "sqlite-world.json",
        {
            "schema": "m102-sqlite-execution-world-v1",
            "world_id": "development_process_sqlite_reuse",
            "slots": c_demand["slots"],
            "cases": cases,
        },
    )
    execute_sqlite = _successful(
        development.execution(
            capsules["execution"],
            "execute-sqlite",
            "--state",
            str(u2_path),
            "--world",
            str(sqlite_world_path),
        )
    )
    record_world_path = _write(
        tmp_path / "record-world.json",
        {
            "schema": "m102-record-execution-world-v1",
            "world_id": "development_process_retention",
            "carrier": "record_alpha",
            "slots": ["prepare", "finish"],
            "cases": [
                {
                    "case_id": "development-process-retention-1",
                    "input": {"raw": "live", "values": [7, 2]},
                    "expected": {"value": "live", "values": [2, 7]},
                }
            ],
        },
    )
    execute_record = _successful(
        development.execution(
            capsules["execution"],
            "execute-record",
            "--state",
            str(u2_path),
            "--world",
            str(record_world_path),
        )
    )

    scientific = [create, acquire_policy, register, acquire_c, execute_sqlite, execute_record]
    assert len({item["pid"] for item in scientific}) == len(scientific)
    for payload in scientific:
        assert payload["isolated_mode"] is True
        assert payload["model_calls"] == payload["network_calls"] == 0
        assert payload["remote_execution_calls"] == 0
        assert payload["imported_project_modules"] == []
        assert all(str(ROOT).lower() not in entry.lower() for entry in payload["search_path"])
    assert reports["execution"]["members"] == [
        "m101_executor.py",
        "m102_executor.py",
        "run.py",
    ]
