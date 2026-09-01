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

# `m109_runtime.attribute` falls through to this component when no rule fires, so it is the
# one the comparator expresses *by* the fallthrough rather than by a rule. T0 reaches it on
# every row; fresh_uniform reaches it only on the rows the seed assigns to it.
FALLTHROUGH_COMPONENT = "operator_table"
FRESH_UNIFORM_RULE_COMPONENTS = tuple(c for c in COMPONENTS if c != FALLTHROUGH_COMPONENT)
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


def _component_order(seed: str) -> list[str]:
    """A deterministic permutation of the components, from the seed alone.

    Eight rows do not divide by three, so one component always receives two rows where the others
    receive three. Dealing over a *fixed* component order made that always the same component --
    `candidate_space` in 400 of 400 seeds -- which is a standing bias, not a uniform prior. The
    seed now chooses which component is short-changed as well as which rows each receives.
    """
    return sorted(
        COMPONENTS,
        key=lambda component: hashlib.sha256(
            ("%s:component:%s" % (seed, component)).encode("ascii")).hexdigest(),
    )


def fresh_uniform_assignment(seed: str = FRESH_UNIFORM_SEED) -> list[str]:
    """Which component `fresh_uniform` names on each feature row.

    Rows are dealt round-robin over a seed-permuted component order, so the assignment is balanced
    to within one row and depends on nothing but the seed. No carrier, demand, outcome or ground
    truth is consulted.
    """
    order = _component_order(seed)
    assignment = [""] * ROW_COUNT
    for position, row in enumerate(_row_order(seed)):
        assignment[row] = order[position % len(order)]
    return assignment


def fresh_uniform_rules(seed: str = FRESH_UNIFORM_SEED) -> list[dict[str, Any]]:
    """The comparator as an ordinary rule cascade, built by the producer's own constructor.

    The lineage permits at most `MAX_MACHINERY_GENERATIONS` (2) rules, so the cascade carries two
    and the hardwired fallthrough supplies the third component. That is not a compromise: it makes
    the partition total across all three components using exactly the mechanism the inherited
    attributor already has, and it is what distinguishes this comparator from T0 -- T0 reaches the
    fallthrough on *every* row, this one reaches it on a seed-chosen third of them.

    The rules are constructed by `m109_runtime.attribution_rule`, so the payload is well-formed and
    `decode_rule` accepts it. The body records what the rule is rather than imitating an acquired
    expression: nothing evaluates it, and a fabricated expression tree would misrepresent a rule
    that was never learned.
    """
    assignment = fresh_uniform_assignment(seed)
    cascade = []
    # Generation order is fixed, so the cascade is deterministic. The fallthrough component is
    # deliberately last and is never given a rule.
    for generation, component in enumerate(FRESH_UNIFORM_RULE_COMPONENTS, start=1):
        table = [assignment[row] == component for row in range(ROW_COUNT)]
        body = {"node": "SEEDED_PARTITION", "seed": seed, "component": component,
                "derivation": "precommitted seed and feature-row index only"}
        cascade.append(lineage.attribution_rule(body, table, component, generation))
    return cascade


def fresh_uniform_state(seed: str = FRESH_UNIFORM_SEED) -> dict[str, Any]:
    return {"rules": fresh_uniform_rules(seed), "policy": None}


def is_information_free(rules: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Does the comparator carry anything it could only have learned?"""
    acquired = [r for r in rules if r["body"].get("node") != "SEEDED_PARTITION"]
    covered = [0] * ROW_COUNT
    for rule in rules:
        for row, fires in enumerate(rule["truth_table"]):
            if fires:
                covered[row] += 1
    # Rows no rule claims fall through to the hardwired component, so the effective assignment is
    # the rules plus that fallthrough.
    effective = []
    for row in range(ROW_COUNT):
        named = [r["selects_component_when_true"] for r in rules if r["truth_table"][row]]
        effective.append(named[0] if named else FALLTHROUGH_COMPONENT)
    counts = {component: effective.count(component) for component in COMPONENTS}
    return {
        "carries_no_acquired_rule": not acquired,
        "every_rule_is_seed_derived": all(
            r["body"].get("derivation") == "precommitted seed and feature-row index only"
            for r in rules),
        "no_row_is_claimed_twice": all(count <= 1 for count in covered),
        "effective_assignment_is_total": len(effective) == ROW_COUNT,
        "is_non_constant": len(set(effective)) > 1,
        "reaches_every_component": set(effective) == set(COMPONENTS),
        "components_named": sorted(set(effective)),
        "rows_per_component": counts,
        "rows_reaching_the_fallthrough": counts[FALLTHROUGH_COMPONENT],
        "unlike_t0_which_reaches_the_fallthrough_on_every_row": counts[
            FALLTHROUGH_COMPONENT] < ROW_COUNT,
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


# One seed's luck is worth about one demand on a small bank -- roughly eight percentage points
# against a ten-point decision margin -- so a single fixed draw is not defensible.
#
# Averaging breaks the pairing the exact test depends on, and a majority vote across seeds does not
# preserve balance: majority-of-uniform is not uniform, and voting 129 seeds produced a 1/2/5 split,
# a worse prior than the 3/3/2 it replaced. Both were tried and rejected.
#
# Instead the achievable assignments are enumerated, and the descendant is faced with the comparator
# at its **strongest** on the revealed bank: the assignment that maximises the comparator's own
# primary successes. That is deterministic, replayable, information-free -- the enumeration consults
# no carrier -- and conservative, because it can only make the descendant's task harder. Seed luck
# is removed rather than averaged away.


def achievable_assignments() -> list[list[str]]:
    """Every balanced row-to-component assignment the construction can produce.

    Balanced means each component receives floor or ceil of ROW_COUNT / len(COMPONENTS) rows, which
    is what makes the comparator a uniform prior rather than a tilted one. Enumerated rather than
    sampled, so the set does not depend on any seed at all.
    """
    from itertools import combinations
    base, extra = divmod(ROW_COUNT, len(COMPONENTS))
    sizes_by_component: list[tuple[str, ...]] = []
    rows = list(range(ROW_COUNT))
    results: list[list[str]] = []

    def deal(remaining: list[int], components: tuple[str, ...], quota: dict[str, int],
             partial: dict[int, str]) -> None:
        if not components:
            results.append([partial[row] for row in rows])
            return
        component, rest = components[0], components[1:]
        for chosen in combinations(remaining, quota[component]):
            nxt = dict(partial)
            for row in chosen:
                nxt[row] = component
            deal([r for r in remaining if r not in chosen], rest, quota, nxt)

    # Which components receive the extra rows is itself part of the space, so no component is
    # permanently short-changed by the enumeration either.
    for larger in combinations(COMPONENTS, extra):
        quota = {c: base + (1 if c in larger else 0) for c in COMPONENTS}
        deal(rows, tuple(COMPONENTS), quota, {})
    return results


def rules_for_assignment(assignment: list[str]) -> list[dict[str, Any]]:
    """A cascade realising one assignment, built by the producer's own constructor."""
    cascade = []
    for generation, component in enumerate(FRESH_UNIFORM_RULE_COMPONENTS, start=1):
        table = [assignment[row] == component for row in range(ROW_COUNT)]
        body = {"node": "SEEDED_PARTITION", "component": component,
                "derivation": "precommitted seed and feature-row index only"}
        cascade.append(lineage.attribution_rule(body, table, component, generation))
    return cascade


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
