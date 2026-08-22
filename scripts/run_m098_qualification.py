"""Run M098's frozen process-death persistence and rollback qualification locally."""

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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from author_m098_qualification_pool import (  # noqa: E402
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

EXPERIMENT = ROOT / "experiments" / "M098"
PROTOCOL_PATH = EXPERIMENT / "PROTOCOL.json"
M097_RESULT_PATH = ROOT / "experiments" / "M097" / "RESULT.json"
RESULT_SCHEMA = "m098-result-v1"
ISOLATED_PYTHON = Path(getattr(sys, "_base_executable", sys.executable)).resolve()


class QualificationRefused(RuntimeError):
    pass


def mechanism_digest(protocol: dict[str, object]) -> tuple[str, dict[str, str]]:
    return file_set_digest(protocol, "mechanism")


def require_frozen(protocol: dict[str, object], pool: dict[str, object]) -> None:
    if protocol.get("status") != "frozen" or pool.get("status") != "frozen":
        raise QualificationRefused("M098 protocol or pool is not frozen")
    if protocol.get("qualification_population", {}).get("pool_digest") != pool.get("pool_digest"):
        raise QualificationRefused("M098 protocol does not bind this pool")
    m097 = json.loads(M097_RESULT_PATH.read_text(encoding="utf-8"))
    binding = protocol.get("m097_input", {})
    if binding.get("result_digest") != m097.get("result_digest"):
        raise QualificationRefused("M097 preserved result differs from the frozen M098 input")
    state = m097.get("scientific_evidence", {}).get("extended_language_state", {})
    if binding.get("state_digest") != state.get("state_digest"):
        raise QualificationRefused("M097 extended state differs from the frozen M098 input")
    measured, _members = mechanism_digest(protocol)
    apparatus, _apparatus_members = file_set_digest(protocol, "qualification_apparatus")
    if protocol.get("mechanism", {}).get("digest") != measured:
        raise QualificationRefused("M098 runtime mechanism moved after freeze")
    if protocol.get("qualification_apparatus", {}).get("digest") != apparatus:
        raise QualificationRefused("M098 apparatus moved after freeze")


def _state_bytes(value: dict[str, object]) -> bytes:
    payload = {key: item for key, item in value.items() if key != "state_digest"}
    value = dict(payload)
    value["state_digest"] = digest(payload)
    return canonical_json(value).encode("ascii")


def _capsule(base: Path) -> tuple[Path, dict[str, str]]:
    capsule = base / "isolated-runtime"
    capsule.mkdir(parents=True)
    members = {
        "m098_runtime.py": ROOT / "metamorphosis" / "m098_runtime.py",
        "run.py": ROOT / "scripts" / "run_m098_fresh_process.py",
    }
    digests = {}
    for name, source in members.items():
        destination = capsule / name
        shutil.copyfile(source, destination)
        digests[name] = hashlib.sha256(destination.read_bytes()).hexdigest()
    if sorted(path.name for path in capsule.iterdir()) != sorted(members):
        raise QualificationRefused("isolated capsule contains an unexpected file")
    return capsule, digests


def _fresh(
    capsule: Path,
    state: Path,
    world_root: Path,
    cases: Path,
) -> dict[str, object]:
    completed = subprocess.run(
        [
            str(ISOLATED_PYTHON), "-I", str(capsule / "run.py"),
            "--state", str(state),
            "--world-root", str(world_root),
            "--component", COMPONENT,
            "--cases", str(cases),
        ],
        cwd=capsule,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        payload = {"confirmed": False, "parse_error": str(error), "stdout": completed.stdout[-500:]}
    return {
        "returncode": completed.returncode,
        "runtime": payload,
        "stderr": completed.stderr[-1000:],
    }


def _producer(base: Path) -> tuple[Path, dict[str, object]]:
    state = base / "lineage-state.json"
    manifest = base / "persist-manifest.json"
    process = subprocess.Popen(
        [
            str(ISOLATED_PYTHON), "-I", str(ROOT / "scripts" / "run_m098_persist_producer.py"),
            "--m097-result", str(M097_RESULT_PATH),
            "--state-out", str(state),
            "--manifest-out", str(manifest),
        ],
        cwd=base,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    stdout, stderr = process.communicate(timeout=30)
    if process.returncode != 0:
        raise QualificationRefused(f"state producer failed: {stderr[-1000:]}")
    value = json.loads(manifest.read_text(encoding="utf-8"))
    value["producer_returncode"] = process.returncode
    value["producer_process_is_terminated"] = process.poll() is not None
    value["producer_stdout_matches_manifest"] = json.loads(stdout) == {
        key: item for key, item in value.items()
        if key not in {"producer_returncode", "producer_process_is_terminated", "producer_stdout_matches_manifest"}
    }
    return state, value


def stable_projection(value: object) -> object:
    """Remove process/location ephemera while retaining every scientific outcome."""
    if isinstance(value, dict):
        return {
            key: stable_projection(item)
            for key, item in value.items()
            if key not in {"pid", "producer_pid", "search_path"}
        }
    if isinstance(value, list):
        return [stable_projection(item) for item in value]
    return value


def run_experiment(pool: dict[str, object]) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="m098-run-") as temporary:
        base = Path(temporary)
        capsule, capsule_digests = _capsule(base)
        state_path, producer = _producer(base)
        original = state_path.read_bytes()
        parsed_state = json.loads(original.decode("ascii"))

        worlds = []
        for entry in pool["entries"]:
            root = build_world(base / "worlds" / str(entry["id"]), entry)
            cases = write_cases(root / "cases.json", entry)
            worlds.append({
                "entry": entry["id"],
                "entry_digest": entry["entry_digest"],
                "fresh": _fresh(capsule, state_path, root, cases),
            })

        first_entry = pool["entries"][0]
        control_root = build_world(base / "controls" / "world", first_entry)
        control_cases = write_cases(control_root / "cases.json", first_entry)

        inherited_value = dict(parsed_state)
        inherited_value["extensions"] = []
        inherited_path = base / "inherited-state.json"
        inherited_path.write_bytes(_state_bytes(inherited_value))
        inherited_control = _fresh(
            capsule, inherited_path, control_root, control_cases
        )

        mutated_value = json.loads(original.decode("ascii"))
        body = mutated_value["extensions"][0]["body"]
        mutated_value["extensions"][0]["body"] = [
            "ADD" if token == "SUB" else token for token in body
        ]
        mutated_bytes = _state_bytes(mutated_value)
        mutated_path = base / "mutated-state.json"
        mutated_path.write_bytes(mutated_bytes)
        semantic_mutation_control = _fresh(
            capsule, mutated_path, control_root, control_cases
        )

        corrupt_path = base / "corrupt-state.json"
        corrupt = bytearray(original)
        corrupt[len(corrupt) // 2] ^= 1
        corrupt_path.write_bytes(bytes(corrupt))
        corrupt_control = _fresh(capsule, corrupt_path, control_root, control_cases)

        before_fault_sha = hashlib.sha256(state_path.read_bytes()).hexdigest()
        state_path.write_bytes(mutated_bytes)
        during_fault = _fresh(capsule, state_path, control_root, control_cases)
        state_path.write_bytes(original)
        restored_bytes_equal = state_path.read_bytes() == original
        after_restore_sha = hashlib.sha256(state_path.read_bytes()).hexdigest()
        after_restore = _fresh(capsule, state_path, control_root, control_cases)

    consumer_pids = [
        row["fresh"]["runtime"].get("pid") for row in worlds
    ] + [
        inherited_control["runtime"].get("pid"),
        semantic_mutation_control["runtime"].get("pid"),
        corrupt_control["runtime"].get("pid"),
        during_fault["runtime"].get("pid"),
        after_restore["runtime"].get("pid"),
    ]
    return {
        "schema": "m098-scientific-evidence-v1",
        "producer": producer,
        "capsule": {
            "members": sorted(capsule_digests),
            "member_digests": capsule_digests,
            "contains_only_runtime_and_entrypoint": sorted(capsule_digests) == [
                "m098_runtime.py", "run.py"
            ],
        },
        "state": {
            "raw_sha256": hashlib.sha256(original).hexdigest(),
            "bytes": len(original),
            "state_digest": parsed_state["state_digest"],
            "extensions": len(parsed_state["extensions"]),
        },
        "post_restart_worlds": worlds,
        "controls": {
            "inherited_without_extension": inherited_control,
            "semantic_mutation": semantic_mutation_control,
            "corrupt_digest": corrupt_control,
        },
        "rollback": {
            "before_fault_sha256": before_fault_sha,
            "during_fault": during_fault,
            "restored_bytes_equal": restored_bytes_equal,
            "after_restore_sha256": after_restore_sha,
            "after_restore": after_restore,
        },
        "process_boundary": {
            "producer_terminated_before_consumers": producer["producer_process_is_terminated"],
            "producer_pid": producer["producer_pid"],
            "consumer_pids": consumer_pids,
            "fresh_process_invocations": len(consumer_pids),
            "consumer_pid_records_present": all(isinstance(pid, int) for pid in consumer_pids),
            "all_consumers_are_distinct_from_producer": all(
                isinstance(pid, int) and pid != producer["producer_pid"] for pid in consumer_pids
            ),
        },
    }


def materialize(*, armed: bool = False) -> dict[str, object]:
    if not armed:
        raise QualificationRefused("M098 result acquisition requires --arm")
    result_path = EXPERIMENT / "RESULT.json"
    if result_path.exists():
        raise QualificationRefused("M098 RESULT.json exists; overwrite and rerun are forbidden")
    protocol_bytes = PROTOCOL_PATH.read_bytes()
    protocol = json.loads(protocol_bytes.decode("utf-8"))
    pool = load_pool()
    require_frozen(protocol, pool)
    source_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()
    dirty = bool(subprocess.run(
        ["git", "status", "--porcelain"], cwd=ROOT,
        capture_output=True, text=True, check=True
    ).stdout.strip())
    if dirty:
        raise QualificationRefused("commit the frozen M098 apparatus before arming")
    if not audit_pool(pool)["passed"]:
        raise QualificationRefused("M098 frozen pool fails preflight")
    started = time.time()
    evidence = run_experiment(pool)
    measured, members = mechanism_digest(protocol)
    apparatus, apparatus_members = file_set_digest(protocol, "qualification_apparatus")
    m097 = json.loads(M097_RESULT_PATH.read_text(encoding="utf-8"))
    withdrawn = sorted(path.name for path in EXPERIMENT.glob("WITHDRAWN_RESULT_*.json"))
    result = {
        "schema": RESULT_SCHEMA,
        "milestone": "M098",
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
        "m097_state_digest": m097["scientific_evidence"]["extended_language_state"]["state_digest"],
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
    expected = (EXPERIMENT / "RESULT.json").resolve()
    if not args.arm:
        print("Refusing to acquire M098 without --arm.", file=sys.stderr)
        return 2
    if not args.out or Path(args.out).resolve() != expected:
        print("An armed run must write exactly experiments/M098/RESULT.json.", file=sys.stderr)
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
