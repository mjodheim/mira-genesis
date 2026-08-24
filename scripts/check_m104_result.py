"""Independent M104 checker with a directly executable repository entry point."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import check_m103_result as predicate_checker  # noqa: E402


EXPERIMENT = ROOT / "experiments" / "M104"
RESULT_PATH = EXPERIMENT / "RESULT.json"
REPORT_PATH = EXPERIMENT / "CHECK_REPORT.json"
PROTOCOL_PATH = EXPERIMENT / "PROTOCOL.json"
POOL_PATH = EXPERIMENT / "QUALIFICATION_POOL.json"
EXPECTED_PREDICATES = [f"P{index}" for index in range(1, 16)]
EXPECTED_M103_PROTOCOL_DIGEST = "cb21a4fa29d9895e477d12f6710eaa4f7c70dfca2e740812fe6846c4ff530de9"
EXPECTED_POOL_DIGEST = "a84fa3c5f9c2db51f31f83fa1b910c48f919bdc5c203d548833a7311d7bf1dad"
EXPECTED_POOL_RAW_SHA256 = "732e2f46eefef4223e5a715db385639f43ceacf00b27e7c83dff9c15fbf8eb62"
M103_PROTOCOL_PATH = ROOT / "experiments" / "M103" / "PROTOCOL.json"
EXPECTED_M104_FILES = [
    ".gitattributes",
    "experiments/M104/README.md",
    "experiments/M104/PRE_REGISTRATION.md",
    "experiments/M104/PROTOCOL_DRAFT.json",
    "experiments/M104/QUALIFICATION_POOL.json",
    "experiments/M104/ADVERSARIAL_REVIEW.md",
    "docs/IP_REVIEWS/M104_PUBLICATION_REVIEW.md",
    "scripts/author_m104_qualification_pool.py",
    "scripts/audit_m104_freshness.py",
    "scripts/run_m104_qualification.py",
    "scripts/check_m104_result.py",
    "scripts/build_m104_protocol.py",
    "tests/test_m104_successor.py",
]
EXPECTED_INHERITED_ORCHESTRATION_FILES = [
    "scripts/run_m103_qualification.py",
    "experiments/M103/DEVELOPMENT_FIXTURE.json",
    "experiments/M103/PREDECESSOR_CONSERVATION.json",
    "experiments/M102/RESULT.json",
    "experiments/M102/CHECK_REPORT.json",
]
EXPECTED_RUNTIME = {
    "python": {"implementation": "cpython", "version_info": [3, 11, 16]},
    "sqlite": {
        "module": "sqlite3",
        "sqlite_version": "3.53.1",
        "sqlite_version_info": [3, 53, 1],
    },
}


canonical_json = predicate_checker.canonical_json
digest = predicate_checker.digest
stable_projection = predicate_checker.stable_projection


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(*arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments], cwd=ROOT, capture_output=True, text=True, check=False
    )
    if completed.returncode != 0:
        raise ValueError(completed.stderr.strip() or "git command failed")
    return completed.stdout.strip()


def _require_annotated_tag(reference: str, *, label: str) -> None:
    if not reference or _git("cat-file", "-t", reference) != "tag":
        raise ValueError(f"M104 {label} must be an annotated tag")


def _verify_file_binding(binding: dict[str, Any], *, label: str) -> None:
    files = binding.get("files")
    expected = binding.get("member_digests")
    if not isinstance(files, list) or not isinstance(expected, dict):
        raise ValueError(f"M104 {label} binding shape is invalid")
    measured = {path: _sha256(ROOT / path) for path in files}
    if measured != expected or digest(measured) != binding.get("digest"):
        raise ValueError(f"M104 {label} bound bytes changed")


def verify_protocol_boundary(
    protocol: dict[str, Any], pool: dict[str, Any], candidate: dict[str, Any]
) -> None:
    protocol_payload = {key: value for key, value in protocol.items() if key != "protocol_digest"}
    if protocol.get("schema") != "m104-protocol-v1" or protocol.get("protocol_digest") != digest(
        protocol_payload
    ):
        raise ValueError("M104 protocol identity or digest mismatch")
    pool_payload = {key: value for key, value in pool.items() if key != "pool_digest"}
    if (
        pool.get("schema") != "m104-qualification-pool-v1"
        or pool.get("pool_digest") != digest(pool_payload)
        or pool.get("pool_digest") != EXPECTED_POOL_DIGEST
    ):
        raise ValueError("M104 qualification pool identity or digest mismatch")
    candidate_payload = {key: value for key, value in candidate.items() if key != "candidate_digest"}
    if candidate.get("schema") != "m104-protocol-candidate-v1" or candidate.get(
        "candidate_digest"
    ) != digest(candidate_payload):
        raise ValueError("M104 protocol candidate identity or digest mismatch")
    candidate_binding = protocol.get("protocol_candidate", {})
    if candidate.get("candidate_digest") != candidate_binding.get("candidate_digest"):
        raise ValueError("M104 final protocol candidate digest binding mismatch")
    if protocol.get("qualification_pool_digest") != pool.get("pool_digest"):
        raise ValueError("M104 protocol qualification pool binding mismatch")
    if candidate.get("qualification_pool_digest") != pool.get("pool_digest"):
        raise ValueError("M104 candidate qualification pool binding mismatch")
    pool_raw = _sha256(POOL_PATH)
    if pool_raw != EXPECTED_POOL_RAW_SHA256:
        raise ValueError("M104 qualification pool frozen raw digest mismatch")
    if protocol.get("qualification_pool_raw_sha256") != pool_raw or candidate.get(
        "qualification_pool_raw_sha256"
    ) != pool_raw:
        raise ValueError("M104 qualification pool raw binding mismatch")
    if protocol.get("candidate_source_ref") != candidate.get("candidate_source_ref"):
        raise ValueError("M104 candidate source reference mismatch")
    for field in (
        "m103_exact_binding",
        "m104_bound_files",
        "canonical_runtime",
        "canonical_result_policy",
        "decisive_conditions",
        "verdict_rule",
    ):
        if protocol.get(field) != candidate.get(field):
            raise ValueError(f"M104 final protocol changed candidate field: {field}")
    if protocol.get("status") != "frozen_protocol_run_not_authorized":
        raise ValueError("M104 final protocol status mismatch")
    acceptance = protocol.get("owner_protocol_acceptance", {})
    if (
        acceptance.get("required") is not True
        or acceptance.get("recorded") is not True
        or not isinstance(acceptance.get("authorization_reference"), str)
        or not acceptance["authorization_reference"]
    ):
        raise ValueError("M104 owner protocol acceptance is absent")
    if protocol.get("canonical_run_allowed") is not False:
        raise ValueError("M104 final protocol is not internally disarmed")
    policy = protocol.get("canonical_result_policy", {})
    if (
        policy.get("canonical_attempts") != 1
        or policy.get("canonical_checker_attempts") != 1
        or policy.get("exclusive_create") is not True
        or policy.get("preserve_first_result_even_if_negative") is not True
    ):
        raise ValueError("M104 unique-attempt result policy mismatch")
    if protocol.get("decisive_conditions") != EXPECTED_PREDICATES:
        raise ValueError("M104 decisive predicate declaration changed")
    if candidate.get("status") != "owner_review_required_run_not_authorized":
        raise ValueError("M104 protocol candidate status mismatch")
    if candidate.get("canonical_run_allowed") is not False or candidate.get(
        "separate_owner_run_authorization_required"
    ) is not True:
        raise ValueError("M104 candidate authorization boundary mismatch")
    if protocol.get("canonical_runtime") != EXPECTED_RUNTIME:
        raise ValueError("M104 frozen runtime declaration mismatch")
    measured_runtime = {
        "python": {"implementation": sys.implementation.name, "version_info": list(sys.version_info[:3])},
        "sqlite": {
            "module": "sqlite3",
            "sqlite_version": sqlite3.sqlite_version,
            "sqlite_version_info": list(sqlite3.sqlite_version_info),
        },
    }
    if measured_runtime != EXPECTED_RUNTIME:
        raise ValueError("M104 checker replay runtime mismatch")

    m103_protocol = json.loads(M103_PROTOCOL_PATH.read_text(encoding="ascii"))
    m103_payload = {key: value for key, value in m103_protocol.items() if key != "protocol_digest"}
    if m103_protocol.get("protocol_digest") != digest(m103_payload) or m103_protocol.get(
        "protocol_digest"
    ) != EXPECTED_M103_PROTOCOL_DIGEST:
        raise ValueError("M104 frozen M103 protocol identity mismatch")
    exact_binding = protocol.get("m103_exact_binding", {})
    if exact_binding.get("protocol_digest") != EXPECTED_M103_PROTOCOL_DIGEST:
        raise ValueError("M104 M103 protocol binding mismatch")
    for name in ("mechanism", "checker"):
        if exact_binding.get("bound_files", {}).get(name) != m103_protocol.get("bound_files", {}).get(
            name
        ):
            raise ValueError(f"M104 M103 {name} membership or digest mismatch")
    inherited = exact_binding.get("bound_files", {}).get("inherited_orchestration", {})
    if inherited.get("files") != EXPECTED_INHERITED_ORCHESTRATION_FILES:
        raise ValueError("M104 inherited orchestration membership mismatch")
    inherited_members = inherited.get("member_digests", {})
    for path in EXPECTED_INHERITED_ORCHESTRATION_FILES[:3]:
        if inherited_members.get(path) != m103_protocol["bound_files"]["apparatus"]["member_digests"][
            path
        ]:
            raise ValueError(f"M104 inherited M103 apparatus digest mismatch: {path}")
    if inherited_members.get("experiments/M102/RESULT.json") != m103_protocol["predecessor"][
        "result_raw_sha256"
    ]:
        raise ValueError("M104 inherited M102 result digest mismatch")
    if inherited_members.get("experiments/M102/CHECK_REPORT.json") != m103_protocol["predecessor"][
        "checker_raw_sha256"
    ]:
        raise ValueError("M104 inherited M102 checker digest mismatch")
    if protocol.get("m104_bound_files", {}).get("files") != EXPECTED_M104_FILES:
        raise ValueError("M104 apparatus membership mismatch")


def verify_result_boundary(protocol: dict[str, Any]) -> None:
    if REPORT_PATH.exists():
        raise ValueError("M104 checker report already exists")
    if _sha256(POOL_PATH) != protocol.get("qualification_pool_raw_sha256"):
        raise ValueError("M104 pool raw bytes changed before checker replay")
    candidate = protocol.get("protocol_candidate", {})
    candidate_path = EXPERIMENT / "PROTOCOL_CANDIDATE.json"
    if _sha256(candidate_path) != candidate.get("raw_sha256"):
        raise ValueError("M104 candidate raw bytes changed before checker replay")
    _verify_file_binding(protocol.get("m104_bound_files", {}), label="apparatus")
    for name in ("mechanism", "checker", "inherited_orchestration"):
        _verify_file_binding(
            protocol.get("m103_exact_binding", {}).get("bound_files", {}).get(name, {}),
            label=f"M103 {name}",
        )
    head = _git("rev-parse", "HEAD")
    result_tag = protocol.get("canonical_result_policy", {}).get("first_result_tag")
    _require_annotated_tag(result_tag, label="first-result reference")
    if _git("rev-list", "-n", "1", result_tag) != head:
        raise ValueError("M104 HEAD is not the preserved first-result tag")
    freeze_tag = protocol.get("freeze_tag")
    _require_annotated_tag(freeze_tag, label="freeze reference")
    freeze_commit = _git("rev-parse", "HEAD^")
    if freeze_commit != _git("rev-list", "-n", "1", freeze_tag):
        raise ValueError("M104 result commit is not the direct child of the freeze")
    changed_paths = _git("diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD").splitlines()
    if changed_paths != ["experiments/M104/RESULT.json"]:
        raise ValueError("M104 first-result commit must contain only RESULT.json")
    committed_result = subprocess.run(
        ["git", "show", "HEAD:experiments/M104/RESULT.json"],
        cwd=ROOT,
        capture_output=True,
        check=False,
    )
    if committed_result.returncode != 0 or committed_result.stdout != RESULT_PATH.read_bytes():
        raise ValueError("M104 working result differs from its committed blob")
    source_ref = protocol.get("source_ref")
    _require_annotated_tag(source_ref, label="owner-review candidate reference")
    candidate_commit = _git("rev-parse", f"{freeze_commit}^")
    if candidate_commit != _git("rev-list", "-n", "1", source_ref):
        raise ValueError("M104 freeze parent is not the accepted candidate tag")
    freeze_paths = _git(
        "diff-tree", "--no-commit-id", "--name-only", "-r", freeze_commit
    ).splitlines()
    if freeze_paths != ["experiments/M104/PROTOCOL.json"]:
        raise ValueError("M104 freeze commit must contain only PROTOCOL.json")
    committed_protocol = subprocess.run(
        ["git", "show", f"{freeze_commit}:experiments/M104/PROTOCOL.json"],
        cwd=ROOT,
        capture_output=True,
        check=False,
    )
    if committed_protocol.returncode != 0 or committed_protocol.stdout != PROTOCOL_PATH.read_bytes():
        raise ValueError("M104 working protocol differs from its frozen blob")
    candidate_paths = _git(
        "diff-tree", "--no-commit-id", "--name-only", "-r", candidate_commit
    ).splitlines()
    if candidate_paths != ["experiments/M104/PROTOCOL_CANDIDATE.json"]:
        raise ValueError("M104 candidate commit must contain only PROTOCOL_CANDIDATE.json")
    committed_candidate = subprocess.run(
        ["git", "show", f"{candidate_commit}:experiments/M104/PROTOCOL_CANDIDATE.json"],
        cwd=ROOT,
        capture_output=True,
        check=False,
    )
    if committed_candidate.returncode != 0 or committed_candidate.stdout != candidate_path.read_bytes():
        raise ValueError("M104 working candidate differs from its accepted blob")
    candidate_source_ref = protocol.get("candidate_source_ref")
    _require_annotated_tag(candidate_source_ref, label="candidate source reference")
    if _git("rev-parse", f"{candidate_commit}^") != _git("rev-list", "-n", "1", candidate_source_ref):
        raise ValueError("M104 candidate parent is not its bound source tag")
    if _git("status", "--porcelain"):
        raise ValueError("M104 checker requires a clean first-result worktree")


def entrypoint_preflight() -> dict[str, Any]:
    from scripts import run_m104_qualification as qualification

    source = Path(__file__).read_bytes()
    return {
        "schema": "m104-checker-entrypoint-preflight-v1",
        "confirmed": ROOT == qualification.ROOT,
        "repository_root_resolved": ROOT == qualification.ROOT,
        "checker_raw_sha256": hashlib.sha256(source).hexdigest(),
        "runner_imported": qualification.__name__ == "scripts.run_m104_qualification",
        "qualification_pool_opened": False,
        "result_opened": False,
        "report_opened": False,
    }


def check_result(result: dict[str, Any], *, replay: bool) -> dict[str, Any]:
    if result.get("schema") != "m104-result-v1" or result.get("attempt") != 1:
        raise ValueError("M104 result identity is invalid")
    payload = {key: value for key, value in result.items() if key != "result_digest"}
    if result.get("result_digest") != digest(payload):
        raise ValueError("M104 result digest mismatch")
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="ascii"))
    pool = json.loads(POOL_PATH.read_text(encoding="ascii"))
    candidate = json.loads((EXPERIMENT / "PROTOCOL_CANDIDATE.json").read_text(encoding="ascii"))
    verify_protocol_boundary(protocol, pool, candidate)
    verify_result_boundary(protocol)
    if result.get("protocol_digest") != protocol.get("protocol_digest"):
        raise ValueError("M104 result protocol binding mismatch")
    if result.get("pool_digest") != pool.get("pool_digest"):
        raise ValueError("M104 result pool binding mismatch")
    evidence = result["scientific_evidence"]
    measured_stable = digest(stable_projection(evidence))
    if result.get("stable_evidence_digest") != measured_stable:
        raise ValueError("M104 stable evidence digest mismatch")
    replay_equal = False
    replay_digest: str | None = None
    if replay:
        from scripts import run_m104_qualification as qualification

        replay_evidence = qualification.run_experiment(pool)
        replay_digest = digest(stable_projection(replay_evidence))
        replay_equal = stable_projection(replay_evidence) == stable_projection(evidence)
    conditions = predicate_checker.evaluate_conditions(evidence, replay_confirmed=replay_equal)
    if sorted(conditions, key=lambda key: int(key[1:])) != EXPECTED_PREDICATES:
        raise ValueError("M104 checker predicate set changed")
    failed = [key for key in EXPECTED_PREDICATES if not conditions[key]]
    report: dict[str, Any] = {
        "schema": "m104-check-report-v1",
        "scientific_verdict": True,
        "verdict": "positive" if not failed else "negative",
        "attempt": 1,
        "conditions": conditions,
        "passed": len(conditions) - len(failed),
        "failed": len(failed),
        "uncomputed": 0,
        "failed_predicates": failed,
        "result_digest": result["result_digest"],
        "stable_evidence_digest": measured_stable,
        "replay_performed": replay,
        "replay_equal": replay_equal,
        "replay_stable_evidence_digest": replay_digest,
        "model_calls": result.get("model_calls"),
        "network_calls": result.get("network_calls"),
        "remote_execution_calls": result.get("remote_execution_calls"),
        "predicate_semantics_source": "frozen_M103_independent_checker",
        "imports_m103_runtime_for_predicates": False,
        "direct_script_root_bootstrap": True,
        "protocol_boundary_confirmed": True,
        "result_boundary_confirmed": True,
    }
    report["report_digest"] = digest(report)
    return report


def _failure_report(error: Exception) -> dict[str, Any]:
    report: dict[str, Any] = {
        "schema": "m104-check-report-v1",
        "scientific_verdict": True,
        "verdict": "negative",
        "failed_closed": True,
        "error": f"{type(error).__name__}: {error}",
        "attempt": 1,
    }
    report["report_digest"] = digest(report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", default=str(RESULT_PATH))
    parser.add_argument("--replay", action="store_true")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--entrypoint-preflight", action="store_true")
    arguments = parser.parse_args()
    if arguments.entrypoint_preflight:
        report = entrypoint_preflight()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["confirmed"] else 3
    try:
        result = json.loads(Path(arguments.result).read_text(encoding="ascii"))
        report = check_result(result, replay=arguments.replay)
    except Exception as error:
        report = _failure_report(error)
        if arguments.write and not REPORT_PATH.exists():
            with REPORT_PATH.open("xb") as handle:
                handle.write(canonical_json(report).encode("ascii"))
        print(json.dumps(report, indent=2, sort_keys=True))
        return 3
    if arguments.write:
        with REPORT_PATH.open("xb") as handle:
            handle.write(canonical_json(report).encode("ascii"))
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["verdict"] == "positive" else 1


if __name__ == "__main__":
    raise SystemExit(main())
