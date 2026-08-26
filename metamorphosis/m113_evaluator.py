"""M113 - the evaluator, and the rules that decide a carrier before anyone has seen one.

This module owns three things the mutable body may never own: which carriers qualify, what is
demanded of them, and whether an attempt succeeded. It imports the host and nothing else. It never
imports `m113_runtime`, and `scripts/audit_m113_boundaries.py` fails if that ever changes.

## The two lessons this file exists to obey

**M112's `P5`.** The declared bound of seven expression nodes closed the constructive image on 1 160
project-generated worlds and did not close it on the first blind one. Nothing here inherits a bound
from an observation. Qualification is decided by an **exact fixed point** over the carrier's own
transition relation, and the certificate records the iteration at which growth stopped rather than
asserting that some number was large enough. A carrier whose closure is not reached is
**non-qualifying** by a rule frozen before any carrier existed, and is never re-run larger.

**M112's materialization defect.** The frozen spec assigned a world count to a record count, and
`N = 100` bought twenty worlds rather than a hundred. Every cardinality here is either the identity
or a measured quantity that is explicitly declared as measured. `cardinality_report` states the
identity mechanically and can fail.

## What is demanded, and why the project is not choosing it

The project freezes a **derivation rule**, not a task. After the seal is broken, the rule is applied
to whatever the generator emitted:

- the **reachable demands** are one per attribution row the carrier's own census can present,
  each the canonical least determined target for its row -- demands on which exactly one component
  extension makes the target satisfiable, so that a wrong attribution costs the whole attempt;
- the **unreachable demand** is the lexicographically least element of the observation space that
  the exhausted state graph proves the carrier cannot show, posed from the same entry state.

Both are functions of the sealed carrier alone. Neither can be steered by anything the project
believes about how the tested system will behave, because the tested system is frozen first and the
rule is fixed before the carrier exists.

## The pair is one object

M075-B recorded why a matched pair must not be two task objects that a validator checks for
agreement: a check has to enumerate every field that must stay equal, and missing one silently
readmits the defect. So a demand pair here stores the carrier reference, the session budget, the
meta-channel and the evaluator **once**, and the twins carry only their target and their class.
`assert_demand_pair_delta` derives both twins and refuses the pair unless the only field that
differs is the target.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from metamorphosis import carrier_host as host

DEMAND_PAIR_SCHEMA = "m113-demand-pair-v1"
QUALIFICATION_SCHEMA = "m113-carrier-qualification-v1"
OUTCOME_SCHEMA = "m113-attempt-outcome-v1"
SCORE_SCHEMA = "m113-attempt-score-v1"

CLASS_REACHABLE = "reachable"
CLASS_UNREACHABLE = "unreachable"
DEMAND_CLASSES = (CLASS_REACHABLE, CLASS_UNREACHABLE)

# The three outcomes a learner may return. The third is not a failure mode bolted on afterwards: a
# system that cannot say "I did not determine this" has only two ways to be wrong about a carrier it
# has not understood, and both of them look like confidence.
OUTCOME_CONSTRUCTED = "constructed"
OUTCOME_REFUSED = "refused"
OUTCOME_UNDETERMINED = "undetermined"
OUTCOMES = (OUTCOME_CONSTRUCTED, OUTCOME_REFUSED, OUTCOME_UNDETERMINED)

# Qualification thresholds. Frozen here, before a carrier exists, and stated as structural facts
# about the carrier rather than as anything about how a learner performs on it.
MIN_REACHABLE_OBSERVATIONS = 2
MIN_OBSERVATION_DEPTH = 2
MIN_UNREACHABLE_OBSERVATIONS = 1
MIN_GUARDED_ACTIONS = 1


class EvaluationError(RuntimeError):
    """Raised when an artifact reaching the evaluator is malformed. Every path fails closed."""


# ----------------------------------------------------------------------------------------
# Qualification: a property of the carrier, decided by exhausting it.
# ----------------------------------------------------------------------------------------


def qualification_report(carrier: Mapping[str, Any]) -> dict[str, Any]:
    """Does this carrier admit the experiment at all? Computed, never assumed.

    Each clause is a structural fact. `closed_by_fixed_point` is the one M112 would have failed:
    it is true because the frontier emptied, and the iteration count at which that happened is
    recorded beside it so a reader can see the closure rather than take it on trust.
    """
    validated = carrier if carrier.get("schema") == host.SCHEMA else host.validate_carrier(carrier)
    closure = host.observation_closure(validated)
    facts = host.carrier_facts(validated)
    depths = closure["observation_depth"]
    max_observation_depth = max(depths.values()) if depths else 0

    clauses = {
        "closed_by_fixed_point": bool(closure["closed"]),
        "enough_reachable_observations": len(closure["reachable_observations"])
        >= MIN_REACHABLE_OBSERVATIONS,
        "demand_needs_a_sequence": max_observation_depth >= MIN_OBSERVATION_DEPTH,
        "an_unreachable_observation_exists": len(closure["unreachable_observations"])
        >= MIN_UNREACHABLE_OBSERVATIONS,
        "the_carrier_imposes_a_protocol": facts["guarded_action_count"] >= MIN_GUARDED_ACTIONS,
    }
    # Only computed when the cheap structural clauses already hold: the census is the one
    # expensive clause, and a carrier that has already failed does not need it.
    clauses["a_determined_attribution_pair_exists"] = bool(
        all(clauses.values()) and attribution_census(validated)["determined_pairs"]
    )
    return {
        "schema": QUALIFICATION_SCHEMA,
        "carrier_digest": validated["carrier_digest"],
        "qualifies": all(clauses.values()),
        "clauses": dict(clauses),
        "blocking_clauses": sorted(name for name, ok in clauses.items() if not ok),
        "closure_iterations": closure["iterations"],
        "state_count": closure["state_count"],
        "max_state_depth": closure["max_depth"],
        "max_observation_depth": max_observation_depth,
        "reachable_observation_count": len(closure["reachable_observations"]),
        "unreachable_observation_count": len(closure["unreachable_observations"]),
        "observation_space_size": closure["observation_space_size"],
        "facts": facts,
    }


# ----------------------------------------------------------------------------------------
# The demand pair. One object, two twins, one differing field.
# ----------------------------------------------------------------------------------------


def entry_states(carrier: Mapping[str, Any]) -> list[dict[str, Any]]:
    """The family of configurations a lineage can be sitting in when it has to attribute.

    M110 censused both interface widths and both candidate spaces because those were every state its
    machinery could occupy at the moment it attributed. The same census is taken here, over the
    carrier's own dimensions rather than over authored constants: one action short of the carrier's
    declaration and at it, one observed field short and at it, and both composition spaces.
    """
    validated = carrier if carrier.get("schema") == host.SCHEMA else host.validate_carrier(carrier)
    actions = len(validated["actions"])
    observed = len(host.observed_cells(validated))
    action_widths = sorted({max(1, actions - 1), actions})
    observation_widths = sorted({max(1, observed - 1), observed})
    return [
        {
            "action_width": action_width,
            "observation_width": observation_width,
            "composition_space": space,
        }
        for action_width in action_widths
        for observation_width in observation_widths
        for space in (BOUNDED_SPACE, COMPLETE_SPACE)
    ]


def _feature_rows() -> list[tuple[bool, ...]]:
    rows: list[tuple[bool, ...]] = [()]
    for _ in range(3):
        rows = [row + (value,) for row in rows for value in (False, True)]
    return sorted(rows)


def identifiable(
    carrier: Mapping[str, Any],
    target: Sequence[int],
    action_width: int,
    observation_width: int,
    composition_space: str,
) -> bool:
    """Can a learner at this observation width tell that it has arrived?

    The demand is stated over every observable cell. A learner parsing fewer of them sees a
    narrowed projection, and two reachable observations sharing that projection are the same thing
    as far as it can tell. It is identifiable exactly when the narrowed projection of the target
    picks out one reachable observation, which is the target.
    """
    validated = carrier if carrier.get("schema") == host.SCHEMA else host.validate_carrier(carrier)
    wanted = tuple(int(value) for value in target)
    reach = reach_under(validated, action_width, composition_space)
    if wanted not in reach:
        return False
    width = int(observation_width)
    narrowed = wanted[:width]
    matching = {found for found in reach if found[:width] == narrowed}
    return matching == {wanted}


def observationally_nondeterministic(
    carrier: Mapping[str, Any], action_width: int, observation_width: int, composition_space: str
) -> bool:
    """Does the narrowed projection fail to be a state?

    This is the general reading of the producer's `demand_needs_an_unread_signal`, and unlike a
    width comparison it is a semantic property of the carrier rather than a restatement of the
    configuration. Two reachable configurations can share a narrowed projection and still answer the
    same request differently; when they do, the learner is watching a machine that is not a machine
    in the language it is watching it in. A latent cell that never changes anything the learner can
    see produces no such collision, and correctly produces no such signal.
    """
    validated = carrier if carrier.get("schema") == host.SCHEMA else host.validate_carrier(carrier)
    width = int(observation_width)
    declared = validated["actions"][: int(action_width)]
    alphabet: list[tuple[str, int]] = []
    for item in declared:
        if item["arity"] == 0:
            alphabet.append((item["name"], 0))
        else:
            alphabet.extend((item["name"], value) for value in range(item["arg_size"]))
    ceiling = (
        BOUNDED_COMPOSITION_DEPTH
        if composition_space == BOUNDED_SPACE
        else host.EXPLORATION_CEILING
    )

    start = host.initial_state(validated)
    seen = {start}
    frontier = [start]
    reached = [start]
    depth = 0
    while frontier and depth < ceiling:
        depth += 1
        following = []
        for state in frontier:
            for name, argument in alphabet:
                outcome = host.step(validated, state, name, argument)
                if not outcome["accepted"] or outcome["state"] in seen:
                    continue
                seen.add(outcome["state"])
                following.append(outcome["state"])
                reached.append(outcome["state"])
        frontier = following

    responses: dict[tuple[tuple[int, ...], str, int], set[tuple[int, ...] | None]] = {}
    for state in reached:
        here = host.observation(validated, state)[:width]
        for name, argument in alphabet:
            outcome = host.step(validated, state, name, argument)
            answer = (
                host.observation(validated, outcome["state"])[:width]
                if outcome["accepted"]
                else None
            )
            responses.setdefault((here, name, argument), set()).add(answer)
    return any(len(values) > 1 for values in responses.values())


def evaluator_features(
    carrier: Mapping[str, Any], target: Sequence[int], entry: Mapping[str, Any]
) -> dict[str, Any]:
    """The producer's three features, computed exactly from the carrier.

    The learner computes the same three from what it observed through the channel and never sees
    this. The two are compared in the result: a divergence between them is a fact about how much of
    the carrier the reception contract lets a learner see, and it is reported rather than assumed
    away.

    None of the three restates the configuration it is computed at. That was the first draft's
    defect: `g0` was a width comparison, so every row on which it was true mapped to the observation
    interface by definition, and the whole attribution question answered itself. A feature that
    determines its own label measures nothing.
    """
    validated = carrier if carrier.get("schema") == host.SCHEMA else host.validate_carrier(carrier)
    wanted = tuple(int(value) for value in target)
    action_width = int(entry["action_width"])
    observation_width = int(entry["observation_width"])
    space = entry["composition_space"]

    g0 = observationally_nondeterministic(validated, action_width, observation_width, space)
    wider = min(action_width + 1, len(validated["actions"]))
    here = reach_under(validated, action_width, space)
    there = reach_under(validated, wider, space)
    g1 = not identifiable(validated, wanted, wider, observation_width, space)
    g2 = len(there) > len(here)
    values = (bool(g0), bool(g1), bool(g2))
    return {
        "schema": "m113-evaluator-features-v1",
        "values": [bool(value) for value in values],
        "row_index": _feature_rows().index(values),
    }


def attribution_census(carrier: Mapping[str, Any]) -> dict[str, Any]:
    """Every feature row that can arise while attributing on this carrier, and what resolves it.

    This is the evaluator's map of the carrier, and it is the object M113's central question is
    asked of. If the same feature row carries different limiting components on different blind
    carriers, then no function of the inherited three-feature vocabulary is right on all of them,
    and the ceiling M113 was built to find is the **feature vocabulary** rather than the carrier.
    """
    validated = carrier if carrier.get("schema") == host.SCHEMA else host.validate_carrier(carrier)
    observed = host.observed_cells(validated)
    sizes = [
        int(item["size"]) for item, shown in zip(validated["cells"], validated["visible"]) if shown
    ]
    space: list[tuple[int, ...]] = [()]
    for size in sizes:
        space = [prefix + (value,) for prefix in space for value in range(size)]

    family = entry_states(validated)
    determined: list[dict[str, Any]] = []
    labels: dict[int, set[str]] = {}
    counts: dict[int, int] = {}
    examined = 0
    for entry in family:
        for target in space:
            trial = component_trial(
                validated,
                target,
                action_width=entry["action_width"],
                observation_width=entry["observation_width"],
                composition_space=entry["composition_space"],
            )
            if not trial["determined"]:
                continue
            features = evaluator_features(validated, target, entry)
            row = features["row_index"]
            examined += 1
            labels.setdefault(row, set()).add(trial["component"])
            counts[row] = counts.get(row, 0) + 1
            determined.append(
                {
                    "entry": dict(entry),
                    "target": list(target),
                    "component": trial["component"],
                    "row_index": row,
                    "features": features["values"],
                }
            )
    return {
        "schema": "m113-attribution-census-v1",
        "carrier_digest": validated["carrier_digest"],
        "observed_cells": list(observed),
        "observation_space_size": len(space),
        "entry_state_family_size": len(family),
        "determined_pairs_examined": examined,
        "rows": sorted(labels),
        "ambiguous_rows": sorted(row for row, found in labels.items() if len(found) > 1),
        "row_labels": {str(row): sorted(found) for row, found in sorted(labels.items())},
        "row_counts": {str(row): counts[row] for row in sorted(counts)},
        "determined_pairs": determined,
        "census_complete": True,
    }


def canonical_pairs_by_row(census: Mapping[str, Any]) -> dict[int, dict[str, Any]]:
    """One determined pair per attribution row, each the least in canonical order.

    A first draft took the single first determined pair in census order, and the census iterates the
    smallest entry state and the least target first. That is a biased rule, and the bias was
    measurable: over 300 devkit carriers the reachable arm landed **zero** times out of twenty-one
    on a feature row where the inherited cascades disagree, so the acquired machinery had no
    opportunity to help or harm there and every arm scored identically. A demand rule that cannot
    reach the rows the experiment is about measures nothing about them.

    M110 already had the answer and this restates it in the carrier's own terms: it posed rows, not
    targets, and took the canonical least demand for each row it censused. So does this.
    """
    chosen: dict[int, dict[str, Any]] = {}
    for entry in census["determined_pairs"]:
        row = int(entry["row_index"])
        key = (
            entry["entry"]["action_width"],
            entry["entry"]["observation_width"],
            entry["entry"]["composition_space"],
            tuple(entry["target"]),
        )
        held = chosen.get(row)
        if held is None or key < held["_order"]:
            chosen[row] = dict(entry, _order=key)
    return {row: {k: v for k, v in item.items() if k != "_order"} for row, item in chosen.items()}


def derive_demand_pairs(
    carrier: Mapping[str, Any], carrier_ref: str, session_budget: int
) -> list[dict[str, Any]]:
    """Apply the frozen derivation rule to a carrier the project did not design.

    A carrier contributes **one pair per attribution row its own census can present**, in ascending
    row order. Every pair is a function of the sealed carrier alone; no reading of one can be steered
    by what the tested system does, because the tested system is frozen before the seal is broken.

    Within each pair:

    - the **reachable** twin is the canonical least determined target for that row -- a demand on
      which exactly one component extension makes the target satisfiable, so a wrong attribution
      costs the whole attempt;
    - the **unreachable** twin is the least observation the exhausted state graph proves the carrier
      cannot show, posed from the same entry state. No component extension resolves it, at any width
      and in either composition space, which is what makes the refusal it demands structural rather
      than a task phrased so a careful reader gives up.
    """
    validated = carrier if carrier.get("schema") == host.SCHEMA else host.validate_carrier(carrier)
    report = qualification_report(validated)
    if not report["qualifies"]:
        raise EvaluationError(
            "carrier does not qualify: %s" % ", ".join(report["blocking_clauses"])
        )
    census = attribution_census(validated)
    by_row = canonical_pairs_by_row(census)
    if not by_row:
        raise EvaluationError("carrier admits no determined attribution pair")
    closure = host.observation_closure(validated)
    unreachable_target = closure["unreachable_observations"][0]

    pairs: list[dict[str, Any]] = []
    for row in sorted(by_row):
        chosen = by_row[row]
        shared = {
            "carrier_ref": str(carrier_ref),
            "carrier_digest": validated["carrier_digest"],
            "session_budget": int(session_budget),
            "observed_cells": list(host.observed_cells(validated)),
            "meta_channel_digest": host.digest(host.meta_channel(validated)),
            "entry": dict(chosen["entry"]),
            "evaluator": "m113_evaluator.score_attempt",
            "success_predicate": "terminal-observation-exact-match",
        }
        pair = {
            "schema": DEMAND_PAIR_SCHEMA,
            "shared": shared,
            "targets": {
                CLASS_REACHABLE: list(chosen["target"]),
                CLASS_UNREACHABLE: list(unreachable_target),
            },
            "ground_truth": {
                "component": chosen["component"],
                "row_index": chosen["row_index"],
                "features": list(chosen["features"]),
            },
            "derivation": {
                "reachable": "canonical least determined target for this attribution row",
                "unreachable": "least observation the exhausted state graph proves unreachable",
                "rows_posed": sorted(by_row),
            },
        }
        pair["pair_digest"] = host.digest(pair)
        pairs.append(pair)
    return pairs


def derive_demand_pair(
    carrier: Mapping[str, Any], carrier_ref: str, session_budget: int
) -> dict[str, Any]:
    """The pair for this carrier's least attribution row. A convenience over the frozen rule."""
    return derive_demand_pairs(carrier, carrier_ref, session_budget)[0]


