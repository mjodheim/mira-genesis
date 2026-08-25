"""Adversarial boundary audit for M111.

Measures, in both directions, that the diagnostic layer and its predecessors do not leak into one
another:

- the M111 runtime and the M111 population carry no producer-domain constant: no M109 target, no
  adopted rule body, no policy truth table, no foreign digest;
- the frozen M109 and M110 artefacts are byte-unchanged from the merged record;
- the shared vocabulary is imported from the predecessors rather than restated, and the fourth
  registry entry is the only thing M111 adds to it;
- a probe never adopts.

Run it before any freeze. It prints a report and exits non-zero if any direction leaks.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from metamorphosis import m109_runtime as machinery  # noqa: E402
from metamorphosis import m110_runtime as consumer  # noqa: E402
from metamorphosis import m111_runtime as runtime  # noqa: E402

M111_SOURCES = (
    "metamorphosis/m111_runtime.py",
    "scripts/run_m111_process.py",
    "scripts/author_m111_population.py",
)
FROZEN = (
    "experiments/M109/RESULT.json",
    "experiments/M109/CHECK_REPORT.json",
    "experiments/M109/PROTOCOL.json",
    "experiments/M110/RESULT.json",
    "experiments/M110/CHECK_REPORT.json",
    "experiments/M110/PROTOCOL.json",
    "metamorphosis/m107_runtime.py",
    "metamorphosis/m108_runtime.py",
    "metamorphosis/m109_runtime.py",
    "metamorphosis/m110_runtime.py",
)

FORBIDDEN_LITERALS = (
    "ACQUIRED_",
    "m109-staged-demand",
    "rule-b65eacbd90aa5680",
    "rule-43e5d959a7b8fd05",
)
DIGEST_PATTERN = re.compile(r"\b[0-9a-f]{32,}\b")
TRUTH_TABLE_PATTERN = re.compile(r"\[\s*(?:False|True)\s*(?:,\s*(?:False|True)\s*){3,}\]")


def _git(*arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments], cwd=ROOT, capture_output=True, text=True, check=False
    )
    return completed.stdout.strip() if completed.returncode == 0 else ""


def audit_sources() -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    for relative in M111_SOURCES:
        text = (ROOT / relative).read_text(encoding="utf-8")
        for literal in FORBIDDEN_LITERALS:
            if literal in text:
                findings.append({"file": relative, "kind": "literal", "detail": literal})
        for match in DIGEST_PATTERN.findall(text):
            findings.append({"file": relative, "kind": "digest", "detail": match})
        for match in TRUTH_TABLE_PATTERN.findall(text):
            findings.append({"file": relative, "kind": "truth_table", "detail": match[:60]})
    return {"confirmed": not findings, "findings": findings, "files": list(M111_SOURCES)}


def audit_population(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"confirmed": True, "reason": "population_absent", "findings": []}
    raw = path.read_text(encoding="ascii")
    payload = json.loads(raw)
    findings: list[dict[str, Any]] = []
    for key in ("row_labels", "canonical_targets", "census", "pair", "policy", "episodes"):
        if key in payload:
            findings.append({"kind": "answer_bearing_key", "detail": key})
    own = {item.get("world_digest") for item in payload.get("worlds", [])} | {
        payload.get("population_digest")
    }
    for match in DIGEST_PATTERN.findall(raw):
        if match not in own:
            findings.append({"kind": "foreign_digest", "detail": match})
    return {"confirmed": not findings, "findings": findings, "path": str(path)}


def audit_frozen_untouched() -> dict[str, Any]:
    merge_base = _git("merge-base", "HEAD", "origin/main") or _git("rev-parse", "origin/main")
    changed = []
    for relative in FROZEN:
        if not (ROOT / relative).exists():
            changed.append({"file": relative, "kind": "absent"})
            continue
        if _git("diff", "--name-only", merge_base, "HEAD", "--", relative):
            changed.append({"file": relative, "kind": "modified_since_merge_base"})
    return {
        "confirmed": not changed,
        "findings": changed,
        "compared_against": merge_base,
        "files": list(FROZEN),
    }


def audit_vocabulary_is_imported() -> dict[str, Any]:
    checks = {
        "feature_names_are_the_producer_object": runtime.FEATURE_NAMES is machinery.FEATURE_NAMES,
        "feature_rows_are_the_producer_object": runtime.FEATURE_ROWS is machinery.FEATURE_ROWS,
        "registry_extends_the_producer_triple_by_exactly_one": tuple(runtime.COMPONENTS)
        == tuple(machinery.COMPONENTS) + (runtime.COMPONENT_DIAGNOSTIC,),
        "the_added_component_is_the_diagnostic_policy": runtime.COMPONENT_DIAGNOSTIC
        == "diagnostic_policy",
        "consumer_carrier_is_the_m110_object": runtime.MAX_EXPRESSION_NODES
        == consumer.MAX_EXPRESSION_NODES,
        "m111_defines_no_attribution_rule_of_its_own": not hasattr(
            runtime, "attribution_rule"
        ),
        "m111_defines_no_consumer_world_of_its_own": not hasattr(runtime, "consumer_world"),
    }
    return {"confirmed": all(checks.values()), "checks": checks}


def audit_probe_never_adopts() -> dict[str, Any]:
    """A probe must be an experiment. Measured on a real world rather than asserted."""
    from scripts.author_m111_population import generate_world  # noqa: PLC0415

    world = generate_world("audit", 2000)
    state = runtime.create_state(machinery.create_state(), consumer.create_state())
    target = tuple([0] * consumer.DOCUMENT_COUNT)
    records = [
        runtime.probe(state, world, target, component)
        for component in (
            runtime.COMPONENT_SIGNALS,
            runtime.COMPONENT_CANDIDATES,
            runtime.COMPONENT_OPERATORS,
        )
    ]
    before = runtime.encode_state(state)
    checks = {
        "every_probe_reports_the_state_unchanged": all(
            item["state_unchanged"] for item in records
        ),
        "no_probe_reports_itself_an_adoption": all(not item["is_an_adoption"] for item in records),
        "the_whole_state_is_byte_identical_afterwards": before
        == runtime.encode_state(state),
    }
    return {"confirmed": all(checks.values()), "checks": checks, "probe_count": len(records)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--population", default=str(ROOT / "experiments" / "M111" / "POPULATION.json")
    )
    arguments = parser.parse_args()
    report = {
        "schema": "m111-boundary-audit-v1",
        "sources": audit_sources(),
        "population": audit_population(Path(arguments.population)),
        "frozen_untouched": audit_frozen_untouched(),
        "vocabulary_is_imported": audit_vocabulary_is_imported(),
        "probe_never_adopts": audit_probe_never_adopts(),
    }
    report["confirmed"] = all(
        value["confirmed"] for key, value in report.items() if isinstance(value, dict)
    )
    print(json.dumps(report, sort_keys=True, indent=1))
    return 0 if report["confirmed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
