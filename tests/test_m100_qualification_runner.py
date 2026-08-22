from __future__ import annotations

import json

import pytest

from scripts import run_m100_qualification as runner
from scripts.author_m100_qualification_pool import (
    COMPONENT,
    build_world,
    canonical_json,
    digest,
    load_pool,
    write_cases,
)


def test_runner_refuses_without_arming() -> None:
    with pytest.raises(runner.QualificationRefused, match="requires --arm"):
        runner.materialize()


def test_runner_refuses_draft_protocol() -> None:
    protocol = {
        "status": "draft",
        "qualification_population": {"pool_digest": load_pool()["pool_digest"]},
    }
    with pytest.raises(runner.QualificationRefused, match="not frozen"):
        runner.require_frozen(protocol, load_pool())


def test_projection_removes_the_complete_frozen_ephemera_set_recursively() -> None:
    value = {
        "pid": 1,
        "process_pids": [2, 3],
        "search_path": ["temporary"],
        "nested": {"pid": 4, "confirmed": True},
        "facts": {"fresh_process_invocations": 4},
    }
    assert runner.stable_projection(value) == {
        "nested": {"confirmed": True},
        "facts": {"fresh_process_invocations": 4},
    }


def test_isolated_development_chain_migrates_acquires_and_executes(tmp_path) -> None:
    capsule, members = runner._capsule(tmp_path)
    assert sorted(members) == ["m100_runtime.py", "run.py"]
    m097 = json.loads(runner.M097_RESULT_PATH.read_text(encoding="utf-8"))
    source = tmp_path / "m097.json"
    source.write_bytes(canonical_json(
        m097["scientific_evidence"]["extended_language_state"]
    ).encode("ascii"))
    s1 = tmp_path / "S1.json"
    s2 = tmp_path / "S2.json"
    s3 = tmp_path / "S3.json"
    migration = runner._migrate(capsule, source, s1)
    acquired_b = runner._acquire(capsule, s1, (1, 1), 4, output=s2)
    acquired_c = runner._acquire(capsule, s2, (1, 2), 5, output=s3)
    assert migration["runtime"]["confirmed"] is True
    assert acquired_b["runtime"]["confirmed"] is True
    assert acquired_c["runtime"]["confirmed"] is True
    assert len({
        migration["runtime"]["pid"], acquired_b["runtime"]["pid"],
        acquired_c["runtime"]["pid"],
    }) == 3
    for row in (migration, acquired_b, acquired_c):
        assert row["runtime"]["isolated_mode"] is True
        assert row["runtime"]["imported_project_modules"] == []

    entry = {
        "id": "development_weighted_probe",
        "cycle": "C",
        "class": "DevelopmentPair",
        "key": "weighted",
        "left_field": "base",
        "right_field": "increment",
        "signature": [1, 2],
        "fields": [
            {"name": "base", "annotation": "int"},
            {"name": "increment", "annotation": "int"},
            {"name": "label", "annotation": "str"},
        ],
        "cases": [
            {"base": 2, "increment": 3, "label": "a"},
            {"base": -1, "increment": 4, "label": "b"},
            {"base": 5, "increment": -2, "label": "c"},
            {"base": 0, "increment": 0, "label": "d"},
        ],
        "caller_count": 1,
    }
    world = build_world(tmp_path / "development-world", entry)
    cases = write_cases(world / "cases.json", entry)
    state = json.loads(s3.read_text(encoding="ascii"))
    operation_id = state["operations"][2]["operation_id"]
    execution = runner._execute(capsule, s3, operation_id, world, cases)
    assert execution["returncode"] == 0
    assert execution["runtime"]["confirmed"] is True
    assert execution["runtime"]["execution"]["cases_passed"] == 4


def test_digest_valid_b_fault_suppresses_c_acquisition() -> None:
    from metamorphosis import m100_runtime as runtime

    m097 = json.loads(runner.M097_RESULT_PATH.read_text(encoding="utf-8"))
    s1 = runtime.migrate_m097_state(canonical_json(
        m097["scientific_evidence"]["extended_language_state"]
    ).encode("ascii"))
    s2 = runtime.acquire(s1, (1, 1), 4, register=True)["next_state"]
    a_id = s2["operations"][0]["operation_id"]
    faulty = runner._rewrite_chain(
        s2, 1, ["PUSH_LEFT", "PUSH_RIGHT", f"CALL:{a_id}"]
    )
    runtime.decode_state(runtime.canonical_json(faulty).encode("ascii"))
    assert runtime.acquire(faulty, (1, 2), 5, register=False)["accepted_candidates"] == 0


def test_complete_development_process_attack_exercises_faults_and_rollback() -> None:
    entries = []
    specifications = (
        ("A", [1, -1], "DevelopmentSubtract", "difference"),
        ("B", [1, 1], "DevelopmentAdd", "combined"),
        ("C", [1, 2], "DevelopmentWeighted", "weighted"),
    )
    for cycle, signature, class_name, key in specifications:
        entry = {
            "id": f"development_attack_{cycle.lower()}",
            "cycle": cycle,
            "class": class_name,
            "key": key,
            "left_field": "left_value",
            "right_field": "right_value",
            "signature": signature,
            "fields": [
                {"name": "label", "annotation": "str"},
                {"name": "right_value", "annotation": "int"},
                {"name": "left_value", "annotation": "int"},
            ],
            "cases": [
                {"label": "a", "right_value": 3, "left_value": 8},
                {"label": "b", "right_value": 0, "left_value": 4},
                {"label": "c", "right_value": -2, "left_value": 1},
                {"label": "d", "right_value": 5, "left_value": -3},
            ],
            "caller_count": 2,
        }
        entry["entry_digest"] = digest(entry)
        entries.append(entry)
    evidence = runner.run_experiment({"entries": entries})
    assert evidence["process_boundary"]["fresh_process_invocations"] == 18
    assert evidence["process_boundary"]["all_invocations_isolated"] is True
    assert all(row["fresh"]["runtime"]["confirmed"] for row in evidence["fresh_worlds_after_s3"])
    controls = evidence["dependency_controls"]
    assert controls["mutate_a_breaks_b"]["runtime"]["confirmed"] is False
    assert controls["mutate_b_breaks_c"]["runtime"]["confirmed"] is False
    assert controls["ablate_a"]["runtime"]["failed_closed"] is True
    assert controls["ablate_b"]["runtime"]["failed_closed"] is True
    assert controls["corrupt_digest"]["runtime"]["failed_closed"] is True
    assert evidence["rollback"]["during_fault"]["runtime"]["confirmed"] is False
    assert evidence["rollback"]["restored_bytes_equal"] is True
    assert evidence["rollback"]["restored_s3_equals_original"] is True
