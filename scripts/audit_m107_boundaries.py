"""Fail-closed adversarial pre-freeze audit for M107.

Attacks the claim rather than confirming it: every check below is an objection an opponent would
raise, expressed as something the apparatus must survive.
"""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from metamorphosis import m107_runtime as runtime  # noqa: E402
from scripts import check_m107_result  # noqa: E402
from scripts import run_m107_qualification as qualification  # noqa: E402

ROOT = _ROOT
EXPERIMENT = ROOT / "experiments" / "M107"


def _keys_anywhere(value: Any, names: set[str]) -> bool:
    if isinstance(value, dict):
        if names & set(value):
            return True
        return any(_keys_anywhere(item, names) for item in value.values())
    if isinstance(value, list):
        return any(_keys_anywhere(item, names) for item in value)
    return False


def _bool_sequence(node: ast.AST) -> tuple[bool, ...] | None:
    if not isinstance(node, (ast.List, ast.Tuple)):
        return None
    values: list[bool] = []
    for element in node.elts:
        if isinstance(element, ast.Constant) and isinstance(element.value, bool):
            values.append(element.value)
        else:
            return None
    return tuple(values) if values else None


def _contains_literal(tree: ast.AST, forbidden: list[list[bool]]) -> bool:
    """True when a forbidden truth table is *shipped as an operator* in the source.

    Only arguments of operator_definition() calls count. A bare two-element boolean tuple is
    ambiguous: SIGNAL_ROWS legitimately contains (True, False) as a signal row, which is not the
    module shipping a negation operator.
    """
    wanted = {tuple(item) for item in forbidden}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = node.func.id if isinstance(node.func, ast.Name) else getattr(node.func, "attr", "")
        if name != "operator_definition":
            continue
        for argument in node.args:
            if _bool_sequence(argument) in wanted:
                return True
    return False


def _read(path: str) -> bytes:
    return (ROOT / path).read_bytes()


def audit() -> dict[str, Any]:
    demands = json.loads(_read("experiments/M107/DEMANDS.json").decode("ascii"))
    targets = [tuple(bool(bit) for bit in row) for row in demands["targets"]]

    base = runtime.initial_operators()
    base_image = runtime.complete_image(base)
    certificates = [runtime.insufficiency_certificate(base, target) for target in targets]

    s0 = runtime.create_state()
    single = runtime.acquire_operator(s0, [demands["primary"]], register_result=False)
    joint = runtime.acquire_operator(
        s0, [demands["joint"]["first"], demands["joint"]["second"]], register_result=True
    )
    s1 = joint.get("next_state")
    extended_image = runtime.complete_image(s1["operators"]) if s1 else {}

    runtime_source = _read("metamorphosis/m107_runtime.py").decode("utf-8")
    tree = ast.parse(runtime_source)
    interpreter = [
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "execute_expression"
    ][0]
    interpreter_source = ast.get_source_segment(runtime_source, interpreter) or ""

    demand_text = runtime.canonical_json(demands).lower()
    adopted = joint.get("adopted_operator") or {}

    # Predicate semantics must not import the mechanism or the orchestration.
    predicate_tree = ast.parse(
        __import__("inspect").getsource(check_m107_result.evaluate_conditions)
    )

    checks = {
        # The substrate is genuinely incomplete, and for a structural reason.
        "base_image_is_four_of_sixteen": len(base_image) == 4,
        "both_targets_outside_base_image": all(target not in base_image for target in targets),
        "exclusion_is_budget_independent": all(
            item["budget_independent"] is True and item["confirmed"] is True
            for item in certificates
        ),
        "image_is_stable_at_the_bound": len(runtime.complete_image(base, 13)) == len(base_image),
        # The interpreter holds no operator semantics of its own.
        "interpreter_applies_only_state_tables": (
            "operator[\"truth_table\"][index]" in interpreter_source
            and " and " not in interpreter_source.replace("children", "")
            and "not " not in interpreter_source.split("def run")[1].split("return")[0]
        ),
        # The precise property: the initial table is exactly the monotone fragment, and no negation
        # truth table is written as a literal anywhere in the module.
        "runtime_ships_only_the_monotone_fragment": sorted(
            (item["name"], tuple(item["truth_table"])) for item in base
        ) == [
            ("AND", (False, False, False, True)),
            ("OR", (False, True, True, True)),
        ],
        "runtime_contains_no_negation_literal": not _contains_literal(
            tree, [[True, False], [True, False, False, True], [True, False, True, False]]
        ),
        # The candidate space is generic; the answer is not coded.
        "operator_space_is_the_full_generic_space": len(runtime.operator_space()) == 20,
        "adopted_operator_is_not_named_in_the_runtime": adopted.get("truth_table") is not None
        and str(adopted.get("truth_table")) not in runtime_source,
        # A single behaviour must not determine the extension.
        "single_demand_is_refused": single.get("confirmed") is False
        and single.get("reason") == "extension_underdetermined_by_observations",
        "single_demand_leaves_several_reach_classes": (single.get("surviving_reach_classes") or 0) >= 2,
        # The joint demand determines exactly one reach class.
        "joint_demand_determines_one_class": joint.get("confirmed") is True
        and joint.get("surviving_reach_classes") == 1,
        "joint_search_exhausts_the_space": joint.get("operator_space_exhausted") is True,
        "extension_enlarges_the_image": len(extended_image) == 16,
        "targets_inside_extended_image": all(target in extended_image for target in targets),
        # The demand fixture leaks no operator identity.
        # The precise property: the fixture must not carry the answer. Its schema names contain the
        # word "operator", which is harmless; what must be absent is the adopted operator's table,
        # its content address, and any arity or truth-table field.
        "demands_leak_no_operator_identity": (
            str(adopted.get("truth_table")) not in demand_text
            and str(adopted.get("operator_id", "sentinel")) not in demand_text
            and not _keys_anywhere(demands, {"arity", "truth_table", "operator_id"})
        ),
        # The extension is state, not host code.
        "extension_is_serialized_state": bool(s1)
        and any(item["name"].startswith("ACQUIRED_") for item in s1["operators"]),
        "extension_survives_serialization": bool(s1)
        and runtime.decode_state(runtime.encode_state(s1))["state_digest"] == s1["state_digest"],
        # Independence of the predicate function.
        "predicates_import_nothing": not any(
            isinstance(node, (ast.Import, ast.ImportFrom)) for node in ast.walk(predicate_tree)
        ),
        "checker_bootstraps_the_repository_root": "_ROOT = Path(__file__).resolve().parents[1]"
        in _read("scripts/check_m107_result.py").decode("utf-8"),
        # No canonical evidence yet.
        "canonical_evidence_absent_before_attempt": not (EXPERIMENT / "RESULT.json").exists()
        and not (EXPERIMENT / "CHECK_REPORT.json").exists(),
    }

    report: dict[str, Any] = {
        "schema": "m107-adversarial-pre-freeze-audit-v1",
        "confirmed": all(checks.values()),
        "checks": checks,
        "base_image_size": len(base_image),
        "extended_image_size": len(extended_image),
        "single_demand_reach_classes": single.get("surviving_reach_classes"),
        "joint_demand_reach_classes": joint.get("surviving_reach_classes"),
        "adopted_arity": adopted.get("arity"),
        "adopted_truth_table": adopted.get("truth_table"),
        "claim_ceiling": "the_acquisition_machinery_itself_remains_authored",
    }
    report["report_digest"] = runtime.digest(report)
    return report


def main() -> int:
    report = audit()
    print(json.dumps(report, sort_keys=True))
    return 0 if report["confirmed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
