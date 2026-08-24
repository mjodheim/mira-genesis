"""Frozen-shape M103 qualification runner; canonical materialization is fail-closed."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sqlite3
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "M103"
DEVELOPMENT_PATH = EXPERIMENT / "DEVELOPMENT_FIXTURE.json"
POOL_PATH = EXPERIMENT / "QUALIFICATION_POOL.json"
PREDECESSOR_CONSERVATION_PATH = EXPERIMENT / "PREDECESSOR_CONSERVATION.json"
PROTOCOL_PATH = EXPERIMENT / "PROTOCOL.json"
RESULT_PATH = EXPERIMENT / "RESULT.json"
CHECK_PATH = EXPERIMENT / "CHECK_REPORT.json"
M102_RESULT_PATH = ROOT / "experiments" / "M102" / "RESULT.json"
M102_CHECK_PATH = ROOT / "experiments" / "M102" / "CHECK_REPORT.json"
ISOLATED_PYTHON = Path(sys.executable).resolve()

M102_RESULT_DIGEST = "92d4ed3ecde9bc48a930d0591a562dedc754bf8ab00eb5a20528be76325624fa"
M102_STABLE_EVIDENCE_DIGEST = "eab68a79c0617d2d4ca48aaf0cd71630aa3a4e4e67b5b4c9b63f4e318ee170fb"
M102_U2_RAW_SHA256 = "3bad4d5400e8d9a11b15ba596336925823ffb4064a5bbe38f93f64b7384a198d"
M102_U2_STATE_DIGEST = "fbf7b0232aa8adf4e67513719c63f19f28c1b7e8b86437af1135ff18335d3a0e"
M101_T2_RAW_SHA256 = "cd5b5994e5a252599807e9ddc2b5733efaf176fe23dd05055b50d883bde0b7a0"
M100_S3_RAW_SHA256 = "fba316a10f294fea4124e460e5a7987cc00b46d3d0e32260ea8cad80b39cf9ac"
POOL_DIGEST = "1f1b5d4289685f8401564d0f0e5d7c4f8ffda10561fbeba9ec8a36114e22b59e"
DEVELOPMENT_DIGEST = "12c099dc2ba39fc387159f7664197af8c2f604d5938f2a61273c5989ae3161ad"
PREDECESSOR_CONSERVATION_DIGEST = (
    "7bfb93b917f78f5f1c2e2c16cee587f8eb50bdd7f9f98d7e922b6ae6506a51ea"
)
PREDECESSOR_CONSERVATION_RAW_SHA256 = (
    "aff59b1527d4cc026886bee233ec2e6f0ba16e14fb11487828a3c2af7cb5d33f"
)

EPHEMERAL_KEYS = {
    "pid",
    "process_pids",
    "search_path",
    "elapsed_seconds",
    "started_at_utc",
    "python_executable",
    "configparser_module",
}


class QualificationRefused(RuntimeError):
    pass


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("ascii")).hexdigest()


def stable_projection(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: stable_projection(item)
            for key, item in sorted(value.items())
            if key not in EPHEMERAL_KEYS and not key.endswith(("_pid", "_pids"))
        }
    if isinstance(value, list):
        return [stable_projection(item) for item in value]
    return value


def file_set_digest(paths: list[str]) -> tuple[str, dict[str, str]]:
    members = {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in paths}
    return digest(members), members


CAPSULE_SOURCES = {
    "runtime": {
        "m100_runtime.py": "metamorphosis/m100_runtime.py",
        "m101_runtime.py": "metamorphosis/m101_runtime.py",
        "m102_runtime.py": "metamorphosis/m102_runtime.py",
        "m103_runtime.py": "metamorphosis/m103_runtime.py",
        "run.py": "scripts/run_m103_process.py",
    },
    "definition_checker": {
        "check_m101_definitions.py": "scripts/check_m101_definitions.py",
        "check_m102_definitions.py": "scripts/check_m102_definitions.py",
        "check_m103_definitions.py": "scripts/check_m103_definitions.py",
        "check_m103_closure.py": "scripts/check_m103_closure.py",
    },
    "predecessor_executor": {
        "m101_executor.py": "metamorphosis/m101_executor.py",
        "m102_executor.py": "metamorphosis/m102_executor.py",
        "run.py": "scripts/run_m102_fresh_process.py",
    },
}


def capsule_binding(sources: dict[str, str]) -> tuple[str, dict[str, str]]:
    members = {
        destination: hashlib.sha256((ROOT / source).read_bytes()).hexdigest()
        for destination, source in sources.items()
    }
    return digest(members), members


def build_capsules(base: Path) -> tuple[dict[str, Path], dict[str, dict[str, Any]]]:
    capsules: dict[str, Path] = {}
    reports: dict[str, dict[str, Any]] = {}
    for name, sources in CAPSULE_SOURCES.items():
        capsule = base / f"m103-{name}-capsule"
        capsule.mkdir(parents=True)
        for destination, source in sources.items():
            shutil.copyfile(ROOT / source, capsule / destination)
        actual = sorted(path.name for path in capsule.iterdir())
        if actual != sorted(sources):
            raise QualificationRefused(f"unexpected member in M103 {name} capsule")
        capsule_digest, member_digests = capsule_binding(sources)
        reports[name] = {
            "members": actual,
            "member_digests": member_digests,
            "capsule_digest": capsule_digest,
            "contains_only_bound_members": True,
        }
        capsules[name] = capsule
    return capsules, reports


def _fresh(capsule: Path, entry: str, arguments: list[str], *, timeout: int = 120) -> dict[str, Any]:
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


def _process(capsule: Path, action: str, **options: Any) -> dict[str, Any]:
    arguments = [action]
    for name in (
        "m102",
        "state",
        "demand",
        "world",
        "out",
        "restore",
        "control",
        "repetitions",
    ):
        value = options.get(name)
        if value is not None:
            arguments.extend([f"--{name}", str(value)])
    if options.get("register"):
        arguments.append("--register")
    return _fresh(capsule, "run.py", arguments)


def _definition_check(capsule: Path, state: Path) -> dict[str, Any]:
    return _fresh(
        capsule,
        "check_m103_definitions.py",
        [
            "--state",
            str(state),
            "--expected-m102-sha256",
            M102_U2_RAW_SHA256,
            "--expected-m102-state-digest",
            M102_U2_STATE_DIGEST,
            "--expected-m101-sha256",
            M101_T2_RAW_SHA256,
            "--expected-m100-sha256",
            M100_S3_RAW_SHA256,
        ],
    )


def _closure_check(capsule: Path, state: Path, demand: Path) -> dict[str, Any]:
    return _fresh(
        capsule,
        "check_m103_closure.py",
        ["--state", str(state), "--demand", str(demand)],
    )


def _predecessor_execution(
    capsule: Path, action: str, state: Path, world: Path
) -> dict[str, Any]:
    return _fresh(
        capsule,
        "run.py",
        [action, "--state", str(state), "--world", str(world)],
    )


def _write_json(path: Path, value: Any) -> Path:
    path.write_bytes(canonical_json(value).encode("ascii"))
    return path


def m102_u2_bytes() -> tuple[bytes, dict[str, Any]]:
    result = json.loads(M102_RESULT_PATH.read_text(encoding="utf-8"))
    if result.get("result_digest") != M102_RESULT_DIGEST:
        raise QualificationRefused("M102 result digest changed")
    if result.get("stable_evidence_digest") != M102_STABLE_EVIDENCE_DIGEST:
        raise QualificationRefused("M102 stable evidence digest changed")
    state = result["scientific_evidence"]["states"]["U2"]["state"]
    raw = canonical_json(state).encode("ascii")
    facts = {
        "result_digest": result["result_digest"],
        "stable_evidence_digest": result["stable_evidence_digest"],
        "u2_raw_sha256": hashlib.sha256(raw).hexdigest(),
        "u2_state_digest": state["state_digest"],
    }
    if facts["u2_raw_sha256"] != M102_U2_RAW_SHA256:
        raise QualificationRefused("M102 U2 raw bytes changed")
    if facts["u2_state_digest"] != M102_U2_STATE_DIGEST:
        raise QualificationRefused("M102 U2 state digest changed")
    checker = json.loads(M102_CHECK_PATH.read_text(encoding="utf-8"))
    if checker.get("verdict") != "positive" or checker.get("passed") != 15:
        raise QualificationRefused("M102 independent positive verdict is unavailable")
    return raw, facts


def verify_pool(pool: dict[str, Any]) -> dict[str, Any]:
    payload = {key: value for key, value in pool.items() if key != "pool_digest"}
    measured = digest(payload)
    checks = {
        "schema": pool.get("schema") == "m103-qualification-pool-v1",
        "digest": pool.get("pool_digest") == measured == POOL_DIGEST,
        "qualification_only": pool.get("qualification_only") is True,
        "producer_absent": pool.get("producer_fixture_included") is False,
        "development_binding": pool.get("development_fixture_digest") == DEVELOPMENT_DIGEST,
        "record_count": pool.get("record_count") == 11,
        "hidden_case_count": pool.get("hidden_case_count") == 16,
        "configuration_worlds": len(pool.get("configuration", {}).get("hidden_worlds", [])) == 4,
        "filesystem_worlds": len(pool.get("filesystem", {}).get("hidden_worlds", [])) == 4,
    }
    return {"confirmed": all(checks.values()), "checks": checks, "measured_digest": measured}


def verify_predecessor_conservation_fixture(fixture: dict[str, Any]) -> dict[str, Any]:
    payload = {key: value for key, value in fixture.items() if key != "fixture_digest"}
    measured = digest(payload)
    entries = fixture.get("entries", [])
    actions = [entry.get("action") for entry in entries if isinstance(entry, dict)]
    checks = {
        "schema": fixture.get("schema") == "m103-predecessor-conservation-fixture-v1",
        "digest": fixture.get("fixture_digest")
        == measured
        == PREDECESSOR_CONSERVATION_DIGEST,
        "entry_count": fixture.get("entry_count") == len(entries) == 7,
        "action_census": actions.count("execute-record") == 1
        and actions.count("execute-sqlite") == 1
        and actions.count("execute-m101-a") == 1
        and actions.count("execute-m101-b") == 1
        and actions.count("execute-m100") == 3,
    }
    return {"confirmed": all(checks.values()), "checks": checks, "measured_digest": measured}


def _confirmed(result: dict[str, Any]) -> bool:
    return result.get("returncode") == 0 and result.get("runtime", {}).get("confirmed") is True


def _refused(result: dict[str, Any]) -> bool:
    return result.get("returncode") in {1, 3} and result.get("runtime", {}).get("confirmed") is False


def _execution_all_passed(result: dict[str, Any]) -> bool:
    if not _confirmed(result):
        return False
    execution = result.get("runtime", {}).get("execution", {})
    if execution.get("confirmed") is not True:
        return False
    if "passed" in execution or "total" in execution:
        return execution.get("passed") == execution.get("total")
    return execution.get("hidden_passed") == execution.get("hidden_total")


def _materialize_worlds(base: Path, name: str, worlds: list[dict[str, Any]]) -> list[Path]:
    paths: list[Path] = []
    for index, world in enumerate(worlds):
        paths.append(_write_json(base / f"{name}-{index}.json", world))
    return paths


def run_experiment(pool: dict[str, Any]) -> dict[str, Any]:
    pool_preflight = verify_pool(pool)
    if not pool_preflight["confirmed"]:
        raise QualificationRefused("M103 qualification pool preflight failed")
    development = json.loads(DEVELOPMENT_PATH.read_text(encoding="ascii"))
    if development.get("fixture_digest") != DEVELOPMENT_DIGEST:
        raise QualificationRefused("M103 DEVELOPMENT fixture digest changed")
    predecessor_conservation_fixture = json.loads(
        PREDECESSOR_CONSERVATION_PATH.read_text(encoding="ascii")
    )
    predecessor_conservation_preflight = verify_predecessor_conservation_fixture(
        predecessor_conservation_fixture
    )
    if not predecessor_conservation_preflight["confirmed"]:
        raise QualificationRefused("M103 predecessor-conservation fixture preflight failed")
    predecessor_raw, predecessor_facts = m102_u2_bytes()

    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="m103-run-") as temp:
        base = Path(temp)
        capsules, capsule_reports = build_capsules(base)
        runtime_capsule = capsules["runtime"]
        checker_capsule = capsules["definition_checker"]
        predecessor_executor_capsule = capsules["predecessor_executor"]

        predecessor_path = base / "m102-u2.json"
        predecessor_path.write_bytes(predecessor_raw)
        producer_path = _write_json(base / "development-producer.json", development["producer"])
        no_limit_path = _write_json(
            base / "development-no-limitation.json", development["non_discriminating_control"]
        )
        development_ambiguity_path = _write_json(
            base / "development-ambiguity.json", development["ambiguous_control"]
        )

        v0_path = base / "v0.json"
        create_v0 = _process(
            runtime_capsule, "create-state", m102=predecessor_path, out=v0_path
        )
        if not _confirmed(create_v0):
            raise QualificationRefused("M103 V0 creation failed")
        v0_raw = v0_path.read_bytes()
        development_closure = _closure_check(checker_capsule, v0_path, producer_path)

        built_only = _process(
            runtime_capsule,
            "acquire-constructor",
            state=v0_path,
            demand=producer_path,
        )
        no_limitation = _process(
            runtime_capsule,
            "acquire-constructor",
            state=v0_path,
            demand=no_limit_path,
        )
        v1_path = base / "v1.json"
        acquire_s_prime = _process(
            runtime_capsule,
            "acquire-constructor",
            state=v0_path,
            demand=producer_path,
            register=True,
            out=v1_path,
        )
        if not _confirmed(acquire_s_prime):
            raise QualificationRefused("M103 S-prime acquisition failed")
        v1_raw = v1_path.read_bytes()
        s_prime_producer_pid = acquire_s_prime["runtime"]["pid"]

        # Qualification-only bytes first enter the capsule inputs after S-prime's process returned.
        config_demand_path = _write_json(
            base / "qualification-configuration-demand.json",
            pool["configuration"]["acquisition"],
        )
        qualification_ambiguity_path = _write_json(
            base / "qualification-ambiguity.json", pool["ambiguous_control"]
        )
        config_world_paths = _materialize_worlds(
            base, "configuration-hidden", pool["configuration"]["hidden_worlds"]
        )
        qualification_materialized_after_s_prime = True
        configuration_closure = _closure_check(checker_capsule, v0_path, config_demand_path)

        s0_configuration = _process(
            runtime_capsule,
            "acquire-consumer",
            state=v0_path,
            demand=config_demand_path,
        )
        more_budget_s0_configuration = _process(
            runtime_capsule,
            "acquire-consumer",
            state=v0_path,
            demand=config_demand_path,
            repetitions=32,
        )
        v1_mutated_path = base / "v1-mutated.json"
        mutate_v1 = _process(
            runtime_capsule,
            "state-control",
            state=v1_path,
            control="constructor-mutate",
            out=v1_mutated_path,
        )
        mutated_configuration = _process(
            runtime_capsule,
            "acquire-consumer",
            state=v1_mutated_path,
            demand=config_demand_path,
        )
        development_ambiguity = _process(
            runtime_capsule,
            "acquire-consumer",
            state=v1_path,
            demand=development_ambiguity_path,
        )
        qualification_ambiguity = _process(
            runtime_capsule,
            "acquire-consumer",
            state=v1_path,
            demand=qualification_ambiguity_path,
        )

        v2_path = base / "v2.json"
        acquire_d = _process(
            runtime_capsule,
            "acquire-consumer",
            state=v1_path,
            demand=config_demand_path,
            register=True,
            out=v2_path,
        )
        if not _confirmed(acquire_d):
            raise QualificationRefused("M103 D acquisition failed")
        v2_raw = v2_path.read_bytes()
        d_producer_pid = acquire_d["runtime"]["pid"]
        configuration_hidden = [
            _process(runtime_capsule, "execute-world", state=v2_path, world=world)
            for world in config_world_paths
        ]

        # Filesystem bytes first enter capsule inputs after D's process returned.
        filesystem_demand_path = _write_json(
            base / "qualification-filesystem-demand.json", pool["filesystem"]["acquisition"]
        )
        filesystem_world_paths = _materialize_worlds(
            base, "filesystem-hidden", pool["filesystem"]["hidden_worlds"]
        )
        filesystem_materialized_after_d = True
        filesystem_closure = _closure_check(checker_capsule, v0_path, filesystem_demand_path)

        s0_filesystem = _process(
            runtime_capsule,
            "acquire-consumer",
            state=v0_path,
            demand=filesystem_demand_path,
        )
        v2_ablated_path = base / "v2-constructor-ablated.json"
        ablate_v2 = _process(
            runtime_capsule,
            "state-control",
            state=v2_path,
            control="constructor-ablate",
            out=v2_ablated_path,
        )
        ablated_filesystem = _process(
            runtime_capsule,
            "acquire-consumer",
            state=v2_ablated_path,
            demand=filesystem_demand_path,
        )
        v2_mutated_path = base / "v2-constructor-mutated.json"
        mutate_v2 = _process(
            runtime_capsule,
            "state-control",
            state=v2_path,
            control="constructor-mutate",
            out=v2_mutated_path,
        )
        mutated_filesystem = _process(
            runtime_capsule,
            "acquire-consumer",
            state=v2_mutated_path,
            demand=filesystem_demand_path,
        )
        feature_ablation_controls: dict[str, dict[str, Any]] = {
            "PARTITION_EQUAL": {
                "mutation": mutate_v2,
                "acquisition": mutated_filesystem,
            }
        }
        for feature, control_name in (
            ("OBSERVE_CONTEXT", "constructor-drop-observe"),
            ("SYNTHESIZE_PARTITIONS", "constructor-drop-synthesize"),
            ("EMIT_GUARDED", "constructor-drop-emit"),
        ):
            feature_path = base / f"v2-without-{feature.lower()}.json"
            mutation = _process(
                runtime_capsule,
                "state-control",
                state=v2_path,
                control=control_name,
                out=feature_path,
            )
            attempt = _process(
                runtime_capsule,
                "acquire-consumer",
                state=feature_path,
                demand=filesystem_demand_path,
            )
            feature_ablation_controls[feature] = {
                "mutation": mutation,
                "acquisition": attempt,
            }
        v3_path = base / "v3.json"
        acquire_e = _process(
            runtime_capsule,
            "acquire-consumer",
            state=v2_path,
            demand=filesystem_demand_path,
            register=True,
            out=v3_path,
        )
        if not _confirmed(acquire_e):
            raise QualificationRefused("M103 E acquisition failed")
        v3_raw = v3_path.read_bytes()
        e_producer_pid = acquire_e["runtime"]["pid"]
        filesystem_hidden = [
            _process(runtime_capsule, "execute-world", state=v3_path, world=world)
            for world in filesystem_world_paths
        ]

        # Truthful boundary: compiled D/E keep executing after S-prime is removed.
        v3_no_constructor_path = base / "v3-no-constructor.json"
        ablate_v3 = _process(
            runtime_capsule,
            "state-control",
            state=v3_path,
            control="constructor-ablate",
            out=v3_no_constructor_path,
        )
        compiled_d_without_s_prime = _process(
            runtime_capsule,
            "execute-world",
            state=v3_no_constructor_path,
            world=config_world_paths[0],
        )
        compiled_e_without_s_prime = _process(
            runtime_capsule,
            "execute-world",
            state=v3_no_constructor_path,
            world=filesystem_world_paths[0],
        )

        v3_no_d_path = base / "v3-no-d.json"
        ablate_d = _process(
            runtime_capsule,
            "state-control",
            state=v3_path,
            control="configuration-ablate",
            out=v3_no_d_path,
        )
        d_absent_execution = _process(
            runtime_capsule,
            "execute-world",
            state=v3_no_d_path,
            world=config_world_paths[0],
        )
        e_after_d_ablation = _process(
            runtime_capsule,
            "execute-world",
            state=v3_no_d_path,
            world=filesystem_world_paths[0],
        )

        v3_no_e_path = base / "v3-no-e.json"
        ablate_e = _process(
            runtime_capsule,
            "state-control",
            state=v3_path,
            control="filesystem-ablate",
            out=v3_no_e_path,
        )
        e_absent_execution = _process(
            runtime_capsule,
            "execute-world",
            state=v3_no_e_path,
            world=filesystem_world_paths[0],
        )
        d_after_e_ablation = _process(
            runtime_capsule,
            "execute-world",
            state=v3_no_e_path,
            world=config_world_paths[0],
        )

        corrupt_path = base / "v3-corrupt.json"
        corrupt_write = _process(
            runtime_capsule,
            "state-control",
            state=v3_path,
            control="corrupt",
            out=corrupt_path,
        )
        corrupt_consumer = _process(runtime_capsule, "conservation", state=corrupt_path)

        restored_v2_path = base / "v2-restored.json"
        rollback = _process(
            runtime_capsule,
            "rollback",
            state=v2_mutated_path,
            restore=v2_path,
            out=restored_v2_path,
        )
        replay_v3_path = base / "v3-from-rollback.json"
        reacquire_e = _process(
            runtime_capsule,
            "acquire-consumer",
            state=restored_v2_path,
            demand=filesystem_demand_path,
            register=True,
            out=replay_v3_path,
        )

        conservation = _process(runtime_capsule, "conservation", state=v3_path)
        definition_validation = _definition_check(checker_capsule, v3_path)

        # Fresh behavioral probes execute the exact M102 bytes retained inside V3.
        retained_m102_path = base / "retained-m102-u2.json"
        retained_m102_raw = json.loads(v3_raw.decode("ascii"))["m102_ascii"].encode("ascii")
        retained_m102_path.write_bytes(retained_m102_raw)
        predecessor_world_paths = _materialize_worlds(
            base,
            "predecessor-conservation",
            [entry["world"] for entry in predecessor_conservation_fixture["entries"]],
        )
        predecessor_behavioral_conservation = [
            {
                "action": entry["action"],
                "world_id": entry["world"].get("world_id", entry["world"].get("id")),
                "fresh": _predecessor_execution(
                    predecessor_executor_capsule,
                    entry["action"],
                    retained_m102_path,
                    world_path,
                ),
            }
            for entry, world_path in zip(
                predecessor_conservation_fixture["entries"],
                predecessor_world_paths,
                strict=True,
            )
        ]

        process_records: list[dict[str, Any]] = [
            create_v0,
            built_only,
            no_limitation,
            acquire_s_prime,
            s0_configuration,
            more_budget_s0_configuration,
            mutate_v1,
            mutated_configuration,
            development_ambiguity,
            qualification_ambiguity,
            acquire_d,
            *configuration_hidden,
            s0_filesystem,
            ablate_v2,
            ablated_filesystem,
            mutate_v2,
            mutated_filesystem,
            *[
                item
                for feature, control in feature_ablation_controls.items()
                if feature != "PARTITION_EQUAL"
                for item in (control["mutation"], control["acquisition"])
            ],
            acquire_e,
            *filesystem_hidden,
            ablate_v3,
            compiled_d_without_s_prime,
            compiled_e_without_s_prime,
            ablate_d,
            d_absent_execution,
            e_after_d_ablation,
            ablate_e,
            e_absent_execution,
            d_after_e_ablation,
            corrupt_write,
            corrupt_consumer,
            rollback,
            reacquire_e,
            conservation,
            *[item["fresh"] for item in predecessor_behavioral_conservation],
        ]
        pids = [
            item.get("runtime", {}).get("pid")
            for item in process_records
            if isinstance(item.get("runtime", {}).get("pid"), int)
        ]
        isolated_records = [
            item
            for item in process_records
            if item.get("runtime", {}).get("schema") == "m103-isolated-process-v1"
        ]

        evidence: dict[str, Any] = {
            "schema": "m103-scientific-evidence-v1",
            "predecessor": predecessor_facts,
            "pool_preflight": pool_preflight,
            "predecessor_conservation_preflight": predecessor_conservation_preflight,
            "capsules": capsule_reports,
            "information_boundary": {
                "development_fixture_digest": development["fixture_digest"],
                "qualification_pool_digest": pool["pool_digest"],
                "qualification_materialized_after_s_prime_producer_return": qualification_materialized_after_s_prime,
                "filesystem_materialized_after_d_producer_return": filesystem_materialized_after_d,
                "s_prime_producer_received_only_v0_and_development_demand": True,
                "s_prime_producer_capsule_contains_pool": False,
                "runtime_source_contains_pool_path": False,
            },
            "states": {
                "V0": {
                    "raw_sha256": hashlib.sha256(v0_raw).hexdigest(),
                    "state_digest": create_v0["runtime"]["output_state_digest"],
                    "state": json.loads(v0_raw.decode("ascii")),
                },
                "V1": {
                    "raw_sha256": hashlib.sha256(v1_raw).hexdigest(),
                    "state_digest": acquire_s_prime["runtime"]["output_state_digest"],
                    "state": json.loads(v1_raw.decode("ascii")),
                },
                "V2": {
                    "raw_sha256": hashlib.sha256(v2_raw).hexdigest(),
                    "state_digest": acquire_d["runtime"]["output_state_digest"],
                    "state": json.loads(v2_raw.decode("ascii")),
                },
                "V3": {
                    "raw_sha256": hashlib.sha256(v3_raw).hexdigest(),
                    "state_digest": acquire_e["runtime"]["output_state_digest"],
                    "state": json.loads(v3_raw.decode("ascii")),
                },
                "m102_bytes_conserved_v0_v1_v2_v3": all(
                    json.loads(raw.decode("ascii"))["m102_ascii"].encode("ascii")
                    == predecessor_raw
                    for raw in (v0_raw, v1_raw, v2_raw, v3_raw)
                ),
            },
            "constructor": {
                "built_only": built_only,
                "no_limitation_control": no_limitation,
                "acquisition": acquire_s_prime,
                "v0_bytes_unchanged_by_built_only": v0_path.read_bytes() == v0_raw,
            },
            "independent_closure": {
                "development": development_closure,
                "configuration": configuration_closure,
                "filesystem": filesystem_closure,
            },
            "configuration": {
                "fresh_s0": s0_configuration,
                "more_budget_s0": more_budget_s0_configuration,
                "mutated_s_prime": mutated_configuration,
                "acquisition": acquire_d,
                "hidden": configuration_hidden,
            },
            "filesystem": {
                "fresh_s0": s0_filesystem,
                "ablated_s_prime": ablated_filesystem,
                "mutated_s_prime": mutated_filesystem,
                "feature_ablations": feature_ablation_controls,
                "acquisition": acquire_e,
                "hidden": filesystem_hidden,
            },
            "refusal": {
                "development_ambiguity": development_ambiguity,
                "qualification_ambiguity": qualification_ambiguity,
                "non_discriminating": no_limitation,
                "states_unchanged": all(
                    item.get("runtime", {}).get("acquisition", {}).get("next_state") is None
                    for item in (development_ambiguity, qualification_ambiguity, no_limitation)
                ),
            },
            "truthful_dependency_boundary": {
                "s_prime_needed_for_configuration_acquisition": _refused(s0_configuration)
                and _confirmed(acquire_d),
                "s_prime_needed_for_filesystem_acquisition": _refused(ablated_filesystem)
                and _confirmed(acquire_e),
                "compiled_d_executes_without_s_prime": _confirmed(compiled_d_without_s_prime),
                "compiled_e_executes_without_s_prime": _confirmed(compiled_e_without_s_prime),
                "runtime_dependency_claimed": False,
                "acquisition_dependency_claimed": True,
            },
            "ablations": {
                "ablate_d": ablate_d,
                "d_absent_execution": d_absent_execution,
                "e_after_d_ablation": e_after_d_ablation,
                "ablate_e": ablate_e,
                "e_absent_execution": e_absent_execution,
                "d_after_e_ablation": d_after_e_ablation,
            },
            "corruption": {"write": corrupt_write, "consumer": corrupt_consumer},
            "rollback": {
                "fault": mutate_v2,
                "fault_blocks_e": mutated_filesystem,
                "rollback": rollback,
                "reacquire_e": reacquire_e,
                "restored_v2_is_byte_exact": restored_v2_path.read_bytes() == v2_raw,
                "reacquired_v3_is_byte_exact": replay_v3_path.read_bytes() == v3_raw,
            },
            "predecessor_conservation": conservation,
            "predecessor_behavioral_conservation": {
                "fixture_digest": predecessor_conservation_fixture["fixture_digest"],
                "retained_m102_raw_sha256": hashlib.sha256(retained_m102_raw).hexdigest(),
                "materialized_after_e_producer_return": True,
                "executions": predecessor_behavioral_conservation,
                "all_isolated": all(
                    item["fresh"]["runtime"].get("isolated_mode") is True
                    for item in predecessor_behavioral_conservation
                ),
                "all_imported_project_modules_empty": all(
                    item["fresh"]["runtime"].get("imported_project_modules") == []
                    for item in predecessor_behavioral_conservation
                ),
                "all_external_call_counters_zero": all(
                    item["fresh"]["runtime"].get(key) == 0
                    for item in predecessor_behavioral_conservation
                    for key in ("model_calls", "network_calls", "remote_execution_calls")
                ),
                "confirmed": all(
                    _execution_all_passed(item["fresh"])
                    for item in predecessor_behavioral_conservation
                ),
            },
            "definition_validation": definition_validation,
            "baseline_parity": {
                "same_v0_predecessor": True,
                "same_runtime_capsule": True,
                "same_public_demands": True,
                "same_action_catalogues": True,
                "s0_complete_image_repeated_in_more_budget_arm": s0_configuration[
                    "runtime"
                ]["acquisition"]["assembled"]
                == more_budget_s0_configuration["runtime"]["acquisition"]["assembled"],
                "more_budget_repetitions": more_budget_s0_configuration["runtime"][
                    "repetitions"
                ],
                "more_budget_total_assembled": more_budget_s0_configuration["runtime"][
                    "total_assembled"
                ],
                "more_budget_repeated_image_identical": more_budget_s0_configuration[
                    "runtime"
                ]["repeated_image_identical"],
                "only_causal_difference": "registered S-prime bytes",
            },
            "process_boundary": {
                "process_pids": pids,
                "scientific_invocations": len(isolated_records),
                "all_isolated": all(
                    item["runtime"].get("isolated_mode") is True for item in isolated_records
                ),
                "all_imported_project_modules_empty": all(
                    item["runtime"].get("imported_project_modules") == []
                    for item in isolated_records
                ),
                "all_external_call_counters_zero": all(
                    item["runtime"].get(key) == 0
                    for item in process_records
                    for key in ("model_calls", "network_calls", "remote_execution_calls")
                ),
                "s_prime_producer_pid": s_prime_producer_pid,
                "d_producer_pid": d_producer_pid,
                "e_producer_pid": e_producer_pid,
                "producer_boundaries_distinct": len(
                    {s_prime_producer_pid, d_producer_pid, e_producer_pid}
                )
                == 3,
                "all_processes_returned": True,
            },
        }
    elapsed = time.monotonic() - started
    evidence["elapsed_seconds"] = elapsed
    return evidence


def _protocol_digest(protocol: dict[str, Any]) -> str:
    payload = {key: value for key, value in protocol.items() if key != "protocol_digest"}
    return digest(payload)


def _verify_bound_files(protocol: dict[str, Any]) -> None:
    groups = protocol.get("bound_files")
    if not isinstance(groups, dict) or set(groups) != {"mechanism", "apparatus", "checker"}:
        raise QualificationRefused("M103 protocol bound-file groups are invalid")
    for name, group in groups.items():
        if not isinstance(group, dict) or not isinstance(group.get("files"), list):
            raise QualificationRefused(f"M103 protocol {name} file binding is invalid")
        measured, members = file_set_digest(group["files"])
        if group.get("member_digests") != members or group.get("digest") != measured:
            raise QualificationRefused(f"M103 protocol {name} files moved")


def _verify_capsule_bindings(protocol: dict[str, Any]) -> None:
    bound = protocol.get("capsules")
    if not isinstance(bound, dict) or set(bound) != set(CAPSULE_SOURCES):
        raise QualificationRefused("M103 protocol capsule census is invalid")
    for name, sources in CAPSULE_SOURCES.items():
        measured, members = capsule_binding(sources)
        item = bound[name]
        if (
            item.get("members") != sorted(sources)
            or item.get("member_sources") != sources
            or item.get("member_digests") != members
            or item.get("digest") != measured
        ):
            raise QualificationRefused(f"M103 protocol {name} capsule moved")


def _verify_canonical_runtime(protocol: dict[str, Any]) -> None:
    expected = {
        "python": {
            "implementation": "cpython",
            "version_info": [3, 11, 16],
        },
        "sqlite": {
            "module": "sqlite3",
            "sqlite_version": "3.53.1",
            "sqlite_version_info": [3, 53, 1],
        },
    }
    current = {
        "python": {
            "implementation": sys.implementation.name,
            "version_info": [
                sys.version_info.major,
                sys.version_info.minor,
                sys.version_info.micro,
            ],
        },
        "sqlite": {
            "module": "sqlite3",
            "sqlite_version": sqlite3.sqlite_version,
            "sqlite_version_info": list(sqlite3.sqlite_version_info),
        },
    }
    if protocol.get("canonical_runtime") != expected or current != expected:
        raise QualificationRefused("M103 canonical runtime identity moved")


def _verify_freeze_commit(protocol: dict[str, Any]) -> None:
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    parent = subprocess.run(
        ["git", "rev-parse", "HEAD^"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    tag = str(protocol["freeze_tag"])
    tag_commit = subprocess.run(
        ["git", "rev-parse", f"refs/tags/{tag}^{{commit}}"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    dirty = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    if head != tag_commit or parent != protocol.get("source_commit") or dirty:
        raise QualificationRefused("M103 freeze commit/tag/worktree binding is invalid")


def require_frozen(protocol: dict[str, Any], pool: dict[str, Any]) -> None:
    if protocol.get("schema") != "m103-protocol-v1":
        raise QualificationRefused("M103 final protocol schema is absent")
    if protocol.get("protocol_digest") != _protocol_digest(protocol):
        raise QualificationRefused("M103 protocol digest mismatch")
    if protocol.get("qualification_pool_digest") != pool.get("pool_digest"):
        raise QualificationRefused("M103 protocol does not bind the qualification pool")
    if protocol.get("development_fixture_digest") != DEVELOPMENT_DIGEST:
        raise QualificationRefused("M103 protocol does not bind DEVELOPMENT")
    if (
        protocol.get("predecessor_conservation_fixture_digest")
        != PREDECESSOR_CONSERVATION_DIGEST
        or protocol.get("predecessor_conservation_fixture_raw_sha256")
        != PREDECESSOR_CONSERVATION_RAW_SHA256
    ):
        raise QualificationRefused("M103 protocol does not bind predecessor conservation")
    if protocol.get("source_commit") in {None, "", "TO_BE_BOUND"}:
        raise QualificationRefused("M103 protocol source commit is not frozen")
    if protocol.get("freeze_tag") in {None, "", "TO_BE_BOUND"}:
        raise QualificationRefused("M103 protocol freeze tag is not frozen")
    if protocol.get("canonical_run_allowed") is not False:
        raise QualificationRefused("M103 protocol must keep run authorization separate")
    acceptance = protocol.get("owner_protocol_acceptance", {})
    if (
        acceptance.get("recorded") is not True
        or not isinstance(acceptance.get("authorization_reference"), str)
        or not acceptance["authorization_reference"].strip()
    ):
        raise QualificationRefused("M103 owner protocol acceptance is absent")
    _verify_bound_files(protocol)
    _verify_capsule_bindings(protocol)
    _verify_canonical_runtime(protocol)
    _verify_freeze_commit(protocol)
    if RESULT_PATH.exists() or CHECK_PATH.exists():
        raise QualificationRefused("M103 canonical result/check path is already occupied")


def preflight() -> dict[str, Any]:
    pool = json.loads(POOL_PATH.read_text(encoding="ascii"))
    conservation_fixture = json.loads(
        PREDECESSOR_CONSERVATION_PATH.read_text(encoding="ascii")
    )
    report: dict[str, Any] = {
        "schema": "m103-preflight-v1",
        "pool": verify_pool(pool),
        "predecessor_conservation": verify_predecessor_conservation_fixture(
            conservation_fixture
        ),
        "result_absent": not RESULT_PATH.exists(),
        "check_report_absent": not CHECK_PATH.exists(),
        "protocol_exists": PROTOCOL_PATH.exists(),
        "python": str(ISOLATED_PYTHON),
    }
    if PROTOCOL_PATH.exists():
        protocol = json.loads(PROTOCOL_PATH.read_text(encoding="ascii"))
        try:
            require_frozen(protocol, pool)
            report["frozen"] = True
            report["protocol_digest"] = protocol["protocol_digest"]
        except Exception as error:
            report["frozen"] = False
            report["freeze_error"] = f"{type(error).__name__}: {error}"
    else:
        report["frozen"] = False
    report["confirmed"] = all(
        (
            report["pool"]["confirmed"],
            report["predecessor_conservation"]["confirmed"],
            report["result_absent"],
            report["check_report_absent"],
            report["frozen"],
        )
    )
    return report


def materialize(*, authorized_by_owner: bool, understand_unique_attempt: bool) -> dict[str, Any]:
    if not authorized_by_owner or not understand_unique_attempt:
        raise QualificationRefused("M103 canonical attempt lacks explicit owner authorization")
    pool = json.loads(POOL_PATH.read_text(encoding="ascii"))
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="ascii"))
    require_frozen(protocol, pool)
    evidence = run_experiment(pool)
    stable_evidence = stable_projection(evidence)
    result: dict[str, Any] = {
        "schema": "m103-result-v1",
        "milestone": "M103",
        "attempt": 1,
        "canonical": True,
        "reroll": False,
        "protocol_digest": protocol["protocol_digest"],
        "pool_digest": pool["pool_digest"],
        "source_commit": protocol["source_commit"],
        "freeze_tag": protocol["freeze_tag"],
        "started_at_utc": datetime.now(UTC).isoformat(),
        "model_calls": 0,
        "network_calls": 0,
        "remote_execution_calls": 0,
        "scientific_evidence": evidence,
        "stable_evidence_digest": digest(stable_evidence),
    }
    result["result_digest"] = digest(result)
    RESULT_PATH.write_bytes(canonical_json(result).encode("ascii"))
    return {
        "materialized": True,
        "result_digest": result["result_digest"],
        "stable_evidence_digest": result["stable_evidence_digest"],
        "path": str(RESULT_PATH),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("preflight", "materialize"))
    parser.add_argument("--authorized-by-owner", action="store_true")
    parser.add_argument("--i-understand-this-is-the-only-canonical-attempt", action="store_true")
    arguments = parser.parse_args()
    try:
        if arguments.action == "preflight":
            report = preflight()
            print(json.dumps(report, indent=2, sort_keys=True))
            return 0 if report["confirmed"] else 1
        report = materialize(
            authorized_by_owner=arguments.authorized_by_owner,
            understand_unique_attempt=arguments.i_understand_this_is_the_only_canonical_attempt,
        )
    except Exception as error:
        print(
            json.dumps(
                {
                    "materialized": False,
                    "failed_closed": True,
                    "error": f"{type(error).__name__}: {error}",
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 3
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
