"""M109 - two successive machinery generations over a self-determined blame record.

M108 qualified one lineage-acquired modification of the acquisition machinery, with authored blame
labels and a single generation. M109 removes both limits:

- a **third registered component**, the candidate space, makes a second generation possible. A
  candidate space restricted to the monotone operators is closed: every operator table reachable
  through it keeps the image monotone, so a non-monotone demand is excluded from the operator axis by
  the same lemma M107 and M108 used, at every node bound. Widening the candidate space is therefore a
  machinery act structurally distinct from extending the operator table.

- the blame label is **not authored**. After a demand is resolved or abandoned the lineage may enter a
  learning phase and run a controlled trial on itself: extend each registered component in turn and
  observe which extension makes that demand constructible. The label is the outcome of that trial.
  Trials are forbidden at resolution time, where the machinery holds one step and must attribute
  without them -- which is the whole reason an attribution rule is worth acquiring.

Rules form an ordered **cascade**: each acquired rule is consulted in adoption order and the first to
fire selects its component; if none fires the hardwired operator axis applies. The cascade is what
keeps every rule monotone and therefore expressible in the language the lineage actually holds at the
moment it acquires it -- M109 claims no expressibility barrier, only that the *evidence* determining
the second rule lies in a history the first rule made possible.

The expression substrate is imported unchanged from `m108_runtime`, which imports `m107_runtime`
unchanged in turn. A fork at any level would end the chain.
"""

from __future__ import annotations

import itertools
import json
from typing import Any, Iterable

from metamorphosis import m107_runtime as expr
from metamorphosis import m108_runtime as base

STATE_SCHEMA = "m109-machinery-state-v1"
RULE_SCHEMA = "m109-attribution-rule-v1"
EPISODE_SCHEMA = "m109-trial-episode-v1"
DEMAND_SCHEMA = base.DEMAND_SCHEMA

COMPONENT_OPERATORS = base.COMPONENT_OPERATORS
COMPONENT_SIGNALS = base.COMPONENT_SIGNALS
COMPONENT_CANDIDATES = "candidate_space"
COMPONENTS = (COMPONENT_OPERATORS, COMPONENT_SIGNALS, COMPONENT_CANDIDATES)

MONOTONE_SPACE = "monotone"
COMPLETE_SPACE = "complete"
CANDIDATE_SPACES = (MONOTONE_SPACE, COMPLETE_SPACE)

WORLD_SIGNAL_WIDTH = base.WORLD_SIGNAL_WIDTH
BASE_SIGNAL_WIDTH = base.BASE_SIGNAL_WIDTH
MAX_SIGNAL_WIDTH = base.MAX_SIGNAL_WIDTH
MAX_EXPRESSION_NODES = base.MAX_EXPRESSION_NODES

# A lineage may extend a registered component; it may never extend the registry, raise a bound, or
# grant itself authority. These ceilings are part of the claim.
MAX_MACHINERY_GENERATIONS = 2
MACHINERY_STEP_BUDGET = 1

# Failure features, in a fixed order. Rules are programs over exactly these.
#   g0 - the demand needs a signal the interface cannot read
#   g1 - the candidate search for this demand exhausted without success
#   g2 - some candidate strictly enlarges reach (demand-independent; a deliberate distractor,
#        true on every row reachable while attributing, so no rule can lean on it)
FEATURE_NAMES = (
    "demand_needs_an_unread_signal",
    "candidate_search_exhausted_for_this_demand",
    "operator_axis_progress_available",
)
FEATURE_COUNT = len(FEATURE_NAMES)
FEATURE_ROWS: tuple[tuple[bool, ...], ...] = tuple(
    tuple(row) for row in itertools.product((False, True), repeat=FEATURE_COUNT)
)

canonical_json = base.canonical_json
digest = base.digest
sha256_bytes = base.sha256_bytes
world_rows = base.world_rows
depends_on_signal = base.depends_on_signal
lift = base.lift
liftable_images = base.liftable_images
expression_image = base.expression_image
is_monotone = base.is_monotone
capability_demand = base.capability_demand
demand_target = base.demand_target
decode_demand = base.decode_demand
node_count = base.node_count


# ----------------------------------------------------------------------------------------
# The candidate space, and the lemma that makes the monotone one closed.
# ----------------------------------------------------------------------------------------


