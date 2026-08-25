"""M111 - can the lineage tell that its own observation does not determine the answer?

M110 measured an acquired machinery improvement doing harm: at a failure row outside its producer's
attribution census the improved lineage was confident, wrong, and strictly worse than the fresh
predecessor it improved on. Widening the census would not fix that. What would is a lineage that
knows when to run an experiment instead of committing.

This module adds one registered component, the **diagnostic policy**, and one primitive, the
**probe**. A probe extends a component, tests whether that would resolve the demand, and rolls back;
the state afterwards is byte-identical to the state before, which is measured rather than promised.
Probes are scarce, so a policy that spends them everywhere is as useless as one that never spends
them.

The lineage carries two states, because it has two languages:

- the **machinery state** is M109's: Boolean operators, the interface width, the candidate space and
  the acquired attribution cascade. This is the language *policies are written in*.
- the **consumer state** is M110's: the four-valued chain over reference-bearing JSON documents. This
  is the domain demands live in.

That separation is what makes generation 3 depend on generation 2. A policy must fire on feature row
3 and not on row 7, row 3 lies below row 7 componentwise, and every monotone program true at the
lower row is true at the upper one. The lineage holds `{AND, OR}`, so no policy it can write
distinguishes them -- until it adopts a non-monotone operator, which exists only in the complete
candidate space that generation 2 acquired.

Both predecessors are imported unchanged. A fork at any level would end the chain.
"""

from __future__ import annotations

import itertools
import json
from typing import Any, Iterable

from metamorphosis import m107_runtime as expr
from metamorphosis import m108_runtime as base
from metamorphosis import m109_runtime as machinery
from metamorphosis import m110_runtime as consumer

STATE_SCHEMA = "m111-diagnostic-state-v1"
POLICY_SCHEMA = "m111-diagnostic-policy-v1"
EPISODE_SCHEMA = "m111-diagnostic-episode-v1"

COMPONENT_OPERATORS = machinery.COMPONENT_OPERATORS
COMPONENT_SIGNALS = machinery.COMPONENT_SIGNALS
COMPONENT_CANDIDATES = machinery.COMPONENT_CANDIDATES
COMPONENT_DIAGNOSTIC = "diagnostic_policy"
COMPONENTS = tuple(machinery.COMPONENTS) + (COMPONENT_DIAGNOSTIC,)

FEATURE_NAMES = machinery.FEATURE_NAMES
FEATURE_COUNT = machinery.FEATURE_COUNT
FEATURE_ROWS = machinery.FEATURE_ROWS

MONOTONE_SPACE = machinery.MONOTONE_SPACE
COMPLETE_SPACE = machinery.COMPLETE_SPACE

MAX_EXPRESSION_NODES = consumer.MAX_EXPRESSION_NODES
POLICY_NODE_BOUND = machinery.MAX_EXPRESSION_NODES
DEFAULT_PROBE_BUDGET = 1
MAX_MACHINERY_GENERATIONS = 3

# The order probes are tried in. Declared, and deliberately measured both ways round: with exactly
# two live candidates, elimination makes either order correct, so the order carries no answer.
PROBE_ORDER_CANDIDATES_FIRST = (COMPONENT_CANDIDATES, COMPONENT_SIGNALS)
PROBE_ORDER_SIGNALS_FIRST = (COMPONENT_SIGNALS, COMPONENT_CANDIDATES)
PROBE_ORDERS = (PROBE_ORDER_CANDIDATES_FIRST, PROBE_ORDER_SIGNALS_FIRST)

canonical_json = machinery.canonical_json
digest = machinery.digest
sha256_bytes = machinery.sha256_bytes


# ----------------------------------------------------------------------------------------
# The policy: a program over the same three features, saying only "here, run an experiment".
# ----------------------------------------------------------------------------------------


def diagnostic_policy(body: dict[str, Any], table: Iterable[bool], generation: int) -> dict[str, Any]:
    rows = [bool(value) for value in table]
    if len(rows) != 2 ** FEATURE_COUNT:
        raise ValueError("M111 policy truth table has the wrong length")
    payload: dict[str, Any] = {
        "schema": POLICY_SCHEMA,
        "features": list(FEATURE_NAMES),
        "body": body,
        "truth_table": rows,
        "selects_component_when_true": COMPONENT_DIAGNOSTIC,
        "generation": int(generation),
    }
    payload["policy_id"] = "policy-" + digest(payload)[:16]
    return payload


