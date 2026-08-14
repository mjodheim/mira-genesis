"""Pre-search tests for M092 path-wise candidate certificate policies."""
from __future__ import annotations

import ast
from pathlib import Path

import metamorphosis.m092_certificate_policy_search as policies
from metamorphosis.m092_certificate_verifier import (
    COUNTDOWN_POSTCONDITION,
    CertificateError,
    verify_global_certificate,
)
from metamorphosis.m092_kernel import Program


COUNTDOWN_PROGRAM: Program = (
    ("SPOP", 0),
    ("LOADI", 1, 1),
    ("JZ", 0, 5),
    ("SUB", 0, 0, 1),
    ("JMP", 2),
    ("SPUSH", 0),
    ("HALT",),
)
COUNTDOWN_WITH_STEP_WITNESS = {
    "schema": "m092-affine-postcondition-v1",
    "witnesses": ["steps"],
    "constraints": [
        {"relation": "eq", "coefficients": {"steps": -1, "x": 1}, "constant": 0},
        {"relation": "eq", "coefficients": {"y": 1}, "constant": 0},
        {"relation": "ge", "coefficients": {"steps": 1}, "constant": 0},
    ],
}


def test_policy_vectors_are_path_major_deterministic_and_include_zero_policy() -> None:
    found = list(policies.enumerate_policy_vectors(("path-b", "path-a"), 1))
    assert found == [
        (("path-a", (0,)), ("path-b", (0,))),
        (("path-a", (0,)), ("path-b", (1,))),
        (("path-a", (1,)), ("path-b", (0,))),
        (("path-a", (1,)), ("path-b", (1,))),
    ]


def test_every_policy_attempt_receives_a_real_contiguous_ordinal() -> None:
    records = list(policies.enumerate_certificate_policy_records(
        COUNTDOWN_PROGRAM,
        COUNTDOWN_POSTCONDITION,
        limit=3,
    ))
    assert records
    assert [record.ordinal for record in records] == list(range(1, len(records) + 1))
    assert len(records) <= 3
    assert all(record.refusal is not None or record.certificate is not None for record in records)


def test_pathwise_generator_still_builds_a_neutral_certificate_accepted_independently() -> None:
    accepted = None
    examined = 0
    for record in policies.enumerate_certificate_policy_records(
        COUNTDOWN_PROGRAM,
        COUNTDOWN_POSTCONDITION,
    ):
        examined += 1
        if record.certificate is None:
            continue
        try:
            accepted = verify_global_certificate(
                COUNTDOWN_PROGRAM,
                record.certificate,
                expected_postcondition=COUNTDOWN_POSTCONDITION,
            )
        except CertificateError:
            continue
        break

    assert examined > 0
    assert accepted is not None
    assert accepted["status"] == "accepted"
    assert accepted["global_domain"] == "every integer x >= 0"
    assert accepted["finite_execution_used"] is False


def test_pathwise_search_can_certify_a_neutral_explicit_step_witness() -> None:
    selected = None
    for record in policies.enumerate_certificate_policy_records(
        COUNTDOWN_PROGRAM,
        COUNTDOWN_WITH_STEP_WITNESS,
    ):
        if record.certificate is None:
            continue
        try:
            receipt = verify_global_certificate(
                COUNTDOWN_PROGRAM,
                record.certificate,
                expected_postcondition=COUNTDOWN_WITH_STEP_WITNESS,
            )
        except CertificateError:
            continue
        selected = (record, receipt)
        break

    assert selected is not None
    record, receipt = selected
    assert record.ghost_count >= 1
    assert any(any(values) for _, values in record.increments)
    assert receipt["status"] == "accepted"
    assert receipt["ghost_counters"] >= 1
    assert receipt["finite_execution_used"] is False


def test_step_witness_uses_a_conjunctive_input_register_ghost_invariant() -> None:
    record = next(
        item
        for item in policies.enumerate_certificate_policy_records(
            COUNTDOWN_PROGRAM,
            COUNTDOWN_WITH_STEP_WITNESS,
        )
        if item.certificate is not None
    )
    assert record.certificate is not None
    loop_invariants = record.certificate["loop_invariants"]
    assert isinstance(loop_invariants, list) and len(loop_invariants) == 1
    constraints = loop_invariants[0]["constraints"]
    assert isinstance(constraints, list)

    # Normalisation makes g0 + r0 - x = 0 the canonical sign.  The relation is not
    # symbolically self-preserving unless the companion invariant r1 = 1 is available;
    # this is the regression that conjunctive induction must retain.
    assert {
        "relation": "eq",
        "coefficients": {"g0": 1, "r0": 1, "x": -1},
        "constant": 0,
    } in constraints
    assert {
        "relation": "eq",
        "coefficients": {"r1": 1},
        "constant": -1,
    } in constraints


def test_policy_search_cannot_import_verifier_or_qualification_material() -> None:
    tree = ast.parse(Path(policies.__file__).read_text(encoding="utf-8"))
    project_imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            project_imports.update(
                alias.name for alias in node.names if alias.name.startswith("metamorphosis")
            )
        elif isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("metamorphosis"):
            project_imports.add(node.module)

    assert project_imports == {
        "metamorphosis.m092_certificate_generator",
        "metamorphosis.m092_kernel",
    }
    assert all("verifier" not in name for name in project_imports)
    assert all("qualification" not in name for name in project_imports)
