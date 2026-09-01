"""H63 arm construction: a non-degenerate fresh comparator and the missing factorial ablations.

The pre-freeze hostile review established three facts about the inherited M113 arm set. They are
discoveries about the instrument, not changes to M113's historical result, which continues to
replay exactly.

  * **T0 is a constant function.** With no acquired rules, `m109_runtime.attribute` falls through
    to a hardwired `operator_table`, on every feature row of every carrier. Beating a constant is
    not evidence that a lineage acquired anything, so T0 cannot be the primary comparator.
  * **No arm had `rules = []` with the acquired policy.** Only `M3` and `ablated` carried the
    policy and both also carried acquired rules, so the diagnostic probe's contribution could
    never be separated from the rules'.
  * **`budget_plus` cannot probe at any budget**, because `policy_fires` is `bool(policy) and ...`
    and its policy is `None`. Comparing a probing lineage against it answers nothing about budget.

This module adds what was missing, and nothing else. Every arm is expressed in the *same state
language* the inherited runtime already speaks -- an ordered rule cascade plus an optional policy --
so `m109_runtime.attribute` and `m113_runtime.resolve` are used unchanged. No M113 module is
modified.

**`fresh_uniform` is information-free by construction.** Its rules are derived from a precommitted
seed and the feature-row index alone. It never sees carrier semantics, never sees which component
is actually correct, and was not tuned on M117 or H63 data. It is deterministic and exactly
replayable from the seed, and it is non-constant: the eight feature rows are dealt across the three
components as evenly as eight divides by three, so it answers differently on different rows without
knowing anything.
"""

from __future__ import annotations

import hashlib
from typing import Any, Mapping, Sequence

from metamorphosis import m109_runtime as lineage
from metamorphosis import m113_runtime as runtime

ARMS_VERSION = "m118-arms-v1"

# Precommitted before any H63 observation. Changing it changes the comparator, so it is frozen
# with the plan and bound by the tested-system freeze.
FRESH_UNIFORM_SEED = "m118-fresh-uniform-v1:6f1c2a9d4b7e30518c26adf95b04e7d3"

COMPONENTS = tuple(lineage.COMPONENTS)
ROW_COUNT = len(runtime.FEATURE_ROWS)

# The primary comparison. Named here so no analysis can quietly re-point it at whichever baseline
# is easiest to beat.
DESCENDANT_ARM = "M3"
PRIMARY_FRESH_ARM = "fresh_uniform"
LEGACY_FRESH_ARM = "T0"

BUDGET_MULTIPLIER = {"budget_plus": 4, "probe_only_budget_plus": 4}


def _row_order(seed: str) -> list[int]:
    """A deterministic permutation of the feature rows, from the seed alone."""
    return sorted(
        range(ROW_COUNT),
        key=lambda row: hashlib.sha256(("%s:row:%d" % (seed, row)).encode("ascii")).hexdigest(),
    )


def fresh_uniform_assignment(seed: str = FRESH_UNIFORM_SEED) -> list[str]:
    """Which component `fresh_uniform` names on each feature row.

    Rows are dealt round-robin over the components in a seed-derived order, so the assignment is
    balanced to within one row and depends on nothing but the seed. No carrier, demand, outcome or
    ground truth is consulted.
    """
    assignment = [""] * ROW_COUNT
    for position, row in enumerate(_row_order(seed)):
        assignment[row] = COMPONENTS[position % len(COMPONENTS)]
    return assignment


def fresh_uniform_rules(seed: str = FRESH_UNIFORM_SEED) -> list[dict[str, Any]]:
    """The comparator as an ordinary rule cascade, so the inherited attributor runs unchanged.

    One rule per component, with disjoint truth tables that partition every feature row. The
    partition is total, so the cascade never falls through to the hardwired constant -- which is
    exactly what makes this comparator non-degenerate where T0 is not.
    """
    assignment = fresh_uniform_assignment(seed)
    rules = []
    for index, component in enumerate(COMPONENTS):
        rules.append({
            "rule_id": "fresh_uniform_%s" % component,
            "generation": 0,
            "selects_component_when_true": component,
            "truth_table": [assignment[row] == component for row in range(ROW_COUNT)],
            "acquired": False,
            "derived_from": "precommitted seed and feature-row index only",
        })
    return rules


