from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest

from scripts import run_m101_qualification as runner
from scripts import check_m101_result as checker
from scripts.audit_m101_boundaries import audit as audit_boundaries
from scripts.author_m101_qualification_pool import digest


def _case(prefix: str, index: int, value: Any, expected: Any) -> dict[str, Any]:
    return {"case_id": f"{prefix}-{index}", "input": value, "expected": expected}


def _split(prefix: str, pairs: list[tuple[Any, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    cases = [_case(prefix, index, value, expected) for index, (value, expected) in enumerate(pairs, 1)]
    return cases[:4], cases[4:]


def _worlds() -> list[dict[str, Any]]:
    worlds = []
    text_values = ["  ash ", " pine\n", "\tiron", "ore ", "  tin", "lead  ", " zinc ", "\ngold"]
    public, hidden = _split("dev-producer", [(value, value.strip().upper()) for value in text_values])
    worlds.append({
        "id": "development_runner_producer", "role": "producer_trigger", "carrier": "text",
        "catalog": [{"kind": "strip"}, {"kind": "upper"}, {"kind": "suffix", "value": "!"}],
        "public_cases": public, "hidden_cases": hidden,
    })
    values = ["A", "B", "C", "D", "E", "F", "G", "H"]
    public, hidden = _split("dev-text", [(value, value.lower() + ".") for value in values])
    worlds.append({
        "id": "development_runner_text", "role": "text_holdout", "carrier": "text",
        "catalog": [{"kind": "suffix", "value": "."}, {"kind": "lower"}, {"kind": "prefix", "value": "x"}],
        "public_cases": public, "hidden_cases": hidden,
    })
    lists = [[3, 1], [0, -2], [8, 4], [], [9, 2], [1], [-3, -7], [5, 5, 2]]
    record_pairs = [({"raw": value, "tag": index}, {"values": sorted(value), "tag": index}) for index, value in enumerate(lists)]
    public, hidden = _split("dev-record", record_pairs)
    worlds.append({
        "id": "development_runner_record", "role": "record_transfer", "carrier": "record",
        "catalog": [{"kind": "rename_key", "old": "raw", "new": "values"}, {"kind": "sort_list", "key": "values"}, {"kind": "drop_key", "key": "tag"}],
        "public_cases": public, "hidden_cases": hidden,
    })
    expressions = ["x + 1", "x - 2", "x * 3", "-x", "x // 2", "x + 8", "x * x", "x - 4"]
    syntax_pairs = [
        (f"def rough(x):\n    return {expression}", f"def clean(value):\n    return {expression.replace('x', 'value')}")
        for expression in expressions
    ]
    public, hidden = _split("dev-syntax", syntax_pairs)
    worlds.append({
        "id": "development_runner_syntax", "role": "syntax_transfer", "carrier": "syntax",
        "catalog": [{"kind": "rename_function", "old": "rough", "new": "clean"}, {"kind": "rename_argument", "function": "clean", "old": "x", "new": "value"}, {"kind": "add_docstring", "text": "x"}],
        "public_cases": public, "hidden_cases": hidden,
    })
    b_pairs = [
        (f"def draft(x):\n    return {expression}", f"def published(value):\n    return {expression.replace('x', 'value')}")
        for expression in expressions
    ]
    public, hidden = _split("dev-b", b_pairs)
    worlds.append({
        "id": "development_runner_b", "role": "b_reuse", "carrier": "syntax",
        "catalog": [{"kind": "rename_function", "old": "draft", "new": "stage"}, {"kind": "rename_argument", "function": "stage", "old": "x", "new": "value"}, {"kind": "rename_function", "old": "stage", "new": "published"}, {"kind": "add_docstring", "text": "x"}],
        "public_cases": public, "hidden_cases": hidden,
    })
    numeric = [(8, 3), (4, 4), (-2, 5), (0, -1), (9, 2), (-3, -6), (1, 7), (5, -4)]
    for name, operation_index, signature in (
        ("sub", 0, (1, -1)), ("add", 1, (1, 1)), ("weighted", 2, (1, 2))
    ):
        public, hidden = _split(
            f"dev-m100-{name}",
            [({"left": left, "right": right}, signature[0] * left + signature[1] * right) for left, right in numeric],
        )
        worlds.append({
            "id": f"development_runner_m100_{name}", "role": "m100_conservation", "carrier": "m100",
            "operation_index": operation_index, "public_cases": public, "hidden_cases": hidden,
        })
    return worlds


def _development_pool() -> dict[str, Any]:
    entries = []
    for world in _worlds():
        entry = {"world": world}
        entry["entry_digest"] = digest(entry)
        entries.append(entry)
    return {"status": "development", "entries": entries}


def test_boundary_audit_closes_all_pre_run_source_checks() -> None:
    report = audit_boundaries()
    assert report["passed"] is True
    assert report["failures"] == []
    assert all(report["checks"].values())


def test_projection_removes_only_the_recursive_frozen_ephemera() -> None:
    value = {
        "pid": 1,
        "process_pids": [1, 2],
        "search_path": ["temporary"],
        "nested": {"pid": 3, "confirmed": True},
        "fresh_process_invocations": 4,
    }
    assert runner.stable_projection(value) == {
        "nested": {"confirmed": True},
        "fresh_process_invocations": 4,
    }


def test_frozen_population_cannot_cross_the_boundary_without_armed_materialize() -> None:
    with pytest.raises(runner.QualificationRefused, match="frozen M101 population"):
        runner.run_experiment({"status": "frozen", "entries": []})
    with pytest.raises(runner.QualificationRefused, match="requires --arm"):
        runner.materialize()


def test_complete_development_chronology_crosses_fresh_processes_and_controls() -> None:
    evidence = runner.run_experiment(_development_pool())
    assert evidence["boundary_audit"]["passed"] is True
    assert evidence["states"]["m100_bytes_conserved"] is True
    assert evidence["states"]["t1_prefix_conserved_in_t2"] is True
    assert evidence["state_chronology"]["t0_unchanged_after_a_build"] is True
    assert evidence["state_chronology"]["t1_unchanged_after_b_build"] is True
    assert evidence["state_chronology"]["b_absent_without_a"]["returncode"] == 1
    assert all(row["fresh"]["runtime"]["confirmed"] for row in evidence["a_reuse"])
    assert all(row["fresh"]["runtime"]["confirmed"] for row in evidence["b_reuse"])
    assert all(row["fresh"]["runtime"]["confirmed"] for row in evidence["m100_conservation"])
    assert all(
        row["fresh"]["runtime"]["execution"]["reachable"] is False
        for row in evidence["fresh_baselines"]
    )
    assert evidence["baseline_parity"]["only_permitted_causal_difference"] is True
    assert evidence["baseline_parity"]["arm_difference"]["differing_state_keys"] == [
        "definitions", "state_digest"
    ]
    assert all(
        row["same_executor_capsule"]
        and row["same_action"]
        and row["same_world_payload_digest"]
        for row in evidence["baseline_parity"]["rows"]
    )
    controls = evidence["dependency_controls"]
    assert all(row["runtime"]["confirmed"] is False for row in controls["fault_breaks_all_b_worlds"])
    assert controls["ablate_a"]["runtime"]["failed_closed"] is True
    assert controls["ablate_b"]["runtime"]["failed_closed"] is True
    assert controls["a_survives_b_ablation"]["runtime"]["confirmed"] is True
    assert controls["corrupt_state"]["runtime"]["failed_closed"] is True
    assert evidence["rollback"]["restored_bytes_equal"] is True
    assert evidence["rollback"]["after_restore"]["runtime"]["confirmed"] is True
    process = evidence["process_boundary"]
    assert process["all_invocations_isolated"] is True
    assert process["all_invocation_ordinals_unique_and_contiguous"] is True
    assert process["synchronous_process_exit_before_next_launch"] is True
    assert process["fresh_subprocess_launch_source_audited"] is True
    assert process["no_project_modules_imported"] is True
    assert process["repository_absent_from_search_paths"] is True
    development_pool = _development_pool()
    for condition in (
        checker.check_p3(evidence, development_pool),
        checker.check_p4(evidence),
        checker.check_p5(evidence),
        checker.check_p6(evidence),
        checker.check_p8(evidence),
        checker.check_p9(evidence),
        checker.check_p10(evidence),
        checker.check_p11(evidence),
        checker.check_p13(evidence),
        checker.check_p14(evidence),
    ):
        assert condition.passed is True, condition.failures


def test_checker_rejects_baseline_parity_shortcuts_even_if_summary_bit_is_forged() -> None:
    evidence = runner.run_experiment(_development_pool())

    different_executor = deepcopy(evidence)
    different_executor["baseline_parity"]["rows"][0]["same_executor_capsule"] = False
    different_executor["baseline_parity"]["only_permitted_causal_difference"] = True
    condition = checker.check_p8(different_executor)
    assert condition.passed is False
    assert "matched-budget structural closure changed" in condition.failures

    extra_state_difference = deepcopy(evidence)
    extra_state_difference["baseline_parity"]["arm_difference"]["differing_state_keys"] = [
        "definitions", "m100_ascii", "state_digest"
    ]
    extra_state_difference["baseline_parity"]["only_permitted_causal_difference"] = True
    condition = checker.check_p8(extra_state_difference)
    assert condition.passed is False
    assert "baseline/retained state diff is not exactly A plus its digest" in condition.failures
