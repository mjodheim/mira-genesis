from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from scripts import audit_m102_boundaries
from scripts import check_m102_result as checker
from scripts import run_m102_qualification as runner
from scripts.author_m102_qualification_pool import load_pool


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


def test_no_m102_scientific_result_exists_before_freeze() -> None:
    assert not (ROOT / "experiments/M102/PROTOCOL.json").exists()
    assert not (ROOT / "experiments/M102/RESULT.json").exists()
    assert not (ROOT / "experiments/M102/CHECK_REPORT.json").exists()
