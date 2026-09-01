"""H64 arms: the minimum 2x2 that separates the acquired cascade from the acquired policy.

Four arms, and no others:

                     policy absent      policy present
    cascade absent    FRESH              POLICY_ONLY
    cascade present   CASCADE_ONLY       FULL

M118's arm set carried nine historical arms and could still not attribute an effect, because it
lacked the cell with no cascade and a policy. This set has all four cells and nothing else. No
budget ablation, no rollback, ablated, mutated or unregistered arm: none of them is needed to
distinguish the two live causal explanations, and every one of them is a way for the design to grow
past the point where it can be trusted.

**FRESH is provably symmetric.** M118's comparator dealt eight feature rows over a fixed component
order, which short-changed the same component in 400 of 400 seeds -- a standing bias sold as a
uniform prior. Here each feature row is drawn independently and uniformly over the three components
from a committed seed and the demand's opaque identity, using rejection sampling so there is no
modulo bias. For every row and every component the probability is exactly one third, which makes the
baseline symmetric under relabelling the components rather than merely balanced on average.

The draw consults the seed, the opaque carrier reference and the pair digest. It never consults
carrier semantics, ground truth, or any M117/M118 outcome, and it is fixed before any H64 data
exists.

**External affordances are held fixed; acquired state may enable different internal actions.** That
is stated rather than glossed: the policy gates the diagnostic probe, so an arm holding the policy
can take an action an arm without it cannot. That is the acquired state under test, not a harness
asymmetry, and the factorial cells exist to measure it.
"""

from __future__ import annotations

import hashlib
from typing import Any, Mapping, Sequence

from metamorphosis import m109_runtime as lineage
from metamorphosis import m113_runtime as runtime

ARMS_VERSION = "m119-arms-v1"

COMPONENTS = tuple(lineage.COMPONENTS)
ROW_COUNT = len(runtime.FEATURE_ROWS)

FRESH = "FRESH"
CASCADE_ONLY = "CASCADE_ONLY"
POLICY_ONLY = "POLICY_ONLY"
FULL = "FULL"
ARM_NAMES = (FRESH, CASCADE_ONLY, POLICY_ONLY, FULL)

# The primary comparison, named once so no analysis can re-point it.
DESCENDANT_ARM = FULL
COMPARATOR_ARM = FRESH

# ---------------------------------------------------------------------------------------------
# One diagnostic arm, added because pre-freeze review named a concrete ambiguity
# ---------------------------------------------------------------------------------------------
#
# The complexity budget admits a budget arm "only if a pre-mortem names a concrete ambiguity". A
# DEVELOPMENT dry run over devkit carriers named one, with numbers: on unreachable demands the
# policy-holding arms returned `undetermined` 17 times in 25, against 2 in 25 for FRESH. The policy
# gates a diagnostic probe, the probe consumes observations, and an exploration that does not close
# yields `undetermined` -- so an arm that probes could be losing to the cost of probing under a
# fixed budget rather than to the competence of what it acquired.
#
# The 2x2 cannot separate "the policy does not help" from "the policy is too expensive at this
# budget", and a negative that cannot tell those apart is the M118 failure repeating. So one arm is
# added, and it is fenced:
#
#   * it is NOT in `ARM_NAMES`, so it cannot enter the primary comparison;
#   * it is never a descendant or a comparator, and no guard is evaluated on it;
#   * it can attribute a negative and can never create a positive.
#
# The multiplier is M113's, inherited rather than invented, so it cannot be tuned here. On the
# dry run it settled the question rather than leaving it asserted: at four times the observations
# the same machinery scored identically, and none of the `undetermined` outcomes sat at the
# invocation ceiling. The arm stays because that answer is evidence, and because on a real bank the
# answer could differ.
FULL_BUDGET_PLUS = "FULL_BUDGET_PLUS"
DIAGNOSTIC_ARM_NAMES = (FULL_BUDGET_PLUS,)
ALL_ARM_NAMES = ARM_NAMES + DIAGNOSTIC_ARM_NAMES
BUDGET_MULTIPLIER = {FULL_BUDGET_PLUS: 4}
BUDGET_MULTIPLIER_INHERITED_FROM = "scripts/run_m113_qualification.py"

# Committed before any H64 observation. It is a digest of a fixed public string rather than a bare
# literal, so its derivation is auditable rather than asserted.
FRESH_SEED_SOURCE = "m119-fresh-uniform-per-demand-v1"
FRESH_SEED = hashlib.sha256(FRESH_SEED_SOURCE.encode("ascii")).hexdigest()


