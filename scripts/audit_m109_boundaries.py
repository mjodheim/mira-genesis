"""Adversarial boundary audit for M109.

Each check makes a specific deflationary reading of a positive M109 testable rather than arguable:
that the host wrote the rules down, that the blame labels are supervision after all, that the trial
is not the same procedure for every component, that the rule space is a menu, that the domain was
sampled, that the machinery could grant itself authority, or that the second generation is really the
first one wearing a different name.

Two of M107's audit checks were themselves vacuous -- a substring test matched the milestone's own
schema name, and a literal test matched a constant that legitimately contains the pattern. The
literal checks below are anchored to exact serialized forms, and every check is verified to fail when
it should before it is trusted.
"""

from __future__ import annotations

import ast
import inspect
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from metamorphosis import m107_runtime as m107  # noqa: E402
from metamorphosis import m109_runtime as runtime  # noqa: E402
from scripts import check_m109_result as checker  # noqa: E402

EXPERIMENT = ROOT / "experiments" / "M109"
RUNTIME_SOURCE = ROOT / "metamorphosis" / "m109_runtime.py"
PROCESS_SOURCE = ROOT / "scripts" / "run_m109_process.py"
CURRICULUM_SOURCE = ROOT / "scripts" / "author_m109_curriculum.py"


def _serialized_forms(values: list[bool]) -> list[str]:
    """Every plausible way an answer could have been written into a source file."""
    return [
        json.dumps(values),
        json.dumps(values, separators=(",", ":")),
        str(values),
        str([1 if value else 0 for value in values]),
        "".join("1" if value else "0" for value in values),
        str(tuple(values)),
    ]


