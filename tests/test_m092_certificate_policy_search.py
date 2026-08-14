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
