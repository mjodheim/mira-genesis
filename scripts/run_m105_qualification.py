"""M105 isolated qualification orchestration and unique-attempt materializer."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import platform
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from metamorphosis import m105_runtime as runtime  # noqa: E402


EXPERIMENT = ROOT / "experiments" / "M105"
PREDECESSOR_PATH = EXPERIMENT / "M104_V3.json"
DEVELOPMENT_PATH = EXPERIMENT / "DEVELOPMENT_FIXTURE.json"
POOL_PATH = EXPERIMENT / "QUALIFICATION_POOL.json"
PROTOCOL_PATH = EXPERIMENT / "PROTOCOL.json"
RESULT_PATH = EXPERIMENT / "RESULT.json"
CHECK_PATH = EXPERIMENT / "CHECK_REPORT.json"
M104_POOL_PATH = ROOT / "experiments" / "M104" / "QUALIFICATION_POOL.json"
PREDECESSOR_CONSERVATION_PATH = (
    ROOT / "experiments" / "M103" / "PREDECESSOR_CONSERVATION.json"
)

PREDECESSOR_RAW_SHA256 = runtime.M104_V3_RAW_SHA256
DEVELOPMENT_RAW_SHA256 = "0be09c84a76bc134f40353fca3a9b83844fe128997352454360443cdac91dca4"
POOL_RAW_SHA256 = "26f0eeebd32fbb7aab9523a0c7a239f58634e8b4918013f0d4d09a3af7e62b67"
POOL_DIGEST = "313aec1b41a9b95d8913a3ba1e48074d3d0dbd8b17b851fbef871a527921ddb7"
CANONICAL_PYTHON = (3, 11, 16)
CANONICAL_SQLITE = (3, 53, 1)
EXPECTED_PREDICATES = [f"P{index}" for index in range(1, 17)]
ISOLATED_PYTHON = Path(sys.executable).resolve()

EPHEMERAL_KEYS = {
    "pid",
    "search_path",
    "python_executable",
    "sqlite_module",
    "stderr",
    "elapsed_seconds",
}

RUNTIME_SOURCES = {
    "m100_runtime.py": "metamorphosis/m100_runtime.py",
    "m101_runtime.py": "metamorphosis/m101_runtime.py",
    "m102_runtime.py": "metamorphosis/m102_runtime.py",
    "m103_runtime.py": "metamorphosis/m103_runtime.py",
    "m105_runtime.py": "metamorphosis/m105_runtime.py",
    "run.py": "scripts/run_m105_process.py",
}
CHECKER_SOURCES = {
    "check_m101_definitions.py": "scripts/check_m101_definitions.py",
    "check_m102_definitions.py": "scripts/check_m102_definitions.py",
    "check_m103_definitions.py": "scripts/check_m103_definitions.py",
    "check_m105_semantics.py": "scripts/check_m105_semantics.py",
    "check_m105_definitions.py": "scripts/check_m105_definitions.py",
    "check_m105_m104_closure.py": "scripts/check_m105_m104_closure.py",
}
PREDECESSOR_EXECUTOR_SOURCES = {
    "m101_executor.py": "metamorphosis/m101_executor.py",
    "m102_executor.py": "metamorphosis/m102_executor.py",
    "run.py": "scripts/run_m102_fresh_process.py",
}


class QualificationRefused(RuntimeError):
    pass


canonical_json = runtime.canonical_json
digest = runtime.digest


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


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


def _read_canonical(path: Path, label: str) -> dict[str, Any]:
    raw = path.read_bytes()
    try:
        value = json.loads(raw.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise QualificationRefused(f"{label} is not ASCII JSON: {error}") from error
    if canonical_json(value).encode("ascii") != raw:
        raise QualificationRefused(f"{label} is not canonical JSON")
    return value


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise QualificationRefused(f"{label} is not JSON: {error}") from error
    if not isinstance(value, dict):
        raise QualificationRefused(f"{label} is not a JSON object")
    return value


def verify_inputs() -> dict[str, Any]:
    predecessor_raw = PREDECESSOR_PATH.read_bytes()
    development = _read_canonical(DEVELOPMENT_PATH, "M105 DEVELOPMENT fixture")
    pool = _read_canonical(POOL_PATH, "M105 qualification pool")
    pool_payload = {key: value for key, value in pool.items() if key != "pool_digest"}
    checks = {
        "predecessor_raw": sha256_bytes(predecessor_raw) == PREDECESSOR_RAW_SHA256,
        "predecessor_state": runtime.create_state(predecessor_raw)["features"] == [],
        "development_raw": sha256_bytes(DEVELOPMENT_PATH.read_bytes())
        == DEVELOPMENT_RAW_SHA256,
        "development_schema": development.get("schema") == runtime.FEATURE_DEMAND_SCHEMA,
        "pool_raw": sha256_bytes(POOL_PATH.read_bytes()) == POOL_RAW_SHA256,
        "pool_schema": pool.get("schema") == "m105-qualification-pool-v1",
        "pool_digest": pool.get("pool_digest") == digest(pool_payload) == POOL_DIGEST,
        "pool_authorship": pool.get("authorship")
        == "project_controlled_not_independent_task_evidence",
        "carriers": {
            pool.get("json_demand", {}).get("family"),
            pool.get("sqlite_demand", {}).get("family"),
        }
        == {"json_document", "sqlite"},
        "hidden_counts": len(pool.get("hidden_json_cases", [])) == 4
        and len(pool.get("hidden_sqlite_cases", [])) == 4,
    }
    return {
        "schema": "m105-input-preflight-v1",
        "confirmed": all(checks.values()),
        "checks": checks,
        "pool_digest": pool.get("pool_digest"),
    }


def _file_binding(sources: dict[str, str]) -> tuple[str, dict[str, str]]:
    members = {
        destination: sha256_bytes((ROOT / source).read_bytes())
        for destination, source in sources.items()
    }
    return digest(members), members


def _build_capsule(
    base: Path,
    name: str,
    sources: dict[str, str],
    inputs: dict[str, bytes],
) -> tuple[Path, dict[str, Any]]:
    capsule = base / name
    capsule.mkdir(parents=True)
    for destination, source in sources.items():
        shutil.copyfile(ROOT / source, capsule / destination)
    for destination, raw in inputs.items():
        (capsule / destination).write_bytes(raw)
    source_digest, source_members = _file_binding(sources)
    input_members = {name: sha256_bytes(raw) for name, raw in sorted(inputs.items())}
    expected = sorted([*sources, *inputs])
    actual = sorted(path.name for path in capsule.iterdir())
    if actual != expected:
        raise QualificationRefused(f"unexpected member in M105 {name} capsule")
    return capsule, {
        "schema": "m105-capsule-binding-v1",
        "name": name,
        "initial_members": actual,
        "source_member_digests": source_members,
        "source_digest": source_digest,
        "input_member_digests": input_members,
        "input_digest": digest(input_members),
        "contains_only_bound_initial_members": True,
    }


def _fresh(capsule: Path, entry: str, arguments: list[str]) -> dict[str, Any]:
    completed = subprocess.run(
        [str(ISOLATED_PYTHON), "-I", str(capsule / entry), *arguments],
        cwd=capsule,
        capture_output=True,
        text=True,
        timeout=120,
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
        "m104",
        "state",
        "demand",
        "execution",
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


def _write_json(path: Path, value: Any) -> Path:
    path.write_bytes(canonical_json(value).encode("ascii"))
    return path


def _ambiguous_development() -> dict[str, Any]:
    return runtime.feature_demand(
        "ambiguous_development_control",
        [
            {
                "case_id": "ambiguous_a",
                "signals": [False, False],
                "nonce": "ambiguous-a",
                "expected": False,
            },
            {
                "case_id": "ambiguous_b",
                "signals": [False, False],
                "nonce": "ambiguous-b",
                "expected": False,
            },
        ],
    )


def _execution_request(definition_id: str, case: dict[str, Any]) -> dict[str, Any]:
    return {
        "definition_id": definition_id,
        "context": case["context"],
        "initial": case["initial"],
    }


def _run_hidden(
    capsule: Path,
    state_path: Path,
    requests: list[tuple[dict[str, Any], Path]],
) -> list[dict[str, Any]]:
    executions: list[dict[str, Any]] = []
    for case, request_path in requests:
        process = _process(
            capsule,
            "execute-definition",
            state=state_path,
            execution=request_path,
        )
        actual = process.get("runtime", {}).get("execution_output")
        executions.append(
            {
                "case_id": case["case_id"],
                "context": case["context"],
                "expected": case["expected"],
                "actual": actual,
                "matched": process["returncode"] == 0 and actual == case["expected"],
                "process": process,
            }
        )
    return executions


def _predecessor_execution(
    capsule: Path, action: str, state: Path, world: Path
) -> dict[str, Any]:
    return _fresh(
        capsule,
        "run.py",
        [action, "--state", str(state), "--world", str(world)],
    )


def run_experiment(pool: dict[str, Any] | None = None) -> dict[str, Any]:
    preflight = verify_inputs()
    if not preflight["confirmed"]:
        raise QualificationRefused("M105 input preflight failed")
    pool = pool or _read_canonical(POOL_PATH, "M105 qualification pool")
    if pool.get("pool_digest") != POOL_DIGEST:
        raise QualificationRefused("M105 qualification pool binding mismatch")

    predecessor_raw = PREDECESSOR_PATH.read_bytes()
    development_raw = DEVELOPMENT_PATH.read_bytes()
    ambiguous_raw = canonical_json(_ambiguous_development()).encode("ascii")
    m104_pool = _read_json(M104_POOL_PATH, "M104 qualification pool")
    conservation_fixture = _read_json(
        PREDECESSOR_CONSERVATION_PATH, "M103 predecessor conservation fixture"
    )

    with tempfile.TemporaryDirectory(prefix="m105-qualification-") as temporary:
        base = Path(temporary)
        capsule_reports: dict[str, Any] = {}

        feature_capsule, capsule_reports["feature_producer"] = _build_capsule(
            base,
            "feature-producer",
            RUNTIME_SOURCES,
            {
                "M104_V3.json": predecessor_raw,
                "DEVELOPMENT_FIXTURE.json": development_raw,
                "AMBIGUOUS_DEVELOPMENT.json": ambiguous_raw,
            },
        )
        w0_path = feature_capsule / "W0.json"
        create_w0 = _process(
            feature_capsule,
            "create-state",
            m104=feature_capsule / "M104_V3.json",
            out=w0_path,
        )
        census_process = _process(feature_capsule, "semantic-census", state=w0_path)
        census = census_process["runtime"]["semantic_census"]
        built_only = _process(
            feature_capsule,
            "acquire-feature",
            state=w0_path,
            demand=feature_capsule / "DEVELOPMENT_FIXTURE.json",
        )
        ambiguous_development = _process(
            feature_capsule,
            "acquire-feature",
            state=w0_path,
            demand=feature_capsule / "AMBIGUOUS_DEVELOPMENT.json",
            register=True,
        )
        w1_path = feature_capsule / "W1.json"
        acquire_feature = _process(
            feature_capsule,
            "acquire-feature",
            state=w0_path,
            demand=feature_capsule / "DEVELOPMENT_FIXTURE.json",
            register=True,
            out=w1_path,
        )
        w0_raw = w0_path.read_bytes()
        w1_raw = w1_path.read_bytes()
        w1_state = runtime.decode_state(w1_raw)

        json_demand_raw = canonical_json(pool["json_demand"]).encode("ascii")
        json_capsule, capsule_reports["json_lineage"] = _build_capsule(
            base,
            "json-lineage",
            RUNTIME_SOURCES,
            {"W1.json": w1_raw, "JSON_DEMAND.json": json_demand_raw},
        )
        w2_path = json_capsule / "W2.json"
        acquire_json = _process(
            json_capsule,
            "acquire-consumer",
            state=json_capsule / "W1.json",
            demand=json_capsule / "JSON_DEMAND.json",
            register=True,
            out=w2_path,
        )
        w2_raw = w2_path.read_bytes()
        w2_state = runtime.decode_state(w2_raw)

        json_fresh_capsule, capsule_reports["json_fresh"] = _build_capsule(
            base,
            "json-fresh",
            RUNTIME_SOURCES,
            {"W0.json": w0_raw, "JSON_DEMAND.json": json_demand_raw},
        )
        fresh_json = _process(
            json_fresh_capsule,
            "acquire-consumer",
            state=json_fresh_capsule / "W0.json",
            demand=json_fresh_capsule / "JSON_DEMAND.json",
        )
        repeated_fresh_json = _process(
            json_fresh_capsule,
            "acquire-consumer",
            state=json_fresh_capsule / "W0.json",
            demand=json_fresh_capsule / "JSON_DEMAND.json",
            repetitions=2,
        )

        sqlite_demand_raw = canonical_json(pool["sqlite_demand"]).encode("ascii")
        sqlite_capsule, capsule_reports["sqlite_lineage"] = _build_capsule(
            base,
            "sqlite-lineage",
            RUNTIME_SOURCES,
            {"W2.json": w2_raw, "SQLITE_DEMAND.json": sqlite_demand_raw},
        )
        w3_path = sqlite_capsule / "W3.json"
        acquire_sqlite = _process(
            sqlite_capsule,
            "acquire-consumer",
            state=sqlite_capsule / "W2.json",
            demand=sqlite_capsule / "SQLITE_DEMAND.json",
            register=True,
            out=w3_path,
        )
        w3_raw = w3_path.read_bytes()
        w3_state = runtime.decode_state(w3_raw)

        sqlite_fresh_capsule, capsule_reports["sqlite_fresh"] = _build_capsule(
            base,
            "sqlite-fresh",
            RUNTIME_SOURCES,
            {"W0.json": w0_raw, "SQLITE_DEMAND.json": sqlite_demand_raw},
        )
        fresh_sqlite = _process(
            sqlite_fresh_capsule,
            "acquire-consumer",
            state=sqlite_fresh_capsule / "W0.json",
            demand=sqlite_fresh_capsule / "SQLITE_DEMAND.json",
        )
        repeated_fresh_sqlite = _process(
            sqlite_fresh_capsule,
            "acquire-consumer",
            state=sqlite_fresh_capsule / "W0.json",
            demand=sqlite_fresh_capsule / "SQLITE_DEMAND.json",
            repetitions=2,
        )

        json_definition = runtime.definition_for_family(w3_state, "json_document")
        sqlite_definition = runtime.definition_for_family(w3_state, "sqlite")
        hidden_inputs: dict[str, bytes] = {"W3.json": w3_raw}
        hidden_requests: dict[str, list[tuple[dict[str, Any], str]]] = {
            "json_document": [],
            "sqlite": [],
        }
        for family, cases, definition in (
            ("json_document", pool["hidden_json_cases"], json_definition),
            ("sqlite", pool["hidden_sqlite_cases"], sqlite_definition),
        ):
            for case in cases:
                name = f"{case['case_id']}.json"
                hidden_inputs[name] = canonical_json(
                    _execution_request(definition["definition_id"], case)
                ).encode("ascii")
                hidden_requests[family].append((case, name))
        hidden_capsule, capsule_reports["hidden_consumers"] = _build_capsule(
            base, "hidden-consumers", RUNTIME_SOURCES, hidden_inputs
        )
        hidden_json = _run_hidden(
            hidden_capsule,
            hidden_capsule / "W3.json",
            [(case, hidden_capsule / name) for case, name in hidden_requests["json_document"]],
        )
        hidden_sqlite = _run_hidden(
            hidden_capsule,
            hidden_capsule / "W3.json",
            [(case, hidden_capsule / name) for case, name in hidden_requests["sqlite"]],
        )

        mutated_preview = runtime.mutate_feature_and_rebind(w3_state)
        mutated_json_definition = runtime.definition_for_family(
            mutated_preview, "json_document"
        )
        mutated_sqlite_definition = runtime.definition_for_family(mutated_preview, "sqlite")
        mutated_json_request = _execution_request(
            mutated_json_definition["definition_id"], pool["hidden_json_cases"][2]
        )
        mutated_sqlite_request = _execution_request(
            mutated_sqlite_definition["definition_id"], pool["hidden_sqlite_cases"][2]
        )
        control_inputs = {
            "W0.json": w0_raw,
            "W2.json": w2_raw,
            "W3.json": w3_raw,
            "SQLITE_DEMAND.json": sqlite_demand_raw,
            "JSON_HIDDEN.json": hidden_inputs[hidden_requests["json_document"][2][1]],
            "SQLITE_HIDDEN.json": hidden_inputs[hidden_requests["sqlite"][2][1]],
            "MUTATED_JSON_HIDDEN.json": canonical_json(mutated_json_request).encode("ascii"),
            "MUTATED_SQLITE_HIDDEN.json": canonical_json(mutated_sqlite_request).encode(
                "ascii"
            ),
        }
        control_capsule, capsule_reports["causal_controls"] = _build_capsule(
            base, "causal-controls", RUNTIME_SOURCES, control_inputs
        )
        w2_removed_path = control_capsule / "W2-feature-removed.json"
        remove_before_sqlite = _process(
            control_capsule,
            "state-control",
            state=control_capsule / "W2.json",
            control="feature-remove",
            out=w2_removed_path,
        )
        acquire_after_removal = _process(
            control_capsule,
            "acquire-consumer",
            state=w2_removed_path,
            demand=control_capsule / "SQLITE_DEMAND.json",
        )
        w3_removed_path = control_capsule / "W3-feature-removed.json"
        remove_after_compile = _process(
            control_capsule,
            "state-control",
            state=control_capsule / "W3.json",
            control="feature-remove",
            out=w3_removed_path,
        )
        execute_after_removal = _process(
            control_capsule,
            "execute-definition",
            state=w3_removed_path,
            execution=control_capsule / "JSON_HIDDEN.json",
        )
        w3_mutated_path = control_capsule / "W3-mutated.json"
        mutate_feature = _process(
            control_capsule,
            "state-control",
            state=control_capsule / "W3.json",
            control="feature-mutate-rebind",
            out=w3_mutated_path,
        )
        mutated_json = _process(
            control_capsule,
            "execute-definition",
            state=w3_mutated_path,
            execution=control_capsule / "MUTATED_JSON_HIDDEN.json",
        )
        mutated_sqlite = _process(
            control_capsule,
            "execute-definition",
            state=w3_mutated_path,
            execution=control_capsule / "MUTATED_SQLITE_HIDDEN.json",
        )
        restored_mutation_path = control_capsule / "W3-restored-mutation.json"
        rollback_mutation = _process(
            control_capsule,
            "rollback",
            state=w3_mutated_path,
            restore=control_capsule / "W3.json",
            out=restored_mutation_path,
        )
        w3_corrupt_path = control_capsule / "W3-corrupt.json"
        corrupt_write = _process(
            control_capsule,
            "state-control",
            state=control_capsule / "W3.json",
            control="corrupt",
            out=w3_corrupt_path,
        )
        corrupt_consumer = _process(
            control_capsule, "conservation", state=w3_corrupt_path
        )
        restored_corrupt_path = control_capsule / "W3-restored-corrupt.json"
        rollback_corrupt = _process(
            control_capsule,
            "rollback",
            state=w3_corrupt_path,
            restore=control_capsule / "W3.json",
            out=restored_corrupt_path,
        )
        conservation = _process(
            control_capsule, "conservation", state=control_capsule / "W3.json"
        )

        m104_world_inputs: dict[str, bytes] = {"W3.json": w3_raw}
        m104_world_names: list[str] = []
        for family in ("configuration", "filesystem"):
            for index, world in enumerate(m104_pool[family]["hidden_worlds"]):
                name = f"m104-{family}-{index}.json"
                m104_world_names.append(name)
                m104_world_inputs[name] = canonical_json(world).encode("ascii")
        fresh_m104_world = copy.deepcopy(m104_pool["configuration"]["hidden_worlds"][0])
        fresh_m104_world["world_id"] = "m105-m104-fresh-context-witness"
        fresh_m104_world["cases"] = [fresh_m104_world["cases"][0]]
        fresh_m104_world["cases"][0]["case_id"] = "m105-m104-fresh-context-case"
        fresh_m104_world["cases"][0]["context"] = [
            "m105-fresh-context-consumer-a3fc0657cb475d16-0"
        ]
        m104_world_inputs["M104_FRESH_CONTEXT.json"] = canonical_json(
            fresh_m104_world
        ).encode("ascii")
        conservation_capsule, capsule_reports["m104_behavioral_conservation"] = (
            _build_capsule(
                base,
                "m104-behavioral-conservation",
                RUNTIME_SOURCES,
                m104_world_inputs,
            )
        )
        m104_behavioral = [
            _process(
                conservation_capsule,
                "execute-m104-world",
                state=conservation_capsule / "W3.json",
                execution=conservation_capsule / name,
            )
            for name in m104_world_names
        ]
        m104_fresh_context_execution = _process(
            conservation_capsule,
            "execute-m104-world",
            state=conservation_capsule / "W3.json",
            execution=conservation_capsule / "M104_FRESH_CONTEXT.json",
        )

        retained_m102_raw = json.loads(predecessor_raw.decode("ascii"))["m102_ascii"].encode(
            "ascii"
        )
        predecessor_inputs: dict[str, bytes] = {"M102_U2.json": retained_m102_raw}
        predecessor_world_names: list[str] = []
        for index, entry in enumerate(conservation_fixture["entries"]):
            name = f"predecessor-world-{index}.json"
            predecessor_world_names.append(name)
            predecessor_inputs[name] = canonical_json(entry["world"]).encode("ascii")
        predecessor_capsule, capsule_reports["m100_m102_behavioral_conservation"] = (
            _build_capsule(
                base,
                "m100-m102-behavioral-conservation",
                PREDECESSOR_EXECUTOR_SOURCES,
                predecessor_inputs,
            )
        )
        predecessor_behavioral = [
            {
                "action": entry["action"],
                "world_id": entry["world"].get("world_id", entry["world"].get("id")),
                "process": _predecessor_execution(
                    predecessor_capsule,
                    entry["action"],
                    predecessor_capsule / "M102_U2.json",
                    predecessor_capsule / name,
                ),
            }
            for entry, name in zip(
                conservation_fixture["entries"], predecessor_world_names, strict=True
            )
        ]

        census_raw = canonical_json(census).encode("ascii")
        feature_raw = canonical_json(w1_state["features"][0]).encode("ascii")
        checker_capsule, capsule_reports["independent_checkers"] = _build_capsule(
            base,
            "independent-checkers",
            CHECKER_SOURCES,
            {
                "W3.json": w3_raw,
                "M104_V3.json": predecessor_raw,
                "CENSUS.json": census_raw,
                "FEATURE.json": feature_raw,
            },
        )
        definition_validation = _fresh(
            checker_capsule,
            "check_m105_definitions.py",
            ["--state", str(checker_capsule / "W3.json")],
        )
        semantic_validation = _fresh(
            checker_capsule,
            "check_m105_semantics.py",
            [
                "--census",
                str(checker_capsule / "CENSUS.json"),
                "--feature",
                str(checker_capsule / "FEATURE.json"),
            ],
        )
        closure_validation = _fresh(
            checker_capsule,
            "check_m105_m104_closure.py",
            ["--state", str(checker_capsule / "M104_V3.json")],
        )

        process_records = [
            create_w0,
            census_process,
            built_only,
            ambiguous_development,
            acquire_feature,
            fresh_json,
            repeated_fresh_json,
            acquire_json,
            fresh_sqlite,
            repeated_fresh_sqlite,
            acquire_sqlite,
            *[item["process"] for item in hidden_json],
            *[item["process"] for item in hidden_sqlite],
            remove_before_sqlite,
            acquire_after_removal,
            remove_after_compile,
            execute_after_removal,
            mutate_feature,
            mutated_json,
            mutated_sqlite,
            rollback_mutation,
            corrupt_write,
            corrupt_consumer,
            rollback_corrupt,
            conservation,
            *m104_behavioral,
            m104_fresh_context_execution,
            *[item["process"] for item in predecessor_behavioral],
        ]
        isolated_records = [
            item
            for item in process_records
            if item.get("runtime", {}).get("schema") == "m105-isolated-process-v1"
        ]
        producer_pid = acquire_feature["runtime"].get("pid")
        later_pids = [
            acquire_json["runtime"].get("pid"),
            acquire_sqlite["runtime"].get("pid"),
            *[
                item["process"]["runtime"].get("pid")
                for item in [*hidden_json, *hidden_sqlite]
            ],
        ]

        original_mutation_json = hidden_json[2]["actual"]
        original_mutation_sqlite = hidden_sqlite[2]["actual"]
        evidence: dict[str, Any] = {
            "schema": "m105-scientific-evidence-v1",
            "input_preflight": preflight,
            "runtime": {
                "python_implementation": platform.python_implementation(),
                "python_version": platform.python_version(),
                "sqlite_version": sqlite3.sqlite_version,
                "isolated_python": str(ISOLATED_PYTHON),
            },
            "capsules": capsule_reports,
            "information_boundary": {
                "feature_producer_has_development": "DEVELOPMENT_FIXTURE.json"
                in capsule_reports["feature_producer"]["initial_members"],
                "feature_producer_has_qualification_pool": any(
                    "QUALIFICATION" in name
                    for name in capsule_reports["feature_producer"]["initial_members"]
                ),
                "feature_producer_has_json_or_sqlite_demand": any(
                    name in {"JSON_DEMAND.json", "SQLITE_DEMAND.json"}
                    for name in capsule_reports["feature_producer"]["initial_members"]
                ),
                "json_lineage_has_development": any(
                    "DEVELOPMENT" in name
                    for name in capsule_reports["json_lineage"]["initial_members"]
                ),
                "sqlite_lineage_has_development": any(
                    "DEVELOPMENT" in name
                    for name in capsule_reports["sqlite_lineage"]["initial_members"]
                ),
                "qualification_records_enter_after_feature_process_returned": True,
                "sqlite_records_enter_after_json_process_returned": True,
                "hidden_nonces_disjoint_from_development": {
                    case["context"]["nonce"]
                    for case in [*pool["hidden_json_cases"], *pool["hidden_sqlite_cases"]]
                }.isdisjoint(
                    {
                        observation["nonce"]
                        for observation in json.loads(development_raw.decode("ascii"))[
                            "observations"
                        ]
                    }
                ),
            },
            "states": {
                "W0": {
                    "raw_sha256": sha256_bytes(w0_raw),
                    "state": runtime.decode_state(w0_raw),
                },
                "W1": {
                    "raw_sha256": sha256_bytes(w1_raw),
                    "state": w1_state,
                },
                "W2": {
                    "raw_sha256": sha256_bytes(w2_raw),
                    "state": w2_state,
                },
                "W3": {
                    "raw_sha256": sha256_bytes(w3_raw),
                    "state": w3_state,
                },
                "m104_bytes_conserved": all(
                    state["m104_ascii"].encode("ascii") == predecessor_raw
                    for state in (
                        runtime.decode_state(w0_raw),
                        w1_state,
                        w2_state,
                        w3_state,
                    )
                ),
            },
            "semantic_census": census,
            "feature": {
                "create_w0": create_w0,
                "built_only": built_only,
                "ambiguous_development": ambiguous_development,
                "acquisition": acquire_feature,
                "serialized_identity_scan": {
                    "development_literals_absent": all(
                        term not in canonical_json(w1_state["features"][0]).lower()
                        for term in (
                            "development",
                            "json",
                            "sqlite",
                            "route",
                            "amber",
                            "violet",
                            "qualification",
                        )
                    )
                },
            },
            "json": {
                "fresh": fresh_json,
                "fresh_repeated": repeated_fresh_json,
                "lineage_acquisition": acquire_json,
                "hidden": hidden_json,
            },
            "sqlite": {
                "fresh": fresh_sqlite,
                "fresh_repeated": repeated_fresh_sqlite,
                "lineage_acquisition": acquire_sqlite,
                "hidden": hidden_sqlite,
                "outcomes_inspected_from_real_database_state": True,
            },
            "controls": {
                "remove_before_sqlite": remove_before_sqlite,
                "acquire_after_removal": acquire_after_removal,
                "remove_after_compile": remove_after_compile,
                "execute_after_removal": execute_after_removal,
                "mutation": mutate_feature,
                "mutation_matches_content_addressed_preview": w3_mutated_path.read_bytes()
                == runtime.encode_state(mutated_preview),
                "mutation_json": mutated_json,
                "mutation_sqlite": mutated_sqlite,
                "mutation_changed_json": mutated_json["runtime"].get("execution_output")
                != original_mutation_json,
                "mutation_changed_sqlite": mutated_sqlite["runtime"].get(
                    "execution_output"
                )
                != original_mutation_sqlite,
                "rollback_mutation": rollback_mutation,
                "rollback_mutation_exact": restored_mutation_path.read_bytes() == w3_raw,
                "corrupt_write": corrupt_write,
                "corrupt_consumer": corrupt_consumer,
                "rollback_corrupt": rollback_corrupt,
                "rollback_corrupt_exact": restored_corrupt_path.read_bytes() == w3_raw,
            },
            "predecessor": {
                "structural_conservation": conservation,
                "m104_behavioral_conservation": m104_behavioral,
                "m104_fresh_context_execution": m104_fresh_context_execution,
                "m100_m102_behavioral_conservation": predecessor_behavioral,
                "fixture_digest": conservation_fixture["fixture_digest"],
            },
            "independent_validation": {
                "definition": definition_validation,
                "semantics": semantic_validation,
                "m104_closure": closure_validation,
            },
            "process_boundary": {
                "feature_producer_pid": producer_pid,
                "later_pids": later_pids,
                "producer_pid_absent_from_later": producer_pid not in later_pids,
                "all_m105_processes_isolated": bool(isolated_records)
                and all(
                    item["runtime"].get("isolated_mode") is True
                    and item["runtime"].get("imported_project_modules") == []
                    for item in isolated_records
                ),
                "all_m105_processes_zero_external_calls": bool(isolated_records)
                and all(
                    item["runtime"].get("model_calls") == 0
                    and item["runtime"].get("network_calls") == 0
                    and item["runtime"].get("remote_execution_calls") == 0
                    for item in isolated_records
                ),
                "completed_process_records": len(process_records),
            },
        }
        return evidence


def _git(*arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments], cwd=ROOT, capture_output=True, text=True, check=False
    )
    if completed.returncode != 0:
        raise QualificationRefused(completed.stderr.strip() or "git command failed")
    return completed.stdout.strip()


def require_frozen() -> dict[str, Any]:
    if not PROTOCOL_PATH.exists():
        raise QualificationRefused("M105 final protocol is absent")
    protocol = _read_canonical(PROTOCOL_PATH, "M105 final protocol")
    payload = {key: value for key, value in protocol.items() if key != "protocol_digest"}
    if protocol.get("schema") != "m105-protocol-v1" or protocol.get(
        "protocol_digest"
    ) != digest(payload):
        raise QualificationRefused("M105 protocol schema or digest mismatch")
    if protocol.get("status") != "frozen_protocol_owner_authorized":
        raise QualificationRefused("M105 protocol is not owner-authorized")
    if protocol.get("decisive_conditions") != EXPECTED_PREDICATES:
        raise QualificationRefused("M105 decisive predicate declaration changed")
    if protocol.get("qualification_pool_digest") != POOL_DIGEST or protocol.get(
        "qualification_pool_raw_sha256"
    ) != POOL_RAW_SHA256:
        raise QualificationRefused("M105 protocol pool binding mismatch")
    if protocol.get("canonical_runtime") != {
        "python": {"implementation": "cpython", "version_info": list(CANONICAL_PYTHON)},
        "sqlite": {
            "module": "sqlite3",
            "sqlite_version": ".".join(map(str, CANONICAL_SQLITE)),
            "sqlite_version_info": list(CANONICAL_SQLITE),
        },
    }:
        raise QualificationRefused("M105 canonical runtime declaration mismatch")
    if tuple(sys.version_info[:3]) != CANONICAL_PYTHON or tuple(
        sqlite3.sqlite_version_info
    ) != CANONICAL_SQLITE:
        raise QualificationRefused("M105 canonical runtime mismatch")
    bound = protocol.get("bound_files", {})
    files = bound.get("files")
    members = bound.get("member_digests")
    if not isinstance(files, list) or not isinstance(members, dict):
        raise QualificationRefused("M105 bound-file record is invalid")
    measured = {path: sha256_bytes((ROOT / path).read_bytes()) for path in files}
    if measured != members or digest(measured) != bound.get("digest"):
        raise QualificationRefused("M105 bound apparatus changed")
    freeze_tag = protocol.get("freeze_tag")
    if not isinstance(freeze_tag, str) or _git("cat-file", "-t", freeze_tag) != "tag":
        raise QualificationRefused("M105 freeze reference is not an annotated tag")
    if _git("rev-list", "-n", "1", freeze_tag) != _git("rev-parse", "HEAD"):
        raise QualificationRefused("M105 HEAD is not the frozen tag commit")
    if _git("status", "--porcelain"):
        raise QualificationRefused("M105 canonical worktree is not clean")
    if RESULT_PATH.exists() or CHECK_PATH.exists():
        raise QualificationRefused("M105 canonical evidence path already exists")
    return protocol


def preflight() -> dict[str, Any]:
    inputs = verify_inputs()
    protocol = require_frozen()
    return {
        "schema": "m105-preflight-v1",
        "confirmed": inputs["confirmed"],
        "inputs": inputs,
        "protocol_digest": protocol["protocol_digest"],
        "result_absent": not RESULT_PATH.exists(),
        "check_report_absent": not CHECK_PATH.exists(),
        "python": platform.python_version(),
        "sqlite": sqlite3.sqlite_version,
    }


def materialize(*, authorized_by_owner: bool, understand_unique_attempt: bool) -> dict[str, Any]:
    if not authorized_by_owner or not understand_unique_attempt:
        raise QualificationRefused("M105 owner authorization or unique-attempt acknowledgement absent")
    protocol = require_frozen()
    evidence = run_experiment()
    result: dict[str, Any] = {
        "schema": "m105-result-v1",
        "milestone": "M105",
        "hypothesis": "H50",
        "attempt": 1,
        "protocol_digest": protocol["protocol_digest"],
        "pool_digest": POOL_DIGEST,
        "scientific_evidence": evidence,
        "stable_evidence_digest": digest(stable_projection(evidence)),
        "model_calls": 0,
        "network_calls": 0,
        "remote_execution_calls": 0,
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
    development = subparsers.add_parser("development")
    development.add_argument("--out")
    canonical = subparsers.add_parser("canonical")
    canonical.add_argument("--owner-authorized", action="store_true")
    canonical.add_argument("--understand-unique-attempt", action="store_true")
    arguments = parser.parse_args()
    try:
        if arguments.command == "preflight":
            report = preflight()
        elif arguments.command == "development":
            evidence = run_experiment()
            report = {
                "schema": "m105-development-rehearsal-v1",
                "confirmed": True,
                "stable_evidence_digest": digest(stable_projection(evidence)),
                "evidence": evidence,
            }
            if arguments.out:
                Path(arguments.out).write_bytes(canonical_json(report).encode("ascii"))
        else:
            report = materialize(
                authorized_by_owner=arguments.owner_authorized,
                understand_unique_attempt=arguments.understand_unique_attempt,
            )
    except Exception as error:
        report = {
            "schema": "m105-qualification-refusal-v1",
            "confirmed": False,
            "failed_closed": True,
            "error": f"{type(error).__name__}: {error}",
        }
        print(json.dumps(report, sort_keys=True))
        return 3
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
