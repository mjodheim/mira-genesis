"""Adversarial source audit for M102's pre-run separation boundaries."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
FILES = {
    "acquisition_runtime": ROOT / "metamorphosis" / "m102_runtime.py",
    "predecessor_runtime": ROOT / "metamorphosis" / "m101_runtime.py",
    "execution_runtime": ROOT / "metamorphosis" / "m102_executor.py",
    "predecessor_executor": ROOT / "metamorphosis" / "m101_executor.py",
    "acquisition_entry": ROOT / "scripts" / "run_m102_acquisition_process.py",
    "execution_entry": ROOT / "scripts" / "run_m102_fresh_process.py",
    "definition_checker": ROOT / "scripts" / "check_m102_definitions.py",
    "predecessor_definition_checker": ROOT / "scripts" / "check_m101_definitions.py",
    "result_checker": ROOT / "scripts" / "check_m102_result.py",
    "pool_author": ROOT / "scripts" / "author_m102_qualification_pool.py",
    "protocol_builder": ROOT / "scripts" / "build_m102_protocol.py",
    "qualification_runner": ROOT / "scripts" / "run_m102_qualification.py",
}


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("ascii")).hexdigest()


def _imports(tree: ast.AST) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module.split(".")[0])
    return found


def _functions(tree: ast.AST) -> dict[str, ast.FunctionDef]:
    return {node.name: node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}


def audit() -> dict[str, Any]:
    sources = {name: path.read_text(encoding="utf-8") for name, path in FILES.items()}
    trees = {name: ast.parse(source) for name, source in sources.items()}
    functions = {name: _functions(tree) for name, tree in trees.items()}
    checks: dict[str, bool] = {}

    execution_functions = set(functions["execution_runtime"])
    checks["execution_runtime_has_no_acquisition_registration_or_state_transition"] = not any(
        name.startswith("acquire")
        or name
        in {
            "register_events",
            "create_state",
            "mutate_policy_to_flat",
            "ablate_policy_raw",
            "mutate_c_duplicate_effect",
            "mutate_m101_b_order",
        }
        for name in execution_functions
    )
    checks["execution_runtime_has_no_search_alphabet_enumerator_pool_or_result_writer"] = all(
        token not in sources["execution_runtime"]
        for token in (
            "POLICY_TOKENS",
            "POLICY_MAX_BODY",
            "C_MAX_TRANSFORMS",
            "import itertools",
            "QUALIFICATION_POOL",
            "RESULT.json",
        )
    )
    checks["execution_runtime_does_not_import_acquisition_runtime"] = (
        "m102_runtime" not in _imports(trees["execution_runtime"])
        and "m102_runtime" not in sources["execution_runtime"].replace('"m102_runtime"', "")
    )
    resolve_text = ast.unparse(functions["execution_runtime"]["_resolve"])
    registry_text = ast.unparse(functions["execution_runtime"]["_registry_index"])
    checks["every_registry_lookup_executes_live_state_policy"] = (
        "_event_key(state['policy']" in resolve_text
        and "_event_key(state['policy']" in registry_text
    )
    c_text = ast.unparse(functions["execution_runtime"]["_execute_c"])
    checks["c_execution_interprets_registered_body_and_live_b"] = all(
        token in c_text for token in ("c_item['body']", "b['definition_id']", "_execute_b")
    ) and all(
        token not in c_text for token in ("add_column", "backfill_length", "rename_column", "create_index")
    )
    checks["sqlite_scoring_reads_real_database_state_and_integrity"] = all(
        name in execution_functions for name in ("_materialize_sqlite", "_snapshot_sqlite")
    ) and all(
        token in sources["execution_runtime"]
        for token in ("PRAGMA table_info", "PRAGMA index_list", "PRAGMA integrity_check")
    )

    runtime_functions = functions["acquisition_runtime"]
    acquire_policy_text = ast.unparse(runtime_functions["acquire_policy"])
    acquire_c_text = ast.unparse(runtime_functions["acquire_c"])
    checks["k_search_exhausts_state_owned_micro_language_without_supplied_target_body"] = all(
        token in acquire_policy_text
        for token in ("itertools.product(POLICY_TOKENS", "POLICY_MAX_BODY", "public_lookups")
    ) and all(
        token not in acquire_policy_text for token in ("target_body", "target_digest", "expected_policy")
    )
    checks["c_search_has_no_host_k_origin_gate"] = "ACQUIRED_POLICY_ORIGIN" not in acquire_c_text
    checks["c_search_fails_from_live_registry_representability"] = all(
        token in acquire_c_text
        for token in (
            "registry_index(checked)",
            "unrepresentable by the live policy",
            "_resolved_sqlite_atomics",
        )
    )
    checks["c_search_does_not_prefilter_exact_four_effect_target_order"] = all(
        token not in acquire_c_text
        for token in (
            "sorted(trace) == [0, 1, 2, 3]",
            "trace == (0, 1, 2, 3)",
            "expected_trace",
        )
    )
    decode_c_text = ast.unparse(runtime_functions["decode_c_definition"])
    checks["c_definition_requires_executed_live_b_and_policy_content_addresses"] = all(
        token in decode_c_text
        for token in (
            "definition_dependencies",
            "policy_dependency",
            "CALL:{b_id}:",
            "content address mismatch",
        )
    )
    checks["flat_control_is_structural_and_budget_independent"] = all(
        token in ast.unparse(runtime_functions["flat_collision_report"])
        for token in ("collision_witnesses", "joint_relation_representable", "budget_independent")
    )

    acquisition_source = sources["acquisition_runtime"] + sources["acquisition_entry"]
    checks["acquisition_capsule_has_no_pool_hidden_loader_or_repository_enumerator"] = all(
        token not in acquisition_source
        for token in (
            "QUALIFICATION_POOL",
            "hidden_cases",
            ".glob(",
            ".rglob(",
            "os.walk",
            "ROOT =",
            "check_m102_result",
        )
    )
    checks["acquisition_entry_imports_only_bare_bound_runtime"] = (
        "m102_runtime" in _imports(trees["acquisition_entry"])
        and not _imports(trees["acquisition_entry"])
        & {"metamorphosis", "scripts", "mira_core"}
    )

    validator_imports = _imports(trees["definition_checker"])
    checks["definition_checker_is_independent_of_m102_implementation"] = not validator_imports & {
        "m102_runtime",
        "m102_executor",
        "metamorphosis",
        "mira_core",
    }
    checks["definition_checker_rebuilds_policy_registry_and_c_symbolically"] = all(
        name in functions["definition_checker"]
        for name in ("_interpret_policy", "_rebuild_registry", "_validate_c")
    )
    result_imports = _imports(trees["result_checker"])
    checks["result_checker_does_not_import_m102_runtime_or_executor"] = not result_imports & {
        "m102_runtime",
        "m102_executor",
        "metamorphosis",
    }
    checks["result_checker_owns_stable_projection_and_independent_sqlite_execution"] = all(
        name in functions["result_checker"]
        for name in (
            "checker_stable_projection",
            "_policy_output",
            "_registry",
            "_c_order",
            "_independent_sqlite",
        )
    ) and "stable_projection," not in sources["result_checker"]
    checks["result_checker_computes_all_fifteen_conditions_without_runner_verdict"] = all(
        f"check_p{index}" in functions["result_checker"] for index in range(1, 16)
    ) and "verdict_helper" not in sources["result_checker"]

    pool_imports = _imports(trees["pool_author"])
    checks["pool_author_is_source_only_and_mechanism_free"] = (
        not pool_imports
        & {
            "m102_runtime",
            "m102_executor",
            "metamorphosis",
            "mira_core",
            "run_m102_qualification",
        }
        and all(
            token in sources["pool_author"]
            for token in (
                '"acquisition_was_run": False',
                '"hidden_success_was_scored": False',
                '"fault_was_injected": False',
            )
        )
    )
    checks["pool_preflight_materialises_raw_sqlite_without_running_transformations"] = (
        "_inspect_raw_sqlite_model" in functions["pool_author"]
        and all(
            token not in sources["pool_author"]
            for token in ("acquire_c(", "execute_c_world(", "execute_sqlite(")
        )
    )

    fresh_text = ast.unparse(functions["qualification_runner"]["_fresh"])
    checks["qualification_runner_launches_one_isolated_synchronous_subprocess_per_invocation"] = all(
        token in fresh_text for token in ("subprocess.run", "'-I'", "cwd=capsule", "check=False")
    )
    materialize_text = ast.unparse(functions["qualification_runner"]["materialize"])
    checks["canonical_runner_is_one_attempt_fail_closed_and_owner_armed"] = all(
        token in materialize_text
        for token in (
            "authorized_by_owner",
            "understand_unique_attempt",
            "RESULT_PATH.exists()",
            "require_frozen",
            "working tree must be clean",
            "RESULT_PATH.open('x'",
        )
    )
    checks["final_protocol_builder_requires_owner_acceptance_and_frozen_pool"] = all(
        token in ast.unparse(functions["protocol_builder"]["build_final"])
        for token in (
            "owner_authorization_reference",
            "pool['status'] != 'frozen'",
            "CANDIDATE_PATH.exists()",
        )
    ) and "i_accept_frozen_protocol" in sources["protocol_builder"]
    canonical_runtime_text = ast.unparse(
        functions["protocol_builder"]["_require_canonical_runtime"]
    )
    checks["protocol_builder_requires_exact_canonical_runtime"] = all(
        token in canonical_runtime_text
        for token in ("CANONICAL_PYTHON_IDENTITY", "CANONICAL_SQLITE_IDENTITY", "raise RuntimeError")
    ) and all(
        "_require_canonical_runtime()" in ast.unparse(functions["protocol_builder"][name])
        for name in ("build_candidate", "build_final")
    )
    run_text = sources["qualification_runner"]
    checks["hidden_materialisation_follows_producer_state_creation_in_source_order"] = (
        run_text.index("u1_path = base / \"U1.json\"")
        < run_text.index("record_paths = {")
        and run_text.index("u2_path = base / \"U2.json\"")
        < run_text.index("sqlite_paths = {")
    )
    checks["runner_records_observations_but_contains_no_scientific_verdict_helper"] = (
        not any(name.startswith("check_p") or name == "verdict" for name in functions["qualification_runner"])
        and "m102-check-report" not in run_text
    )

    capsule_names = (
        "acquisition_runtime",
        "predecessor_runtime",
        "execution_runtime",
        "predecessor_executor",
        "acquisition_entry",
        "execution_entry",
    )
    capsule_source = "".join(sources[name] for name in capsule_names)
    capsule_imports = set().union(*(_imports(trees[name]) for name in capsule_names))
    dangerous_calls = {
        node.func.id
        for name in capsule_names
        for node in ast.walk(trees[name])
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        and node.func.id in {"__import__", "eval", "exec", "compile"}
    }
    checks["capsules_have_no_model_network_dynamic_code_or_authority_path"] = (
        not capsule_imports
        & {
            "anthropic",
            "http",
            "openai",
            "requests",
            "socket",
            "subprocess",
            "urllib",
            "webbrowser",
        }
        and not dangerous_calls
        and "git push" not in capsule_source
    )

    report: dict[str, Any] = {
        "schema": "m102-boundary-audit-v1",
        "scientific_verdict": False,
        "passed": all(checks.values()),
        "checks": checks,
        "file_sha256": {
            str(path.relative_to(ROOT)).replace("\\", "/"): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in FILES.values()
        },
        "failures": [name for name, passed in checks.items() if not passed],
    }
    report["report_digest"] = digest(report)
    return report


def main() -> int:
    report = audit()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
