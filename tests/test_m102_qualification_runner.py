from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from metamorphosis import m102_runtime as runtime
from scripts import audit_m102_boundaries
from scripts import check_m102_result as checker
from scripts import build_m102_protocol as protocol_builder
from scripts import run_m102_qualification as runner
from scripts.author_m102_qualification_pool import load_pool
from scripts.author_m102_qualification_pool import digest


ROOT = Path(__file__).resolve().parents[1]


def test_m102_adversarial_source_audit_is_clean() -> None:
    report = audit_m102_boundaries.audit()
    assert report["passed"] is True
    assert report["failures"] == []
    assert len(report["checks"]) >= 25
    assert report["scientific_verdict"] is False


def test_canonical_materializer_refuses_without_both_owner_flags() -> None:
    with pytest.raises(runner.QualificationRefused, match="owner authorization"):
        runner.materialize(authorized_by_owner=False, understand_unique_attempt=True)
    with pytest.raises(runner.QualificationRefused, match="owner authorization"):
        runner.materialize(authorized_by_owner=True, understand_unique_attempt=False)


def test_draft_protocol_and_candidate_pool_cannot_arm_qualification() -> None:
    protocol = json.loads(
        (ROOT / "experiments/M102/PROTOCOL_DRAFT.json").read_text(encoding="utf-8")
    )
    pool = load_pool()
    with pytest.raises(runner.QualificationRefused, match="not frozen"):
        runner.require_frozen(protocol, pool)


def test_capsule_bindings_have_closed_expected_member_census() -> None:
    assert sorted(runner.CAPSULE_SOURCES["acquisition"]) == [
        "m101_runtime.py",
        "m102_runtime.py",
        "run.py",
    ]
    assert sorted(runner.CAPSULE_SOURCES["execution"]) == [
        "m101_executor.py",
        "m102_executor.py",
        "run.py",
    ]
    assert sorted(runner.CAPSULE_SOURCES["definition_checker"]) == [
        "check_m101_definitions.py",
        "check_m102_definitions.py",
    ]
    for sources in runner.CAPSULE_SOURCES.values():
        capsule_digest, members = runner.capsule_binding(sources)
        assert len(capsule_digest) == 64
        assert set(members) == set(sources)


def test_checker_owns_same_precommitted_projection_independently() -> None:
    value = {
        "pid": 10,
        "nested": {
            "search_path": ["ephemeral"],
            "elapsed_seconds": 1.2,
            "scientific": [1, {"started_at_utc": "ephemeral", "kept": "yes"}],
        },
    }
    expected = {"nested": {"scientific": [1, {"kept": "yes"}]}}
    assert runner.stable_projection(value) == expected
    assert checker.checker_stable_projection(value) == expected
    assert runner.stable_projection is not checker.checker_stable_projection


def test_result_checker_does_not_import_m102_implementation() -> None:
    source = (ROOT / "scripts/check_m102_result.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    imports.update(
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    )
    assert not imports & {"metamorphosis", "m102_runtime", "m102_executor"}
    assert all(f"check_p{index}" in checker.__dict__ for index in range(1, 16))


def test_protocol_candidate_is_exact_but_cannot_arm_a_run() -> None:
    candidate = protocol_builder.build_candidate()
    assert candidate["status"] == "owner_review_required"
    assert candidate["canonical_run_allowed"] is False
    assert candidate["attempt"] == 1
    assert candidate["qualification_population"]["pool_digest"] == load_pool()["pool_digest"]
    assert candidate["predecessor"]["m101_t2_raw_sha256"] == (
        "cd5b5994e5a252599807e9ddc2b5733efaf176fe23dd05055b50d883bde0b7a0"
    )
    assert candidate["freeze"]["owner_acceptance_required"] is True
    with pytest.raises(ValueError, match="source commit"):
        protocol_builder.build_final("not-a-commit", "not-authorized")


def test_no_m102_scientific_result_exists_before_freeze() -> None:
    assert not (ROOT / "experiments/M102/RESULT.json").exists()
    assert not (ROOT / "experiments/M102/CHECK_REPORT.json").exists()


def _cases(prefix: str, pairs: list[tuple[object, object]]) -> tuple[list[dict], list[dict]]:
    values = [
        {"case_id": f"development-{prefix}-{index}", "input": value, "expected": expected}
        for index, (value, expected) in enumerate(pairs, start=1)
    ]
    return values[:2], values[2:]


