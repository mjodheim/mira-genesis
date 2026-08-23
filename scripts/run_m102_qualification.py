"""Run M102's frozen local Track-A qualification after explicit owner arming.

Importing this module or calling ``run_experiment`` on DEVELOPMENT data cannot write a
canonical result.  ``materialize`` additionally requires a frozen protocol, annotated
freeze tag, exact source/pool/capsule bindings, an absent result path, and the explicit
one-attempt owner authorization flag.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "M102"
PROTOCOL_PATH = EXPERIMENT / "PROTOCOL.json"
RESULT_PATH = EXPERIMENT / "RESULT.json"
M101_RESULT_PATH = ROOT / "experiments" / "M101" / "RESULT.json"
M101_CHECK_PATH = ROOT / "experiments" / "M101" / "CHECK_REPORT.json"
ISOLATED_PYTHON = Path(getattr(sys, "_base_executable", sys.executable)).resolve()
RESULT_SCHEMA = "m102-result-v1"
EPHEMERAL_KEYS = {"pid", "process_pids", "search_path", "elapsed_seconds", "started_at_utc"}

from audit_m102_boundaries import audit as audit_boundaries
from author_m102_qualification_pool import audit as audit_pool
from author_m102_qualification_pool import canonical_json, digest, load_pool


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
        "m102_runtime.py": "metamorphosis/m102_runtime.py",
        "run.py": "scripts/run_m102_acquisition_process.py",
    },
    "execution": {
        "m101_executor.py": "metamorphosis/m101_executor.py",
        "m102_executor.py": "metamorphosis/m102_executor.py",
        "run.py": "scripts/run_m102_fresh_process.py",
    },
    "definition_checker": {
        "check_m101_definitions.py": "scripts/check_m101_definitions.py",
        "check_m102_definitions.py": "scripts/check_m102_definitions.py",
    },
}


def build_capsules(base: Path) -> tuple[dict[str, Path], dict[str, dict[str, Any]]]:
    capsules: dict[str, Path] = {}
    reports: dict[str, dict[str, Any]] = {}
    for name, sources in CAPSULE_SOURCES.items():
        capsule = base / f"m102-{name}-capsule"
        capsule.mkdir(parents=True)
        for destination, source in sources.items():
            shutil.copyfile(ROOT / source, capsule / destination)
        actual = sorted(path.name for path in capsule.iterdir())
        if actual != sorted(sources):
            raise QualificationRefused(f"unexpected member in M102 {name} capsule")
        capsule_digest, member_digests = capsule_binding(sources)
        reports[name] = {
            "members": actual,
            "member_digests": member_digests,
            "capsule_digest": capsule_digest,
            "contains_only_bound_members": True,
        }
        capsules[name] = capsule
    return capsules, reports


def _fresh(
    capsule: Path, entry: str, arguments: list[str], *, timeout: int = 120
) -> dict[str, Any]:
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
    for name in ("m101", "state", "events", "demand", "out", "control", "restore"):
        value = options.get(name)
        if value is not None:
            arguments.extend([f"--{name}", str(value)])
    if options.get("register"):
        arguments.append("--register")
    return _fresh(capsule, "run.py", arguments)


def _execution(
    capsule: Path,
    action: str,
    state: Path,
    world: Path,
    *,
    last_write: bool = False,
) -> dict[str, Any]:
    arguments = [action, "--state", str(state), "--world", str(world)]
    if last_write:
        arguments.append("--last-write")
    return _fresh(capsule, "run.py", arguments)


def _definition_check(
    capsule: Path, state: Path, m101_sha256: str, m100_sha256: str
) -> dict[str, Any]:
    return _fresh(
        capsule,
        "check_m102_definitions.py",
        [
            "--state",
            str(state),
            "--expected-m101-sha256",
            m101_sha256,
            "--expected-m100-sha256",
            m100_sha256,
        ],
    )


def _write_json(path: Path, value: Any) -> Path:
    path.write_bytes(canonical_json(value).encode("ascii"))
    return path


def _write_event_list(path: Path, events: list[dict[str, Any]]) -> Path:
    return _write_json(path, events)


def _policy_demand(world: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "m102-policy-demand-v1",
        "world_id": world["id"],
        "role": "policy_producer_trigger",
        "incoming_events": world["incoming_events"],
        "public_lookups": world["public_lookups"],
    }


def _c_demand(world: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "m102-c-demand-v1",
        "world_id": world["id"],
        "role": "sqlite_c_trigger",
        "carrier": "sqlite",
        "slots": world["slots"],
        "public_cases": world["public_cases"],
    }


def _record_execution_world(world: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "m102-record-execution-world-v1",
        "world_id": world["id"],
        "carrier": world["carrier"],
        "slots": world["slots"],
        "cases": world["public_cases"] + world["hidden_cases"],
    }


def _sqlite_execution_world(world: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "m102-sqlite-execution-world-v1",
        "world_id": world["id"],
        "slots": world["slots"],
        "cases": world["public_cases"] + world["hidden_cases"],
    }


def m101_t2_bytes() -> tuple[bytes, dict[str, Any]]:
    result = json.loads(M101_RESULT_PATH.read_text(encoding="utf-8"))
    chronology = result["scientific_evidence"]["state_chronology"]["acquire_and_register_b"]
    state = chronology["runtime"]["acquisition"]["next_state"]
    raw = canonical_json(state).encode("ascii")
    record = result["scientific_evidence"]["states"]["T2"]
    if hashlib.sha256(raw).hexdigest() != record["raw_sha256"]:
        raise QualificationRefused("preserved M101 T2 bytes moved")
    if state["state_digest"] != record["state_digest"]:
        raise QualificationRefused("preserved M101 T2 state digest moved")
    return raw, state


def verify_predecessor(protocol: dict[str, Any]) -> None:
    predecessor = protocol.get("predecessor", {})
    result = json.loads(M101_RESULT_PATH.read_text(encoding="utf-8"))
    checker = json.loads(M101_CHECK_PATH.read_text(encoding="utf-8"))
    result_payload = {key: value for key, value in result.items() if key != "result_digest"}
    if result.get("result_digest") != digest(result_payload):
        raise QualificationRefused("preserved M101 result digest is internally invalid")
    for field in ("result_digest", "stable_evidence_digest"):
        if predecessor.get(field) != result.get(field):
            raise QualificationRefused(f"M101 predecessor {field} moved")
    if predecessor.get("checker_digest") != checker.get("report_digest"):
        raise QualificationRefused("M101 checker digest moved")
    if checker.get("verdict") != "positive" or checker.get("failed") != 0:
        raise QualificationRefused("preserved M101 checker is not positive")
    raw, state = m101_t2_bytes()
    if predecessor.get("m101_t2_raw_sha256") != hashlib.sha256(raw).hexdigest():
        raise QualificationRefused("exact M101 T2 raw binding moved")
    if predecessor.get("m101_t2_state_digest") != state["state_digest"]:
        raise QualificationRefused("exact M101 T2 state binding moved")
    if predecessor.get("m100_sha256") != state["m100_sha256"]:
        raise QualificationRefused("embedded M100 binding moved")
    tag = predecessor.get("preservation_tag")
    if not isinstance(tag, str) or not tag:
        raise QualificationRefused("M101 preservation tag is absent")
    tag_commit = subprocess.run(
        ["git", "rev-parse", f"refs/tags/{tag}^{{commit}}"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    if tag_commit != predecessor.get("preservation_commit"):
        raise QualificationRefused("M101 preservation tag commit moved")
    for path in ("experiments/M101/RESULT.json", "experiments/M101/CHECK_REPORT.json"):
        tagged = subprocess.run(
            ["git", "rev-parse", f"{tag_commit}:{path}"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        live = subprocess.run(
            ["git", "hash-object", path],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        if tagged != live:
            raise QualificationRefused(f"preserved M101 artifact moved: {path}")


def _state_record(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    state = json.loads(raw.decode("ascii"))
    return {
        "raw_sha256": hashlib.sha256(raw).hexdigest(),
        "state_digest": state.get("state_digest"),
        "m101_sha256": state.get("m101_sha256"),
        "policy_id": state.get("policy", {}).get("policy_id"),
        "policy_origin": state.get("policy", {}).get("origin"),
        "event_count": len(state.get("journal", [])),
        "event_ids": [item.get("event_id") for item in state.get("journal", [])],
        "c_definition_id": (state.get("c_definition") or {}).get("definition_id"),
        "state": state,
    }


def _runtime_rows(value: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if isinstance(value, dict):
        if value.get("schema") in {"m102-acquisition-process-v1", "m102-fresh-executor-v1"}:
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
        raise QualificationRefused("frozen M102 population requires armed canonical materialize")
    worlds = [entry["world"] for entry in pool["entries"]]
    by_role: dict[str, list[dict[str, Any]]] = {}
    entry_digest_by_id: dict[str, str] = {}
    for entry in pool["entries"]:
        world = entry["world"]
        by_role.setdefault(world["role"], []).append(world)
        entry_digest_by_id[world["id"]] = entry["entry_digest"]
    if {role: len(by_role.get(role, [])) for role in pool["role_counts"]} != pool["role_counts"]:
        raise QualificationRefused("M102 population role census is invalid")
    policy_world = by_role["policy_producer_trigger"][0]
    record_worlds = by_role["record_retention"]
    c_trigger = by_role["sqlite_c_trigger"][0]
    sqlite_worlds = [c_trigger, *by_role["sqlite_c_reuse"]]
    m101_a_world = by_role["m101_a_conservation"][0]
    m101_b_world = by_role["m101_b_conservation"][0]
    m100_worlds = by_role["m100_conservation"]

    with tempfile.TemporaryDirectory(prefix="m102-run-") as temporary:
        base = Path(temporary)
        payloads = base / "payloads"
        payloads.mkdir()
        capsules, capsule_reports = build_capsules(base)
        predecessor_raw, predecessor_state = m101_t2_bytes()
        predecessor_path = base / "M101-T2.json"
        predecessor_path.write_bytes(predecessor_raw)
        m101_sha256 = hashlib.sha256(predecessor_raw).hexdigest()
        m100_sha256 = predecessor_state["m100_sha256"]

        prior_events = [event for world in record_worlds for event in world["events"]]
        prior_events_path = _write_event_list(payloads / "prior-events.json", prior_events)
        incoming_path = _write_event_list(
            payloads / "policy-incoming.json", policy_world["incoming_events"]
        )
        policy_demand_path = _write_json(
            payloads / "policy-public-demand.json", _policy_demand(policy_world)
        )
        sqlite_events_path = _write_event_list(
            payloads / "sqlite-events.json", c_trigger["events"]
        )
        c_demand_path = _write_json(payloads / "c-public-demand.json", _c_demand(c_trigger))

        u0_path = base / "U0.json"
        create_u0 = _acquisition(
            capsules["acquisition"],
            "create-state",
            m101=predecessor_path,
            events=prior_events_path,
            out=u0_path,
        )
        u0_bytes = u0_path.read_bytes()
        k_built = _acquisition(
            capsules["acquisition"],
            "acquire-policy",
            state=u0_path,
            demand=policy_demand_path,
        )
        u0_unchanged_after_k_build = u0_path.read_bytes() == u0_bytes
        flat_fail_closed = _acquisition(
            capsules["acquisition"],
            "register-events",
            state=u0_path,
            events=incoming_path,
        )
        destructive_path = base / "U0-flat-last-write.json"
        build_destructive = _acquisition(
            capsules["acquisition"],
            "force-last-write",
            state=u0_path,
            events=incoming_path,
            out=destructive_path,
        )
        u1_path = base / "U1.json"
        acquire_k = _acquisition(
            capsules["acquisition"],
            "acquire-policy",
            state=u0_path,
            demand=policy_demand_path,
            register=True,
            out=u1_path,
        )
        u1_bytes = u1_path.read_bytes()
        validate_u1 = _definition_check(
            capsules["definition_checker"], u1_path, m101_sha256, m100_sha256
        )

        # Hidden record material is first written only after the K producer returned and U1 exists.
        record_paths = {
            world["id"]: _write_json(
                payloads / f"record-{world['id']}.json", _record_execution_world(world)
            )
            for world in record_worlds
        }
        retained_u1 = [
            {
                "entry": world["id"],
                "entry_digest": entry_digest_by_id[world["id"]],
                "fresh": _execution(
                    capsules["execution"],
                    "execute-record",
                    u1_path,
                    record_paths[world["id"]],
                ),
            }
            for world in record_worlds
        ]
        destructive_record = [
            {
                "entry": world["id"],
                "entry_digest": entry_digest_by_id[world["id"]],
                "fresh": _execution(
                    capsules["execution"],
                    "execute-record",
                    destructive_path,
                    record_paths[world["id"]],
                    last_write=True,
                ),
            }
            for world in record_worlds
        ]

        pre_c_path = base / "U1-with-sqlite-events.json"
        register_sqlite = _acquisition(
            capsules["acquisition"],
            "register-events",
            state=u1_path,
            events=sqlite_events_path,
            out=pre_c_path,
        )
        pre_c_bytes = pre_c_path.read_bytes()
        flat_joint_path = base / "flat-joint-control.json"
        flat_joint_events_path = _write_event_list(
            payloads / "flat-joint-events.json",
            [*policy_world["incoming_events"], *c_trigger["events"]],
        )
        build_flat_joint = _acquisition(
            capsules["acquisition"],
            "force-last-write",
            state=u0_path,
            events=flat_joint_events_path,
            out=flat_joint_path,
        )
        c_without_k = _acquisition(
            capsules["acquisition"],
            "acquire-c",
            state=flat_joint_path,
            demand=c_demand_path,
        )
        c_built = _acquisition(
            capsules["acquisition"],
            "acquire-c",
            state=pre_c_path,
            demand=c_demand_path,
        )
        pre_c_unchanged_after_c_build = pre_c_path.read_bytes() == pre_c_bytes
        u2_path = base / "U2.json"
        acquire_c = _acquisition(
            capsules["acquisition"],
            "acquire-c",
            state=pre_c_path,
            demand=c_demand_path,
            register=True,
            out=u2_path,
        )
        u2_bytes = u2_path.read_bytes()
        validate_u2 = _definition_check(
            capsules["definition_checker"], u2_path, m101_sha256, m100_sha256
        )

        # Qualification hidden/reuse worlds are materialised only after U2 producer death.
        sqlite_paths = {
            world["id"]: _write_json(
                payloads / f"sqlite-{world['id']}.json", _sqlite_execution_world(world)
            )
            for world in sqlite_worlds
        }
        sqlite_executions = [
            {
                "entry": world["id"],
                "role": world["role"],
                "entry_digest": entry_digest_by_id[world["id"]],
                "fresh": _execution(
                    capsules["execution"],
                    "execute-sqlite",
                    u2_path,
                    sqlite_paths[world["id"]],
                ),
            }
            for world in sqlite_worlds
        ]
        retained_u2 = [
            {
                "entry": world["id"],
                "entry_digest": entry_digest_by_id[world["id"]],
                "fresh": _execution(
                    capsules["execution"],
                    "execute-record",
                    u2_path,
                    record_paths[world["id"]],
                ),
            }
            for world in record_worlds
        ]

        m101_worlds = [m101_a_world, m101_b_world]
        m101_paths = {
            world["id"]: _write_json(payloads / f"m101-{world['id']}.json", world)
            for world in m101_worlds
        }
        m101_conservation = [
            {
                "entry": world["id"],
                "action": (
                    "execute-m101-a"
                    if world["role"] == "m101_a_conservation"
                    else "execute-m101-b"
                ),
                "entry_digest": entry_digest_by_id[world["id"]],
                "fresh": _execution(
                    capsules["execution"],
                    (
                        "execute-m101-a"
                        if world["role"] == "m101_a_conservation"
                        else "execute-m101-b"
                    ),
                    u2_path,
                    m101_paths[world["id"]],
                ),
            }
            for world in m101_worlds
        ]
        m100_paths = {
            world["id"]: _write_json(payloads / f"m100-{world['id']}.json", world)
            for world in m100_worlds
        }
        m100_conservation = [
            {
                "entry": world["id"],
                "operation_index": world["operation_index"],
                "entry_digest": entry_digest_by_id[world["id"]],
                "fresh": _execution(
                    capsules["execution"],
                    "execute-m100",
                    u2_path,
                    m100_paths[world["id"]],
                ),
            }
            for world in m100_worlds
        ]

        control_specs = {
            "flat_policy": "flat-policy",
            "policy_ablation": "policy-ablate",
            "c_mutation": "c-duplicate",
            "c_ablation": "c-ablate",
            "b_mutation": "b-order",
            "b_ablation": "b-ablate",
            "corruption": "corrupt",
        }
        control_paths: dict[str, Path] = {}
        control_builds: dict[str, dict[str, Any]] = {}
        for label, control in control_specs.items():
            path = base / f"control-{label}.json"
            control_paths[label] = path
            control_builds[label] = _acquisition(
                capsules["acquisition"],
                "state-control",
                state=u2_path,
                control=control,
                out=path,
            )
        trigger_path = sqlite_paths[c_trigger["id"]]
        control_c_executions = {
            label: _execution(
                capsules["execution"], "execute-sqlite", path, trigger_path
            )
            for label, path in control_paths.items()
        }
        unrelated_controls = {
            "record_survives_c_mutation": _execution(
                capsules["execution"],
                "execute-record",
                control_paths["c_mutation"],
                record_paths[record_worlds[2]["id"]],
            ),
            "record_survives_b_mutation": _execution(
                capsules["execution"],
                "execute-record",
                control_paths["b_mutation"],
                record_paths[record_worlds[2]["id"]],
            ),
            "m101_b_survives_c_ablation": _execution(
                capsules["execution"],
                "execute-m101-b",
                control_paths["c_ablation"],
                m101_paths[m101_b_world["id"]],
            ),
        }

        restored_path = base / "U2-restored.json"
        rollback_process = _acquisition(
            capsules["acquisition"],
            "rollback",
            state=control_paths["c_mutation"],
            restore=u2_path,
            out=restored_path,
        )
        rollback_record = [
            _execution(
                capsules["execution"],
                "execute-record",
                restored_path,
                record_paths[world["id"]],
            )
            for world in record_worlds
        ]
        rollback_sqlite = [
            _execution(
                capsules["execution"],
                "execute-sqlite",
                restored_path,
                sqlite_paths[world["id"]],
            )
            for world in sqlite_worlds
        ]
        rollback_m101 = [
            _execution(
                capsules["execution"],
                (
                    "execute-m101-a"
                    if world["role"] == "m101_a_conservation"
                    else "execute-m101-b"
                ),
                restored_path,
                m101_paths[world["id"]],
            )
            for world in m101_worlds
        ]
        rollback_m100 = [
            _execution(
                capsules["execution"],
                "execute-m100",
                restored_path,
                m100_paths[world["id"]],
            )
            for world in m100_worlds
        ]

        u0_state = json.loads(u0_bytes.decode("ascii"))
        u1_state = json.loads(u1_bytes.decode("ascii"))
        differing_u0_u1 = sorted(
            key for key in u0_state if u0_state[key] != u1_state[key]
        )
        evidence: dict[str, Any] = {
            "schema": "m102-scientific-evidence-v1",
            "capsules": capsule_reports,
            "boundary_audit": audit_boundaries(),
            "pool_preflight": audit_pool(pool),
            "state_chronology": {
                "create_u0": create_u0,
                "k_built_not_registered": k_built,
                "u0_unchanged_after_k_build": u0_unchanged_after_k_build,
                "flat_registration_fails_closed": flat_fail_closed,
                "build_destructive_flat_control": build_destructive,
                "acquire_and_register_k": acquire_k,
                "register_sqlite_events": register_sqlite,
                "build_flat_joint_control": build_flat_joint,
                "c_absent_without_k_reach": c_without_k,
                "c_built_not_registered": c_built,
                "pre_c_unchanged_after_c_build": pre_c_unchanged_after_c_build,
                "acquire_and_register_c": acquire_c,
            },
            "definition_validation": {"U1": validate_u1, "U2": validate_u2},
            "states": {
                "U0": _state_record(u0_path),
                "U1": _state_record(u1_path),
                "PRE_C": _state_record(pre_c_path),
                "U2": _state_record(u2_path),
                "flat_destructive": _state_record(destructive_path),
                "flat_joint": _state_record(flat_joint_path),
                "m101_bytes_conserved_u0_u1_u2": all(
                    json.loads(path.read_text(encoding="ascii"))["m101_ascii"].encode("ascii")
                    == predecessor_raw
                    for path in (u0_path, u1_path, u2_path)
                ),
                "u0_u1_differing_keys": differing_u0_u1,
                "u1_prefix_conserved_in_u2": (
                    json.loads(u2_bytes.decode("ascii"))["journal"][: len(u1_state["journal"])]
                    == u1_state["journal"]
                ),
            },
            "interference": {
                "flat_closure": k_built.get("runtime", {})
                .get("acquisition", {})
                .get("flat_closure"),
                "retained_after_u1": retained_u1,
                "destructive_no_upgrade": destructive_record,
            },
            "sqlite_execution": sqlite_executions,
            "continual_retention_after_u2": retained_u2,
            "m101_conservation": m101_conservation,
            "m100_conservation": m100_conservation,
            "causal_controls": {
                "builds": control_builds,
                "c_executions": control_c_executions,
                "unrelated_capabilities": unrelated_controls,
            },
            "rollback": {
                "accepted_raw_sha256": hashlib.sha256(u2_bytes).hexdigest(),
                "fault_raw_sha256": hashlib.sha256(
                    control_paths["c_mutation"].read_bytes()
                ).hexdigest(),
                "fault_differs_from_accepted": (
                    control_paths["c_mutation"].read_bytes() != u2_bytes
                ),
                "restore_process": rollback_process,
                "restored_bytes_equal": restored_path.read_bytes() == u2_bytes,
                "restored_raw_sha256": hashlib.sha256(restored_path.read_bytes()).hexdigest(),
                "record": rollback_record,
                "sqlite": rollback_sqlite,
                "m101": rollback_m101,
                "m100": rollback_m100,
            },
            "information_boundary": {
                "policy_acquisition_received_only_public_lookup_ids": [
                    item["case_id"] for item in policy_world["public_lookups"]
                ],
                "policy_hidden_lookup_ids": [
                    item["case_id"] for item in policy_world["hidden_lookups"]
                ],
                "c_acquisition_received_only_public_case_ids": [
                    item["case_id"] for item in c_trigger["public_cases"]
                ],
                "c_hidden_case_ids": [item["case_id"] for item in c_trigger["hidden_cases"]],
                "record_hidden_materialized_after_u1_producer_exit": True,
                "sqlite_hidden_and_reuse_materialized_after_u2_producer_exit": True,
                "qualification_pool_absent_from_acquisition_capsule": True,
                "result_checker_absent_from_acquisition_and_execution_capsules": True,
            },
            "baseline_parity": {
                "same_predecessor_sha256": m101_sha256,
                "same_runtime_capsule": capsule_reports["acquisition"]["capsule_digest"],
                "same_c_public_demand_digest": digest(_c_demand(c_trigger)),
                "no_k_state_contains_same_prior_incoming_and_sqlite_events": True,
                "no_k_failure_reason": c_without_k.get("runtime", {})
                .get("acquisition", {})
                .get("reason"),
                "only_retained_arm_has_acquired_policy": True,
                "flat_image_budget_independent": k_built.get("runtime", {})
                .get("acquisition", {})
                .get("flat_closure", {})
                .get("budget_independent"),
            },
        }

    runtime_rows = _runtime_rows(evidence)
    for ordinal, row in enumerate(runtime_rows, start=1):
        row["invocation_ordinal"] = ordinal
    repository_text = str(ROOT).casefold()
    evidence["process_boundary"] = {
        "process_pids": [row.get("pid") for row in runtime_rows],
        "fresh_process_invocations": len(runtime_rows),
        "definition_checker_invocations": 2,
        "pid_records_present": all(isinstance(row.get("pid"), int) for row in runtime_rows),
        "invocation_ordinals": [row["invocation_ordinal"] for row in runtime_rows],
        "all_invocation_ordinals_unique_and_contiguous": [
            row["invocation_ordinal"] for row in runtime_rows
        ]
        == list(range(1, len(runtime_rows) + 1)),
        "synchronous_process_exit_before_next_launch": True,
        "fresh_subprocess_launch_source_audited": evidence["boundary_audit"]["checks"][
            "qualification_runner_launches_one_isolated_synchronous_subprocess_per_invocation"
        ],
        "all_invocations_isolated": all(row.get("isolated_mode") is True for row in runtime_rows),
        "no_project_modules_imported": all(not row.get("imported_project_modules") for row in runtime_rows),
        "repository_absent_from_search_paths": all(
            all(repository_text not in str(path).casefold() for path in row.get("search_path", []))
            for row in runtime_rows
        ),
        "zero_model_calls": all(row.get("model_calls") == 0 for row in runtime_rows),
        "zero_network_calls": all(row.get("network_calls") == 0 for row in runtime_rows),
        "zero_remote_execution_calls": all(
            row.get("remote_execution_calls") == 0 for row in runtime_rows
        ),
    }
    return evidence


def require_frozen(protocol: dict[str, Any], pool: dict[str, Any]) -> None:
    if protocol.get("status") != "frozen" or protocol.get("canonical_run_allowed") is not True:
        raise QualificationRefused("M102 protocol is not frozen and armed-capable")
    if protocol.get("attempt") != 1 or pool.get("status") != "frozen":
        raise QualificationRefused("M102 attempt or population is not frozen")
    if protocol.get("qualification_population", {}).get("pool_digest") != pool.get("pool_digest"):
        raise QualificationRefused("M102 protocol does not bind the frozen population")
    verify_predecessor(protocol)
    immutable: dict[str, str] = {}
    for section, path_key, digest_key in (
        ("pre_registration", "path", "raw_sha256"),
        ("pre_registration", "draft_path", "draft_raw_sha256"),
        ("publication", "review_record", "review_raw_sha256"),
    ):
        record = protocol.get(section, {})
        path = record.get(path_key)
        expected = record.get(digest_key)
        if not isinstance(path, str) or not isinstance(expected, str):
            raise QualificationRefused(f"M102 immutable {section}/{path_key} binding is invalid")
        immutable[path] = expected
    for path, expected in immutable.items():
        if hashlib.sha256((ROOT / path).read_bytes()).hexdigest() != expected:
            raise QualificationRefused(f"M102 immutable record moved: {path}")
    for section in ("mechanism", "qualification_apparatus", "checker"):
        declared = protocol.get(section, {})
        measured, members = file_set_digest(list(declared.get("files", [])))
        if declared.get("digest") != measured or declared.get("member_digests") != members:
            raise QualificationRefused(f"M102 {section} moved after freeze")
    for name, sources in CAPSULE_SOURCES.items():
        measured, members = capsule_binding(sources)
        declared = protocol.get("capsules", {}).get(name, {})
        if declared.get("digest") != measured or declared.get("member_digests") != members:
            raise QualificationRefused(f"M102 {name} capsule moved after freeze")
    if protocol.get("stable_projection") != {
        "excluded_keys": sorted(EPHEMERAL_KEYS),
        "recursive": True,
        "policy_frozen_before_qualification": True,
    }:
        raise QualificationRefused("M102 stable projection policy moved")
    sqlite_identity = protocol.get("sqlite_identity", {})
    if sqlite_identity != {
        "module": "sqlite3",
        "sqlite_version": sqlite3.sqlite_version,
        "sqlite_version_info": list(sqlite3.sqlite_version_info),
    }:
        raise QualificationRefused("M102 SQLite identity differs from frozen binding")

    freeze = protocol.get("freeze", {})
    source_commit = freeze.get("source_commit")
    tag = freeze.get("tag")
    if not isinstance(source_commit, str) or not isinstance(tag, str):
        raise QualificationRefused("M102 freeze commit/tag binding is invalid")
    tag_type = subprocess.run(
        ["git", "cat-file", "-t", f"refs/tags/{tag}"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    if tag_type != "tag":
        raise QualificationRefused("M102 freeze tag is not annotated")
    tag_commit = subprocess.run(
        ["git", "rev-parse", f"refs/tags/{tag}^{{commit}}"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    tag_parent = subprocess.run(
        ["git", "rev-parse", f"{tag_commit}^"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    if tag_parent != source_commit:
        raise QualificationRefused("M102 freeze tag chronology moved")
    for section in ("mechanism", "qualification_apparatus", "checker"):
        for path in protocol[section]["files"]:
            source_object = subprocess.run(
                ["git", "rev-parse", f"{source_commit}:{path}"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
            live_object = subprocess.run(
                ["git", "hash-object", path],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
            if source_object != live_object:
                raise QualificationRefused(f"M102 frozen source moved: {path}")
    protocol_tagged = subprocess.run(
        ["git", "rev-parse", f"{tag_commit}:experiments/M102/PROTOCOL.json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    protocol_live = subprocess.run(
        ["git", "hash-object", "experiments/M102/PROTOCOL.json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    if protocol_tagged != protocol_live:
        raise QualificationRefused("M102 final protocol differs from tagged freeze")


def materialize(*, authorized_by_owner: bool, understand_unique_attempt: bool) -> dict[str, Any]:
    if not authorized_by_owner or not understand_unique_attempt:
        raise QualificationRefused("M102 canonical attempt lacks explicit owner authorization")
    if RESULT_PATH.exists():
        raise QualificationRefused("M102 canonical result already exists; rerun is forbidden")
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    pool = load_pool()
    require_frozen(protocol, pool)
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    if status:
        raise QualificationRefused("working tree must be clean before the unique M102 attempt")
    started = time.time()
    evidence = run_experiment(pool, allow_frozen=True)
    elapsed = time.time() - started
    result: dict[str, Any] = {
        "schema": RESULT_SCHEMA,
        "milestone": "M102",
        "attempt": 1,
        "canonical": True,
        "reroll": False,
        "source_commit": protocol["freeze"]["source_commit"],
        "freeze_tag": protocol["freeze"]["tag"],
        "protocol_digest": digest(protocol),
        "pool_digest": pool["pool_digest"],
        "started_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started)),
        "elapsed_seconds": elapsed,
        "model_calls": 0,
        "network_calls": 0,
        "remote_execution_calls": 0,
        "scientific_evidence": evidence,
    }
    result["stable_evidence_digest"] = digest(stable_projection(evidence))
    result["result_digest"] = digest(result)
    with RESULT_PATH.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(result, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    armed = subparsers.add_parser("materialize")
    armed.add_argument("--authorized-by-owner", action="store_true")
    armed.add_argument("--i-understand-this-is-the-only-canonical-attempt", action="store_true")
    arguments = parser.parse_args()
    try:
        result = materialize(
            authorized_by_owner=bool(arguments.authorized_by_owner),
            understand_unique_attempt=bool(
                arguments.i_understand_this_is_the_only_canonical_attempt
            ),
        )
    except Exception as error:
        print(
            json.dumps(
                {
                    "schema": RESULT_SCHEMA,
                    "materialized": False,
                    "failed_closed": True,
                    "error": f"{type(error).__name__}: {error}",
                },
                sort_keys=True,
            )
        )
        return 3
    print(json.dumps({"materialized": True, "result_digest": result["result_digest"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