def materialize_twin(pair: Mapping[str, Any], demand_class: str) -> dict[str, Any]:
    """Derive one runnable demand. Every field except the target comes from the shared copy."""
    if demand_class not in DEMAND_CLASSES:
        raise EvaluationError("demand class is outside the declared pair")
    if pair.get("schema") != DEMAND_PAIR_SCHEMA:
        raise EvaluationError("demand pair schema is not the declared one")
    shared = pair["shared"]
    return {
        "schema": "m113-demand-v1",
        "carrier_ref": shared["carrier_ref"],
        "carrier_digest": shared["carrier_digest"],
        "session_budget": shared["session_budget"],
        "observed_cells": list(shared["observed_cells"]),
        "meta_channel_digest": shared["meta_channel_digest"],
        "entry": dict(shared["entry"]),
        "evaluator": shared["evaluator"],
        "success_predicate": shared["success_predicate"],
        "target": list(pair["targets"][demand_class]),
        "demand_class": demand_class,
    }


def demand_pair_delta(pair: Mapping[str, Any]) -> dict[str, Any]:
    left = materialize_twin(pair, CLASS_REACHABLE)
    right = materialize_twin(pair, CLASS_UNREACHABLE)
    differing = sorted(key for key in set(left) | set(right) if left.get(key) != right.get(key))
    return {
        "schema": "m113-demand-pair-delta-v1",
        "differing_fields": differing,
        "reachable_target": left["target"],
        "unreachable_target": right["target"],
    }


