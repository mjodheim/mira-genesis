"""The two checkers CI depends on, exercised as processes rather than as imports.

M086-A's positive verdict rested partly on a scientific checker that existed without being
decisive in CI. A checker whose module is correct but whose exit status is not is the same defect
one layer down, so these tests run the entry points the workflow runs and assert on the status
code it will see.
"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
READINESS = ROOT / "scripts/check_blind_bank_readiness.py"
LEAKAGE = ROOT / "scripts/check_blind_bank_leakage.py"
DEVKIT = ROOT / "scripts/run_blind_bank_devkit.py"


def _run(script: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *arguments],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )


def test_the_readiness_checker_reports_and_succeeds_without_arguments() -> None:
    completed = _run(READINESS)
    assert completed.returncode == 0, completed.stderr
    report = json.loads(completed.stdout)
    assert report["schema"] == "m075b-blind-bank-readiness-v1"
    assert report["phase"] == "draft"


def test_the_readiness_checker_refuses_to_declare_readiness() -> None:
    # Exit 2 is the fail-closed answer, and it must stay that way until the whole ordered chain
    # exists. A checker that returned 0 here would authorize a reveal on an empty repository.
    assert _run(READINESS, "--require-ready").returncode == 2


def test_the_ci_reveal_assertion_passes_on_the_current_tree() -> None:
    completed = _run(READINESS, "--assert-not-revealed")
    assert completed.returncode == 0, completed.stderr


def test_the_ci_phase_assertion_is_decisive() -> None:
    assert _run(READINESS, "--require-phase", "reveal_authorized").returncode == 4
    assert _run(READINESS, "--require-phase", "draft").returncode == 0


def test_the_ci_self_test_confirms_the_causal_bindings() -> None:
    # The step that makes `sealed-bank-boundary` decisive about the three P1 properties rather
    # than only about the absence of artifacts.
    completed = _run(READINESS, "--self-test")
    assert completed.returncode == 0, completed.stderr
    assert "refuse their violations" in completed.stdout


def test_the_self_test_detects_a_removed_binding() -> None:
    """The self-test must fail when a guarantee is taken away, or it guarantees nothing."""

    import importlib

    sys.path.insert(0, str(ROOT / "scripts"))
    module = importlib.import_module("check_blind_bank_readiness")
    original = module.sealed_run_binding_problems
    try:
        module.sealed_run_binding_problems = lambda **_kwargs: []
        failures = module._self_test()
    finally:
        module.sealed_run_binding_problems = original
    assert failures
    assert module._self_test() == []


def test_the_leakage_checker_passes_on_the_current_tree() -> None:
    completed = _run(LEAKAGE)
    assert completed.returncode == 0, completed.stderr + completed.stdout


def test_the_devkit_runs_without_writing_into_the_repository() -> None:
    before = _tracked_and_present()
    completed = _run(DEVKIT)
    assert completed.returncode == 0, completed.stderr
    assert "DEVELOPMENT" in completed.stdout or "development" in completed.stdout
    assert _tracked_and_present() == before


def _tracked_and_present() -> set[str]:
    return {
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / "experiments/M075B").rglob("*")
        if path.is_file()
    }


@pytest.mark.parametrize("script", [READINESS, LEAKAGE, DEVKIT])
def test_every_entry_point_exists_and_is_executable_python(script: Path) -> None:
    assert script.is_file()
    completed = _run(script, "--help")
    assert completed.returncode == 0, completed.stderr
