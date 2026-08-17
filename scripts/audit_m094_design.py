"""Re-runnable design audit for M094, executed before any freeze.

M094 inherits implementation code that was committed ahead of its protocol
(`metamorphosis/m094_component_discovery.py`, `metamorphosis/m094_transform.py`).
That code carries docstrings claiming the lineage diagnoses its own target and
that "the winning patch emerges from the search, not from authored code".

This script measures whether those claims hold. It computes, from the real
repository, every number quoted in `experiments/M094/DESIGN_AUDIT.md` and
writes them to `experiments/M094/DESIGN_AUDIT.json`.

It asserts nothing about M094's eventual verdict. It exists so that the defects
are on the record with reproducible numbers *before* a protocol is frozen, and
so that a later reader can re-run it and get the same figures.

    python -m scripts.audit_m094_design
"""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

from metamorphosis.m094_component_discovery import (
    ELIGIBLE_COMPONENTS,
    KNOWN_PATTERNS,
    diagnose,
    inspect_all,
)
from metamorphosis.m094_transform import TRANSFORM_TEMPLATES

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT = REPO_ROOT / "experiments" / "M094" / "DESIGN_AUDIT.json"


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical_json(value).encode("ascii")).hexdigest()


def indicator_discrimination() -> dict:
    """How many eligible components does each insufficiency indicator match?

    An indicator matching exactly one component cannot discriminate: it names
    that component rather than measuring a property of it.
    """

    rows: dict[str, dict] = {}
    for pattern in KNOWN_PATTERNS:
        counts = {}
        for spec in ELIGIBLE_COMPONENTS:
            source = (REPO_ROOT / spec.path).read_text(encoding="utf-8")
            counts[spec.path] = source.count(pattern.source_indicator)
        matching = [path for path, n in counts.items() if n > 0]
        rows[pattern.name] = {
            "indicator": pattern.source_indicator,
            "severity": pattern.severity,
            "occurrences_per_component": counts,
            "components_matched": len(matching),
            "matches_exactly_one_component": len(matching) == 1,
        }
    return rows


def capability_presence_blindness() -> dict:
    """Does the `missing_query_method` verdict depend on the method existing?

    The pattern claims a query method is absent. If it fires identically whether
    or not the method is defined, it does not measure absence.
    """

    memory_path = REPO_ROOT / "mira_core" / "memory.py"
    source = memory_path.read_text(encoding="utf-8")

    tree = ast.parse(source)
    defined_methods = {
        node.name
        for parent in ast.walk(tree)
        if isinstance(parent, ast.ClassDef) and parent.name == "MemoryLedger"
        for node in parent.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }

    pattern = next(p for p in KNOWN_PATTERNS if p.name == "missing_query_method")
    fires_now = source.count(pattern.source_indicator)

    # Remove the query method entirely and re-measure the same indicator.
    stripped_lines: list[str] = []
    skipping = False
    for line in source.splitlines(keepends=True):
        if line.lstrip().startswith("def events_by_kind"):
            skipping = True
            continue
        if skipping:
            # A new sibling definition ends the removed block.
            if line.strip() and not line.startswith(" " * 8):
                skipping = False
            else:
                continue
        stripped_lines.append(line)
    stripped = "".join(stripped_lines)
    fires_without = stripped.count(pattern.source_indicator)

    return {
        "indicator": pattern.source_indicator,
        "query_method_is_defined": "events_by_kind" in defined_methods,
        "indicator_occurrences_with_method_present": fires_now,
        "indicator_occurrences_with_method_removed": fires_without,
        "verdict_changes_when_capability_is_added": fires_now != fires_without,
        "diagnoses_absence_of_a_capability_that_is_present": (
            "events_by_kind" in defined_methods and fires_now > 0
        ),
    }


def selection_determinism() -> dict:
    """Is the selected component decided by measurement or by authored weights?"""

    observations = inspect_all(REPO_ROOT)
    hypothesis = diagnose(observations)

    scores = {o.component.path: o.total_severity_score for o in observations}
    reachable = [path for path, score in scores.items() if score > 0]

    # Re-score with every authored severity flattened to 1. If the winner is
    # unchanged only because rivals score zero, the weights are not what decides;
    # the indicator set is.
    flat_scores: dict[str, int] = {}
    for spec in ELIGIBLE_COMPONENTS:
        source = (REPO_ROOT / spec.path).read_text(encoding="utf-8")
        flat_scores[spec.path] = sum(
            source.count(p.source_indicator) for p in KNOWN_PATTERNS
        )

    return {
        "selected": hypothesis.selected_component.path,
        "severity_scores": scores,
        "scores_with_flattened_severities": flat_scores,
        "components_reachable_at_all": reachable,
        "components_that_can_never_be_selected": [
            path for path, score in scores.items() if score == 0
        ],
        "selection_is_unanimous_across_weightings": (
            max(scores, key=lambda k: scores[k]) == max(flat_scores, key=lambda k: flat_scores[k])
        ),
    }


