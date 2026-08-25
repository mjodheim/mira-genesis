"""Adversarial boundary audit for M110.

Measures, in both directions, that the consumer family and the producer laboratory do not leak into
one another:

- the consumer runtime and the consumer population carry no producer-domain constant: no producer
  target, no adopted rule body, no truth table, no producer digest, no Boolean operator name;
- the producer's frozen artefacts are byte-unchanged from the merged M109 record;
- the only producer content the consumer reaches is the rule cascade it is handed, and it reaches it
  by importing the producer module rather than restating it.

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

from metamorphosis import m109_runtime as producer  # noqa: E402
from metamorphosis import m110_runtime as runtime  # noqa: E402

CONSUMER_SOURCES = (
    "metamorphosis/m110_runtime.py",
    "scripts/run_m110_process.py",
    "scripts/author_m110_population.py",
)
PRODUCER_FROZEN = (
    "experiments/M109/RESULT.json",
    "experiments/M109/CHECK_REPORT.json",
    "experiments/M109/PROTOCOL.json",
    "experiments/M109/DEMAND_STAGE1.json",
    "experiments/M109/DEMAND_STAGE2.json",
    "metamorphosis/m107_runtime.py",
    "metamorphosis/m108_runtime.py",
    "metamorphosis/m109_runtime.py",
)

# Strings that would betray producer-domain content inside the consumer. The component and feature
# names are deliberately excluded: they are the shared authored vocabulary, are imported rather than
# restated, and are declared in the pre-registration as excluded from the claim.
FORBIDDEN_LITERALS = (
    '"AND"',
    '"OR"',
    "'AND'",
    "'OR'",
    "m109-staged-demand",
    "demand_needs_an_unread_signal",
    "candidate_search_exhausted_for_this_demand",
    "operator_axis_progress_available",
)
DIGEST_PATTERN = re.compile(r"\b[0-9a-f]{32,}\b")
TRUTH_TABLE_PATTERN = re.compile(r"\[\s*(?:False|True)\s*(?:,\s*(?:False|True)\s*){3,}\]")


def _git(*arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments], cwd=ROOT, capture_output=True, text=True, check=False
    )
    return completed.stdout.strip() if completed.returncode == 0 else ""


def audit_consumer_sources() -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    for relative in CONSUMER_SOURCES:
        text = (ROOT / relative).read_text(encoding="utf-8")
        for literal in FORBIDDEN_LITERALS:
            if literal in text:
                findings.append({"file": relative, "kind": "literal", "detail": literal})
        for match in DIGEST_PATTERN.findall(text):
            findings.append({"file": relative, "kind": "digest", "detail": match})
        for match in TRUTH_TABLE_PATTERN.findall(text):
            findings.append({"file": relative, "kind": "truth_table", "detail": match[:60]})
    return {"confirmed": not findings, "findings": findings, "files": list(CONSUMER_SOURCES)}


def audit_population(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"confirmed": True, "reason": "population_absent", "findings": []}
    raw = path.read_text(encoding="ascii")
    payload = json.loads(raw)
    findings: list[dict[str, Any]] = []
    for key in ("row_labels", "canonical_targets", "census", "rows", "witnesses", "trial"):
        if key in payload:
            findings.append({"kind": "answer_bearing_key", "detail": key})
    for match in DIGEST_PATTERN.findall(raw):
        # World digests are the population's own identities; anything else is a leak.
        if match not in {item.get("world_digest") for item in payload.get("worlds", [])} | {
            payload.get("population_digest")
        }:
            findings.append({"kind": "foreign_digest", "detail": match})
    for literal in FORBIDDEN_LITERALS:
        if literal.strip("\"'") in raw and literal.strip("\"'") not in ("AND", "OR"):
            findings.append({"kind": "literal", "detail": literal})
    return {"confirmed": not findings, "findings": findings, "path": str(path)}


def audit_producer_untouched() -> dict[str, Any]:
    merge_base = _git("merge-base", "HEAD", "origin/main") or _git("rev-parse", "origin/main")
    changed = []
    for relative in PRODUCER_FROZEN:
        if not (ROOT / relative).exists():
            changed.append({"file": relative, "kind": "absent"})
            continue
        diff = _git("diff", "--name-only", merge_base, "HEAD", "--", relative)
        if diff:
            changed.append({"file": relative, "kind": "modified_since_merge_base"})
    return {
        "confirmed": not changed,
        "findings": changed,
        "compared_against": merge_base,
        "files": list(PRODUCER_FROZEN),
    }


def audit_vocabulary_is_imported() -> dict[str, Any]:
    """The shared vocabulary must be the producer's object, not an equal-looking copy."""
    checks = {
        "components_are_the_producer_object": runtime.COMPONENTS is producer.COMPONENTS,
        "feature_names_are_the_producer_object": runtime.FEATURE_NAMES is producer.FEATURE_NAMES,
        "feature_rows_are_the_producer_object": runtime.FEATURE_ROWS is producer.FEATURE_ROWS,
        "candidate_spaces_are_the_producer_object": runtime.CANDIDATE_SPACES
        is producer.CANDIDATE_SPACES,
        "consumer_defines_no_rule_decoder": not hasattr(runtime, "attribution_rule"),
        "attribution_agrees_with_the_producer_on_every_row": all(
            runtime.attribute({"rules": []}, {"row_index": row})["component"]
            == producer.attribute({"rules": []}, {"row_index": row})["component"]
            for row in range(len(producer.FEATURE_ROWS))
        ),
    }
    return {"confirmed": all(checks.values()), "checks": checks}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--population", default=str(ROOT / "experiments" / "M110" / "POPULATION.json")
    )
    arguments = parser.parse_args()
    report = {
        "schema": "m110-boundary-audit-v1",
        "consumer_sources": audit_consumer_sources(),
        "population": audit_population(Path(arguments.population)),
        "producer_untouched": audit_producer_untouched(),
        "vocabulary_is_imported": audit_vocabulary_is_imported(),
    }
    report["confirmed"] = all(
        value["confirmed"] for key, value in report.items() if isinstance(value, dict)
    )
    print(json.dumps(report, sort_keys=True, indent=1))
    return 0 if report["confirmed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