def decode_policy(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict) or raw.get("schema") != POLICY_SCHEMA:
        raise ValueError("M111 policy payload is invalid")
    if list(raw.get("features") or []) != list(FEATURE_NAMES):
        raise ValueError("M111 policy feature vocabulary changed")
    rebuilt = diagnostic_policy(
        raw.get("body"), raw.get("truth_table") or [], raw.get("generation", 0)
    )
    if rebuilt["policy_id"] != raw.get("policy_id"):
        raise ValueError("M111 policy identity mismatch")
    return rebuilt


def policy_fires(policy: dict[str, Any] | None, row: int) -> bool:
    return bool(policy) and bool(policy["truth_table"][row])


# ----------------------------------------------------------------------------------------
# Lineage state: two languages, one cascade, one policy, one scarce budget.
# ----------------------------------------------------------------------------------------


def create_state(
    machinery_state: dict[str, Any],
    consumer_state: dict[str, Any],
    *,
    policy: dict[str, Any] | None = None,
    probe_budget: int = DEFAULT_PROBE_BUDGET,
) -> dict[str, Any]:
    budget = int(probe_budget)
    if budget < 0:
        raise ValueError("M111 probe budget is negative")
    payload = {
        "machinery_state": machinery.decode_state(machinery_state),
        "consumer_state": consumer.decode_state(consumer_state),
        "policy": decode_policy(policy) if policy else None,
        "probe_budget": budget,
        "component_registry": list(COMPONENTS),
        "feature_vocabulary": list(FEATURE_NAMES),
    }
    if payload["machinery_state"]["rules"] != payload["consumer_state"]["rules"]:
        raise ValueError("M111 machinery and consumer cascades disagree")
    return {"schema": STATE_SCHEMA, **payload, "state_digest": digest(payload)}


def decode_state(raw: bytes | str | dict[str, Any]) -> dict[str, Any]:
    if isinstance(raw, (bytes, bytearray)):
        value = json.loads(bytes(raw).decode("ascii"))
    elif isinstance(raw, str):
        value = json.loads(raw)
    else:
        value = json.loads(canonical_json(raw))
    if not isinstance(value, dict) or value.get("schema") != STATE_SCHEMA:
        raise ValueError("M111 state payload is invalid")
    if list(value.get("component_registry") or []) != list(COMPONENTS):
        raise ValueError("M111 component registry changed")
    if list(value.get("feature_vocabulary") or []) != list(FEATURE_NAMES):
        raise ValueError("M111 feature vocabulary changed")
    rebuilt = create_state(
        value.get("machinery_state"),
        value.get("consumer_state"),
        policy=value.get("policy"),
        probe_budget=int(value.get("probe_budget", DEFAULT_PROBE_BUDGET)),
    )
    if rebuilt["state_digest"] != value.get("state_digest"):
        raise ValueError("M111 state digest mismatch")
    return rebuilt


def encode_state(state: dict[str, Any]) -> bytes:
    return canonical_json(decode_state(state)).encode("ascii")


def adapter_projection(state: dict[str, Any]) -> dict[str, Any]:
    """Everything the arms must share. Equality across arms is measured, not promised."""
    decoded = decode_state(state)
    return {
        "consumer_operators": decoded["consumer_state"]["operators"],
        "interface_width": decoded["consumer_state"]["interface_width"],
        "component_registry": decoded["component_registry"],
        "feature_vocabulary": decoded["feature_vocabulary"],
        "probe_budget": decoded["probe_budget"],
    }


# ----------------------------------------------------------------------------------------
# The probe: an experiment that leaves nothing behind.
# ----------------------------------------------------------------------------------------


def probe(
    state: dict[str, Any],
    world: dict[str, Any],
    target: Iterable[int],
    component: str,
    max_nodes: int = MAX_EXPRESSION_NODES,
) -> dict[str, Any]:
    """Extend one component, ask whether that would resolve the demand, then roll back.

    The rollback is not a promise: the consumer state is serialized before and after and the two byte
    strings are compared in the returned record.
    """
    if component not in machinery.COMPONENTS:
        raise ValueError("M111 probe names a component outside the registry")
    current = state["consumer_state"]
    before = consumer.encode_state(current)
    wanted = tuple(int(value) for value in target)

    if component == COMPONENT_SIGNALS:
        extension = consumer.extend_signal_interface(current)
        reached = bool(
            extension["confirmed"]
            and consumer.construct(extension["next_state"], world, wanted, max_nodes)[
                "constructible"
            ]
        )
    elif component == COMPONENT_CANDIDATES:
        reached = consumer._widened_then_extended(current, world, wanted, max_nodes) is not None
    else:
        reached = bool(
            consumer.extend_operator_table(current, world, wanted, max_nodes)["confirmed"]
        )

    after = consumer.encode_state(current)
    return {
        "schema": "m111-probe-v1",
        "component": component,
        "would_resolve": bool(reached),
        "state_unchanged": before == after,
        "state_digest_before": current["state_digest"],
        "state_digest_after": consumer.decode_state(after)["state_digest"],
        "is_an_adoption": False,
    }


