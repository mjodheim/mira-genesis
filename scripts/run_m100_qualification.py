"""Run M100's frozen cumulative-acquisition qualification locally."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import time
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from metamorphosis import m100_runtime as state_runtime  # noqa: E402
from author_m100_qualification_pool import (  # noqa: E402
    COMPONENT,
    OUTPUT as POOL_PATH,
    audit as audit_pool,
    build_world,
    canonical_json,
    digest,
    load_pool,
    write_cases,
)
from run_m095_qualification import file_set_digest  # noqa: E402
from run_m098_qualification import QualificationRefused  # noqa: E402

EXPERIMENT = ROOT / "experiments" / "M100"
PROTOCOL_PATH = EXPERIMENT / "PROTOCOL.json"
RESULT_PATH = EXPERIMENT / "RESULT.json"
M097_RESULT_PATH = ROOT / "experiments" / "M097" / "RESULT.json"
M099_RESULT_PATH = ROOT / "experiments" / "M099" / "RESULT.json"
M099_CHECK_PATH = ROOT / "experiments" / "M099" / "CHECK_REPORT.json"
RESULT_SCHEMA = "m100-result-v1"
ISOLATED_PYTHON = Path(getattr(sys, "_base_executable", sys.executable)).resolve()
EPHEMERAL_KEYS = frozenset({"pid", "process_pids", "search_path"})


def stable_projection(value: object) -> object:
    """Remove only the process/location fields frozen as non-scientific ephemera."""
    if isinstance(value, dict):
        return {
            key: stable_projection(item)
            for key, item in value.items()
            if key not in EPHEMERAL_KEYS
        }
    if isinstance(value, list):
        return [stable_projection(item) for item in value]
    return value


def mechanism_digest(protocol: dict[str, object]) -> tuple[str, dict[str, str]]:
    return file_set_digest(protocol, "mechanism")


def require_frozen(protocol: dict[str, object], pool: dict[str, object]) -> None:
    if protocol.get("status") != "frozen" or pool.get("status") != "frozen":
        raise QualificationRefused("M100 protocol or pool is not frozen")
    if protocol.get("qualification_population", {}).get("pool_digest") != pool.get("pool_digest"):
        raise QualificationRefused("M100 protocol does not bind this pool")
    m097 = json.loads(M097_RESULT_PATH.read_text(encoding="utf-8"))
    m099 = json.loads(M099_RESULT_PATH.read_text(encoding="utf-8"))
    m099_check = json.loads(M099_CHECK_PATH.read_text(encoding="utf-8"))
    inputs = protocol.get("preserved_inputs", {})
    expected = {
        "m097_result_digest": m097.get("result_digest"),
        "m097_extended_state_digest": m097.get("scientific_evidence", {}).get(
            "extended_language_state", {}
        ).get("state_digest"),
        "m097_inherited_state_digest": m097.get("scientific_evidence", {}).get(
            "inherited_language_state", {}
        ).get("state_digest"),
        "m099_result_digest": m099.get("result_digest"),
        "m099_checker_digest": m099_check.get("report_digest"),
    }
    for key, value in expected.items():
        if inputs.get(key) != value:
            raise QualificationRefused(f"{key} differs from the frozen M100 input")
    measured, _members = mechanism_digest(protocol)
    apparatus, _apparatus_members = file_set_digest(protocol, "qualification_apparatus")
    if protocol.get("mechanism", {}).get("digest") != measured:
        raise QualificationRefused("M100 cumulative mechanism moved after freeze")
    if protocol.get("qualification_apparatus", {}).get("digest") != apparatus:
        raise QualificationRefused("M100 apparatus moved after freeze")


def _capsule(base: Path) -> tuple[Path, dict[str, str]]:
    capsule = base / "isolated-runtime"
    capsule.mkdir(parents=True)
    members = {
        "m100_runtime.py": ROOT / "metamorphosis" / "m100_runtime.py",
        "run.py": ROOT / "scripts" / "run_m100_isolated.py",
    }
    digests = {}
    for name, source in members.items():
        destination = capsule / name
        shutil.copyfile(source, destination)
        digests[name] = hashlib.sha256(destination.read_bytes()).hexdigest()
    if sorted(path.name for path in capsule.iterdir()) != sorted(members):
        raise QualificationRefused("M100 isolated capsule contains an unexpected file")
    return capsule, digests


def _fresh(capsule: Path, arguments: list[str]) -> dict[str, object]:
    completed = subprocess.run(
        [str(ISOLATED_PYTHON), "-I", str(capsule / "run.py"), *arguments],
        cwd=capsule,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        payload = {
            "confirmed": False,
            "parse_error": str(error),
            "stdout_tail": completed.stdout[-500:],
        }
    return {
        "returncode": completed.returncode,
        "runtime": payload,
        "stderr": completed.stderr[-1000:],
    }


def _migrate(capsule: Path, source: Path, destination: Path) -> dict[str, object]:
    return _fresh(capsule, [
        "migrate", "--m097-state", str(source), "--output-state", str(destination),
    ])


def _acquire(
    capsule: Path,
    state: Path,
    target: tuple[int, int],
    bound: int,
    *,
    output: Path | None = None,
) -> dict[str, object]:
    arguments = [
        "acquire", "--state", str(state), "--target-left", str(target[0]),
        "--target-right", str(target[1]), "--bound", str(bound),
    ]
    if output is not None:
        arguments += ["--register", "--output-state", str(output)]
    return _fresh(capsule, arguments)


def _execute(
    capsule: Path,
    state: Path,
    operation_id: str,
    world_root: Path,
    cases: Path,
) -> dict[str, object]:
    return _fresh(capsule, [
        "execute", "--state", str(state), "--operation-id", operation_id,
        "--world-root", str(world_root), "--component", COMPONENT, "--cases", str(cases),
    ])


def _rewrite_chain(
    state: dict[str, object], mutation_index: int, replacement_body: list[str]
) -> dict[str, object]:
    """Create a digest-valid semantic fault while retaining live downstream calls."""
    rewritten = []
    remapped: dict[str, str] = {}
    for index, original in enumerate(state["operations"]):
        body = list(replacement_body if index == mutation_index else original["body"])
        body = [
            f"CALL:{remapped.get(token[5:], token[5:])}" if token.startswith("CALL:") else token
            for token in body
        ]
        dependencies = state_runtime._dependency_ids(body)
        definition = state_runtime._definition(body, dependencies, str(original["origin"]))
        remapped[str(original["operation_id"])] = str(definition["operation_id"])
        rewritten.append(definition)
    return state_runtime._state(
        str(state["inherited_digest"]), str(state["origin_m097_state_digest"]), rewritten
    )


def _write_canonical(path: Path, state: dict[str, object]) -> bytes:
    raw = state_runtime.encode_state(state)
    path.write_bytes(raw)
    return raw


def _runtime_rows(value: object) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    if isinstance(value, dict):
        if value.get("schema") == state_runtime.RUNTIME_SCHEMA:
            rows.append(value)
        for item in value.values():
            rows.extend(_runtime_rows(item))
    elif isinstance(value, list):
        for item in value:
            rows.extend(_runtime_rows(item))
    return rows


def run_experiment(pool: dict[str, object]) -> dict[str, object]:
    m097 = json.loads(M097_RESULT_PATH.read_text(encoding="utf-8"))
    inherited_m097 = m097["scientific_evidence"]["inherited_language_state"]
    extended_m097 = m097["scientific_evidence"]["extended_language_state"]

    with tempfile.TemporaryDirectory(prefix="m100-run-") as temporary:
        base = Path(temporary)
        capsule, capsule_digests = _capsule(base)
        inherited_path = base / "m097-inherited.json"
        extended_path = base / "m097-extended.json"
        inherited_path.write_bytes(canonical_json(inherited_m097).encode("ascii"))
        extended_path.write_bytes(canonical_json(extended_m097).encode("ascii"))

        s0_path = base / "S0.json"
        s1_path = base / "S1.json"
        migration_s0 = _migrate(capsule, inherited_path, s0_path)
        migration_s1 = _migrate(capsule, extended_path, s1_path)
        s0_bytes = s0_path.read_bytes()
        s1_bytes = s1_path.read_bytes()
        s0 = json.loads(s0_bytes.decode("ascii"))
        s1 = json.loads(s1_bytes.decode("ascii"))

        b_without_a = _acquire(capsule, s0_path, (1, 1), 4)
        c_without_b = _acquire(capsule, s1_path, (1, 2), 5)
        b_built_not_registered = _acquire(capsule, s1_path, (1, 1), 4)
        s1_unchanged_after_build = s1_path.read_bytes() == s1_bytes
        c_after_unregistered_b = _acquire(capsule, s1_path, (1, 2), 5)

        s2_path = base / "S2.json"
        acquisition_b = _acquire(capsule, s1_path, (1, 1), 4, output=s2_path)
        s2_bytes = s2_path.read_bytes()
        s2 = json.loads(s2_bytes.decode("ascii"))
        s3_path = base / "S3.json"
        acquisition_c = _acquire(capsule, s2_path, (1, 2), 5, output=s3_path)
        s3_bytes = s3_path.read_bytes()
        s3 = json.loads(s3_bytes.decode("ascii"))
        operation_ids = {
            "A": str(s3["operations"][0]["operation_id"]),
            "B": str(s3["operations"][1]["operation_id"]),
            "C": str(s3["operations"][2]["operation_id"]),
        }

        worlds = []
        for entry in pool["entries"]:
            world_root = build_world(base / "worlds" / str(entry["id"]), entry)
            cases = write_cases(world_root / "cases.json", entry)
            worlds.append({
                "entry": entry["id"],
                "entry_digest": entry["entry_digest"],
                "cycle": entry["cycle"],
                "operation_id": operation_ids[str(entry["cycle"])],
                "fresh": _execute(
                    capsule, s3_path, operation_ids[str(entry["cycle"])], world_root, cases
                ),
            })

        entries = {str(item["cycle"]): item for item in pool["entries"]}
        control_worlds = {}
        for cycle in ("B", "C"):
            entry = entries[cycle]
            root = build_world(base / "controls" / f"world-{cycle}", entry)
            cases = write_cases(root / "cases.json", entry)
            control_worlds[cycle] = (root, cases)

        mutated_a = _rewrite_chain(s3, 0, ["PUSH_LEFT", "PUSH_RIGHT", "ADD"])
        mutated_a_path = base / "mutated-A-S3.json"
        _write_canonical(mutated_a_path, mutated_a)
        mutate_a_breaks_b = _execute(
            capsule, mutated_a_path, str(mutated_a["operations"][1]["operation_id"]),
            *control_worlds["B"],
        )

        a_id = str(s3["operations"][0]["operation_id"])
        mutated_b = _rewrite_chain(
            s3, 1, ["PUSH_LEFT", "PUSH_RIGHT", f"CALL:{a_id}"]
        )
        mutated_b_path = base / "mutated-B-S3.json"
        _write_canonical(mutated_b_path, mutated_b)
        mutate_b_breaks_c = _execute(
            capsule, mutated_b_path, str(mutated_b["operations"][2]["operation_id"]),
            *control_worlds["C"],
        )

        without_a = state_runtime._state(
            str(s3["inherited_digest"]), str(s3["origin_m097_state_digest"]),
            list(s3["operations"])[1:],
        )
        without_a_path = base / "without-A.json"
        without_a_path.write_bytes(canonical_json(without_a).encode("ascii"))
        ablate_a = _execute(
            capsule, without_a_path, operation_ids["C"], *control_worlds["C"]
        )

        without_b = state_runtime._state(
            str(s3["inherited_digest"]), str(s3["origin_m097_state_digest"]),
            [s3["operations"][0], s3["operations"][2]],
        )
        without_b_path = base / "without-B.json"
        without_b_path.write_bytes(canonical_json(without_b).encode("ascii"))
        ablate_b = _execute(
            capsule, without_b_path, operation_ids["C"], *control_worlds["C"]
        )

        corrupt_path = base / "corrupt-S3.json"
        corrupt = bytearray(s3_bytes)
        corrupt[len(corrupt) // 2] ^= 1
        corrupt_path.write_bytes(bytes(corrupt))
        corrupt_digest = _execute(
            capsule, corrupt_path, operation_ids["C"], *control_worlds["C"]
        )

        live_s2 = base / "live-S2.json"
        live_s2.write_bytes(s2_bytes)
        faulty_s2 = _rewrite_chain(
            s2, 1, ["PUSH_LEFT", "PUSH_RIGHT", f"CALL:{s2['operations'][0]['operation_id']}"]
        )
        faulty_s2_bytes = state_runtime.encode_state(faulty_s2)
        before_fault_sha256 = hashlib.sha256(live_s2.read_bytes()).hexdigest()
        live_s2.write_bytes(faulty_s2_bytes)
        during_fault = _acquire(capsule, live_s2, (1, 2), 5)
        live_s2.write_bytes(s2_bytes)
        restored_bytes_equal = live_s2.read_bytes() == s2_bytes
        rollback_s3_path = base / "rollback-S3.json"
        after_restore = _acquire(capsule, live_s2, (1, 2), 5, output=rollback_s3_path)

        evidence: dict[str, object] = {
            "schema": "m100-scientific-evidence-v1",
            "capsule": {
                "members": sorted(capsule_digests),
                "member_digests": capsule_digests,
                "contains_only_runtime_and_entrypoint": sorted(capsule_digests)
                == ["m100_runtime.py", "run.py"],
            },
            "migrations": {"pre_acquisition_to_s0": migration_s0, "acquired_a_to_s1": migration_s1},
            "acquisition_chain": {
                "s0_without_a_for_b": b_without_a,
                "s1_without_b_for_c": c_without_b,
                "b_built_not_registered": b_built_not_registered,
                "s1_unchanged_after_unregistered_build": s1_unchanged_after_build,
                "c_after_unregistered_b": c_after_unregistered_b,
                "acquire_and_register_b": acquisition_b,
                "acquire_and_register_c": acquisition_c,
            },
            "states": {
                "S0": {"raw_sha256": hashlib.sha256(s0_bytes).hexdigest(), "state": s0},
                "S1": {"raw_sha256": hashlib.sha256(s1_bytes).hexdigest(), "state": s1},
                "S2": {"raw_sha256": hashlib.sha256(s2_bytes).hexdigest(), "state": s2},
                "S3": {"raw_sha256": hashlib.sha256(s3_bytes).hexdigest(), "state": s3},
                "operation_ids": operation_ids,
                "s1_prefix_conserved_in_s2": s2["operations"][:1] == s1["operations"],
                "s2_prefix_conserved_in_s3": s3["operations"][:2] == s2["operations"],
            },
            "fresh_worlds_after_s3": worlds,
            "dependency_controls": {
                "mutate_a_breaks_b": mutate_a_breaks_b,
                "mutate_b_breaks_c": mutate_b_breaks_c,
                "ablate_a": ablate_a,
                "ablate_b": ablate_b,
                "corrupt_digest": corrupt_digest,
            },
            "rollback": {
                "before_fault_sha256": before_fault_sha256,
                "faulty_state_differs": faulty_s2_bytes != s2_bytes,
                "during_fault": during_fault,
                "restored_bytes_equal": restored_bytes_equal,
                "after_restore_sha256": hashlib.sha256(live_s2.read_bytes()).hexdigest(),
                "after_restore": after_restore,
                "restored_s3_equals_original": (
                    rollback_s3_path.exists() and rollback_s3_path.read_bytes() == s3_bytes
                ),
            },
        }

    runtime_rows = _runtime_rows(evidence)
    process_pids = [row.get("pid") for row in runtime_rows]
    repository_text = str(ROOT).casefold()
    evidence["process_boundary"] = {
        "process_pids": process_pids,
        "fresh_process_invocations": len(runtime_rows),
        "pid_records_present": all(isinstance(pid, int) for pid in process_pids),
        "all_key_cycle_processes_distinct": len({
            migration_s1["runtime"].get("pid"),
            acquisition_b["runtime"].get("pid"),
            acquisition_c["runtime"].get("pid"),
        }) == 3,
        "all_invocations_isolated": all(row.get("isolated_mode") is True for row in runtime_rows),
        "no_project_modules_imported": all(not row.get("imported_project_modules") for row in runtime_rows),
        "repository_absent_from_search_paths": all(
            all(repository_text not in str(path).casefold() for path in row.get("search_path", []))
            for row in runtime_rows
        ),
    }
    return evidence


def materialize(*, armed: bool = False) -> dict[str, object]:
    if not armed:
        raise QualificationRefused("M100 result acquisition requires --arm")
    if RESULT_PATH.exists():
        raise QualificationRefused("M100 RESULT.json exists; overwrite and rerun are forbidden")
    protocol_bytes = PROTOCOL_PATH.read_bytes()
    protocol = json.loads(protocol_bytes.decode("utf-8"))
    pool = load_pool()
    require_frozen(protocol, pool)
    source_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()
    dirty = bool(subprocess.run(
        ["git", "status", "--porcelain"], cwd=ROOT,
        capture_output=True, text=True, check=True,
    ).stdout.strip())
    if dirty:
        raise QualificationRefused("commit the frozen M100 apparatus before arming")
    if not audit_pool(pool)["passed"]:
        raise QualificationRefused("M100 frozen pool fails preflight")
    started = time.time()
    evidence = run_experiment(pool)
    measured, members = mechanism_digest(protocol)
    apparatus, apparatus_members = file_set_digest(protocol, "qualification_apparatus")
    m097 = json.loads(M097_RESULT_PATH.read_text(encoding="utf-8"))
    m099 = json.loads(M099_RESULT_PATH.read_text(encoding="utf-8"))
    m099_check = json.loads(M099_CHECK_PATH.read_text(encoding="utf-8"))
    withdrawn = sorted(path.name for path in EXPERIMENT.glob("WITHDRAWN_RESULT_*.json"))
    result = {
        "schema": RESULT_SCHEMA,
        "milestone": "M100",
        "track": "A",
        "attempt": len(withdrawn) + 1,
        "prior_attempts": withdrawn,
        "source_commit": source_commit,
        "working_tree_was_dirty_at_recording": False,
        "model_calls": 0,
        "network_calls": 0,
        "remote_execution": False,
        "protocol_raw_sha256": hashlib.sha256(protocol_bytes).hexdigest(),
        "pool_digest": pool["pool_digest"],
        "m097_result_digest": m097["result_digest"],
        "m097_extended_state_digest": m097["scientific_evidence"]["extended_language_state"][
            "state_digest"
        ],
        "m097_inherited_state_digest": m097["scientific_evidence"]["inherited_language_state"][
            "state_digest"
        ],
        "m099_result_digest": m099["result_digest"],
        "m099_checker_digest": m099_check["report_digest"],
        "mechanism_digest": measured,
        "mechanism_members": members,
        "qualification_apparatus_digest": apparatus,
        "qualification_apparatus_members": apparatus_members,
        "scientific_evidence": evidence,
        "stable_evidence_digest": digest(stable_projection(evidence)),
        "elapsed_seconds": round(time.time() - started, 3),
    }
    result["result_digest"] = digest(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm", action="store_true")
    parser.add_argument("--out", default=None)
    args = parser.parse_args()
    expected = RESULT_PATH.resolve()
    if not args.arm:
        print("Refusing to acquire M100 without --arm.", file=sys.stderr)
        return 2
    if not args.out or Path(args.out).resolve() != expected:
        print("An armed run must write exactly experiments/M100/RESULT.json.", file=sys.stderr)
        return 2
    try:
        result = materialize(armed=True)
    except QualificationRefused as error:
        print(f"Refused: {error}", file=sys.stderr)
        return 2
    expected.parent.mkdir(parents=True, exist_ok=True)
    expected.write_text(canonical_json(result) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
