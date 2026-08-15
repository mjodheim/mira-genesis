from __future__ import annotations

import ast
from pathlib import Path

import pytest

from metamorphosis.m092_adoption import (
    downstream_primitive_id,
    extend_language,
    extend_substrate,
    operation_key,
)
from metamorphosis.m092_adoption_checkpoint import load_frozen_base
from metamorphosis.m092_kernel import program_digest
from metamorphosis.m092_qualification_contract import (
    FAMILY_ALTERNATING,
    FAMILY_COMPLEMENTARY,
    execution_contract,
)
from metamorphosis.m092_qualification_execution import (
    QualificationExecutionError,
    QualificationWorld,
    execute_qualification_world,
)


# Neutral identity semantics, deliberately not the M092 parity target.  On inputs 0 and 1 it lets the
# family-composition mechanics be exercised without rehearsing the qualifying transformation.
NEUTRAL_IDENTITY_PROGRAM = (
    ("SPOP", 0),
    ("SPUSH", 0),
    ("HALT",),
)


def _neutral_extended_runtime():
    base_language, base_substrate, _, _ = load_frozen_base()
    key = operation_key(NEUTRAL_IDENTITY_PROGRAM)
    primitive_id = downstream_primitive_id(NEUTRAL_IDENTITY_PROGRAM)
    receipt = {
        "program_digest": program_digest(NEUTRAL_IDENTITY_PROGRAM),
        "operation_key": key,
        "primitive_id": primitive_id,
    }
    substrate = extend_substrate(base_substrate, NEUTRAL_IDENTITY_PROGRAM, receipt=receipt)
    language = extend_language(base_language, substrate, NEUTRAL_IDENTITY_PROGRAM, receipt=receipt)
    return language, substrate, key, primitive_id


def _execute(family: str, value: int):
    language, substrate, _, primitive_id = _neutral_extended_runtime()
    return execute_qualification_world(
        QualificationWorld(family, f"neutral-{family}-{value}", value),
        downstream_primitive_id=primitive_id,
        language=language,
        substrate=substrate,
        qualification_contract=execution_contract(),
        reproduction_gate_open=True,
        adoption_committed=True,
        fresh_process_loaded=True,
    )


def test_alternating_family_executes_dynamic_acquired_primitive() -> None:
    result = _execute(FAMILY_ALTERNATING, 1)
    assert result["success"] is True
    assert result["actual_slot0"] == 1
    assert result["expected_slot0"] == 1
    assert result["program"] == [[result["downstream_primitive_id"], [0, 0]]]
    assert result["language_digest_before"] == result["language_digest_after"]
    assert result["substrate_digest_before"] == result["substrate_digest_after"]
    assert result["operation_registration_during_attempt"] is False


def test_complementary_family_is_same_primitive_then_inherited_neg_inc() -> None:
    result = _execute(FAMILY_COMPLEMENTARY, 1)
    assert result["success"] is True
    assert result["actual_slot0"] == 0
    assert result["expected_slot0"] == 0
    assert result["program"] == [
        [result["downstream_primitive_id"], [0, 0]],
        ["APPLY_UNARY", [0, "neg"]],
        ["APPLY_UNARY", [0, "inc"]],
    ]


def test_executor_scores_failure_instead_of_repairing_neutral_semantics() -> None:
    # Identity is not parity for 2; the executor must preserve that negative observation.
    result = _execute(FAMILY_ALTERNATING, 2)
    assert result["success"] is False
    assert result["actual_slot0"] == 2
    assert result["expected_slot0"] == 0
    assert result["refusal_code"] is None


@pytest.mark.parametrize(
    "gate,adopted,fresh",
    [(False, True, True), (True, False, True), (True, True, False)],
)
def test_execution_refuses_before_every_chronology_gate(gate: bool, adopted: bool, fresh: bool) -> None:
    language, substrate, _, primitive_id = _neutral_extended_runtime()
    with pytest.raises(QualificationExecutionError):
        execute_qualification_world(
            QualificationWorld(FAMILY_ALTERNATING, "gate-test", 0),
            downstream_primitive_id=primitive_id,
            language=language,
            substrate=substrate,
            qualification_contract=execution_contract(),
            reproduction_gate_open=gate,
            adoption_committed=adopted,
            fresh_process_loaded=fresh,
        )


def test_dependency_ablation_refuses_before_scoring() -> None:
    language, substrate, key, primitive_id = _neutral_extended_runtime()
    ablated = substrate.without(key)
    with pytest.raises(QualificationExecutionError, match="exactly one live acquired"):
        execute_qualification_world(
            QualificationWorld(FAMILY_ALTERNATING, "dependency-ablated", 0),
            downstream_primitive_id=primitive_id,
            language=language,
            substrate=ablated,
            qualification_contract=execution_contract(),
            reproduction_gate_open=True,
            adoption_committed=True,
            fresh_process_loaded=True,
        )


def test_contract_drift_refuses_execution() -> None:
    language, substrate, _, primitive_id = _neutral_extended_runtime()
    contract = execution_contract()
    contract["more_budget_same_substrate_complete_search_repetitions"] = 11
    with pytest.raises(QualificationExecutionError, match="contract validation failed"):
        execute_qualification_world(
            QualificationWorld(FAMILY_ALTERNATING, "contract-drift", 0),
            downstream_primitive_id=primitive_id,
            language=language,
            substrate=substrate,
            qualification_contract=contract,
            reproduction_gate_open=True,
            adoption_committed=True,
            fresh_process_loaded=True,
        )


def test_execution_module_cannot_import_search_reproduction_or_hidden_generator() -> None:
    source = Path("metamorphosis/m092_qualification_execution.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    forbidden = {
        "metamorphosis.m092_qualification_generator",
        "metamorphosis.m092_criterion_search",
        "scripts.package_m092_canonical_search",
        "scripts.run_m092_independent_reproduction",
    }
    assert imports.isdisjoint(forbidden)