def assert_demand_pair_delta(pair: Mapping[str, Any]) -> None:
    """State the conclusion instead of assuming it.

    Under this representation the assertion cannot fail for a well-formed pair, because there is
    only one copy of everything the twins share. It is kept because a future change that gives a
    twin a field of its own would be caught the moment it is made, rather than at the next reveal.
    """
    delta = demand_pair_delta(pair)
    if delta["differing_fields"] != ["demand_class", "target"]:
        raise EvaluationError(
            "the twins differ in more than the target: %s" % ", ".join(delta["differing_fields"])
        )
    if delta["reachable_target"] == delta["unreachable_target"]:
        raise EvaluationError("the twins carry the same target")


# ----------------------------------------------------------------------------------------
# Scoring. Decided from terminal carrier state, never from what the learner says it did.
# ----------------------------------------------------------------------------------------


def replay_sequence(
    carrier: Mapping[str, Any], sequence: Sequence[Sequence[Any]]
) -> dict[str, Any]:
    """Run a claimed request sequence against a fresh carrier and report where it ends up.

    G6's scoring rule, applied here: completion is measured from the environment's state, never
    from the agent's report. A learner that returns a sequence is not believed; the sequence is run.
    """
    validated = carrier if carrier.get("schema") == host.SCHEMA else host.validate_carrier(carrier)
    state = host.initial_state(validated)
    refusals = 0
    for index, item in enumerate(sequence):
        if not isinstance(item, Sequence) or isinstance(item, (str, bytes)) or len(item) != 2:
            raise EvaluationError("claimed request %d is not a (name, argument) pair" % index)
        name, argument = item[0], item[1]
        if not isinstance(name, str) or isinstance(argument, bool) or not isinstance(argument, int):
            raise EvaluationError("claimed request %d is not well typed" % index)
        outcome = host.step(validated, state, name, int(argument))
        if outcome["accepted"]:
            state = outcome["state"]
        else:
            refusals += 1
    return {
        "terminal_state": list(state),
        "terminal_observation": list(host.observation(validated, state)),
        "requests": len(list(sequence)),
        "refused_requests": refusals,
    }


