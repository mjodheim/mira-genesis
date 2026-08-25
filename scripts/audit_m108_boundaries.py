"""Adversarial boundary audit for M108.

Every check here exists to make a specific deflationary reading of a positive M108 testable rather
than arguable: that the host wrote the answer down, that the rule space was a menu, that the
attribution domain was sampled, that the machinery could grant itself authority, or that the
hardwired baseline was a straw man.

Two of M107's audit checks were themselves wrong -- a substring test matched the milestone's own
schema name, and a literal test matched a constant that legitimately contains the pattern. The
literal checks below are anchored to exact serialized forms for that reason.
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
from metamorphosis import m108_runtime as runtime  # noqa: E402
from scripts import check_m108_result as checker  # noqa: E402

EXPERIMENT = ROOT / "experiments" / "M108"
RUNTIME_SOURCE = ROOT / "metamorphosis" / "m108_runtime.py"
PROCESS_SOURCE = ROOT / "scripts" / "run_m108_process.py"


def _serialized_forms(values: list[bool]) -> list[str]:
    """Every plausible way the answer could have been written into a source file."""
    return [
        json.dumps(values),
        json.dumps(values, separators=(",", ":")),
        str(values),
        str([1 if value else 0 for value in values]),
        "".join("1" if value else "0" for value in values),
        str(tuple(values)),
    ]


def audit() -> dict[str, Any]:
    episodes = json.loads((EXPERIMENT / "EPISODES.json").read_text(encoding="ascii"))
    demand_fixture = json.loads((EXPERIMENT / "DEMAND.json").read_text(encoding="ascii"))
    target = list(runtime.demand_target(demand_fixture["demand"]))

    m0 = runtime.create_state(episodes["m0_operators"], signal_width=runtime.BASE_SIGNAL_WIDTH)
    monotone = runtime.create_state(
        m107.initial_operators(), signal_width=runtime.BASE_SIGNAL_WIDTH
    )
    acquisition = runtime.acquire_attribution(m0, episodes["episodes"], register_result=True)
    m1 = acquisition.get("next_state")
    rule_table = list((acquisition.get("adopted_rule") or {}).get("truth_table") or [])
    domain = runtime.attribution_domain()

    runtime_text = RUNTIME_SOURCE.read_text(encoding="utf-8")
    process_text = PROCESS_SOURCE.read_text(encoding="utf-8")
    sources = runtime_text + process_text

    # The candidate space must be the lineage's own image, not a host-supplied menu.
    acquisition_source = inspect.getsource(runtime.acquire_attribution)

    hardwired_blames = {
        runtime.attribute(m0, {"row_index": row})["component"] for row in domain["rows"]
    }
    state_held_blames = {
        row: runtime.attribute(m1, {"row_index": row})["component"] for row in domain["rows"]
    }

    contradictory = runtime.acquire_attribution(
        m0,
        [
            episodes["episodes"][0],
            runtime.attribution_episode(
                "contradiction",
                operators=episodes["episodes"][0]["operators"],
                signal_width=episodes["episodes"][0]["signal_width"],
                target=runtime.demand_target(episodes["episodes"][0]["demand"]),
                blamed_component=runtime.COMPONENT_SIGNALS,
            ),
        ],
        register_result=False,
    )

    over_ceiling = runtime.extend_signal_interface(
        runtime.create_state(m0["operators"], signal_width=runtime.MAX_SIGNAL_WIDTH)
    )
    tampered_registry = json.loads(runtime.encode_state(m0).decode("ascii"))
    tampered_registry["component_registry"] = ["operator_table", "signal_interface", "evaluator"]
    try:
        runtime.decode_state(tampered_registry)
        registry_locked = False
    except ValueError:
        registry_locked = True

    checks = {
        "canonical_evidence_absent_before_attempt": not (
            (EXPERIMENT / "RESULT.json").exists() or (EXPERIMENT / "CHECK_REPORT.json").exists()
        ),
        "runtime_does_not_contain_the_later_demand": not any(
            form in sources for form in _serialized_forms(target)
        ),
        "runtime_does_not_contain_the_adopted_rule": not any(
            form in sources for form in _serialized_forms(rule_table)
        ),
        "runtime_names_no_component_in_its_feature_vocabulary": not any(
            component in name for name in runtime.FEATURE_NAMES for component in runtime.COMPONENTS
        ),
        "no_episode_carries_the_later_demand": all(
            list(runtime.demand_target(item["demand"])) != target for item in episodes["episodes"]
        ),
        "rule_space_is_the_lineage_own_image": "expression_image(state[" in acquisition_source
        and "operator_space" not in acquisition_source,
        "attribution_domain_is_a_complete_census": domain["census_complete"] is True
        and domain["unconstructible_pairs_examined"] > 1000
        and domain["state_family_size"] > 1,
        "monotone_lineage_has_no_consistent_rule": runtime.acquire_attribution(
            monotone, episodes["episodes"], register_result=False
        )["consistent_rule_count"]
        == 0,
        "hardwired_attribution_blames_one_component_everywhere": hardwired_blames
        == {runtime.COMPONENT_OPERATORS},
        "state_held_rule_attributes_differently": runtime.COMPONENT_SIGNALS
        in set(state_held_blames.values()),
        "target_is_outside_the_base_interface_for_any_operators": runtime.structural_exclusion_certificate(
            target, runtime.BASE_SIGNAL_WIDTH
        )["confirmed"],
        "target_is_outside_the_monotone_image_at_full_width": runtime.monotone_exclusion_certificate(
            m107.initial_operators(), target
        )["confirmed"],
        "target_is_reachable_once_both_generations_hold": runtime.construct(
            runtime.create_state(m0["operators"], signal_width=runtime.WORLD_SIGNAL_WIDTH), target
        )["constructible"],
        "interpreter_is_m107_generalized_not_a_second_one": runtime.interpreter_equivalence_certificate(
            m0["operators"]
        )["confirmed"],
        "contradictory_episodes_are_refused": contradictory["confirmed"] is False
        and contradictory["reason"] == "attribution_episodes_are_contradictory",
        "signal_interface_ceiling_is_enforced": over_ceiling["confirmed"] is False
        and over_ceiling["reason"] == "signal_interface_ceiling_reached",
        "the_lineage_cannot_extend_its_own_component_registry": registry_locked,
        "checker_predicates_import_nothing": not any(
            isinstance(node, (ast.Import, ast.ImportFrom))
            for node in ast.walk(ast.parse(inspect.getsource(checker.evaluate_conditions)))
        ),
    }
    return {
        "schema": "m108-boundary-audit-v1",
        "confirmed": all(checks.values()),
        "checks": checks,
        "attribution_domain_rows": domain["rows"],
        "adopted_rule_truth_table": rule_table,
        "monotone_rule_space_size": len(
            runtime.expression_image(m107.initial_operators(), runtime.FEATURE_COUNT)
        ),
        "extended_rule_space_size": len(
            runtime.expression_image(m0["operators"], runtime.FEATURE_COUNT)
        ),
    }


def main() -> int:
    report = audit()
    print(json.dumps(report, sort_keys=True, indent=2))
    return 0 if report["confirmed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
