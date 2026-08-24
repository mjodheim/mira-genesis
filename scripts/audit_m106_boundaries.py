"""Fail-closed adversarial pre-freeze audit for M106."""

from __future__ import annotations

import ast
import hashlib
import inspect
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from metamorphosis import m105_runtime as runtime
from scripts import check_m105_definitions
from scripts import check_m105_m104_closure
from scripts import check_m105_semantics
from scripts import run_m106_qualification as qualification


EXPERIMENT = ROOT / "experiments" / "M106"


def _read(path: str) -> bytes:
    return (ROOT / path).read_bytes()


def _sha(path: str) -> str:
    return hashlib.sha256(_read(path)).hexdigest()


def _function(tree: ast.Module, name: str) -> ast.FunctionDef:
    matches = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name]
    if len(matches) != 1:
        raise ValueError(f"M106 audit could not isolate function {name}")
    return matches[0]


def audit() -> dict[str, Any]:
    predecessor_raw = _read("experiments/M106/M104_V3.json")
    development = json.loads(
        _read("experiments/M106/DEVELOPMENT_FIXTURE.json").decode("ascii")
    )
    pool = json.loads(_read("experiments/M106/QUALIFICATION_POOL.json").decode("ascii"))
    w0 = runtime.create_state(predecessor_raw)
    feature_result = runtime.acquire_feature(w0, development, register_result=True)
    w1 = feature_result["next_state"]
    json_lineage = runtime.acquire_consumer(
        w1, pool["json_demand"], register_result=True
    )
    w2 = json_lineage["next_state"]
    sqlite_lineage = runtime.acquire_consumer(
        w2, pool["sqlite_demand"], register_result=True
    )
    w3 = sqlite_lineage["next_state"]
    json_fresh = runtime.acquire_consumer(w0, pool["json_demand"], register_result=False)
    sqlite_fresh = runtime.acquire_consumer(w0, pool["sqlite_demand"], register_result=False)
    census = runtime.semantic_census()
    feature = w1["features"][0]
    feature_serialized = runtime.canonical_json(feature).lower()

    source = _read("metamorphosis/m105_runtime.py").decode("utf-8")
    tree = ast.parse(source)
    acquire_feature_source = ast.get_source_segment(
        source, _function(tree, "acquire_feature")
    ) or ""
    json_adapter = _function(tree, "_json_execute")
    sqlite_adapter = _function(tree, "_sqlite_execute")
    trace_adapter = _function(tree, "_execute_trace")
    execute_definition = _function(tree, "execute_definition")
    execute_source = ast.get_source_segment(source, execute_definition) or ""
    predicate_source = inspect.getsource(
        __import__("scripts.check_m106_result", fromlist=["evaluate_conditions"]).evaluate_conditions
    )

    allowed_ops = {"CONST", "INPUT", "NOT", "AND", "OR"}
    observed_ops: set[str] = set()
    for row in census["representatives"]:
        for node in ast.walk(ast.parse(repr(row["body"]))):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if node.value in allowed_ops:
                    observed_ops.add(node.value)
    development_text = runtime.canonical_json(development).lower()
    qualification_only_literals = {
        "m106_json_document_hidden_0",
        "m106_sqlite_hidden_0",
        "m106-json-public-thistle",
        "m106-sqlite-public-basalt",
        "channel",
        "harbor",
        "quartz",
    }
    producer_members = {
        *qualification.RUNTIME_SOURCES,
        "M104_V3.json",
        "DEVELOPMENT_FIXTURE.json",
        "AMBIGUOUS_DEVELOPMENT.json",
    }
    checker_sources = [
        _read(path).decode("utf-8")
        for path in (
            "scripts/check_m105_definitions.py",
            "scripts/check_m105_semantics.py",
            "scripts/check_m105_m104_closure.py",
        )
    ]
    checker_imports = {
        alias.name
        for checker_source in checker_sources
        for node in ast.walk(ast.parse(checker_source))
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    predicate_tree = ast.parse(predicate_source)

    definition_report = check_m105_definitions.validate(runtime.encode_state(w3))
    semantic_report = check_m105_semantics.validate(census, feature)
    closure_report = check_m105_m104_closure.validate(predecessor_raw)
    mutated = runtime.mutate_feature_and_rebind(w3)
    original_context = pool["hidden_json_cases"][2]["context"]
    original_initial = pool["hidden_json_cases"][2]["initial"]
    original_output = runtime.execute_definition(
        w3,
        runtime.definition_for_family(w3, "json_document"),
        original_context,
        original_initial,
    )
    mutated_output = runtime.execute_definition(
        mutated,
        runtime.definition_for_family(mutated, "json_document"),
        original_context,
        original_initial,
    )

    checks = {
        "exact_m104_raw_binding": _sha("experiments/M106/M104_V3.json")
        == runtime.M104_V3_RAW_SHA256,
        "empty_initial_registry": w0["features"] == [] and w0["definitions"] == [],
        "complete_semantic_image": census["semantic_count"] == 16
        and census["complete_two_input_boolean_image"] is True,
        "only_preregistered_lower_operators": observed_ops == allowed_ops,
        "feature_acquisition_source_has_no_future_identity": not any(
            term in acquire_feature_source.lower()
            for term in ("json_document", "sqlite", "channel", "harbor", "violet")
        ),
        "feature_bytes_have_no_fixture_or_carrier_identity": not any(
            term in feature_serialized
            for term in (
                "development",
                "json",
                "sqlite",
                "channel",
                "harbor",
                "quartz",
                "qualification",
            )
        ),
        "development_has_no_qualification_only_literals": not any(
            term in development_text for term in qualification_only_literals
        ),
        "producer_capsule_has_no_future_material": not any(
            name in producer_members
            for name in (
                "QUALIFICATION_POOL.json",
                "JSON_DEMAND.json",
                "SQLITE_DEMAND.json",
                "RESULT.json",
                "CHECK_REPORT.json",
            )
        ),
        "carrier_adapters_receive_no_context": all(
            "context" not in {argument.arg for argument in function.args.args}
            for function in (json_adapter, sqlite_adapter, trace_adapter)
        ),
        "execution_does_not_pass_context_to_carrier": "_execute_trace(selected[\"family\"], selected[\"actions\"], body, initial)"
        in execute_source,
        "fresh_json_exhausts_and_is_ambiguous": json_fresh["enumerated_feature_semantics"]
        == 16
        and json_fresh["semantic_image_exhausted"] is True
        and json_fresh["semantic_classes"] > 1
        and json_fresh["confirmed"] is False,
        "fresh_sqlite_exhausts_and_is_ambiguous": sqlite_fresh[
            "enumerated_feature_semantics"
        ]
        == 16
        and sqlite_fresh["semantic_image_exhausted"] is True
        and sqlite_fresh["semantic_classes"] > 1
        and sqlite_fresh["confirmed"] is False,
        "lineage_both_consumers_confirmed": json_lineage["confirmed"] is True
        and sqlite_lineage["confirmed"] is True,
        "definitions_keep_live_feature_dependency": all(
            definition["feature_id"] == feature["feature_id"]
            for definition in w3["definitions"]
        ),
        "content_addressed_mutation_changes_behavior": runtime.encode_state(mutated)
        != runtime.encode_state(w3)
        and original_output != mutated_output,
        "independent_definition_validation": definition_report["confirmed"] is True,
        "independent_semantic_validation": semantic_report["confirmed"] is True,
        "independent_m104_closure": closure_report["confirmed"] is True,
        "independent_checkers_do_not_import_m105_runtime": not any(
            name.endswith("m105_runtime") or name.endswith("run_m106_qualification")
            for name in checker_imports
        ),
        "predicate_function_imports_no_runtime_or_qualification": not any(
            isinstance(node, (ast.Import, ast.ImportFrom)) for node in ast.walk(predicate_tree)
        ),
        "canonical_evidence_absent_before_attempt": not (EXPERIMENT / "RESULT.json").exists()
        and not (EXPERIMENT / "CHECK_REPORT.json").exists(),
    }
    report: dict[str, Any] = {
        "schema": "m106-adversarial-pre-freeze-audit-v1",
        "confirmed": all(checks.values()),
        "checks": checks,
        "fresh_semantic_classes": {
            "json_document": json_fresh["semantic_classes"],
            "sqlite": sqlite_fresh["semantic_classes"],
        },
        "feature_id": feature["feature_id"],
        "feature_truth_table": feature["truth_table"],
        "definition_ids": [definition["definition_id"] for definition in w3["definitions"]],
        "claim_ceiling": "fixed_lower_boolean_interpreter_and_authored_interfaces",
    }
    report["report_digest"] = runtime.digest(report)
    return report


def main() -> int:
    report = audit()
    print(json.dumps(report, sort_keys=True))
    return 0 if report["confirmed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