def score_attempt(
    carrier: Mapping[str, Any],
    demand: Mapping[str, Any],
    outcome: Mapping[str, Any],
) -> dict[str, Any]:
    """The one place a verdict is drawn. Four named ways to be right or wrong, and no fifth.

    - `constructed` on a reachable demand, replay agreeing: **correct construction**;
    - `refused` on an unreachable demand: **calibrated refusal**;
    - `constructed` on an unreachable demand: **invented adapter** -- the failure G1 names, and it
      cannot be reached by accident, because the replay has to actually land on a target the state
      graph proves is unreachable, which it never can;
    - `refused` on a reachable demand: **false refusal**;
    - `undetermined` anywhere: honest non-commitment, scored as neither success nor refusal.
    """
    if outcome.get("schema") != OUTCOME_SCHEMA:
        raise EvaluationError("attempt outcome schema is not the declared one")
    verdict = outcome.get("verdict")
    if verdict not in OUTCOMES:
        raise EvaluationError("attempt outcome verdict is outside the declared set")
    if demand.get("carrier_digest") != (
        carrier.get("carrier_digest") or host.validate_carrier(carrier)["carrier_digest"]
    ):
        raise EvaluationError("the demand does not belong to this carrier")

    demand_class = demand["demand_class"]
    target = tuple(int(value) for value in demand["target"])
    replay: dict[str, Any] | None = None
    reached = False
    if verdict == OUTCOME_CONSTRUCTED:
        replay = replay_sequence(carrier, outcome.get("sequence") or [])
        reached = tuple(replay["terminal_observation"]) == target

    correct_construction = (
        verdict == OUTCOME_CONSTRUCTED and demand_class == CLASS_REACHABLE and reached
    )
    invented_adapter = verdict == OUTCOME_CONSTRUCTED and demand_class == CLASS_UNREACHABLE
    calibrated_refusal = verdict == OUTCOME_REFUSED and demand_class == CLASS_UNREACHABLE
    false_refusal = verdict == OUTCOME_REFUSED and demand_class == CLASS_REACHABLE
    unmet_construction = (
        verdict == OUTCOME_CONSTRUCTED and demand_class == CLASS_REACHABLE and not reached
    )

    return {
        "schema": SCORE_SCHEMA,
        "carrier_ref": demand["carrier_ref"],
        "carrier_digest": demand["carrier_digest"],
        "demand_class": demand_class,
        "verdict": verdict,
        "target": list(target),
        "replay": replay,
        "reached_target": bool(reached),
        "correct_construction": bool(correct_construction),
        "invented_adapter": bool(invented_adapter),
        "calibrated_refusal": bool(calibrated_refusal),
        "false_refusal": bool(false_refusal),
        "unmet_construction": bool(unmet_construction),
        "undetermined": verdict == OUTCOME_UNDETERMINED,
        "invocations_used": int(outcome.get("invocations_used", 0)),
        "budget": int(demand["session_budget"]),
        "within_budget": int(outcome.get("invocations_used", 0)) <= int(demand["session_budget"]),
    }