# ----------------------------------------------------------------------------------------
# Resolution: consult the policy, spend a probe if it fires and the budget allows, then commit.
# ----------------------------------------------------------------------------------------


def _commit(
    consumer_state: dict[str, Any],
    world: dict[str, Any],
    target: tuple[int, ...],
    component: str,
    max_nodes: int,
) -> dict[str, Any]:
    if component == COMPONENT_SIGNALS:
        extension = consumer.extend_signal_interface(consumer_state)
    elif component == COMPONENT_CANDIDATES:
        widened = consumer.widen_candidate_space(consumer_state)
        extension = (
            consumer.extend_operator_table(widened["next_state"], world, target, max_nodes)
            if widened["confirmed"]
            else widened
        )
        if extension.get("confirmed"):
            extension = dict(extension)
            extension["component"] = COMPONENT_CANDIDATES
    else:
        extension = consumer.extend_operator_table(consumer_state, world, target, max_nodes)
    return extension


def resolve(
    state: dict[str, Any],
    world: dict[str, Any],
    demand: dict[str, Any],
    *,
    probe_order: Iterable[str] = PROBE_ORDER_CANDIDATES_FIRST,
    force_probe: bool | None = None,
    max_nodes: int = MAX_EXPRESSION_NODES,
) -> dict[str, Any]:
    """One machinery step, plus at most `probe_budget` probes across the whole sequence.

    `force_probe` overrides the policy and is how the never-probe and always-probe controls are run
    on exactly the same code path as the diagnostic arm.
    """
    decoded = consumer.decode_demand(demand)
    wanted = tuple(decoded["target"])
    current = decode_state(state)
    consumer_state = current["consumer_state"]
    budget = current["probe_budget"]

    built = consumer.construct(consumer_state, world, wanted, max_nodes)
    if built["constructible"]:
        return {
            "schema": "m111-resolution-v1",
            "confirmed": True,
            "probes_spent": 0,
            "probe_records": [],
            "policy_fired": False,
            "decided_by": "already_constructible",
            "attributed_component": None,
            "construction": built,
            "remaining_probe_budget": budget,
            "final_state_digest": current["state_digest"],
        }

    features = consumer.failure_features(consumer_state, world, wanted, max_nodes)
    row = features["row_index"]
    fired = policy_fires(current["policy"], row)
    wants_probe = fired if force_probe is None else bool(force_probe)

    probe_records: list[dict[str, Any]] = []
    chosen: str | None = None
    decided_by = "attribution_cascade"

    if wants_probe and budget > 0:
        order = list(probe_order)
        record = probe(current, world, wanted, order[0], max_nodes)
        probe_records.append(record)
        budget -= 1
        if record["would_resolve"]:
            chosen = order[0]
            decided_by = "probe_confirmed"
        else:
            chosen = order[1]
            decided_by = "probe_eliminated"
    if chosen is None:
        chosen = consumer.attribute(consumer_state, features)["component"]

    extension = _commit(consumer_state, world, wanted, chosen, max_nodes)
    resolved = bool(extension.get("confirmed"))
    construction = (
        consumer.construct(extension["next_state"], world, wanted, max_nodes)
        if resolved
        else built
    )
    return {
        "schema": "m111-resolution-v1",
        "confirmed": bool(resolved and construction["constructible"]),
        "probes_spent": len(probe_records),
        "probe_records": probe_records,
        "policy_fired": bool(fired),
        "probe_requested": bool(wants_probe),
        "budget_allowed_the_probe": bool(wants_probe and current["probe_budget"] > 0),
        "decided_by": decided_by,
        "feature_row": row,
        "features": features,
        "attributed_component": chosen,
        "construction": construction,
        "remaining_probe_budget": budget,
        "final_state_digest": current["state_digest"],
    }