def template_authorship() -> dict:
    """Does the transformation language contain the repair, or build it?"""

    import inspect as _inspect

    templates = []
    for template in TRANSFORM_TEMPLATES:
        source = _inspect.getsource(template)
        templates.append({
            "name": template.__name__,
            "source_digest": hashlib.sha256(source.encode("utf-8")).hexdigest(),
            "contains_literal_method_body": "def {method_name}" in source
            or "def {" in source,
            "contains_component_specific_branch": "MemoryLedger" in source,
            "emits_fixed_method_name_shape": "_by_kind" in source,
        })

    return {
        "template_count": len(templates),
        "templates": templates,
        "search_space_size": len(templates),
        "a_single_template_means_no_search": len(templates) <= 1,
    }


def corrected_measure_threshold_sensitivity() -> dict:
    """Does the corrected measure's own authored constant decide the winner?

    `RenderAsMapping.min_fields` is authored. Defect 3 was diagnosed partly by
    showing that flattening the inherited severities changed nothing, so the
    same question must be put to the replacement: if the selected component
    moves when the threshold moves, then the constant is what selects, and the
    measure has reproduced the defect it was written to remove.
    """

    import metamorphosis.m094_diagnosis as diagnosis

    components = [
        "mira_core/memory.py",
        "mira_core/safety.py",
        "mira_core/contracts.py",
    ]
    original = diagnosis.CAPABILITY_SHAPES
    sweep: dict[str, object] = {}
    try:
        for threshold in (2, 3, 4, 5, 6):
            diagnosis.CAPABILITY_SHAPES = (
                diagnosis.FilterByAttribute(),
                diagnosis.RenderAsMapping(min_fields=threshold),
            )
            result = diagnosis.diagnose(REPO_ROOT, components)
            sweep[str(threshold)] = {
                "selected": result.selected,
                "unmet": [
                    {"class": i.class_name, "demand": i.demand} for i in result.unmet
                ],
            }
    finally:
        diagnosis.CAPABILITY_SHAPES = original

    selections = {row["selected"] for row in sweep.values()}  # type: ignore[index]
    return {
        "declared_threshold": diagnosis.RenderAsMapping().min_fields,
        "sweep": sweep,
        "distinct_selections": sorted(s for s in selections if s),
        "selection_is_stable_across_thresholds": len(selections) == 1,
        "authored_constant_decides_the_winner": len(selections) > 1,
    }


def main() -> int:
    report = {
        "schema": "m094-design-audit-v1",
        "milestone": "M094",
        "status": "audit_only_nothing_is_frozen",
        "audited_modules": [
            "metamorphosis/m094_component_discovery.py",
            "metamorphosis/m094_transform.py",
        ],
        "indicator_discrimination": indicator_discrimination(),
        "capability_presence_blindness": capability_presence_blindness(),
        "selection_determinism": selection_determinism(),
        "template_authorship": template_authorship(),
        "corrected_measure_threshold_sensitivity": corrected_measure_threshold_sensitivity(),
    }
    report["digest"] = _digest(
        {k: v for k, v in report.items() if k != "digest"}
    )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(_canonical_json(report) + "\n", encoding="utf-8", newline="\n")

    print(f"M094 design audit written to {OUTPUT.relative_to(REPO_ROOT)}")
    print(f"digest {report['digest']}")
    print()

    disc = report["indicator_discrimination"]
    for name, row in disc.items():
        flag = "  NON-DISCRIMINATING" if row["matches_exactly_one_component"] else ""
        print(f"  {name:32s} matches {row['components_matched']}/3 components{flag}")

    blind = report["capability_presence_blindness"]
    print()
    print(f"  query method defined: {blind['query_method_is_defined']}")
    print(
        f"  indicator fires {blind['indicator_occurrences_with_method_present']}x with it present, "
        f"{blind['indicator_occurrences_with_method_removed']}x with it removed"
    )
    print(f"  verdict changes when capability added: {blind['verdict_changes_when_capability_is_added']}")

    sel = report["selection_determinism"]
    print()
    print(f"  selected: {sel['selected']}")
    print(f"  never selectable: {sel['components_that_can_never_be_selected']}")

    tpl = report["template_authorship"]
    print()
    print(f"  transformation templates: {tpl['template_count']}")
    print(f"  single template means no search: {tpl['a_single_template_means_no_search']}")

    sens = report["corrected_measure_threshold_sensitivity"]
    print()
    print("  corrected measure, threshold sweep:")
    for threshold, row in sens["sweep"].items():
        print(f"    min_fields={threshold}: {row['selected']}")
    if sens["authored_constant_decides_the_winner"]:
        print("    UNSTABLE — the authored threshold decides the winner")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
