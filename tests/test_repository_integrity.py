"""Regression checks for the repository-integrity checker itself."""
from __future__ import annotations

from check_repository_integrity import check_dependencies


def test_repository_scripts_are_local_not_a_distribution_dependency() -> None:
    assert check_dependencies() == []
