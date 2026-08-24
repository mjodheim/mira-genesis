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
PROTOCOL = ROOT / "experiments" / "M104" / "PROTOCOL.json"
RESULT = ROOT / "experiments" / "M104" / "RESULT.json"
REPORT = ROOT / "experiments" / "M104" / "CHECK_REPORT.json"
RESULT_DIGEST = "f2be4d8516207187f0892eb6c8cecd0f648563456f33aa07fe13787b0e867de3"
RESULT_RAW_SHA256 = "74723305da4899bc8b716363b6a393f7efe33eb772a8479d2f7b504544789935"
STABLE_EVIDENCE_DIGEST = "9f2d175866d766ae530b1015e5b3ff7fbd42ab939a421a67c1b333e1106d274f"
REPORT_DIGEST = "7032528b7c3234d5f3e759dbdda2d1fbdaa0d29fb28f3160602ca68915fe836d"
REPORT_RAW_SHA256 = "90037f262c99fb745240f4dfe3fe920a118e29060bf04a7b455337fce8aec242"


def _git(*arguments: str, binary: bool = False) -> str | bytes:
    completed = subprocess.run(
        ["git", *arguments], cwd=ROOT, capture_output=True, text=not binary, check=True
    )
    return completed.stdout if binary else completed.stdout.strip()


def test_fresh_pool_and_preserved_evidence_are_exact() -> None:
    raw = POOL.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == runner.POOL_RAW_SHA256
    with pytest.raises(RuntimeError, match="cannot be authored after a result exists"):
        author.build_pool()
    pool = json.loads(raw)
    report = runner.verify_pool(pool)
    assert report["confirmed"] is True
    assert pool["pool_digest"] == runner.POOL_DIGEST
    assert pool["record_count"] == 11
    assert pool["hidden_case_count"] == 16
    assert hashlib.sha256(RESULT.read_bytes()).hexdigest() == RESULT_RAW_SHA256
    assert hashlib.sha256(REPORT.read_bytes()).hexdigest() == REPORT_RAW_SHA256


def test_freshness_audit_closes_every_named_identity_category() -> None:
    report = freshness.audit()
    assert report["confirmed"] is False
    assert report["checks"]["canonical_evidence_absent"] is False
    assert all(
        value is True
        for key, value in report["checks"].items()
        if key != "canonical_evidence_absent"
    )
    assert report["overlaps"] == {
        "ids": [],
        "contexts": [],
        "descriptors": [],
        "initials": [],
    }


def test_exact_direct_script_entrypoint_works_from_another_directory_without_data_access() -> None:
    before = POOL.read_bytes()
    result_before = RESULT.read_bytes()
    report_before = REPORT.read_bytes()
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
    assert RESULT.read_bytes() == result_before
    assert REPORT.read_bytes() == report_before


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
    for path in protocol_builder.INHERITED_ORCHESTRATION_FILES[:3]:
        expected = protocol["bound_files"]["apparatus"]["member_digests"][path]
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected
    assert hashlib.sha256((ROOT / "experiments/M102/RESULT.json").read_bytes()).hexdigest() == (
        protocol["predecessor"]["result_raw_sha256"]
    )
    assert hashlib.sha256((ROOT / "experiments/M102/CHECK_REPORT.json").read_bytes()).hexdigest() == (
        protocol["predecessor"]["checker_raw_sha256"]
    )


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
    before = RESULT.read_bytes()
    with pytest.raises(runner.QualificationRefused, match="owner authorization"):
        runner.materialize(authorized_by_owner=False, understand_unique_attempt=False)
    assert RESULT.read_bytes() == before