def _development_rehearsal_pool() -> dict:
    alpha_events = [
        runtime.registry_event(
            "development_alpha", "prepare", {"kind": "rename_key", "old": "raw", "new": "value"}
        ),
        runtime.registry_event(
            "development_alpha", "finish", {"kind": "sort_list", "key": "values"}
        ),
    ]
    gamma_events = [
        runtime.registry_event(
            "development_gamma", "gamma_prepare", {"kind": "drop_key", "key": "obsolete"}
        ),
        runtime.registry_event(
            "development_gamma",
            "gamma_finish",
            {"kind": "set_default", "key": "phase", "value": "ready"},
        ),
    ]
    theta_events = [
        runtime.registry_event(
            "development_theta",
            "theta_prepare",
            {"kind": "set_default", "key": "verified", "value": True},
        ),
        runtime.registry_event(
            "development_theta",
            "theta_finish",
            {"kind": "rename_key", "old": "entries", "new": "samples"},
        ),
    ]
    incoming = [
        runtime.registry_event(
            "development_beta", "prepare", {"kind": "drop_key", "key": "trash"}
        ),
        runtime.registry_event(
            "development_beta",
            "finish",
            {"kind": "set_default", "key": "status", "value": "queued"},
        ),
    ]
    record_specs = [
        (
            "development_record_alpha",
            "development_alpha",
            ["prepare", "finish"],
            alpha_events,
            [
                (
                    {"raw": f"a-{index}", "values": [index + 2, index]},
                    {"value": f"a-{index}", "values": [index, index + 2]},
                )
                for index in range(1, 5)
            ],
        ),
        (
            "development_record_gamma",
            "development_gamma",
            ["gamma_prepare", "gamma_finish"],
            gamma_events,
            [
                (
                    {"id": index, "obsolete": "remove"},
                    {"id": index, "phase": "ready"},
                )
                for index in range(5, 9)
            ],
        ),
        (
            "development_record_theta",
            "development_theta",
            ["theta_prepare", "theta_finish"],
            theta_events,
            [
                (
                    {"id": index, "entries": [index, index + 1]},
                    {"id": index, "samples": [index, index + 1], "verified": True},
                )
                for index in range(9, 13)
            ],
        ),
    ]
    records = []
    for world_id, carrier, slots, events, pairs in record_specs:
        public, hidden = _cases(world_id, pairs)
        records.append(
            {
                "id": world_id,
                "role": "record_retention",
                "carrier": carrier,
                "slots": slots,
                "events": events,
                "public_cases": public,
                "hidden_cases": hidden,
            }
        )
    relation = [*alpha_events, *gamma_events, *theta_events, *incoming]
    lookups = [
        {
            "case_id": f"development-policy-lookup-{index}",
            "carrier": event["carrier"],
            "slot": event["slot"],
            "expected_descriptor": event["descriptor"],
        }
        for index, event in enumerate(relation, start=1)
    ]
    policy = {
        "id": "development_policy_collision",
        "role": "policy_producer_trigger",
        "carrier": "registry",
        "incoming_events": incoming,
        "public_lookups": lookups[:4],
        "hidden_lookups": lookups[4:],
    }
    sqlite_events = [
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

    def sqlite_case(case_id: str, rows: list[dict]) -> dict:
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
                    {"id": row["id"], "label": row["name"], "priority": len(row["name"])}
                    for row in rows
                ],
                "indexes": [
                    {"name": "idx_items_label_priority", "columns": ["label", "priority"]}
                ],
            },
        }

    sqlite_cases = [
        sqlite_case(f"development-sqlite-trigger-{index}", [{"id": index, "name": name}])
        for index, name in enumerate(("mercury", "neon", "argon", "xenon"), start=1)
    ]
    sqlite_trigger = {
        "id": "development_sqlite_trigger",
        "role": "sqlite_c_trigger",
        "carrier": "sqlite",
        "slots": ["prepare", "derive", "rename", "index"],
        "events": sqlite_events,
        "public_cases": sqlite_cases[:2],
        "hidden_cases": sqlite_cases[2:],
    }
    reuse_cases = [
        sqlite_case(f"development-sqlite-reuse-{index}", [{"id": 20 + index, "name": name}])
        for index, name in enumerate(("copper", "silver", "gold", "platinum"), start=1)
    ]
    sqlite_reuse = {
        "id": "development_sqlite_reuse",
        "role": "sqlite_c_reuse",
        "carrier": "sqlite",
        "slots": ["prepare", "derive", "rename", "index"],
        "public_cases": reuse_cases[:2],
        "hidden_cases": reuse_cases[2:],
    }
    text_pairs = [
        (value, value.replace("_", " ").upper())
        for value in ("red_ore", "blue_ash", "green_moss", "white_sand")
    ]
    text_public, text_hidden = _cases("m101-a", text_pairs)
    m101_a = {
        "id": "development_m101_a",
        "role": "m101_a_conservation",
        "carrier": "text",
        "catalog": [
            {"kind": "upper"},
            {"kind": "prefix", "value": "unused"},
            {"kind": "replace", "old": "_", "new": " "},
        ],
        "public_cases": text_public,
        "hidden_cases": text_hidden,
    }
    syntax_pairs = []
    for index in range(1, 5):
        source = f"def raw_signal(datum):\n    return datum + {index}"
        expected = (
            "def sealed_signal(reading):\n"
            f"    return abs(reading + {index})"
        )
        syntax_pairs.append((source, expected))
    syntax_public, syntax_hidden = _cases("m101-b", syntax_pairs)
    m101_b = {
        "id": "development_m101_b",
        "role": "m101_b_conservation",
        "carrier": "syntax",
        "catalog": [
            {
                "kind": "rename_argument",
                "function": "sealed_signal",
                "old": "datum",
                "new": "reading",
            },
            {"kind": "rename_function", "old": "raw_signal", "new": "sealed_signal"},
            {"kind": "wrap_return", "call": "abs"},
            {"kind": "add_docstring", "text": "excluded formatting distractor"},
        ],
        "public_cases": syntax_public,
        "hidden_cases": syntax_hidden,
    }
    numeric_pairs = [
        ({"left": left, "right": right}, left - right)
        for left, right in ((4, 1), (8, 3), (-2, 5), (9, -4))
    ]
    numeric_public, numeric_hidden = _cases("m100", numeric_pairs)
    m100 = {
        "id": "development_m100_subtraction",
        "role": "m100_conservation",
        "carrier": "m100",
        "operation_index": 0,
        "public_cases": numeric_public,
        "hidden_cases": numeric_hidden,
    }
    worlds = [policy, *records, sqlite_trigger, sqlite_reuse, m101_a, m101_b, m100]
    entries = []
    for world in worlds:
        entry = {"world": world}
        entry["entry_digest"] = digest(entry)
        entries.append(entry)
    return {
        "schema": "m102-development-rehearsal-pool-v1",
        "milestone": "M102-DEVELOPMENT",
        "status": "development",
        "population_size": len(entries),
        "role_counts": {
            "policy_producer_trigger": 1,
            "record_retention": 3,
            "sqlite_c_trigger": 1,
            "sqlite_c_reuse": 1,
            "m101_a_conservation": 1,
            "m101_b_conservation": 1,
            "m100_conservation": 1,
        },
        "entries": entries,
    }