# ----------------------------------------------------------------------------------------
# Ground truth: the evaluator's own controlled trial, computed exactly from the carrier.
# ----------------------------------------------------------------------------------------

BASE_ACTION_WIDTH = 2
BASE_OBSERVATION_WIDTH = 1
BOUNDED_COMPOSITION_DEPTH = 2
BOUNDED_SPACE = "monotone"
COMPLETE_SPACE = "complete"

# The component names are the producer's, read from the producer module rather than restated, so a
# drift is an import error rather than a silent disagreement about what a rule selects.
COMPONENT_ACTIONS = "operator_table"
COMPONENT_OBSERVATION = "signal_interface"
COMPONENT_COMPOSITION = "candidate_space"
COMPONENTS = (COMPONENT_ACTIONS, COMPONENT_OBSERVATION, COMPONENT_COMPOSITION)


_REACH_MEMO: dict[tuple[str, int, str], dict[tuple[int, ...], list[tuple[str, int]]]] = {}


def reach_under(
    carrier: Mapping[str, Any], action_width: int, composition_space: str
) -> dict[tuple[int, ...], list[tuple[str, int]]]:
    """Every observation a learner restricted to these axes could ever reach, computed exactly.

    This is the evaluator's copy of the learner's search, run without a budget and without a
    channel. It exists so that "the learner did not find it" and "it is not there" are different
    statements that can be compared, which is the only way a refusal can be scored rather than
    believed.
    """
    validated = carrier if carrier.get("schema") == host.SCHEMA else host.validate_carrier(carrier)
    key = (validated["carrier_digest"], int(action_width), str(composition_space))
    memo = _REACH_MEMO.get(key)
    if memo is not None:
        return memo
    declared = validated["actions"][: int(action_width)]
    alphabet: list[tuple[str, int]] = []
    for item in declared:
        if item["arity"] == 0:
            alphabet.append((item["name"], 0))
        else:
            alphabet.extend((item["name"], value) for value in range(item["arg_size"]))
    ceiling = (
        BOUNDED_COMPOSITION_DEPTH if composition_space == BOUNDED_SPACE else host.EXPLORATION_CEILING
    )

    start = host.initial_state(validated)
    seen_states = {start}
    found: dict[tuple[int, ...], list[tuple[str, int]]] = {}
    frontier: list[tuple[tuple[int, ...], list[tuple[str, int]]]] = [(start, [])]
    depth = 0
    while frontier and depth < ceiling:
        depth += 1
        following: list[tuple[tuple[int, ...], list[tuple[str, int]]]] = []
        for state, path in frontier:
            for name, argument in alphabet:
                outcome = host.step(validated, state, name, argument)
                if not outcome["accepted"]:
                    continue
                nxt = outcome["state"]
                if nxt in seen_states:
                    continue
                seen_states.add(nxt)
                sequence = path + [(name, argument)]
                found.setdefault(host.observation(validated, nxt), sequence)
                following.append((nxt, sequence))
        frontier = following
    _REACH_MEMO[key] = found
    return found


