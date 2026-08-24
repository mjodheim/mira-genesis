"""M104 fresh-population orchestration over the exact frozen M103 mechanism."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import run_m103_qualification as m103  # noqa: E402


EXPERIMENT = ROOT / "experiments" / "M104"
POOL_PATH = EXPERIMENT / "QUALIFICATION_POOL.json"
PROTOCOL_CANDIDATE_PATH = EXPERIMENT / "PROTOCOL_CANDIDATE.json"
PROTOCOL_PATH = EXPERIMENT / "PROTOCOL.json"
RESULT_PATH = EXPERIMENT / "RESULT.json"
CHECK_PATH = EXPERIMENT / "CHECK_REPORT.json"
M103_PROTOCOL_PATH = ROOT / "experiments" / "M103" / "PROTOCOL.json"
POOL_DIGEST = "a84fa3c5f9c2db51f31f83fa1b910c48f919bdc5c203d548833a7311d7bf1dad"
POOL_RAW_SHA256 = "732e2f46eefef4223e5a715db385639f43ceacf00b27e7c83dff9c15fbf8eb62"
M103_PROTOCOL_DIGEST = "cb21a4fa29d9895e477d12f6710eaa4f7c70dfca2e740812fe6846c4ff530de9"
CANONICAL_PYTHON = (3, 11, 16)
CANONICAL_SQLITE = (3, 53, 1)


class QualificationRefused(RuntimeError):
    pass


canonical_json = m103.canonical_json
digest = m103.digest
stable_projection = m103.stable_projection


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def verify_pool(pool: dict[str, Any]) -> dict[str, Any]:
    payload = {key: value for key, value in pool.items() if key != "pool_digest"}
    measured = digest(payload)
    checks = {
        "schema": pool.get("schema") == "m104-qualification-pool-v1",
        "milestone": pool.get("milestone") == "M104",
        "digest": pool.get("pool_digest") == measured == POOL_DIGEST,
        "raw_sha256": sha256_bytes(POOL_PATH.read_bytes()) == POOL_RAW_SHA256,
        "fresh": pool.get("fresh_from_m103") is True,
        "qualification_only": pool.get("qualification_only") is True,
        "producer_absent": pool.get("producer_fixture_included") is False,
        "development_binding": pool.get("development_fixture_digest") == m103.DEVELOPMENT_DIGEST,
        "record_count": pool.get("record_count") == 11,
        "hidden_case_count": pool.get("hidden_case_count") == 16,
        "configuration_worlds": len(pool.get("configuration", {}).get("hidden_worlds", [])) == 4,
        "filesystem_worlds": len(pool.get("filesystem", {}).get("hidden_worlds", [])) == 4,
    }
    return {"confirmed": all(checks.values()), "checks": checks, "measured_digest": measured}


def run_experiment(pool: dict[str, Any]) -> dict[str, Any]:
    if not verify_pool(pool)["confirmed"]:
        raise QualificationRefused("M104 qualification pool preflight failed")
    original_digest = m103.POOL_DIGEST
    original_verify = m103.verify_pool
    try:
        m103.POOL_DIGEST = POOL_DIGEST
        m103.verify_pool = verify_pool
        return m103.run_experiment(pool)
    finally:
        m103.POOL_DIGEST = original_digest
        m103.verify_pool = original_verify


def _git(*arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments], cwd=ROOT, capture_output=True, text=True, check=False
    )
    if completed.returncode != 0:
        raise QualificationRefused(completed.stderr.strip() or "git command failed")
    return completed.stdout.strip()


def _canonical_runtime_confirmed() -> bool:
    return (
        sys.implementation.name == "cpython"
        and tuple(sys.version_info[:3]) == CANONICAL_PYTHON
        and tuple(sqlite3.sqlite_version_info) == CANONICAL_SQLITE
    )


def _verify_file_binding(binding: dict[str, Any], *, label: str) -> None:
    files = binding.get("files")
    expected_members = binding.get("member_digests")
    if not isinstance(files, list) or not isinstance(expected_members, dict):
        raise QualificationRefused(f"M104 {label} binding shape is invalid")
    measured = {path: sha256_bytes((ROOT / path).read_bytes()) for path in files}
    if measured != expected_members or digest(measured) != binding.get("digest"):
        raise QualificationRefused(f"M104 {label} bound bytes changed")


def require_frozen() -> dict[str, Any]:
    if not PROTOCOL_PATH.exists():
        raise QualificationRefused("M104 final protocol is absent")
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="ascii"))
    payload = {key: value for key, value in protocol.items() if key != "protocol_digest"}
    if protocol.get("protocol_digest") != digest(payload):
        raise QualificationRefused("M104 protocol digest mismatch")
    if protocol.get("schema") != "m104-protocol-v1":
        raise QualificationRefused("M104 protocol schema mismatch")
    if protocol.get("qualification_pool_digest") != POOL_DIGEST:
        raise QualificationRefused("M104 protocol pool binding mismatch")
    if protocol.get("m103_protocol_digest") != M103_PROTOCOL_DIGEST:
        raise QualificationRefused("M104 protocol changed its M103 mechanism binding")
    if sha256_bytes(POOL_PATH.read_bytes()) != protocol.get("qualification_pool_raw_sha256"):
        raise QualificationRefused("M104 qualification pool raw bytes changed")
    candidate_binding = protocol.get("protocol_candidate", {})
    if sha256_bytes(PROTOCOL_CANDIDATE_PATH.read_bytes()) != candidate_binding.get("raw_sha256"):
        raise QualificationRefused("M104 protocol candidate raw bytes changed")
    _verify_file_binding(protocol.get("m104_bound_files", {}), label="apparatus")
    m103_binding = protocol.get("m103_exact_binding", {})
    for name in ("mechanism", "checker"):
        _verify_file_binding(
            m103_binding.get("bound_files", {}).get(name, {}),
            label=f"M103 {name}",
        )
    if protocol.get("owner_protocol_acceptance", {}).get("recorded") is not True:
        raise QualificationRefused("M104 owner protocol acceptance is absent")
    if protocol.get("canonical_run_allowed") is not False:
        raise QualificationRefused("M104 protocol must remain internally disarmed")
    if not _canonical_runtime_confirmed():
        raise QualificationRefused("M104 canonical runtime mismatch")
    if RESULT_PATH.exists() or CHECK_PATH.exists():
        raise QualificationRefused("M104 canonical evidence path already exists")
    freeze_tag = protocol.get("freeze_tag")
    source_ref = protocol.get("source_ref")
    if not freeze_tag or not source_ref:
        raise QualificationRefused("M104 freeze identity is incomplete")
    head = _git("rev-parse", "HEAD")
    if _git("rev-list", "-n", "1", freeze_tag) != head:
        raise QualificationRefused("M104 HEAD is not the frozen tag commit")
    if _git("rev-parse", "HEAD^") != _git("rev-list", "-n", "1", source_ref):
        raise QualificationRefused("M104 freeze parent is not the accepted source ref")
    changed_paths = _git("diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD").splitlines()
    if changed_paths != ["experiments/M104/PROTOCOL.json"]:
        raise QualificationRefused("M104 freeze commit must contain only the final protocol")
    if _git("status", "--porcelain"):
        raise QualificationRefused("M104 canonical worktree is not clean")
    return protocol


def preflight() -> dict[str, Any]:
    pool = json.loads(POOL_PATH.read_text(encoding="ascii"))
    pool_report = verify_pool(pool)
    protocol = require_frozen()
    return {
        "schema": "m104-preflight-v1",
        "confirmed": pool_report["confirmed"],
        "pool": pool_report,
        "protocol_digest": protocol["protocol_digest"],
        "result_absent": not RESULT_PATH.exists(),
        "check_report_absent": not CHECK_PATH.exists(),
        "python": platform.python_version(),
        "sqlite": sqlite3.sqlite_version,
    }


def materialize(*, authorized_by_owner: bool, understand_unique_attempt: bool) -> dict[str, Any]:
    if not authorized_by_owner:
        raise QualificationRefused("M104 canonical run requires distinct owner authorization")
    if not understand_unique_attempt:
        raise QualificationRefused("M104 unique-attempt acknowledgement is absent")
    protocol = require_frozen()
    pool = json.loads(POOL_PATH.read_text(encoding="ascii"))
    evidence = run_experiment(pool)
    result: dict[str, Any] = {
        "schema": "m104-result-v1",
        "milestone": "M104",
        "hypothesis": "H49",
        "attempt": 1,
        "protocol_digest": protocol["protocol_digest"],
        "pool_digest": pool["pool_digest"],
        "scientific_evidence": evidence,
        "stable_evidence_digest": digest(stable_projection(evidence)),
        "model_calls": 0,
        "network_calls": 0,
        "remote_execution_calls": 0,
        "m103_result_used_as_evidence": False,
    }
    result["result_digest"] = digest(result)
    with RESULT_PATH.open("xb") as handle:
        handle.write(canonical_json(result).encode("ascii"))
    return {
        "materialized": True,
        "path": str(RESULT_PATH),
        "result_digest": result["result_digest"],
        "stable_evidence_digest": result["stable_evidence_digest"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("preflight")
    materialize_parser = subparsers.add_parser("materialize")
    materialize_parser.add_argument("--authorized-by-owner", action="store_true")
    materialize_parser.add_argument(
        "--i-understand-this-is-the-only-canonical-attempt", action="store_true"
    )
    arguments = parser.parse_args()
    try:
        if arguments.command == "preflight":
            report = preflight()
        else:
            report = materialize(
                authorized_by_owner=arguments.authorized_by_owner,
                understand_unique_attempt=(
                    arguments.i_understand_this_is_the_only_canonical_attempt
                ),
            )
    except Exception as error:
        print(json.dumps({"confirmed": False, "error": f"{type(error).__name__}: {error}"}, indent=2))
        return 3
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