def candidate_operators(space: str) -> list[dict[str, Any]]:
    if space not in CANDIDATE_SPACES:
        raise ValueError("M109 candidate space is outside the authored registry")
    everything = expr.operator_space()
    if space == COMPLETE_SPACE:
        return everything
    return [item for item in everything if expr._operator_is_monotone(item)]


def _named(candidate: dict[str, Any]) -> dict[str, Any]:
    return expr.operator_definition(
        "ACQUIRED_%s" % candidate["operator_id"][-8:],
        candidate["arity"],
        candidate["truth_table"],
    )


def candidate_space_closure_certificate(
    operators: Iterable[dict[str, Any]],
    width: int,
    space: str = MONOTONE_SPACE,
    max_nodes: int = MAX_EXPRESSION_NODES,
) -> dict[str, Any]:
    """The monotone candidate space is closed: nothing reachable through it is non-monotone."""
    held = list(operators)
    reachable: set[tuple[bool, ...]] = set(
        lift(table, width) if width < WORLD_SIGNAL_WIDTH else table
        for table in expression_image(held, width, max_nodes)
    )
    for candidate in candidate_operators(space):
        extended = held + [_named(candidate)]
        reachable |= {
            lift(table, width) if width < WORLD_SIGNAL_WIDTH else table
            for table in expression_image(extended, width, max_nodes)
        }
    all_candidates_monotone = all(
        expr._operator_is_monotone(item) for item in candidate_operators(space)
    )
    all_held_monotone = all(expr._operator_is_monotone(item) for item in held)
    reachable_all_monotone = all(is_monotone(table, WORLD_SIGNAL_WIDTH) for table in reachable)
    certificate = {
        "schema": "m109-candidate-closure-v1",
        "space": space,
        "width": width,
        "max_nodes": max_nodes,
        "candidate_count": len(candidate_operators(space)),
        "reachable_count": len(reachable),
        "every_held_operator_is_monotone": all_held_monotone,
        "every_candidate_is_monotone": all_candidates_monotone,
        "everything_reachable_is_monotone": reachable_all_monotone,
        "closed_by_monotonicity_lemma": bool(
            all_held_monotone and all_candidates_monotone and reachable_all_monotone
        ),
        "budget_independent": bool(
            all_held_monotone and all_candidates_monotone and reachable_all_monotone
        ),
    }
    certificate["confirmed"] = certificate["closed_by_monotonicity_lemma"]
    return certificate


# ----------------------------------------------------------------------------------------
# Lineage state: operator table, signal interface, candidate space, rule cascade.
# ----------------------------------------------------------------------------------------


def attribution_rule(
    body: dict[str, Any], table: Iterable[bool], component: str, generation: int
) -> dict[str, Any]:
    rows = [bool(value) for value in table]
    if len(rows) != 2 ** FEATURE_COUNT:
        raise ValueError("M109 rule truth table has the wrong length")
    if component not in COMPONENTS:
        raise ValueError("M109 rule targets a component outside the registry")
    payload: dict[str, Any] = {
        "schema": RULE_SCHEMA,
        "features": list(FEATURE_NAMES),
        "body": body,
        "truth_table": rows,
        "selects_component_when_true": component,
        "generation": int(generation),
    }
    payload["rule_id"] = "rule-" + digest(payload)[:16]
    return payload


def decode_rule(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict) or raw.get("schema") != RULE_SCHEMA:
        raise ValueError("M109 rule payload is invalid")
    if list(raw.get("features") or []) != list(FEATURE_NAMES):
        raise ValueError("M109 rule feature vocabulary changed")
    rebuilt = attribution_rule(
        raw.get("body"),
        raw.get("truth_table") or [],
        raw.get("selects_component_when_true"),
        raw.get("generation", 0),
    )
    if rebuilt["rule_id"] != raw.get("rule_id"):
        raise ValueError("M109 rule identity mismatch")
    return rebuilt


