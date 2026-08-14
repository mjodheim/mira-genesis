"""Check the M092 path-wise certificate-policy layer without loading target qualification.

This is a pre-search readiness check. It exercises a neutral countdown theorem with an explicit
step-count witness and proves that policy enumeration is deterministic, that failed construction
attempts remain countable, and that the candidate-side policy module has no verifier/qualification
import edge.
"""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

import metamorphosis.m092_certificate_policy_search as policies
from metamorphosis.m092_certificate_generator import POSTCONDITION_SCHEMA
from metamorphosis.m092_kernel import Program
from metamorphosis.m092_runtime import canonical_bytes


COUNTDOWN_PROGRAM: Program = (
    ("SPOP", 0),
    ("LOADI", 1, 1),
    ("JZ", 0, 5),
    ("SUB", 0, 0, 1),
    ("JMP", 2),
    ("SPUSH", 0),
    ("HALT",),
)
COUNTDOWN_REQUIREMENT = {
    "schema": POSTCONDITION_SCHEMA,
    "witnesses": ["steps"],
    "constraints": [
        {"relation": "eq", "coefficients": {"steps": -1, "x": 1}, "constant": 0},
        {"relation": "eq", "coefficients": {"y": 1}, "constant": 0},
        {"relation": "ge", "coefficients": {"steps": 1}, "constant": 0},
    ],
}


def _project_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names if alias.name.startswith("metamorphosis"))
        elif isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("metamorphosis"):
            found.add(node.module)
    return found


def main() -> int:
    module_path = Path(policies.__file__).resolve()
    imports = _project_imports(module_path)
    expected_imports = {
        "metamorphosis.m092_certificate_generator",
        "metamorphosis.m092_kernel",
    }
    if imports != expected_imports:
        raise SystemExit(f"candidate policy import boundary differs: {sorted(imports)}")

    first_records = list(policies.enumerate_certificate_policy_records(
        COUNTDOWN_PROGRAM, COUNTDOWN_REQUIREMENT, limit=32,
    ))
    second_records = list(policies.enumerate_certificate_policy_records(
        COUNTDOWN_PROGRAM, COUNTDOWN_REQUIREMENT, limit=32,
    ))
    first = [record.to_dict(include_certificate=False) for record in first_records]
    second = [record.to_dict(include_certificate=False) for record in second_records]
    if first != second or not first:
        raise SystemExit("neutral path-wise certificate policy search is not deterministic")
    if [item["ordinal"] for item in first] != list(range(1, len(first) + 1)):
        raise SystemExit("certificate policy attempt ordinals are not contiguous")

    constructed_records = [record for record in first_records if record.constructed]
    if not constructed_records:
        raise SystemExit("neutral witness rehearsal did not construct any complete certificate")
    if not any(
        record.ghost_count >= 1 and any(any(values) for _, values in record.increments)
        for record in constructed_records
    ):
        raise SystemExit("neutral witness rehearsal never exercised an incrementing ghost policy")

    constructed = len(constructed_records)
    refused = len(first) - constructed
    report = {
        "schema": "m092-certificate-policy-readiness-v1",
        "neutral_theorem_only": True,
        "neutral_witness": "steps",
        "qualification_loaded": False,
        "target_theorem_loaded": False,
        "module_imports": sorted(imports),
        "attempts": len(first),
        "constructed": constructed,
        "refused": refused,
        "incrementing_ghost_policy_constructed": True,
        "ordinals_contiguous": True,
        "deterministic": True,
        "policy_prefix_digest": hashlib.sha256(canonical_bytes(first)).hexdigest(),
    }
    report["report_digest"] = hashlib.sha256(canonical_bytes(report)).hexdigest()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
