"""The M092 candidate-side generator must agree with the independent verifier on a neutral task."""
from __future__ import annotations

import ast
from pathlib import Path

import metamorphosis.m092_certificate_generator as generator
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


def test_generic_generator_produces_a_neutral_global_certificate() -> None:
    accepted: list[dict[str, object]] = []
    generated = 0
    for certificate in generator.generate_candidate_certificates(
        COUNTDOWN_PROGRAM, COUNTDOWN_POSTCONDITION,
    ):
        generated += 1
        try:
            report = verify_global_certificate(
                COUNTDOWN_PROGRAM,
                certificate,
                expected_postcondition=COUNTDOWN_POSTCONDITION,
            )
        except CertificateError:
            continue
        accepted.append(report)
        break

    assert generated > 0
    assert accepted
    assert accepted[0]["status"] == "accepted"
    assert accepted[0]["global_domain"] == "every integer x >= 0"
    assert accepted[0]["finite_execution_used"] is False


def test_generation_is_byte_deterministic_for_the_neutral_task() -> None:
    first = next(generator.generate_candidate_certificates(
        COUNTDOWN_PROGRAM, COUNTDOWN_POSTCONDITION,
    ))
    second = next(generator.generate_candidate_certificates(
        COUNTDOWN_PROGRAM, COUNTDOWN_POSTCONDITION,
    ))
    assert first == second


def test_generator_cannot_import_the_independent_verifier_or_qualification() -> None:
    tree = ast.parse(Path(generator.__file__).read_text(encoding="utf-8"))
    project_imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            project_imports.update(
                alias.name for alias in node.names if alias.name.startswith("metamorphosis")
            )
        elif isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("metamorphosis"):
            project_imports.add(node.module)

    assert project_imports == {
        "metamorphosis.m092_kernel",
        "metamorphosis.m092_proof_search",
        "metamorphosis.m092_runtime",
    }