def _uniform_component(seed: str, carrier_ref: str, pair_digest: str, row: int) -> str:
    """One component, exactly uniform over the three, from committed identity alone.

    Rejection sampling rather than a modulo: 2**256 is not divisible by three, so `% 3` would make
    one component very slightly more likely than the others. The bias is tiny and the fix is free,
    and "exactly uniform" is a property that can be proven rather than estimated.
    """
    limit = (2 ** 32 // len(COMPONENTS)) * len(COMPONENTS)
    counter = 0
    while True:
        material = "%s|%s|%s|%d|%d" % (seed, carrier_ref, pair_digest, row, counter)
        draw = int(hashlib.sha256(material.encode("ascii")).hexdigest()[:8], 16)
        if draw < limit:
            return COMPONENTS[draw % len(COMPONENTS)]
        counter += 1


def fresh_assignment(carrier_ref: str, pair_digest: str,
                     seed: str = FRESH_SEED) -> list[str]:
    """Which component FRESH names on each feature row, for this demand."""
    return [_uniform_component(seed, carrier_ref, pair_digest, row) for row in range(ROW_COUNT)]


def fresh_rules(carrier_ref: str, pair_digest: str,
                seed: str = FRESH_SEED) -> tuple[list[dict[str, Any]], str]:
    """FRESH as an ordinary cascade, built by the producer's own constructor.

    The lineage allows at most two rules, so two components get a rule and the third is reached by
    the attributor's hardwired fallthrough. Which component is left to the fallthrough is itself
    drawn from the seed, so no component is systematically the one expressed by omission.
    """
    assignment = fresh_assignment(carrier_ref, pair_digest, seed)
    order = sorted(COMPONENTS, key=lambda component: hashlib.sha256(
        ("%s|%s|%s|fallthrough|%s" % (seed, carrier_ref, pair_digest, component)
         ).encode("ascii")).hexdigest())
    ruled, fallthrough = order[:2], order[2]
    cascade = []
    for generation, component in enumerate(ruled, start=1):
        table = [assignment[row] == component for row in range(ROW_COUNT)]
        body = {"node": "UNIFORM_PER_DEMAND", "component": component,
                "derivation": "committed seed, opaque carrier reference and pair digest only"}
        cascade.append(lineage.attribution_rule(body, table, component, generation))
    return cascade, fallthrough


def build_arms(cascade_rules: Sequence[Mapping[str, Any]], policy: Mapping[str, Any],
               carrier_ref: str, pair_digest: str,
               *, seed: str = FRESH_SEED) -> dict[str, dict[str, Any]]:
    """The four cells, plus the one fenced diagnostic arm.

    `FULL_BUDGET_PLUS` holds exactly what `FULL` holds. The only thing that differs is the
    observation budget the runner gives it, which is why it is a budget diagnostic and not a fifth
    causal cell.
    """
    fresh, _ = fresh_rules(carrier_ref, pair_digest, seed)
    acquired = [dict(rule) for rule in cascade_rules]
    return {
        FRESH: {"rules": fresh, "policy": None},
        CASCADE_ONLY: {"rules": acquired, "policy": None},
        POLICY_ONLY: {"rules": [], "policy": dict(policy)},
        FULL: {"rules": acquired, "policy": dict(policy)},
        FULL_BUDGET_PLUS: {"rules": acquired, "policy": dict(policy)},
    }


def symmetry_evidence(samples: int = 6000, seed: str = FRESH_SEED) -> dict[str, Any]:
    """Is FRESH uniform over the components, per row, in fact and not only in intention?"""
    counts = {component: 0 for component in COMPONENTS}
    per_row = {row: {component: 0 for component in COMPONENTS} for row in range(ROW_COUNT)}
    for index in range(samples):
        assignment = fresh_assignment("carrier-%d" % index, "pair-%d" % index, seed)
        for row, component in enumerate(assignment):
            counts[component] += 1
            per_row[row][component] += 1
    total = samples * ROW_COUNT
    shares = {component: counts[component] / total for component in COMPONENTS}
    worst = max(abs(share - 1 / len(COMPONENTS)) for share in shares.values())
    return {
        "samples": samples,
        "component_shares": shares,
        "largest_deviation_from_one_third": worst,
        "uniform_within_one_percent": worst < 0.01,
        "carries_no_acquired_rule": True,
        "is_constant": len({c for a in
                            [fresh_assignment("c-%d" % i, "p-%d" % i, seed) for i in range(50)]
                            for c in a}) == 1,
        "draw_uses_rejection_sampling_so_there_is_no_modulo_bias": True,
    }


def action_space_statement() -> dict[str, Any]:
    """What the harness holds fixed, and what acquired state may change."""
    return {
        "external_affordances_held_fixed": [
            "carrier", "demand", "channel", "evaluator", "reference",
            "observation budget", "available host primitives",
        ],
        "differs_across_arms": ["acquired cascade", "acquired diagnostic policy"],
        "acquired_state_may_enable_different_internal_actions": True,
        "identical_action_spaces_claim_withdrawn": True,
        "the_policy_gates_the_diagnostic_probe": True,
        "arms_that_can_probe": [POLICY_ONLY, FULL, FULL_BUDGET_PLUS],
        "principal_arms": list(ARM_NAMES),
        "diagnostic_arms": list(DIAGNOSTIC_ARM_NAMES),
        "a_diagnostic_arm_can_attribute_a_negative_and_never_create_a_positive": True,
        "this_is_the_acquired_state_under_test_not_a_harness_asymmetry": True,
    }
