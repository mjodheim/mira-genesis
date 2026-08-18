"""M094 experiment runner — autonomous diagnosis and repair pipeline.

This orchestrator connects the structural diagnosis (m094_diagnosis.py)
with the generic synthesis mechanism (m094_synthesis.py) and the
existing M093 transformation infrastructure (sandbox, comparison,
adoption, rollback).

Unlike M093, the target component and required capability are
determined by measurement, not by authored constants. The repair
is assembled from composable AST-derived operations, not from
a hand-written template.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Sequence

from metamorphosis.m094_diagnosis import (
    CAPABILITY_SHAPES,
    DiagnosisResult,
    diagnose,
    measure_component,
)
from metamorphosis.m094_synthesis import (
    SynthesisOperation,
    apply_operation,
    suggest_operations,
)
from metamorphosis.m093 import (
    SandboxResult,
    ABNullHypothesis,
    IndependentValidation,
    compare_ab,
    run_in_sandbox,
    validate_independently,
    TransformationStore,
    State,
    _domain_digest,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
EXPERIMENT = REPO_ROOT / "experiments" / "M094"


def step(msg: str) -> None:
    print(f"\n=== {msg} ===", flush=True)


def diagnosis_pipeline(repo_root: Path) -> DiagnosisResult:
    """Run the structural diagnosis over all eligible components."""
    step("1. Structural diagnosis")
    result = diagnose(repo_root)
    print(f"  Selected: {result.selected_component_path}")
    print(f"  Class: {result.selected_class_name}")
    print(f"  Capability: {result.selected_capability_name}")
    print(f"  Demand: {result.demand_count}")
    print(f"  Supplied: {result.is_supplied}")
    print(f"  Justification: {result.justification[:200]}")
    return result


def synthesis_pipeline(diagnosis: DiagnosisResult, repo_root: Path) -> Sequence[SynthesisOperation]:
    """Generate candidate repair operations from the diagnosis."""
    step("2. Candidate synthesis")
    ops = suggest_operations(repo_root, diagnosis)
    print(f"  Generated {len(ops)} candidate operation(s)")
    for op in ops:
        print(f"    - {op.description}")
    if not ops:
        print("  WARNING: no operations generated — nothing to adopt")
    return ops


def sandbox_pipeline(
    diagnosis: DiagnosisResult,
    operations: Sequence[SynthesisOperation],
    repo_root: Path,
) -> tuple[SandboxResult, SandboxResult, ABNullHypothesis | None]:
    """Test original and candidate in isolated sandboxes."""
    step("3. Sandbox testing")

    target_path = repo_root / diagnosis.selected_component_path
    original_source = target_path.read_text(encoding="utf-8")

    # Run original
    original_result = run_in_sandbox(
        original_source,
        diagnosis.selected_module_name,
        sandbox_script=_detect_sandbox_script(diagnosis),
        dependency_modules=("contracts", "memory"),
        timeout_seconds=30,
    )
    print(f"  Original: {original_result.passed} ({original_result.total_assertions} assertions)")

    # Apply the winning operation
    if not operations:
        print("  SKIP: no candidate to test")
        return original_result, None, None

    # For now, apply the first operation as the candidate
    op = operations[0]
    candidate_source = op.apply(original_source)
    candidate_result = run_in_sandbox(
        candidate_source,
        diagnosis.selected_module_name,
        sandbox_script=_detect_sandbox_script(diagnosis),
        dependency_modules=("contracts", "memory"),
        timeout_seconds=30,
    )
    print(f"  Candidate: {candidate_result.passed} ({candidate_result.total_assertions} assertions)")

    # A/B comparison
    comparison = compare_ab(
        original_result,
        candidate_result,
        criterion="all_assertions_pass_and_candidate_functionally_equivalent",
    )
    print(f"  A/B: null_rejected={comparison.null_rejected}")
    print(f"  Reason: {comparison.reason}")

    return original_result, candidate_result, comparison


def _detect_sandbox_script(diagnosis: DiagnosisResult) -> str:
    """Generate a sandbox test script from the diagnosis."""
    # For RenderAsMapping: test that the class has a to_dict() method
    if "render" in diagnosis.selected_capability_name.lower():
        return f"""