def test_positive_result_report_and_history_are_preserved_exactly() -> None:
    protocol = json.loads(PROTOCOL.read_text(encoding="ascii"))
    result = json.loads(RESULT.read_text(encoding="ascii"))
    report = json.loads(REPORT.read_text(encoding="ascii"))
    result_payload = {key: value for key, value in result.items() if key != "result_digest"}
    report_payload = {key: value for key, value in report.items() if key != "report_digest"}
    assert result["result_digest"] == runner.digest(result_payload) == RESULT_DIGEST
    assert result["stable_evidence_digest"] == STABLE_EVIDENCE_DIGEST
    assert result["protocol_digest"] == protocol["protocol_digest"]
    assert result["pool_digest"] == runner.POOL_DIGEST
    assert report["report_digest"] == runner.digest(report_payload) == REPORT_DIGEST
    assert report["result_digest"] == RESULT_DIGEST
    assert report["stable_evidence_digest"] == STABLE_EVIDENCE_DIGEST
    assert report["replay_stable_evidence_digest"] == STABLE_EVIDENCE_DIGEST
    assert report["verdict"] == "positive"
    assert report["scientific_verdict"] is True
    assert report["passed"] == 15
    assert report["failed"] == report["uncomputed"] == 0
    assert report["failed_predicates"] == []
    assert report["conditions"] == {f"P{index}": True for index in range(1, 16)}
    assert report["replay_performed"] is report["replay_equal"] is True
    assert report["protocol_boundary_confirmed"] is True
    assert report["result_boundary_confirmed"] is True
    assert result["model_calls"] == result["network_calls"] == result["remote_execution_calls"] == 0

    freeze_commit = _git("rev-list", "-n", "1", "experiment/m104-frozen-protocol-v1")
    first_commit = _git("rev-list", "-n", "1", "experiment/m104-canonical-first-result")
    positive_commit = _git("rev-list", "-n", "1", "experiment/m104-positive-result")
    assert _git("cat-file", "-t", "experiment/m104-canonical-first-result") == "tag"
    assert _git("cat-file", "-t", "experiment/m104-positive-result") == "tag"
    assert _git("rev-parse", f"{first_commit}^") == freeze_commit
    assert _git("rev-parse", f"{positive_commit}^") == first_commit
    assert _git("diff-tree", "--no-commit-id", "--name-only", "-r", first_commit) == (
        "experiments/M104/RESULT.json"
    )
    assert _git("diff-tree", "--no-commit-id", "--name-only", "-r", positive_commit) == (
        "experiments/M104/CHECK_REPORT.json"
    )
    assert _git("show", f"{first_commit}:experiments/M104/RESULT.json", binary=True) == RESULT.read_bytes()
    assert _git("show", f"{positive_commit}:experiments/M104/CHECK_REPORT.json", binary=True) == (
        REPORT.read_bytes()
    )


def test_positive_tag_preserves_every_frozen_causal_file() -> None:
    protocol = json.loads(PROTOCOL.read_text(encoding="ascii"))
    reference = "experiment/m104-positive-result"
    bindings = [protocol["m104_bound_files"]]
    bindings.extend(protocol["m103_exact_binding"]["bound_files"].values())
    for binding in bindings:
        for path, expected in binding["member_digests"].items():
            preserved = _git("show", f"{reference}:{path}", binary=True)
            assert hashlib.sha256(preserved).hexdigest() == expected


def test_checker_predicate_logic_is_frozen_and_runtime_independent() -> None:
    source = Path(checker.__file__).read_text(encoding="utf-8")
    assert "from metamorphosis import m103_runtime" not in source
    assert "predicate_checker.evaluate_conditions" in source
    assert checker.EXPECTED_PREDICATES == [f"P{index}" for index in range(1, 16)]
    assert "def verify_result_boundary" in source
    assert "first-result commit must contain only RESULT.json" in source
    assert "working result differs from its committed blob" in source
    assert "freeze commit must contain only PROTOCOL.json" in source
    assert "candidate commit must contain only PROTOCOL_CANDIDATE.json" in source
    assert "candidate parent is not its bound source tag" in source
    assert "must be an annotated tag" in source
    assert "result_boundary_confirmed" in source
    assert "protocol_boundary_confirmed" in source
    assert "protocol identity or digest mismatch" in source
    assert "qualification pool identity or digest mismatch" in source
    assert "protocol candidate identity or digest mismatch" in source
    assert "protocol qualification pool binding mismatch" in source
    assert checker.EXPECTED_POOL_DIGEST == runner.POOL_DIGEST
    assert checker.EXPECTED_POOL_RAW_SHA256 == runner.POOL_RAW_SHA256
    assert checker.EXPECTED_M104_FILES == protocol_builder.M104_FILES
    assert checker.EXPECTED_INHERITED_ORCHESTRATION_FILES == (
        protocol_builder.INHERITED_ORCHESTRATION_FILES
    )


def test_finalization_has_a_read_only_candidate_commit_validator() -> None:
    source = Path(protocol_builder.__file__).read_text(encoding="utf-8")
    assert "def validate_candidate_commit" in source
    assert "candidate commit must contain only the candidate artifact" in source
    assert "working candidate differs from its committed blob" in source
    assert "owner-review candidate tag does not resolve to HEAD" in source
    assert "candidate_source_ref" in source
    assert '"candidate_source_commit"' not in source
    assert "must be an annotated tag" in source


def test_canonical_preflight_verifies_every_freeze_blob_and_path() -> None:
    source = Path(runner.__file__).read_text(encoding="utf-8")
    assert "def _verify_file_binding" in source
    assert "qualification pool raw bytes changed" in source
    assert "protocol candidate raw bytes changed" in source
    assert "M103 {name}" in source
    assert "freeze commit must contain only the final protocol" in source
    assert "must be an annotated tag" in source
    assert "protocol candidate identity or digest mismatch" in source
    assert "final protocol changed accepted candidate field" in source
    assert "accepted candidate commit contains other changes" in source
    assert "working protocol differs from its frozen blob" in source
    assert runner.EXPECTED_M104_FILES == protocol_builder.M104_FILES
    assert runner.EXPECTED_INHERITED_ORCHESTRATION_FILES == (
        protocol_builder.INHERITED_ORCHESTRATION_FILES
    )
    assert 'for name in ("mechanism", "checker", "inherited_orchestration")' in source
