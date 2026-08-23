"""Run M101's frozen local Track-A qualification after explicit arming."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "M101"
PROTOCOL_PATH = EXPERIMENT / "PROTOCOL.json"
RESULT_PATH = EXPERIMENT / "RESULT.json"
M100_RESULT_PATH = ROOT / "experiments" / "M100" / "RESULT.json"
ISOLATED_PYTHON = Path(getattr(sys, "_base_executable", sys.executable)).resolve()
RESULT_SCHEMA = "m101-result-v1"
EPHEMERAL_KEYS = {"pid", "process_pids", "search_path"}

from audit_m101_boundaries import audit as audit_boundaries
from author_m101_qualification_pool import audit as audit_pool
from author_m101_qualification_pool import canonical_json, digest, load_pool


class QualificationRefused(RuntimeError):
    pass


def stable_projection(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: stable_projection(item)
            for key, item in value.items()
            if key not in EPHEMERAL_KEYS
        }
    if isinstance(value, list):
        return [stable_projection(item) for item in value]
    return value


def file_set_digest(paths: list[str]) -> tuple[str, dict[str, str]]:
    members = {
        path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in paths
    }
    return digest(members), members


def capsule_binding(members: dict[str, str]) -> tuple[str, dict[str, str]]:
    measured = {
        destination: hashlib.sha256((ROOT / source).read_bytes()).hexdigest()
        for destination, source in members.items()
    }
    return digest(measured), measured


CAPSULE_SOURCES = {
    "acquisition": {
        "m101_runtime.py": "metamorphosis/m101_runtime.py",
        "run.py": "scripts/run_m101_acquisition_process.py",
    },
    "execution": {
        "m101_executor.py": "metamorphosis/m101_executor.py",
        "run.py": "scripts/run_m101_fresh_process.py",
    },
    "definition_checker": {
        "check.py": "scripts/check_m101_definitions.py",
    },
}


def build_capsules(base: Path) -> tuple[dict[str, Path], dict[str, dict[str, Any]]]:
    capsules: dict[str, Path] = {}
    reports: dict[str, dict[str, Any]] = {}
    for capsule_name, sources in CAPSULE_SOURCES.items():
        capsule = base / f"m101-{capsule_name}-capsule"
        capsule.mkdir(parents=True)
        for destination, source in sources.items():
            shutil.copyfile(ROOT / source, capsule / destination)
        actual = sorted(path.name for path in capsule.iterdir())
        if actual != sorted(sources):
            raise QualificationRefused(f"unexpected member in {capsule_name} capsule")
        capsule_digest, member_digests = capsule_binding(sources)
        reports[capsule_name] = {
            "members": actual,
            "member_digests": member_digests,
            "capsule_digest": capsule_digest,
            "contains_only_bound_members": True,
        }
        capsules[capsule_name] = capsule
    return capsules, reports


def _fresh(capsule: Path, entry: str, arguments: list[str], *, timeout: int = 60) -> dict[str, Any]:
    completed = subprocess.run(
        [str(ISOLATED_PYTHON), "-I", str(capsule / entry), *arguments],
        cwd=capsule,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        payload = {
            "confirmed": False,
            "failed_closed": True,
            "parse_error": str(error),
            "stdout_tail": completed.stdout[-500:],
        }
    return {
        "returncode": completed.returncode,
        "runtime": payload,
        "stderr": completed.stderr[-1000:],
    }


def _acquisition(capsule: Path, action: str, **options: Any) -> dict[str, Any]:
    arguments = [action]
    for name in ("m100", "state", "demand", "out", "control", "restore"):
        value = options.get(name)
        if value is not None:
            arguments.extend([f"--{name}", str(value)])
    if options.get("register"):
        arguments.append("--register")
    return _fresh(capsule, "run.py", arguments)


def _execution(capsule: Path, action: str, state: Path, world: Path) -> dict[str, Any]:
    return _fresh(
        capsule,
        "run.py",
        [action, "--state", str(state), "--world", str(world)],
    )


def _definition_check(capsule: Path, state: Path, m100_sha256: str) -> dict[str, Any]:
    return _fresh(
        capsule,
        "check.py",
        ["--state", str(state), "--expected-m100-sha256", m100_sha256],
    )


def _write_json(path: Path, value: Any) -> Path:
    path.write_bytes(canonical_json(value).encode("ascii"))
    return path


def public_demand(world: dict[str, Any]) -> dict[str, Any]:
    if world.get("carrier") not in {"text", "record", "syntax"}:
        raise ValueError("only a new-carrier world has M101 public demand")
    return {
        "schema": "m101-public-demand-v1",
        "world_id": world["id"],
        "role": world["role"],
        "carrier": world["carrier"],
        "catalog": world["catalog"],
        "public_cases": world["public_cases"],
    }


def m100_s3_bytes() -> tuple[bytes, str]:
    result = json.loads(M100_RESULT_PATH.read_text(encoding="utf-8"))
    record = result["scientific_evidence"]["states"]["S3"]
    raw = canonical_json(record["state"]).encode("ascii")
    measured = hashlib.sha256(raw).hexdigest()
    if measured != record["raw_sha256"]:
        raise QualificationRefused("the preserved M100 S3 bytes no longer match their result")
    return raw, measured


def _state_record(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    state = json.loads(raw.decode("ascii"))
    return {
        "raw_sha256": hashlib.sha256(raw).hexdigest(),
        "state_digest": state["state_digest"],
        "m100_sha256": state["m100_sha256"],
        "definition_count": len(state["definitions"]),
        "definition_ids": [item["definition_id"] for item in state["definitions"]],
        "definitions": state["definitions"],
    }


def _runtime_rows(value: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if isinstance(value, dict):
        if value.get("schema") in {"m101-acquisition-process-v1", "m101-fresh-executor-v1"}:
            rows.append(value)
        for item in value.values():
            rows.extend(_runtime_rows(item))
    elif isinstance(value, list):
        for item in value:
            rows.extend(_runtime_rows(item))
    return rows


def _success(row: dict[str, Any]) -> bool:
    return row.get("returncode") == 0 and row.get("runtime", {}).get("confirmed") is True


def _failure(row: dict[str, Any]) -> bool:
    return row.get("returncode") != 0 and row.get("runtime", {}).get("confirmed") is False


def run_experiment(pool: dict[str, Any], *, allow_frozen: bool = False) -> dict[str, Any]:
    if pool.get("status") == "frozen" and not allow_frozen:
        raise QualificationRefused("the frozen M101 population may run only through armed materialize")
    worlds = [entry["world"] for entry in pool["entries"]]
    producers = [world for world in worlds if world["role"] == "producer_trigger"]
    transfers = [
        world
        for world in worlds
        if world["role"] in {"text_holdout", "record_transfer", "syntax_transfer"}
    ]
    b_worlds = [world for world in worlds if world["role"] == "b_reuse"]
    conservation = [world for world in worlds if world["role"] == "m100_conservation"]
    if not producers or not transfers or not b_worlds or not conservation:
        raise QualificationRefused("development population does not exercise every M101 phase")
    producer = producers[0]

    with tempfile.TemporaryDirectory(prefix="m101-run-") as temporary:
        base = Path(temporary)
        capsules, capsule_reports = build_capsules(base)
        payload_root = base / "payloads"
        payload_root.mkdir()
        world_paths = {
            world["id"]: _write_json(payload_root / f"world-{world['id']}.json", world)
            for world in worlds
        }
        demand_paths = {
            world["id"]: _write_json(
                payload_root / f"demand-{world['id']}.json", public_demand(world)
            )
            for world in worlds
            if world["carrier"] != "m100"
        }
        m100_raw, m100_sha256 = m100_s3_bytes()
        m100_path = base / "M100-S3.json"
        m100_path.write_bytes(m100_raw)

        t0_path = base / "T0.json"
        create_t0 = _acquisition(
            capsules["acquisition"], "create-state", m100=m100_path, out=t0_path
        )
        t0_bytes = t0_path.read_bytes()
        a_built = _acquisition(
            capsules["acquisition"],
            "acquire-a",
            state=t0_path,
            demand=demand_paths[producer["id"]],
        )
        t0_unchanged_after_a_build = t0_path.read_bytes() == t0_bytes

        baselines = []
        for world in transfers:
            baselines.append(
                {
                    "entry": world["id"],
                    "public_demand_digest": digest(public_demand(world)),
                    "fresh": _acquisition(
                        capsules["acquisition"],
                        "baseline",
                        state=t0_path,
                        demand=demand_paths[world["id"]],
                    ),
                }
            )

        t1_path = base / "T1.json"
        acquire_a = _acquisition(
            capsules["acquisition"],
            "acquire-a",
            state=t0_path,
            demand=demand_paths[producer["id"]],
            register=True,
            out=t1_path,
        )
        t1_bytes = t1_path.read_bytes()
        validate_t1 = _definition_check(capsules["definition_checker"], t1_path, m100_sha256)

        a_worlds = [producer, *transfers]
        a_executions = [
            {
                "entry": world["id"],
                "role": world["role"],
                "entry_digest": next(
                    entry["entry_digest"] for entry in pool["entries"] if entry["world"] is world
                ),
                "fresh": _execution(
                    capsules["execution"], "execute-a", t1_path, world_paths[world["id"]]
                ),
            }
            for world in a_worlds
        ]

        b_trigger = b_worlds[0]
        b_without_a = _acquisition(
            capsules["acquisition"],
            "acquire-b",
            state=t0_path,
            demand=demand_paths[b_trigger["id"]],
        )
        b_built = _acquisition(
            capsules["acquisition"],
            "acquire-b",
            state=t1_path,
            demand=demand_paths[b_trigger["id"]],
        )
        t1_unchanged_after_b_build = t1_path.read_bytes() == t1_bytes
        t2_path = base / "T2.json"
        acquire_b = _acquisition(
            capsules["acquisition"],
            "acquire-b",
            state=t1_path,
            demand=demand_paths[b_trigger["id"]],
            register=True,
            out=t2_path,
        )
        t2_bytes = t2_path.read_bytes()
        validate_t2 = _definition_check(capsules["definition_checker"], t2_path, m100_sha256)
        b_executions = [
            {
                "entry": world["id"],
                "entry_digest": next(
                    entry["entry_digest"] for entry in pool["entries"] if entry["world"] is world
                ),
                "fresh": _execution(
                    capsules["execution"], "execute-b", t2_path, world_paths[world["id"]]
                ),
            }
            for world in b_worlds
        ]
        m100_executions = [
            {
                "entry": world["id"],
                "operation_index": world["operation_index"],
                "entry_digest": next(
                    entry["entry_digest"] for entry in pool["entries"] if entry["world"] is world
                ),
                "fresh": _execution(
                    capsules["execution"], "execute-m100", t2_path, world_paths[world["id"]]
                ),
            }
            for world in conservation
        ]

        fault_path = base / "T2-fault.json"
        ablate_a_path = base / "T2-without-A.json"
        ablate_b_path = base / "T2-without-B.json"
        corrupt_path = base / "T2-corrupt.json"
        create_fault = _acquisition(
            capsules["acquisition"], "state-control", state=t2_path, control="rewrite-a", out=fault_path
        )
        create_ablate_a = _acquisition(
            capsules["acquisition"], "state-control", state=t2_path, control="ablate-a", out=ablate_a_path
        )
        create_ablate_b = _acquisition(
            capsules["acquisition"], "state-control", state=t2_path, control="ablate-b", out=ablate_b_path
        )
        create_corrupt = _acquisition(
            capsules["acquisition"], "state-control", state=t2_path, control="corrupt", out=corrupt_path
        )
        fault_executions = [
            _execution(
                capsules["execution"], "execute-b", fault_path, world_paths[world["id"]]
            )
            for world in b_worlds
        ]
        ablate_a_execution = _execution(
            capsules["execution"], "execute-b", ablate_a_path, world_paths[b_trigger["id"]]
        )
        ablate_b_execution = _execution(
            capsules["execution"], "execute-b", ablate_b_path, world_paths[b_trigger["id"]]
        )
        unrelated_after_b_ablation = _execution(
            capsules["execution"],
            "execute-a",
            ablate_b_path,
            world_paths[transfers[0]["id"]],
        )
        corrupt_execution = _execution(
            capsules["execution"], "execute-b", corrupt_path, world_paths[b_trigger["id"]]
        )
        restored_path = base / "T2-restored.json"
        rollback = _acquisition(
            capsules["acquisition"],
            "rollback",
            state=fault_path,
            restore=t2_path,
            out=restored_path,
        )
        after_rollback = _execution(
            capsules["execution"], "execute-b", restored_path, world_paths[b_trigger["id"]]
        )

        states = {
            "T0": _state_record(t0_path),
            "T1": _state_record(t1_path),
            "T2": _state_record(t2_path),
            "m100_raw_sha256": m100_sha256,
            "m100_bytes_conserved": all(
                json.loads(path.read_text(encoding="ascii"))["m100_ascii"].encode("ascii") == m100_raw
                for path in (t0_path, t1_path, t2_path)
            ),
            "t1_prefix_conserved_in_t2": (
                json.loads(t2_bytes.decode("ascii"))["definitions"][:1]
                == json.loads(t1_bytes.decode("ascii"))["definitions"]
            ),
        }
        baseline_by_entry = {row["entry"]: row for row in baselines}
        execution_by_entry = {row["entry"]: row for row in a_executions}
        parity_rows = []
        for world in transfers:
            baseline_row = baseline_by_entry[world["id"]]["fresh"]["runtime"]["baseline"]
            execution_row = execution_by_entry[world["id"]]["fresh"]["runtime"]["execution"]
            parity_rows.append(
                {
                    "entry": world["id"],
                    "catalog_digest": digest(world["catalog"]),
                    "public_demand_digest": digest(public_demand(world)),
                    "public_case_ids_equal": baseline_row["public_case_ids"]
                    == execution_row["public_case_ids"],
                    "candidate_budget_equal": baseline_row["candidate_budget"]
                    == execution_row["inference"]["assembled"],
                    "baseline_structural_max_atomic_effects": baseline_row[
                        "structural_max_atomic_effects"
                    ],
                    "retained_state_has_registered_a": True,
                    "baseline_has_registered_a": False,
                }
            )
        baseline_parity = {
            "common_descriptor": {
                "m100_sha256": m100_sha256,
                "acquisition_capsule_digest": capsule_reports["acquisition"]["capsule_digest"],
                "execution_capsule_digest": capsule_reports["execution"]["capsule_digest"],
                "validation_policy": "closed public demand; exact hidden equality",
                "observation_budget": 4,
            },
            "arm_difference": {
                "baseline_state_digest": states["T0"]["state_digest"],
                "retained_state_digest": states["T1"]["state_digest"],
                "baseline_definition_count": 0,
                "retained_definition_count": 1,
                "permitted_difference": "registered A and state digest implied by that registration",
            },
            "rows": parity_rows,
            "only_permitted_causal_difference": all(
                row["public_case_ids_equal"] and row["candidate_budget_equal"]
                for row in parity_rows
            ),
        }

        evidence: dict[str, Any] = {
            "schema": "m101-scientific-evidence-v1",
            "capsules": capsule_reports,
            "boundary_audit": audit_boundaries(),
            "state_chronology": {
                "create_t0": create_t0,
                "a_built_not_registered": a_built,
                "t0_unchanged_after_a_build": t0_unchanged_after_a_build,
                "acquire_and_register_a": acquire_a,
                "b_absent_without_a": b_without_a,
                "b_built_not_registered": b_built,
                "t1_unchanged_after_b_build": t1_unchanged_after_b_build,
                "acquire_and_register_b": acquire_b,
            },
            "definition_validation": {"T1": validate_t1, "T2": validate_t2},
            "states": states,
            "fresh_baselines": baselines,
            "baseline_parity": baseline_parity,
            "a_reuse": a_executions,
            "b_reuse": b_executions,
            "m100_conservation": m100_executions,
            "dependency_controls": {
                "create_fault": create_fault,
                "fault_breaks_all_b_worlds": fault_executions,
                "create_ablate_a": create_ablate_a,
                "ablate_a": ablate_a_execution,
                "create_ablate_b": create_ablate_b,
                "ablate_b": ablate_b_execution,
                "a_survives_b_ablation": unrelated_after_b_ablation,
                "create_corrupt": create_corrupt,
                "corrupt_state": corrupt_execution,
            },
            "rollback": {
                "fault_raw_sha256": hashlib.sha256(fault_path.read_bytes()).hexdigest(),
                "accepted_raw_sha256": hashlib.sha256(t2_bytes).hexdigest(),
                "fault_differs_from_accepted": fault_path.read_bytes() != t2_bytes,
                "restore_process": rollback,
                "restored_bytes_equal": restored_path.read_bytes() == t2_bytes,
                "restored_raw_sha256": hashlib.sha256(restored_path.read_bytes()).hexdigest(),
                "after_restore": after_rollback,
            },
        }

    runtime_rows = _runtime_rows(evidence)
    pids = [row.get("pid") for row in runtime_rows]
    repository_text = str(ROOT).casefold()
    evidence["process_boundary"] = {
        "process_pids": pids,
        "fresh_process_invocations": len(runtime_rows),
        "definition_checker_invocations": 2,
        "pid_records_present": all(isinstance(pid, int) for pid in pids),
        "all_processes_distinct": len(set(pids)) == len(pids),
        "all_invocations_isolated": all(row.get("isolated_mode") is True for row in runtime_rows),
        "no_project_modules_imported": all(not row.get("imported_project_modules") for row in runtime_rows),
        "repository_absent_from_search_paths": all(
            all(repository_text not in str(path).casefold() for path in row.get("search_path", []))
            for row in runtime_rows
        ),
    }
    return evidence


def require_frozen(protocol: dict[str, Any], pool: dict[str, Any]) -> None:
    if protocol.get("status") != "frozen" or protocol.get("canonical_run_allowed") is not True:
        raise QualificationRefused("M101 protocol is not frozen and armed-capable")
    if pool.get("status") != "frozen":
        raise QualificationRefused("M101 population is not frozen")
    if protocol.get("qualification_population", {}).get("pool_digest") != pool.get("pool_digest"):
        raise QualificationRefused("M101 protocol does not bind the frozen pool")
    for section in ("mechanism", "qualification_apparatus", "checker"):
        declared = protocol.get(section, {})
        measured, _members = file_set_digest(list(declared.get("files", [])))
        if declared.get("digest") != measured:
            raise QualificationRefused(f"M101 {section} moved after freeze")
    for name, sources in CAPSULE_SOURCES.items():
        measured, members = capsule_binding(sources)
        declared = protocol.get("capsules", {}).get(name, {})
        if declared.get("digest") != measured or declared.get("member_digests") != members:
            raise QualificationRefused(f"M101 {name} capsule moved after freeze")
    if protocol.get("stable_projection") != {
        "excluded_keys": sorted(EPHEMERAL_KEYS),
        "recursive": True,
        "policy_frozen_before_qualification": True,
    }:
        raise QualificationRefused("M101 stable projection is not the implemented frozen policy")
    freeze = protocol.get("freeze", {})
    candidate_commit = freeze.get("freeze_commit")
    freeze_ref = freeze.get("freeze_ref")
    if not isinstance(candidate_commit, str) or len(candidate_commit) != 40:
        raise QualificationRefused("M101 freeze-candidate commit is not bound")
    if not isinstance(freeze_ref, str) or not freeze_ref.startswith("experiment/m101-"):
        raise QualificationRefused("M101 immutable freeze ref is not bound")
    resolved_ref = subprocess.run(
        ["git", "rev-parse", f"refs/tags/{freeze_ref}"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if resolved_ref.returncode != 0:
        raise QualificationRefused("M101 immutable freeze ref does not exist")
    freeze_commit = resolved_ref.stdout.strip()
    parent = subprocess.run(
        ["git", "rev-parse", f"{freeze_commit}^"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    if parent != candidate_commit:
        raise QualificationRefused("M101 freeze ref is not the direct child of its bound candidate")
    candidate_bound_paths = {
        "experiments/M101/QUALIFICATION_POOL.json",
        *protocol["mechanism"]["files"],
        *protocol["qualification_apparatus"]["files"],
        *protocol["checker"]["files"],
    }
    for path in sorted(candidate_bound_paths):
        committed = subprocess.run(
            ["git", "show", f"{candidate_commit}:{path}"],
            cwd=ROOT,
            capture_output=True,
            check=True,
        ).stdout
        if committed != (ROOT / path).read_bytes():
            raise QualificationRefused(f"bound M101 artifact moved after candidate commit: {path}")
    committed_protocol = subprocess.run(
        ["git", "show", f"{freeze_commit}:experiments/M101/PROTOCOL.json"],
        cwd=ROOT,
        capture_output=True,
        check=True,
    ).stdout
    if committed_protocol != PROTOCOL_PATH.read_bytes():
        raise QualificationRefused("live M101 protocol differs from the immutable freeze ref")


def materialize(*, armed: bool = False) -> dict[str, Any]:
    if not armed:
        raise QualificationRefused("M101 result acquisition requires --arm")
    if RESULT_PATH.exists():
        raise QualificationRefused("M101 RESULT.json exists; overwrite and rerun are forbidden")
    protocol_bytes = PROTOCOL_PATH.read_bytes()
    protocol = json.loads(protocol_bytes.decode("utf-8"))
    pool = load_pool()
    require_frozen(protocol, pool)
    dirty = bool(
        subprocess.run(
            ["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.strip()
    )
    if dirty:
        raise QualificationRefused("commit the frozen M101 apparatus before arming")
    if not audit_pool(pool)["passed"] or not audit_boundaries()["passed"]:
        raise QualificationRefused("M101 frozen pre-run audits do not pass")
    source_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()
    freeze_ref = protocol["freeze"]["freeze_ref"]
    frozen_commit = subprocess.run(
        ["git", "rev-parse", f"refs/tags/{freeze_ref}"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    if source_commit != frozen_commit:
        raise QualificationRefused("canonical M101 must run exactly from the immutable freeze commit")
    started = time.time()
    evidence = run_experiment(pool, allow_frozen=True)
    mechanism_digest, mechanism_members = file_set_digest(protocol["mechanism"]["files"])
    apparatus_digest, apparatus_members = file_set_digest(
        protocol["qualification_apparatus"]["files"]
    )
    checker_digest, checker_members = file_set_digest(protocol["checker"]["files"])
    result: dict[str, Any] = {
        "schema": RESULT_SCHEMA,
        "milestone": "M101",
        "hypothesis": "H46",
        "decision_slot": "D070",
        "track": "A",
        "attempt": 1,
        "prior_attempts": [],
        "source_commit": source_commit,
        "working_tree_was_dirty_at_recording": False,
        "model_calls": 0,
        "network_calls": 0,
        "remote_execution": False,
        "protocol_raw_sha256": hashlib.sha256(protocol_bytes).hexdigest(),
        "pool_digest": pool["pool_digest"],
        "mechanism_digest": mechanism_digest,
        "mechanism_members": mechanism_members,
        "qualification_apparatus_digest": apparatus_digest,
        "qualification_apparatus_members": apparatus_members,
        "checker_digest": checker_digest,
        "checker_members": checker_members,
        "scientific_evidence": evidence,
        "stable_evidence_digest": digest(stable_projection(evidence)),
        "elapsed_seconds": round(time.time() - started, 3),
    }
    result["result_digest"] = digest(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm", action="store_true")
    parser.add_argument("--out")
    arguments = parser.parse_args()
    if not arguments.arm:
        print("Refusing to acquire M101 without --arm.", file=sys.stderr)
        return 2
    if not arguments.out or Path(arguments.out).resolve() != RESULT_PATH.resolve():
        print("An armed run must write exactly experiments/M101/RESULT.json.", file=sys.stderr)
        return 2
    try:
        result = materialize(armed=True)
    except QualificationRefused as error:
        print(f"Refused: {error}", file=sys.stderr)
        return 2
    RESULT_PATH.write_text(canonical_json(result) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