def resolve_sequence(
    state: dict[str, Any],
    world: dict[str, Any],
    demands: Iterable[dict[str, Any]],
    *,
    probe_order: Iterable[str] = PROBE_ORDER_CANDIDATES_FIRST,
    force_probe: bool | None = None,
    max_nodes: int = MAX_EXPRESSION_NODES,
) -> dict[str, Any]:
    """A sequence sharing one probe budget. The budget is the scarce resource under test."""
    current = decode_state(state)
    budget = current["probe_budget"]
    outcomes = []
    for item in demands:
        stepped = create_state(
            current["machinery_state"],
            current["consumer_state"],
            policy=current["policy"],
            probe_budget=budget,
        )
        report = resolve(
            stepped,
            world,
            item,
            probe_order=probe_order,
            force_probe=force_probe,
            max_nodes=max_nodes,
        )
        budget = report["remaining_probe_budget"]
        outcomes.append(
            {
                "demand_digest": item["demand_digest"],
                "target": list(item["target"]),
                "confirmed": report["confirmed"],
                "feature_row": report.get("feature_row"),
                "policy_fired": report.get("policy_fired"),
                "probes_spent": report["probes_spent"],
                "decided_by": report["decided_by"],
                "attributed_component": report.get("attributed_component"),
                "executes_to_target": bool(
                    (report.get("construction") or {}).get("executes_to_target")
                ),
                "probe_records": report["probe_records"],
            }
        )
    return {
        "schema": "m111-sequence-v1",
        "starting_probe_budget": current["probe_budget"],
        "remaining_probe_budget": budget,
        "probes_spent": sum(item["probes_spent"] for item in outcomes),
        "resolved_count": sum(1 for item in outcomes if item["confirmed"]),
        "all_resolved": all(item["confirmed"] for item in outcomes),
        "outcomes": outcomes,
    }


# ----------------------------------------------------------------------------------------
# The record the lineage produces for itself, and the policy it derives from it.
# ----------------------------------------------------------------------------------------


def record_episode(
    consumer_state: dict[str, Any],
    world: dict[str, Any],
    target: Iterable[int],
    max_nodes: int = MAX_EXPRESSION_NODES,
) -> dict[str, Any]:
    """A learning-phase observation: the feature row, and which component the trial says resolves it."""
    wanted = tuple(int(value) for value in target)
    trial = consumer.component_trial(consumer_state, world, wanted, max_nodes)
    features = consumer.failure_features(consumer_state, world, wanted, max_nodes)
    payload = {
        "schema": EPISODE_SCHEMA,
        "target": list(wanted),
        "world_digest": world["world_digest"],
        "state_digest": consumer_state["state_digest"],
        "features": features,
        "component": trial["component"],
        "usable": bool(trial["determined"]),
        "label_source": "consumer_component_trial",
    }
    payload["episode_digest"] = digest(payload)
    return payload