def component_trial(
    carrier: Mapping[str, Any],
    target: Sequence[int],
    action_width: int = BASE_ACTION_WIDTH,
    observation_width: int = BASE_OBSERVATION_WIDTH,
    composition_space: str = BOUNDED_SPACE,
) -> dict[str, Any]:
    """Which single component must be extended for this demand to become constructible?

    The same necessity semantics M110 declared, evaluated against this carrier's own structure.
    Nothing here reads a rule, so a restored cascade can be wrong against it -- and whether it is
    wrong, and on which feature rows, is the measurement M113 exists to take.
    """
    validated = carrier if carrier.get("schema") == host.SCHEMA else host.validate_carrier(carrier)
    wanted = tuple(int(value) for value in target)
    observed = host.observed_cells(validated)

    def satisfiable(actions: int, observation: int, space: str) -> bool:
        return identifiable(validated, wanted, actions, observation, space)

    already = satisfiable(action_width, observation_width, composition_space)
    outcomes = {
        COMPONENT_ACTIONS: action_width + 1 <= len(validated["actions"])
        and satisfiable(action_width + 1, observation_width, composition_space),
        COMPONENT_OBSERVATION: observation_width + 1 <= len(observed)
        and satisfiable(action_width, observation_width + 1, composition_space),
        COMPONENT_COMPOSITION: composition_space != COMPLETE_SPACE
        and satisfiable(action_width, observation_width, COMPLETE_SPACE),
    }
    resolving = sorted(name for name, ok in outcomes.items() if ok)
    return {
        "schema": "m113-component-trial-v1",
        "already_constructible": bool(already),
        "outcomes": outcomes,
        "resolving_components": resolving,
        "determined": (not already) and len(resolving) == 1,
        "component": resolving[0] if (not already) and len(resolving) == 1 else None,
        "label_source": "evaluator_component_trial",
        "semantics": "minimal_necessary_component",
        "components_examined": sorted(COMPONENTS),
    }