def fresh_uniform_state(seed: str = FRESH_UNIFORM_SEED) -> dict[str, Any]:
    return {"rules": fresh_uniform_rules(seed), "policy": None}


def is_information_free(rules: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Does the comparator carry anything it could only have learned?"""
    acquired = [r["rule_id"] for r in rules if r.get("acquired") is not False]
    generations = sorted({int(r.get("generation", 0)) for r in rules})
    covered = [0] * ROW_COUNT
    for rule in rules:
        for row, fires in enumerate(rule["truth_table"]):
            if fires:
                covered[row] += 1
    named = {r["selects_component_when_true"] for r in rules}
    return {
        "carries_no_acquired_rule": not acquired,
        "every_generation_is_zero": generations == [0],
        "partitions_every_row_exactly_once": all(count == 1 for count in covered),
        "is_non_constant": len(named) > 1,
        "components_named": sorted(named),
        "rows_per_component": {
            component: sum(1 for r in rules if r["selects_component_when_true"] == component
                           for row, fires in enumerate(r["truth_table"]) if fires)
            for component in COMPONENTS
        },
    }


def build_arms(first: Mapping[str, Any], second: Mapping[str, Any],
               policy: Mapping[str, Any], mutated_rule: Mapping[str, Any],
               *, seed: str = FRESH_UNIFORM_SEED) -> dict[str, dict[str, Any]]:
    """Every H63 arm, including the factorial cells the inherited set was missing.

    The 2x2 the review asked for, which is what lets a positive result be attributed:

                     policy absent        policy present
        rules absent  T0 / fresh_uniform  probe_only
        rules present  M2                 M3
    """
    return {
        # Legacy, retained as a regression arm and explicitly not the primary comparator.
        "T0": {"rules": [], "policy": None},
        "M1": {"rules": [dict(first)], "policy": None},
        "M2": {"rules": [dict(first), dict(second)], "policy": None},
        "M3": {"rules": [dict(first), dict(second)], "policy": dict(policy)},
        # The non-degenerate fresh comparator. Primary.
        "fresh_uniform": fresh_uniform_state(seed),
        # The missing factorial cell: the acquired policy with no acquired rules, so the probe's
        # contribution is separable from the cascade's.
        "probe_only": {"rules": [], "policy": dict(policy)},
        # A budget control that can actually take the probing action.
        "probe_only_budget_plus": {"rules": [], "policy": dict(policy)},
        "rollback": {"rules": [], "policy": None},
        "ablated": {"rules": [dict(first)], "policy": dict(policy)},
        "mutated": {"rules": [dict(first), dict(mutated_rule)], "policy": None},
        "unregistered": {"rules": [], "policy": None,
                         "built_but_unregistered": second["rule_id"]},
        # Legacy budget control. Retained, and unable to probe -- which is why
        # probe_only_budget_plus exists beside it.
        "budget_plus": {"rules": [], "policy": None},
    }


ARM_NAMES = ("T0", "M1", "M2", "M3", "fresh_uniform", "probe_only", "probe_only_budget_plus",
             "rollback", "ablated", "mutated", "unregistered", "budget_plus")


def action_space_statement() -> dict[str, Any]:
    """What is held fixed and what is not. Stated rather than glossed.

    The claim "only the Genesis state differs across arms" is withdrawn. It is literally true and
    misleading, because the state itself determines whether the diagnostic probe action can occur:
    `policy_fires` is `bool(policy) and ...`, so an arm without a policy cannot probe at any budget.
    """
    return {
        "held_fixed_across_arms": ["carrier", "demand pair", "channel", "evaluator", "reference",
                                   "base observation budget"],
        "differs_across_arms": ["the Genesis state: the acquired rule cascade and the acquired "
                                "diagnostic policy"],
        "state_may_enable_different_internal_actions": True,
        "only_the_genesis_state_differs_claim_withdrawn": True,
        "probe_action_requires_a_policy": True,
        "arms_that_can_probe": ["M3", "probe_only", "probe_only_budget_plus", "ablated"],
        "budget_ablations": {"budget_plus": "4x budget, cannot probe (legacy)",
                             "probe_only_budget_plus": "4x budget, can probe"},
        "the_factorial_arms_measure_this_mechanism_rather_than_pretending_it_away": True,
    }
