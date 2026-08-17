"""Candidate-side M092 proof search remains deterministic and verifier-independent."""
from __future__ import annotations

import ast
from pathlib import Path

from metamorphosis.m092_proof_search import find_affine_proof, proof_search_receipt


def c(relation: str, coefficients: dict[str, int], constant: int = 0) -> dict[str, object]:
    return {"relation": relation, "coefficients": coefficients, "constant": constant}


def test_equality_can_use_signed_equality_premises() -> None:
    premises = [c("eq", {"x": 1, "r0": -1}), c("eq", {"r0": 1, "g0": -2})]
    goal = c("eq", {"x": 1, "g0": -2})
    assert find_affine_proof(premises, goal, multiplier_bound=2) == {
        "multipliers": [1, 1],
        "slack": 0,
    }


def test_inequality_uses_nonnegative_multiplier_and_slack() -> None:
    premises = [c("ge", {"r0": 1}, -2)]
    goal = c("ge", {"r0": 1})
    assert find_affine_proof(premises, goal, multiplier_bound=3) == {
        "multipliers": [1],
        "slack": 2,
    }


def test_inequality_cannot_be_used_to_assert_equality() -> None:
    premises = [c("ge", {"x": 1})]
    assert find_affine_proof(premises, c("eq", {"x": 1}), multiplier_bound=3) is None


def test_search_order_and_receipt_are_deterministic() -> None:
    premises = [c("eq", {"a": 1}), c("eq", {"a": 1, "b": -1})]
    goal = c("eq", {"b": 1})
    first = proof_search_receipt(premises, goal, multiplier_bound=2)
    second = proof_search_receipt(premises, goal, multiplier_bound=2)
    assert first == second
    assert first["proof_found"] is True


def test_candidate_proof_search_does_not_import_the_independent_verifier() -> None:
    import metamorphosis.m092_proof_search as proof_search

    tree = ast.parse(Path(proof_search.__file__).read_text(encoding="utf-8"))
    project_imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            project_imports.update(alias.name for alias in node.names if alias.name.startswith("metamorphosis"))
        elif isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("metamorphosis"):
            project_imports.add(node.module)
    assert project_imports == set()
