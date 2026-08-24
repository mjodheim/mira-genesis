from __future__ import annotations

import ast
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import audit_m104_freshness as freshness
from scripts import author_m104_qualification_pool as author
from scripts import check_m104_result as checker
from scripts import build_m104_protocol as protocol_builder
from scripts import run_m104_qualification as runner


ROOT = Path(__file__).resolve().parents[1]
POOL = ROOT / "experiments" / "M104" / "QUALIFICATION_POOL.json"
RESULT = ROOT / "experiments" / "M104" / "RESULT.json"
REPORT = ROOT / "experiments" / "M104" / "CHECK_REPORT.json"


def test_fresh_pool_is_exact_complete_and_not_executed() -> None:
    raw = POOL.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == runner.POOL_RAW_SHA256
    assert raw == runner.canonical_json(author.build_pool()).encode("ascii") + b"\n"
    pool = json.loads(raw)
    report = runner.verify_pool(pool)
    assert report["confirmed"] is True
    assert pool["pool_digest"] == runner.POOL_DIGEST
    assert pool["record_count"] == 11
    assert pool["hidden_case_count"] == 16
    assert not RESULT.exists()
    assert not REPORT.exists()


def test_freshness_audit_closes_every_named_identity_category() -> None:
    report = freshness.audit()
    assert report["confirmed"] is True
    assert report["overlaps"] == {
        "ids": [],
        "contexts": [],
        "descriptors": [],
        "initials": [],
    }


def test_exact_direct_script_entrypoint_works_from_another_directory_without_data_access() -> None:
    before = POOL.read_bytes()
    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_m104_result.py"), "--entrypoint-preflight"],
        cwd=ROOT / "experiments" / "M104",
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
    report = json.loads(completed.stdout)
    assert report["confirmed"] is True
    assert report["runner_imported"] is True
    assert report["repository_root_resolved"] is True
    assert "repository_root" not in report
    assert report["qualification_pool_opened"] is False
    assert report["result_opened"] is False
    assert report["report_opened"] is False
    assert POOL.read_bytes() == before
    assert not RESULT.exists()
    assert not REPORT.exists()


def test_entrypoint_preflight_call_surface_does_not_open_scientific_paths() -> None:
    source = (ROOT / "scripts" / "check_m104_result.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    function = next(
        node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "entrypoint_preflight"
    )
    call_names = {
        node.func.attr if isinstance(node.func, ast.Attribute) else node.func.id
        for node in ast.walk(function)
        if isinstance(node, ast.Call) and isinstance(node.func, (ast.Attribute, ast.Name))
    }
    assert not ({"open", "read_text", "read_bytes"} - {"read_bytes"}) & call_names
    assert "read_text" not in call_names
    assert "open" not in call_names
    assert "run_experiment" not in call_names


def test_m103_frozen_mechanism_members_remain_exact() -> None:
    protocol = json.loads((ROOT / "experiments" / "M103" / "PROTOCOL.json").read_text(encoding="ascii"))
    assert protocol["protocol_digest"] == runner.M103_PROTOCOL_DIGEST
    for group in ("mechanism", "checker"):
        for path, expected in protocol["bound_files"][group]["member_digests"].items():
            assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected


def test_closed_m103_artifacts_are_not_reused_or_changed() -> None:
    assert hashlib.sha256((ROOT / "experiments" / "M103" / "RESULT.json").read_bytes()).hexdigest() == (
        "6d89f26f994124ef7207ed1c580a7a72cd468a83d3f8787c1085a5b8e062ff26"
    )
    assert not (ROOT / "experiments" / "M103" / "CHECK_REPORT.json").exists()
    failure = json.loads(
        (ROOT / "experiments" / "M103" / "CHECKER_FAILURE.json").read_text(encoding="ascii")
    )
    assert failure["scientific_verdict"] == "negative"
    assert failure["rerun_or_post_verdict_repair_allowed"] is False


def test_canonical_materialization_remains_denied_without_owner_authorization() -> None:
    with pytest.raises(runner.QualificationRefused, match="owner authorization"):
        runner.materialize(authorized_by_owner=False, understand_unique_attempt=False)
    assert not RESULT.exists()


def test_checker_predicate_logic_is_frozen_and_runtime_independent() -> None:
    source = Path(checker.__file__).read_text(encoding="utf-8")
    assert "from metamorphosis import m103_runtime" not in source
    assert "predicate_checker.evaluate_conditions" in source
    assert checker.EXPECTED_PREDICATES == [f"P{index}" for index in range(1, 16)]


def test_finalization_has_a_read_only_candidate_commit_validator() -> None:
    source = Path(protocol_builder.__file__).read_text(encoding="utf-8")
    assert "def validate_candidate_commit" in source
    assert "candidate commit must contain only the candidate artifact" in source
    assert "working candidate differs from its committed blob" in source
    assert "owner-review candidate tag does not resolve to HEAD" in source
    assert "candidate_source_ref" in source
    assert '"candidate_source_commit"' not in source