def audit() -> dict[str, Any]:
    stage1 = json.loads((EXPERIMENT / "DEMAND_STAGE1.json").read_text(encoding="ascii"))
    stage2 = json.loads((EXPERIMENT / "DEMAND_STAGE2.json").read_text(encoding="ascii"))
    first = list(runtime.demand_target(stage1["demand"]))
    second = list(runtime.demand_target(stage2["demand"]))

    m0 = runtime.create_state()
    domain = runtime.attribution_domain()
    episode1 = runtime.record_episode(m0, stage1["demand"])
    acq1 = runtime.acquire_rule(m0, [episode1], domain, register_result=True)
    m1 = acq1["next_state"]
    resolved1 = runtime.resolve(m1, stage1["demand"])
    m1_after = runtime.create_state(
        m1["operators"],
        signal_width=resolved1["final_signal_width"],
        candidate_space=resolved1["final_candidate_space"],
        rules=m1["rules"],
    )
    episode2 = runtime.record_episode(m1_after, stage2["demand"])
    acq2 = runtime.acquire_rule(m1_after, [episode1, episode2], domain, register_result=True)
    m2 = acq2["next_state"]

    rule1 = list(acq1["adopted_rule"]["truth_table"])
    rule2 = list(acq2["adopted_rule"]["truth_table"])
    sources = (
        RUNTIME_SOURCE.read_text(encoding="utf-8")
        + PROCESS_SOURCE.read_text(encoding="utf-8")
        + CURRICULUM_SOURCE.read_text(encoding="utf-8")
    )

    probe_trial = runtime.component_trial(m0, stage1["demand"])
    trial_source = inspect.getsource(runtime.component_trial)
    acquire_source = inspect.getsource(runtime.acquire_rule)
    resolve_source = inspect.getsource(runtime.resolve)

    handed = runtime.acquire_rule(m0, [episode2], domain, register_result=False)
    conflated = runtime.acquire_rule(m0, [episode1, episode2], domain, register_result=False)

    over_generations = runtime.acquire_rule(
        m2, [episode1, episode2], domain, register_result=False
    )
    tampered = json.loads(runtime.encode_state(m0).decode("ascii"))
    tampered["component_registry"] = [*runtime.COMPONENTS, "evaluator"]
    try:
        runtime.decode_state(tampered)
        registry_locked = False
    except ValueError:
        registry_locked = True
    tampered_space = json.loads(runtime.encode_state(m0).decode("ascii"))
    tampered_space["candidate_space"] = "unbounded"
    try:
        runtime.decode_state(tampered_space)
        space_locked = False
    except ValueError:
        space_locked = True

    checks = {
        "canonical_evidence_absent_before_attempt": not (
            (EXPERIMENT / "RESULT.json").exists() or (EXPERIMENT / "CHECK_REPORT.json").exists()
        ),
        "no_source_contains_either_staged_demand": not any(
            form in sources for form in _serialized_forms(first) + _serialized_forms(second)
        ),
        "no_source_contains_either_adopted_rule": not any(
            form in sources for form in _serialized_forms(rule1) + _serialized_forms(rule2)
        ),
        "feature_names_do_not_name_a_component": not any(
            component in name
            for name in runtime.FEATURE_NAMES
            for component in runtime.COMPONENTS
        ),
        "no_episode_fixture_exists": not (EXPERIMENT / "EPISODES.json").exists(),
        # Behavioural, not a source-string search: an earlier version of this check looked for the
        # component names as literals and failed because the code refers to them by constant. What
        # matters is that the trial actually examines every registered component and declares the
        # rule it applies.
        "the_trial_examines_every_registered_component": sorted(probe_trial["outcomes"])
        == sorted(runtime.COMPONENTS)
        and probe_trial["components_examined"] == sorted(runtime.COMPONENTS)
        and probe_trial["label_source"] == "lineage_component_trial"
        and probe_trial["semantics"] == "minimal_necessary_component",
        "the_trial_reads_no_host_annotation": "blamed_component" not in trial_source
        and "expected" not in trial_source,
        "resolution_performs_no_trial": "component_trial" not in resolve_source
        and '"trials_performed": 0' in resolve_source,
        "rule_space_is_the_lineage_own_image": "expression_image(state[" in acquire_source
        and "operator_space" not in acquire_source,
        "attribution_domain_is_a_complete_census": domain["census_complete"] is True
        and domain["ambiguous_rows"] == []
        and domain["determined_pairs_examined"] > 1000
        and domain["state_family_size"] > 1,
        "no_domain_row_carries_two_labels": all(
            len(labels) == 1 for labels in domain["row_labels"].values()
        ),
        "the_monotone_candidate_space_is_closed_by_lemma": runtime.candidate_space_closure_certificate(
            m0["operators"], m0["signal_width"]
        )["closed_by_monotonicity_lemma"],
        "the_two_generations_target_different_components": acq1["selected_component"]
        != acq2["selected_component"],
        "the_two_generations_adopt_different_rules": acq1["adopted_rule"]["rule_id"]
        != acq2["adopted_rule"]["rule_id"],
        "a_handed_stage_two_record_is_refused": handed["confirmed"] is False,
        "a_record_naming_two_components_is_refused": conflated["confirmed"] is False
        and conflated["reason"] == "uncovered_episodes_name_more_than_one_component",
        "the_generation_ceiling_is_enforced": over_generations["confirmed"] is False
        and over_generations["reason"] == "machinery_generation_ceiling_reached",
        "the_lineage_cannot_extend_its_own_component_registry": registry_locked,
        "the_lineage_cannot_invent_a_candidate_space": space_locked,
        "checker_predicates_import_nothing": not any(
            isinstance(node, (ast.Import, ast.ImportFrom))
            for node in ast.walk(ast.parse(inspect.getsource(checker.evaluate_conditions)))
        ),
    }
    return {
        "schema": "m109-boundary-audit-v1",
        "confirmed": all(checks.values()),
        "checks": checks,
        "attribution_domain_rows": domain["rows"],
        "row_labels": domain["row_labels"],
        "generation_one": {
            "component": acq1["selected_component"],
            "truth_table": rule1,
            "consistent": acq1["consistent_rule_count"],
            "space": acq1["rule_space_size"],
        },
        "generation_two": {
            "component": acq2["selected_component"],
            "truth_table": rule2,
            "consistent": acq2["consistent_rule_count"],
        },
        "handed_counterfactual_reason": handed.get("reason"),
    }


def main() -> int:
    report = audit()
    print(json.dumps(report, sort_keys=True, indent=2))
    return 0 if report["confirmed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
