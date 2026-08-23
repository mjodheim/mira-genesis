"""Adversarial source audit for M101's pre-run separation boundaries."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FILES = {
    "acquisition_runtime": ROOT / "metamorphosis" / "m101_runtime.py",
    "execution_runtime": ROOT / "metamorphosis" / "m101_executor.py",
    "acquisition_entry": ROOT / "scripts" / "run_m101_acquisition_process.py",
    "execution_entry": ROOT / "scripts" / "run_m101_fresh_process.py",
    "definition_checker": ROOT / "scripts" / "check_m101_definitions.py",
    "result_checker": ROOT / "scripts" / "check_m101_result.py",
    "pool_author": ROOT / "scripts" / "author_m101_qualification_pool.py",
    "qualification_runner": ROOT / "scripts" / "run_m101_qualification.py",
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
    return {
        node.name: node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
    }


def audit() -> dict[str, Any]:
    sources = {name: path.read_text(encoding="utf-8") for name, path in FILES.items()}
    trees = {name: ast.parse(source) for name, source in sources.items()}
    checks: dict[str, bool] = {}

    execution_functions = set(_functions(trees["execution_runtime"]))
    checks["execution_runtime_has_no_acquisition_or_registration_function"] = not any(
        name.startswith("acquire") or name in {"register", "baseline", "create_state"}
        for name in execution_functions
    )
    checks["execution_runtime_has_no_search_alphabet_or_result_writer"] = all(
        token not in sources["execution_runtime"]
        for token in ("A_TOKENS", "A_MAX_BODY", "B_MAX_BODY", "RESULT.json", "QUALIFICATION_POOL")
    )
    checks["execution_runtime_has_no_producer_or_pool_import"] = (
        "producer_trigger" not in sources["execution_runtime"]
        and not _imports(trees["execution_runtime"])
        & {"m101_runtime", "scripts", "metamorphosis"}
    )

    a_executor = _functions(trees["execution_runtime"])["_execute_a_body"]
    a_executor_text = ast.unparse(a_executor).lower()
    checks["a_execution_path_is_carrier_neutral"] = not any(
        term in a_executor_text
        for term in (
            "text", "record", "mapping", "dict", "syntax", "ast", "rename",
            "strip", "upper", "lower", "sort", "docstring",
        )
    )
    b_executor_text = ast.unparse(
        _functions(trees["execution_runtime"])["_execute_b_body"]
    ).lower()
    checks["b_execution_path_is_carrier_neutral"] = not any(
        term in b_executor_text
        for term in (
            "text", "record", "mapping", "syntax", "ast", "rename",
            "strip", "upper", "lower", "sort", "docstring",
        )
    )
    checks["carrier_specific_code_is_confined_to_atomic_adapters"] = all(
        name in execution_functions
        for name in ("_text_atomic", "_record_atomic", "_syntax_atomic", "atomic_from_descriptor")
    )
    checks["execution_revalidates_executable_m100_state"] = (
        "decode_m100_state" in execution_functions
        and any(
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "decode_m100_state"
            for node in ast.walk(_functions(trees["execution_runtime"])["decode_state"])
        )
    )

    acquisition_imports = _imports(trees["acquisition_entry"])
    checks["acquisition_entry_imports_only_bare_bound_runtime"] = (
        "m101_runtime" in acquisition_imports
        and not acquisition_imports & {"metamorphosis", "scripts", "mira_core"}
    )
    checks["acquisition_capsule_source_has_no_pool_or_hidden_case_loader"] = all(
        token not in sources["acquisition_entry"] + sources["acquisition_runtime"]
        for token in ("QUALIFICATION_POOL", "author_m101", "hidden_cases")
    )
    checks["acquisition_capsule_has_no_ambient_payload_or_repository_enumerator"] = all(
        token not in sources["acquisition_entry"] + sources["acquisition_runtime"]
        for token in (".glob(", ".rglob(", ".iterdir(", "os.listdir", "os.walk", "ROOT =")
    )
    checks["acquisition_api_uses_closed_public_projection"] = all(
        token in sources["acquisition_runtime"]
        for token in ("PUBLIC_DEMAND_SCHEMA", "decode_public_demand", "public_case_ids")
    )

    validator_imports = _imports(trees["definition_checker"])
    checks["definition_checker_is_implementation_independent"] = not validator_imports & {
        "m101_runtime", "m101_executor", "metamorphosis", "scripts", "mira_core"
    }
    checks["definition_checker_recomputes_symbolic_a_and_b"] = all(
        name in _functions(trees["definition_checker"]) for name in ("_symbolic_a", "_symbolic_b")
    )
    checks["result_checker_owns_the_stable_projection"] = (
        "def checker_stable_projection" in sources["result_checker"]
        and "stable_projection," not in sources["result_checker"]
    )
    checks["pool_author_is_source_only_and_mechanism_free"] = (
        not _imports(trees["pool_author"])
        & {"m101_runtime", "m101_executor", "metamorphosis", "mira_core"}
        and all(
            token in sources["pool_author"]
            for token in (
                '"acquisition_was_run": False',
                '"execution_was_run": False',
                '"fault_was_injected": False',
            )
        )
    )
    fresh_launcher = _functions(trees["qualification_runner"])["_fresh"]
    fresh_launcher_text = ast.unparse(fresh_launcher)
    checks[
        "qualification_runner_launches_one_isolated_synchronous_subprocess_per_invocation"
    ] = all(
        token in fresh_launcher_text
        for token in ("subprocess.run", "'-I'", "cwd=capsule", "check=False")
    )

    runtime_functions = _functions(trees["acquisition_runtime"])
    acquisition_search_text = (
        ast.unparse(runtime_functions["acquire_a"])
        + ast.unparse(runtime_functions["acquire_b"])
    )
    checks["acquisition_search_does_not_prefilter_exact_target_trace"] = all(
        token not in acquisition_search_text
        for token in (
            "_a_call_order(body) != (0, 1)",
            "_b_call_order(body, a_id) != (0, 1, 2)",
        )
    )
    t0_baseline = _functions(trees["execution_runtime"])["_execute_t0_baseline"]
    t0_baseline_text = ast.unparse(t0_baseline)
    checks["baseline_language_is_exactly_one_atomic_application"] = (
        "atomic.apply" in t0_baseline_text
        and "_execute_a_body" not in t0_baseline_text
        and "_execute_b_body" not in t0_baseline_text
        and all(
        token in t0_baseline_text
        for token in ("structural_max_atomic_effects", "more_budget_same_language_can_exceed_one_effect")
        )
    )
    checks["baseline_budget_matches_two_slot_resolution_budget"] = (
        "len(catalog) ** 2" in t0_baseline_text
        and "candidate_budget" in t0_baseline_text
    )
    mechanism_source = sources["acquisition_runtime"] + sources["execution_runtime"]
    checks["host_pipeline_shortcut_is_absent"] = all(
        token not in mechanism_source
        for token in ("apply_pipeline", "infer_slots", "resolve_slots")
    )
    checks["finished_composition_primitive_is_absent"] = all(
        token not in mechanism_source
        for token in ('"COMPOSE"', '"CHAIN"')
    )
    checks["baseline_and_retained_arms_use_one_executor_action"] = all(
        token in sources["qualification_runner"]
        for token in (
            '"same_executor_capsule": True',
            'baseline_envelope["action"]',
            'retained_envelope["action"]',
            'differing_state_keys == ["definitions", "state_digest"]',
        )
    )
    capsule_source = "".join(
        sources[name]
        for name in (
            "acquisition_runtime", "execution_runtime", "acquisition_entry", "execution_entry"
        )
    )
    capsule_imports = set().union(
        *(
            _imports(trees[name])
            for name in (
                "acquisition_runtime", "execution_runtime", "acquisition_entry", "execution_entry"
            )
        )
    )
    checks["capsules_have_no_model_network_or_dynamic_code_path"] = (
        not capsule_imports
        & {
            "anthropic", "http", "openai", "requests", "socket", "urllib", "webbrowser"
        }
        and all(
            token not in capsule_source
            for token in ("__import__(", "eval(", "exec(", "compile(")
        )
    )

    report: dict[str, Any] = {
        "schema": "m101-boundary-audit-v1",
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