def create_state(
    operators: Iterable[dict[str, Any]] | None = None,
    *,
    signal_width: int = BASE_SIGNAL_WIDTH,
    candidate_space: str = MONOTONE_SPACE,
    rules: Iterable[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    width = int(signal_width)
    if width not in range(1, MAX_SIGNAL_WIDTH + 1):
        raise ValueError("M109 signal interface width is outside the authored ceiling")
    if candidate_space not in CANDIDATE_SPACES:
        raise ValueError("M109 candidate space is outside the authored registry")
    cascade = [decode_rule(item) for item in (rules or [])]
    if len(cascade) > MAX_MACHINERY_GENERATIONS:
        raise ValueError("M109 machinery generation ceiling exceeded")
    if [item["generation"] for item in cascade] != list(range(1, len(cascade) + 1)):
        raise ValueError("M109 rule cascade is not a contiguous generation sequence")
    source = list(operators) if operators is not None else expr.initial_operators()
    payload = {
        "operators": [expr.decode_operator(item) for item in source],
        "signal_width": width,
        "candidate_space": candidate_space,
        "rules": cascade,
        "component_registry": list(COMPONENTS),
    }
    return {"schema": STATE_SCHEMA, **payload, "state_digest": digest(payload)}


def decode_state(raw: bytes | str | dict[str, Any]) -> dict[str, Any]:
    if isinstance(raw, (bytes, bytearray)):
        value = json.loads(bytes(raw).decode("ascii"))
    elif isinstance(raw, str):
        value = json.loads(raw)
    else:
        value = json.loads(canonical_json(raw))
    if not isinstance(value, dict) or value.get("schema") != STATE_SCHEMA:
        raise ValueError("M109 state payload is invalid")
    if list(value.get("component_registry") or []) != list(COMPONENTS):
        raise ValueError("M109 component registry changed")
    rebuilt = create_state(
        value.get("operators") or [],
        signal_width=int(value.get("signal_width", BASE_SIGNAL_WIDTH)),
        candidate_space=value.get("candidate_space", MONOTONE_SPACE),
        rules=value.get("rules") or [],
    )
    if rebuilt["state_digest"] != value.get("state_digest"):
        raise ValueError("M109 state digest mismatch")
    return rebuilt


def encode_state(state: dict[str, Any]) -> bytes:
    return canonical_json(decode_state(state)).encode("ascii")


_IMAGE_MEMO: dict[tuple[str, int], dict[tuple[bool, ...], dict[str, Any]]] = {}


def state_image(
    state: dict[str, Any], max_nodes: int = MAX_EXPRESSION_NODES
) -> dict[tuple[bool, ...], dict[str, Any]]:
    """A pure function of (operator table, width, bound), so it is memoized by state digest."""
    key = (state["state_digest"], max_nodes)
    memo = _IMAGE_MEMO.get(key)
    if memo is None:
        width = state["signal_width"]
        memo = {
            lift(table, width) if width < WORLD_SIGNAL_WIDTH else table: node
            for table, node in expression_image(state["operators"], width, max_nodes).items()
        }
        _IMAGE_MEMO[key] = memo
    return memo


def construct(
    state: dict[str, Any], target: Iterable[bool], max_nodes: int = MAX_EXPRESSION_NODES
) -> dict[str, Any]:
    wanted = tuple(bool(value) for value in target)
    image = state_image(state, max_nodes)
    witness = image.get(wanted)
    report: dict[str, Any] = {
        "target": list(wanted),
        "constructible": witness is not None,
        "image_size": len(image),
        "signal_width": state["signal_width"],
        "candidate_space": state["candidate_space"],
        "witness": witness,
        "witness_nodes": node_count(witness) if witness else None,
        "executes_to_target": False,
    }
    if witness is not None:
        table = {item["name"]: item for item in state["operators"]}
        replay = tuple(
            base.execute_expression(table, witness, row[: state["signal_width"]])
            for row in world_rows()
        )
        report["executes_to_target"] = replay == wanted
    return report


# ----------------------------------------------------------------------------------------
# Extending a registered component. Three axes, each with its own structural character.
# ----------------------------------------------------------------------------------------


_ONE_STEP_MEMO: dict[tuple[str, int], dict[tuple[bool, ...], dict[str, Any]]] = {}


def _one_step_operator_reach(
    state: dict[str, Any], max_nodes: int = MAX_EXPRESSION_NODES
) -> dict[tuple[bool, ...], dict[str, Any]]:
    """Every world table one candidate addition can reach, and a witness state for each.

    Demand-independent, so it is computed once per state rather than once per demand. Candidates are
    visited in the canonical order of the authored space, so the witness state is deterministic.
    """
    key = (state["state_digest"], max_nodes)
    memo = _ONE_STEP_MEMO.get(key)
    if memo is not None:
        return memo
    memo = {}
    for candidate in candidate_operators(state["candidate_space"]):
        extended = create_state(
            state["operators"] + [_named(candidate)],
            signal_width=state["signal_width"],
            candidate_space=state["candidate_space"],
            rules=state["rules"],
        )
        for table in state_image(extended, max_nodes):
            memo.setdefault(table, extended)
    _ONE_STEP_MEMO[key] = memo
    return memo


def extend_operator_table(
    state: dict[str, Any], target: Iterable[bool], max_nodes: int = MAX_EXPRESSION_NODES
) -> dict[str, Any]:
    """Search the current candidate space for an operator that makes the target constructible."""
    wanted = tuple(bool(value) for value in target)
    space = candidate_operators(state["candidate_space"])
    reach = _one_step_operator_reach(state, max_nodes)
    extended = reach.get(wanted)
    if extended is not None:
        return {
            "confirmed": True,
            "component": COMPONENT_OPERATORS,
            "candidate_space_size": len(space),
            "candidate_space_exhausted": False,
            "next_state": extended,
        }
    return {
        "confirmed": False,
        "component": COMPONENT_OPERATORS,
        "reason": "candidate_space_exhausted_for_this_demand",
        "candidate_space_size": len(space),
        "candidate_space_exhausted": True,
    }


def extend_signal_interface(state: dict[str, Any]) -> dict[str, Any]:
    width = state["signal_width"] + 1
    if width > MAX_SIGNAL_WIDTH:
        return {
            "confirmed": False,
            "component": COMPONENT_SIGNALS,
            "reason": "signal_interface_ceiling_reached",
        }
    return {
        "confirmed": True,
        "component": COMPONENT_SIGNALS,
        "signal_width": width,
        "next_state": create_state(
            state["operators"],
            signal_width=width,
            candidate_space=state["candidate_space"],
            rules=state["rules"],
        ),
    }


def widen_candidate_space(state: dict[str, Any]) -> dict[str, Any]:
    if state["candidate_space"] == COMPLETE_SPACE:
        return {
            "confirmed": False,
            "component": COMPONENT_CANDIDATES,
            "reason": "candidate_space_ceiling_reached",
        }
    return {
        "confirmed": True,
        "component": COMPONENT_CANDIDATES,
        "candidate_space": COMPLETE_SPACE,
        "next_state": create_state(
            state["operators"],
            signal_width=state["signal_width"],
            candidate_space=COMPLETE_SPACE,
            rules=state["rules"],
        ),
    }


def _widened_then_extended(
    state: dict[str, Any], target: Iterable[bool], max_nodes: int
) -> dict[str, Any] | None:
    """Widening the candidate space only helps through the operator search it unlocks."""
    widened = widen_candidate_space(state)
    if not widened["confirmed"]:
        return None
    found = extend_operator_table(widened["next_state"], target, max_nodes)
    return found["next_state"] if found["confirmed"] else None


# ----------------------------------------------------------------------------------------
# The trial: the lineage determines the blame label by experiment on itself.
# ----------------------------------------------------------------------------------------


def component_trial(
    state: dict[str, Any], demand: dict[str, Any], max_nodes: int = MAX_EXPRESSION_NODES
) -> dict[str, Any]:
    """Extend each registered component in turn and record which one resolves this demand.

    The procedure is identical for every component and reads no host annotation. A demand that more
    than one component resolves is unusable as evidence and is reported as such rather than assigned.
    """
    wanted = demand_target(demand)
    outcomes: dict[str, bool] = {}

    found = extend_operator_table(state, wanted, max_nodes)
    outcomes[COMPONENT_OPERATORS] = bool(found["confirmed"])

    widened = extend_signal_interface(state)
    outcomes[COMPONENT_SIGNALS] = bool(
        widened["confirmed"] and construct(widened["next_state"], wanted, max_nodes)["constructible"]
    )

    reached = _widened_then_extended(state, wanted, max_nodes)
    outcomes[COMPONENT_CANDIDATES] = bool(reached is not None) and not outcomes[COMPONENT_OPERATORS]

    resolving = sorted(name for name, ok in outcomes.items() if ok)
    return {
        "schema": "m109-component-trial-v1",
        "outcomes": outcomes,
        "resolving_components": resolving,
        "determined": len(resolving) == 1,
        "component": resolving[0] if len(resolving) == 1 else None,
        "label_source": "lineage_component_trial",
    }


# ----------------------------------------------------------------------------------------
# Failure features and the ordered attribution cascade.
# ----------------------------------------------------------------------------------------


def failure_features(
    state: dict[str, Any], demand: dict[str, Any], max_nodes: int = MAX_EXPRESSION_NODES
) -> dict[str, Any]:
    wanted = demand_target(demand)
    width = state["signal_width"]
    g0 = any(depends_on_signal(wanted, index) for index in range(width, WORLD_SIGNAL_WIDTH))
    g1 = not extend_operator_table(state, wanted, max_nodes)["confirmed"]
    held = set(state_image(state, max_nodes))
    g2 = bool(set(_one_step_operator_reach(state, max_nodes)) - held)
    values = (bool(g0), bool(g1), bool(g2))
    return {
        "schema": "m109-failure-features-v1",
        "features": list(FEATURE_NAMES),
        "values": [bool(value) for value in values],
        "row_index": FEATURE_ROWS.index(values),
    }


def attribute(state: dict[str, Any], features: dict[str, Any]) -> dict[str, Any]:
    """Ordered cascade: the first acquired rule that fires selects its component."""
    row = features["row_index"]
    for rule in state["rules"]:
        if bool(rule["truth_table"][row]):
            return {
                "component": rule["selects_component_when_true"],
                "mode": "state_held_rule",
                "rule_id": rule["rule_id"],
                "generation": rule["generation"],
            }
    return {
        "component": COMPONENT_OPERATORS,
        "mode": "hardwired_operator_axis",
        "rule_id": None,
        "generation": 0,
    }


# ----------------------------------------------------------------------------------------
# Episodes the lineage records for itself, and the rule it derives from them.
# ----------------------------------------------------------------------------------------


def record_episode(
    state: dict[str, Any], demand: dict[str, Any], max_nodes: int = MAX_EXPRESSION_NODES
) -> dict[str, Any]:
    """A learning-phase observation: the state in force, the features, and the trial outcome."""
    trial = component_trial(state, demand, max_nodes)
    features = failure_features(state, demand, max_nodes)
    payload: dict[str, Any] = {
        "schema": EPISODE_SCHEMA,
        "demand_digest": demand["demand_digest"],
        "state_digest": state["state_digest"],
        "signal_width": state["signal_width"],
        "candidate_space": state["candidate_space"],
        "features": features,
        "trial": trial,
        "component": trial["component"],
        "usable": bool(trial["determined"]),
    }
    payload["episode_digest"] = digest(payload)
    return payload


def attribution_domain(
    states: Iterable[dict[str, Any]], max_nodes: int = MAX_EXPRESSION_NODES
) -> dict[str, Any]:
    """Which feature rows can arise while attributing, over every state and every world function."""
    witnesses: dict[int, dict[str, Any]] = {}
    ambiguous: list[int] = []
    labels: dict[int, set[str]] = {}
    examined = 0
    for state in states:
        image = state_image(state, max_nodes)
        for table in itertools.product((False, True), repeat=2 ** WORLD_SIGNAL_WIDTH):
            target = tuple(table)
            if target in image:
                continue
            demand = capability_demand("domain-probe", target)
            trial = component_trial(state, demand, max_nodes)
            if not trial["determined"]:
                continue
            examined += 1
            row = failure_features(state, demand, max_nodes)["row_index"]
            labels.setdefault(row, set()).add(trial["component"])
            witnesses.setdefault(
                row,
                {
                    "row_index": row,
                    "values": list(FEATURE_ROWS[row]),
                    "signal_width": state["signal_width"],
                    "candidate_space": state["candidate_space"],
                    "component": trial["component"],
                },
            )
    for row, found in labels.items():
        if len(found) > 1:
            ambiguous.append(row)
    return {
        "schema": "m109-attribution-domain-v1",
        "rows": sorted(witnesses),
        "unreachable_rows": [row for row in range(len(FEATURE_ROWS)) if row not in witnesses],
        "ambiguous_rows": sorted(ambiguous),
        "row_labels": {str(row): sorted(found) for row, found in sorted(labels.items())},
        "determined_pairs_examined": examined,
        "census_complete": True,
        "witnesses": [witnesses[row] for row in sorted(witnesses)],
    }


def acquire_rule(
    state: dict[str, Any],
    episodes: Iterable[dict[str, Any]],
    domain: dict[str, Any],
    *,
    register_result: bool,
    max_nodes: int = MAX_EXPRESSION_NODES,
) -> dict[str, Any]:
    """Derive the next cascade rule from the episodes the current cascade does not already cover.

    The candidate space is `expression_image(state operators)` over the feature signals -- the
    language the lineage itself holds, not a host-supplied menu.
    """
    usable = [item for item in episodes if item.get("usable")]
    uncovered = [
        item
        for item in usable
        if attribute(state, item["features"])["mode"] == "hardwired_operator_axis"
    ]
    positives = sorted({item["component"] for item in uncovered} - {COMPONENT_OPERATORS})
    report: dict[str, Any] = {
        "schema": "m109-rule-acquisition-v1",
        "generation": len(state["rules"]) + 1,
        "episode_count": len(usable),
        "uncovered_episode_count": len(uncovered),
        "candidate_components": positives,
        "labels_are_lineage_determined": all(
            item["trial"]["label_source"] == "lineage_component_trial" for item in usable
        ),
    }
    if len(state["rules"]) >= MAX_MACHINERY_GENERATIONS:
        report["confirmed"] = False
        report["reason"] = "machinery_generation_ceiling_reached"
        return report
    if len(positives) != 1:
        report["confirmed"] = False
        report["reason"] = (
            "no_uncovered_component_to_attribute"
            if not positives
            else "uncovered_episodes_name_more_than_one_component"
        )
        return report

    component = positives[0]
    observed: dict[int, bool] = {}
    for item in uncovered:
        row = item["features"]["row_index"]
        fires = item["component"] == component
        if observed.setdefault(row, fires) != fires:
            report["confirmed"] = False
            report["reason"] = "trial_record_is_contradictory"
            return report

    # Conservatism: a rule may fire only where the lineage has positive evidence. A relevant row it
    # has never observed is required NOT to fire, so an acquisition can never reach past its own
    # record -- which is also what leaves the later rows available to a later generation.
    relevant = [row for row in domain["rows"] if row not in _covered_rows(state)]
    required = {row: bool(observed.get(row, False)) for row in relevant}
    space = expression_image(state["operators"], FEATURE_COUNT, max_nodes)
    consistent = {
        table: node
        for table, node in space.items()
        if all(bool(table[row]) is value for row, value in required.items())
    }
    classes: dict[tuple[bool, ...], list[tuple[bool, ...]]] = {}
    for table in consistent:
        classes.setdefault(tuple(bool(table[row]) for row in relevant), []).append(table)

    report.update(
        {
            "selected_component": component,
            "observed_feature_rows": sorted(observed),
            "relevant_domain_rows": relevant,
            "unobserved_relevant_rows_held_non_firing": sorted(set(relevant) - set(observed)),
            "adoption_is_conservative": True,
            "rule_space_size": len(space),
            "rule_space_exhausted": True,
            "consistent_rule_count": len(consistent),
            "surviving_rule_classes": len(classes),
        }
    )
    if not consistent:
        report["confirmed"] = False
        report["reason"] = "no_expressible_rule_reproduces_the_trial_record"
        return report
    if len(classes) != 1:
        report["confirmed"] = False
        report["reason"] = "rule_underdetermined_by_the_trial_record"
        return report

    canonical = min(
        consistent,
        key=lambda table: (node_count(consistent[table]), canonical_json(consistent[table])),
    )
    rule = attribution_rule(
        consistent[canonical], canonical, component, len(state["rules"]) + 1
    )
    report["confirmed"] = True
    report["adopted_rule"] = rule
    report["registered"] = bool(register_result)
    if register_result:
        report["next_state"] = create_state(
            state["operators"],
            signal_width=state["signal_width"],
            candidate_space=state["candidate_space"],
            rules=list(state["rules"]) + [rule],
        )
    return report


def _covered_rows(state: dict[str, Any]) -> list[int]:
    return [
        row
        for row in range(len(FEATURE_ROWS))
        if any(bool(rule["truth_table"][row]) for rule in state["rules"])
    ]


# ----------------------------------------------------------------------------------------
# Resolution: one machinery step, no trial.
# ----------------------------------------------------------------------------------------


def resolve(
    state: dict[str, Any], demand: dict[str, Any], max_nodes: int = MAX_EXPRESSION_NODES
) -> dict[str, Any]:
    """One machinery step. Attribution decides which component is extended; no trial is permitted."""
    decoded = decode_demand(demand)
    wanted = demand_target(decoded)
    current = decode_state(state)
    trace: list[dict[str, Any]] = []
    for step in range(MACHINERY_STEP_BUDGET + 1):
        built = construct(current, wanted, max_nodes)
        if built["constructible"]:
            return {
                "schema": "m109-resolution-v1",
                "confirmed": True,
                "steps": step,
                "trace": trace,
                "construction": built,
                "final_signal_width": current["signal_width"],
                "final_candidate_space": current["candidate_space"],
                "final_state_digest": current["state_digest"],
                "trials_performed": 0,
            }
        if step == MACHINERY_STEP_BUDGET:
            break
        features = failure_features(current, decoded, max_nodes)
        blame = attribute(current, features)
        if blame["component"] == COMPONENT_SIGNALS:
            extension = extend_signal_interface(current)
        elif blame["component"] == COMPONENT_CANDIDATES:
            widened = widen_candidate_space(current)
            extension = (
                extend_operator_table(widened["next_state"], wanted, max_nodes)
                if widened["confirmed"]
                else widened
            )
            if extension.get("confirmed"):
                extension = dict(extension)
                extension["component"] = COMPONENT_CANDIDATES
        else:
            extension = extend_operator_table(current, wanted, max_nodes)
        entry = {
            "step": step,
            "features": features,
            "attribution": blame,
            "extension": {k: v for k, v in extension.items() if k != "next_state"},
            "reach_before": built["image_size"],
        }
        if extension.get("confirmed"):
            entry["reach_after"] = len(state_image(extension["next_state"], max_nodes))
            entry["reach_strictly_grew"] = entry["reach_after"] > entry["reach_before"]
        trace.append(entry)
        if not extension.get("confirmed"):
            return {
                "schema": "m109-resolution-v1",
                "confirmed": False,
                "reason": extension.get("reason", "extension_refused"),
                "steps": step + 1,
                "trace": trace,
                "construction": built,
                "final_signal_width": current["signal_width"],
                "final_candidate_space": current["candidate_space"],
                "final_state_digest": current["state_digest"],
                "trials_performed": 0,
            }
        current = extension["next_state"]
    return {
        "schema": "m109-resolution-v1",
        "confirmed": False,
        "reason": "machinery_step_budget_reached",
        "steps": MACHINERY_STEP_BUDGET,
        "trace": trace,
        "construction": construct(current, wanted, max_nodes),
        "final_signal_width": current["signal_width"],
        "final_candidate_space": current["candidate_space"],
        "final_state_digest": current["state_digest"],
        "trials_performed": 0,
    }


# ----------------------------------------------------------------------------------------
# ReachImprove: every world function a machinery can ever get the lineage to construct.
# ----------------------------------------------------------------------------------------


def reach_improve(
    state: dict[str, Any], budget: int = 2, max_nodes: int = MAX_EXPRESSION_NODES
) -> dict[str, Any]:
    """Exhaustive census over every state the machinery can reach within its budget.

    The axes available are exactly the components the cascade can name: a machinery that cannot
    attribute a failure to a component can never extend it, so that axis is closed to it.
    """
    axes = {rule["selects_component_when_true"] for rule in state["rules"]}
    axes.add(COMPONENT_OPERATORS)
    reached: set[tuple[bool, ...]] = set(state_image(state, max_nodes))
    frontier = [state]
    for _ in range(budget):
        produced: dict[str, dict[str, Any]] = {}
        for item in frontier:
            options: list[dict[str, Any]] = []
            if COMPONENT_SIGNALS in axes:
                options.append(extend_signal_interface(item))
            if COMPONENT_CANDIDATES in axes:
                options.append(widen_candidate_space(item))
            for candidate in candidate_operators(item["candidate_space"]):
                options.append(
                    {
                        "confirmed": True,
                        "next_state": create_state(
                            item["operators"] + [_named(candidate)],
                            signal_width=item["signal_width"],
                            candidate_space=item["candidate_space"],
                            rules=item["rules"],
                        ),
                    }
                )
            for option in options:
                if not option.get("confirmed"):
                    continue
                following = option["next_state"]
                image = state_image(following, max_nodes)
                reached |= set(image)
                produced.setdefault(following["state_digest"], following)
        frontier = list(produced.values())
    return {
        "schema": "m109-reach-improve-v1",
        "budget": budget,
        "axes": sorted(axes),
        "size": len(reached),
        "tables": sorted("".join("1" if bit else "0" for bit in table) for table in reached),
    }