def test_full_runner_rehearses_only_on_development_population() -> None:
    pool = _development_rehearsal_pool()
    evidence = runner.run_experiment(pool)
    assert evidence["states"]["U2"]["c_definition_id"]
    assert all(row["fresh"]["runtime"]["confirmed"] for row in evidence["sqlite_execution"])
    assert all(
        row["fresh"]["runtime"]["confirmed"]
        for row in evidence["continual_retention_after_u2"]
    )
    assert evidence["rollback"]["restored_bytes_equal"] is True
    assert all(
        row["runtime"]["confirmed"] is False
        for row in evidence["causal_controls"]["c_executions"].values()
    )
    assert all(
        row["runtime"]["confirmed"] is True
        for row in evidence["causal_controls"]["unrelated_capabilities"].values()
    )
    assert evidence["state_chronology"]["c_absent_without_k_reach"]["runtime"][
        "acquisition"
    ]["reason"] == "joint registered descriptors are unrepresentable by the live policy"
    assert evidence["process_boundary"]["all_invocations_isolated"] is True
    assert evidence["process_boundary"]["zero_model_calls"] is True
    replay = runner.run_experiment(pool)
    assert digest(runner.stable_projection(replay)) == digest(
        runner.stable_projection(evidence)
    )
    assert not (ROOT / "experiments/M102/RESULT.json").exists()