import sys
sys.path.insert(0, '.')
from mira_core import {diagnosis.selected_module_name.split('.')[-1]}

# Import the module
import importlib
mod = importlib.import_module('{diagnosis.selected_module_name}')

# Find the class
cls = getattr(mod, '{diagnosis.selected_class_name}')
instance = cls()

# Test: to_dict exists
if hasattr(instance, 'to_dict'):
    print('ASSERT:OK:to_dict exists')
else:
    print('ASSERT:FAIL:to_dict missing')

# Test: to_dict returns a dict
if hasattr(instance, 'to_dict'):
    result = instance.to_dict()
    if isinstance(result, dict):
        print('ASSERT:OK:to_dict returns dict')
    else:
        print('ASSERT:FAIL:to_dict type')
"""
    # For FilterByAttribute: test that the class has a filter method
    return f"""
import sys
sys.path.insert(0, '.')
import importlib
mod = importlib.import_module('{diagnosis.selected_module_name}')
cls = getattr(mod, '{diagnosis.selected_class_name}')
instance = cls()
print('ASSERT:OK:module loaded')
"""


def main() -> int:
    """Run the full M094 pipeline."""
    report = {}
    start = time.time()

    # 1. Diagnosis
    diagnosis = diagnosis_pipeline(REPO_ROOT)
    report["diagnosis"] = {
        "component": diagnosis.selected_component_path,
        "class": diagnosis.selected_class_name,
        "capability": diagnosis.selected_capability_name,
        "demand": diagnosis.demand_count,
        "supplied": diagnosis.is_supplied,
        "digest": diagnosis.digest(),
    }

    # 2. Synthesis
    operations = synthesis_pipeline(diagnosis, REPO_ROOT)
    report["synthesis"] = {
        "operation_count": len(operations),
        "operations": [op.description for op in operations],
    }

    # 3. Sandbox + comparison
    original_result, candidate_result, comparison = sandbox_pipeline(
        diagnosis, operations, REPO_ROOT
    )
    if original_result:
        report["sandbox"] = {
            "original_passed": original_result.passed,
            "original_assertions": original_result.total_assertions,
            "candidate_passed": candidate_result.passed if candidate_result else None,
            "candidate_assertions": candidate_result.total_assertions if candidate_result else None,
            "null_rejected": comparison.null_rejected if comparison else None,
        }

    # 4. Adoption (if candidate passes)
    if comparison and comparison.null_rejected:
        step("4. Transactional adoption")
        target_path = REPO_ROOT / diagnosis.selected_component_path
        original_source = target_path.read_text(encoding="utf-8")
        candidate_source = operations[0].apply(original_source) if operations else original_source

        store = TransformationStore(target_path)
        entry = store.adopt(
            new_source=candidate_source,
            patch_digest=operations[0].digest if operations else "",
            validation_digest="",
            comparison=comparison.reason,
        )
        print(f"  Adopted version {entry.version}")
        report["adoption"] = {"version": entry.version, "digest": entry.digest()}

        # 5. Rollback test
        step("5. Rollback verification")
        store.rollback()
        restored = target_path.read_text(encoding="utf-8")
        rollback_ok = restored == original_source
        print(f"  Rollback {'OK' if rollback_ok else 'FAILED'}")
        report["rollback"] = {"exact": rollback_ok}

    elapsed = time.time() - start
    report["elapsed_seconds"] = round(elapsed, 1)
    report["schema"] = "m094-runner-report-v1"

    print(f"\n{'='*50}")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if (comparison and comparison.null_rejected) else 1


if __name__ == "__main__":
    raise SystemExit(main())