def undetermined_rows(episodes: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Rows the lineage's own record shows resolving through more than one component."""
    seen: dict[int, set[str]] = {}
    for item in episodes:
        if not item.get("usable"):
            continue
        seen.setdefault(item["features"]["row_index"], set()).add(item["component"])
    return {
        "schema": "m111-undetermined-rows-v1",
        "observed_rows": sorted(seen),
        "row_components": {str(row): sorted(found) for row, found in sorted(seen.items())},
        "undetermined": sorted(row for row, found in seen.items() if len(found) > 1),
        "determined": sorted(row for row, found in seen.items() if len(found) == 1),
    }


def policy_rule_space(
    machinery_state: dict[str, Any], max_nodes: int = POLICY_NODE_BOUND
) -> dict[tuple[bool, ...], dict[str, Any]]:
    """The programs the lineage can write, in the Boolean language its machinery state holds."""
    return base.expression_image(machinery_state["operators"], FEATURE_COUNT, max_nodes)


def acquire_policy(
    state: dict[str, Any],
    episodes: Iterable[dict[str, Any]],
    *,
    register_result: bool,
    max_nodes: int = POLICY_NODE_BOUND,
) -> dict[str, Any]:
    """Derive a policy firing on the rows the record shows undetermined, and on no other observed row.

    If the language the lineage holds cannot express such a program, it says so and then looks for an
    operator that would make it expressible -- in its own candidate space. A lineage whose candidate
    space is still the monotone one finds nothing, by the monotonicity lemma, because every monotone
    program true at a lower row is true at every row above it.
    """
    current = decode_state(state)
    machinery_state = current["machinery_state"]
    survey = undetermined_rows(episodes)
    required = {row: True for row in survey["undetermined"]}
    required.update({row: False for row in survey["determined"]})

    report: dict[str, Any] = {
        "schema": "m111-policy-acquisition-v1",
        "generation": len(machinery_state["rules"]) + 1,
        "episode_count": sum(1 for item in episodes if item.get("usable")),
        "row_components": survey["row_components"],
        "undetermined_rows": survey["undetermined"],
        "determined_rows": survey["determined"],
        "required_rows": {str(row): value for row, value in sorted(required.items())},
        "labels_are_lineage_determined": True,
        "candidate_space": machinery_state["candidate_space"],
    }
    if not survey["undetermined"]:
        report["confirmed"] = False
        report["reason"] = "the_record_shows_no_undetermined_row"
        return report

    def consistent(space: dict[tuple[bool, ...], dict[str, Any]]) -> dict[tuple[bool, ...], Any]:
        return {
            table: node
            for table, node in space.items()
            if all(bool(table[row]) is value for row, value in required.items())
        }

    held_space = policy_rule_space(machinery_state, max_nodes)
    held_consistent = consistent(held_space)
    report["rule_space_size_before"] = len(held_space)
    report["consistent_in_held_language"] = len(held_consistent)
    report["expressible_in_held_language"] = bool(held_consistent)

    adopted_operator = None
    space = held_space
    survivors = held_consistent
    if not held_consistent:
        report["blocked_reason"] = "no_expressible_policy_in_the_held_language"
        # The lineage looks for an operator that would make it expressible, in its own space.
        for candidate in machinery.candidate_operators(machinery_state["candidate_space"]):
            named = expr.operator_definition(
                "POLICY_%s" % candidate["operator_id"][-8:],
                candidate["arity"],
                candidate["truth_table"],
            )
            extended = machinery.create_state(
                machinery_state["operators"] + [named],
                signal_width=machinery_state["signal_width"],
                candidate_space=machinery_state["candidate_space"],
                rules=machinery_state["rules"],
            )
            trial_space = policy_rule_space(extended, max_nodes)
            trial_consistent = consistent(trial_space)
            if trial_consistent:
                adopted_operator = named
                machinery_state = extended
                space = trial_space
                survivors = trial_consistent
                break
        report["operator_search_examined"] = len(
            machinery.candidate_operators(machinery_state["candidate_space"])
        )
        report["operator_adopted_to_make_it_expressible"] = adopted_operator is not None
        if adopted_operator is not None:
            report["adopted_operator"] = adopted_operator
            report["adopted_operator_is_monotone"] = expr._operator_is_monotone(adopted_operator)

    report["rule_space_size_after"] = len(space)
    report["consistent_policy_count"] = len(survivors)
    if not survivors:
        report["confirmed"] = False
        report["reason"] = "no_expressible_policy_and_no_operator_makes_one_expressible"
        return report

    canonical = min(
        survivors,
        key=lambda table: (base.node_count(survivors[table]), canonical_json(survivors[table])),
    )
    policy = diagnostic_policy(
        survivors[canonical], canonical, len(machinery_state["rules"]) + 1
    )
    report["confirmed"] = True
    report["adopted_policy"] = policy
    report["policy_fires_on"] = [
        index for index, value in enumerate(policy["truth_table"]) if value
    ]
    report["registered"] = bool(register_result)
    if register_result:
        report["next_state"] = create_state(
            machinery_state,
            current["consumer_state"],
            policy=policy,
            probe_budget=current["probe_budget"],
        )
    return report


# ----------------------------------------------------------------------------------------
# The exhibit: two demands, one feature row, two different answers.
# ----------------------------------------------------------------------------------------


def base_state_survey(
    world: dict[str, Any], max_nodes: int = MAX_EXPRESSION_NODES
) -> dict[str, Any]:
    """Which rows arise at the base state, and which of them carry more than one component.

    The demands are posed at the base state, so base-state structure is what admission needs. The
    full four-state census still runs inside the experiment and is what P6 is computed from; this is
    a cheaper view of the same trial, not a different one.
    """
    state = consumer.create_state()
    image = consumer.state_image(state, world, max_nodes)
    labels: dict[int, set[str]] = {}
    counts: dict[int, int] = {}
    least: dict[int, tuple[int, ...]] = {}
    for values in itertools.product(consumer.VALUES, repeat=consumer.DOCUMENT_COUNT):
        if values in image:
            continue
        trial = consumer.component_trial(state, world, values, max_nodes)
        if not trial["determined"]:
            continue
        row = consumer.failure_features(state, world, values, max_nodes)["row_index"]
        labels.setdefault(row, set()).add(trial["component"])
        counts[row] = counts.get(row, 0) + 1
        if row not in least or values < least[row]:
            least[row] = values
    return {
        "schema": "m111-base-state-survey-v1",
        "rows": sorted(labels),
        "ambiguous_rows": sorted(row for row, found in labels.items() if len(found) > 1),
        "determined_rows": sorted(row for row, found in labels.items() if len(found) == 1),
        "row_counts": {str(row): counts[row] for row in sorted(counts)},
        "least_targets": {str(row): list(least[row]) for row in sorted(least)},
    }


def ambiguous_pair(
    world: dict[str, Any], row: int = 3, max_nodes: int = MAX_EXPRESSION_NODES
) -> dict[str, Any] | None:
    """The two least targets at `row` that resolve through different components, if they exist.

    This is the whole impossibility argument, and it is an exhibit rather than an argument: the two
    demands present the machinery with the identical observation and have different answers, so no
    function of that observation is right on both. Found by the consumer's own trial; nothing here
    reads a rule, a policy or an arm.
    """
    state = consumer.create_state()
    image = consumer.state_image(state, world, max_nodes)
    by_component: dict[str, list[tuple[int, ...]]] = {}
    for values in itertools.product(consumer.VALUES, repeat=consumer.DOCUMENT_COUNT):
        if values in image:
            continue
        trial = consumer.component_trial(state, world, values, max_nodes)
        if not trial["determined"]:
            continue
        if consumer.failure_features(state, world, values, max_nodes)["row_index"] != row:
            continue
        by_component.setdefault(trial["component"], []).append(values)
    if len(by_component) < 2:
        return None
    ordered = sorted(by_component)
    targets = {name: list(sorted(by_component[name])[0]) for name in ordered}
    rows = {
        name: consumer.failure_features(state, world, values, max_nodes)["row_index"]
        for name, values in targets.items()
    }
    return {
        "schema": "m111-ambiguous-pair-v1",
        "row": row,
        "components": ordered,
        "targets": targets,
        "counts": {name: len(by_component[name]) for name in ordered},
        "feature_rows": rows,
        "same_feature_row": len(set(rows.values())) == 1,
        "different_components": len(set(ordered)) > 1,
        "world_digest": world["world_digest"],
    }


# ----------------------------------------------------------------------------------------
# The lemma that makes generation 3 depend on generation 2.
# ----------------------------------------------------------------------------------------


def expressibility_certificate(
    machinery_state: dict[str, Any], lower_row: int, upper_row: int,
    max_nodes: int = POLICY_NODE_BOUND
) -> dict[str, Any]:
    """No monotone program fires at a lower feature row without firing at every row above it."""
    lower = FEATURE_ROWS[lower_row]
    upper = FEATURE_ROWS[upper_row]
    space = policy_rule_space(machinery_state, max_nodes)
    separating = [table for table in space if table[lower_row] and not table[upper_row]]
    monotone_candidates = machinery.candidate_operators(MONOTONE_SPACE)
    complete_candidates = machinery.candidate_operators(COMPLETE_SPACE)
    certificate = {
        "schema": "m111-expressibility-v1",
        "lower_row": lower_row,
        "upper_row": upper_row,
        "lower_below_upper_componentwise": all(
            (not a) or b for a, b in zip(lower, upper)
        ),
        "held_operator_names": sorted(item["name"] for item in machinery_state["operators"]),
        "every_held_operator_is_monotone": all(
            expr._operator_is_monotone(item) for item in machinery_state["operators"]
        ),
        "rule_space_size": len(space),
        "separating_program_count": len(separating),
        "monotone_candidate_count": len(monotone_candidates),
        "complete_candidate_count": len(complete_candidates),
        "non_monotone_in_monotone_space": sum(
            0 if expr._operator_is_monotone(item) else 1 for item in monotone_candidates
        ),
        "non_monotone_in_complete_space": sum(
            0 if expr._operator_is_monotone(item) else 1 for item in complete_candidates
        ),
        "max_nodes": max_nodes,
    }
    certificate["separable_in_the_held_language"] = bool(separating)
    certificate["closed_by_monotonicity_lemma"] = bool(
        certificate["lower_below_upper_componentwise"]
        and certificate["every_held_operator_is_monotone"]
        and not separating
    )
    certificate["confirmed"] = certificate["closed_by_monotonicity_lemma"]
    return certificate