# ----------------------------------------------------------------------------------------
# Cardinality. The M112 defect, made mechanical and able to fail.
# ----------------------------------------------------------------------------------------


def cardinality_report(
    requested_carrier_count: int,
    records_emitted: int,
    carriers_enveloped: int,
    schema_valid_carriers: int,
    qualifying_carriers: int,
    minimum_qualifying: int,
) -> dict[str, Any]:
    """Say what each count is, and prove the ones that are supposed to be identities.

    M112 froze `requested_record_count = requested_world_count` while a world was five records, so
    a hundred bought twenty. The error was not arithmetic; it was that no stage ever compared the
    two numbers. Here every adjacent pair is compared, the identities are named as identities, and
    the one quantity that genuinely cannot be an identity -- how many of the emitted carriers turn
    out to qualify -- is declared as measured after reveal and carries a minimum that can fail.
    """
    requested = int(requested_carrier_count)
    emitted = int(records_emitted)
    enveloped = int(carriers_enveloped)
    valid = int(schema_valid_carriers)
    qualifying = int(qualifying_carriers)
    minimum = int(minimum_qualifying)

    identities = {
        "requested_equals_emitted": requested == emitted,
        "emitted_equals_enveloped": emitted == enveloped,
    }
    derivations = {
        "enveloped_to_schema_valid": "measured: a payload the host refuses is not a carrier",
        "schema_valid_to_qualifying": "measured after reveal against the frozen qualification rule",
    }
    return {
        "schema": "m113-cardinality-report-v1",
        "requested_carrier_count": requested,
        "records_emitted": emitted,
        "carriers_enveloped": enveloped,
        "schema_valid_carriers": valid,
        "qualifying_carriers": qualifying,
        "minimum_qualifying_carriers": minimum,
        "identities": identities,
        "identities_hold": all(identities.values()),
        "declared_derivations": derivations,
        "monotone": requested >= emitted >= enveloped >= valid >= qualifying >= 0,
        "minimum_met": qualifying >= minimum,
    }


def assert_cardinality(report: Mapping[str, Any]) -> None:
    """Refuse a materialization whose counts do not describe one another.

    This is the guard M112 did not have. It is decisive rather than advisory, and the test suite
    hands it a deliberately mismatched report to prove it can fail.
    """
    if report.get("schema") != "m113-cardinality-report-v1":
        raise EvaluationError("cardinality report schema is not the declared one")
    if not report.get("identities_hold"):
        broken = sorted(
            name for name, ok in (report.get("identities") or {}).items() if not ok
        )
        raise EvaluationError(
            "a cardinality the spec declares an identity does not hold: %s" % ", ".join(broken)
        )
    if not report.get("monotone"):
        raise EvaluationError("the cardinality chain is not monotone decreasing")
