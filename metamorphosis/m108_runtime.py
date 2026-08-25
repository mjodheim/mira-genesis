"""M108 - the acquisition machinery itself, held as lineage state.

M107 qualified an endogenous extension of the lower *interpreter*: an acquisition changed what the
lineage could express, taking `complete_image` from four of sixteen to sixteen. Recursive depth was
zero, because the machinery that performs acquisitions -- the search, the adoption rule, the
candidate space and above all the **attribution of failure** -- was authored and fixed.

M108 moves one level down. Two extensible components are registered from the start:

- the **operator table** the interpreter applies (the component M107 could extend);
- the **signal interface**, which inputs an expression is permitted to read.

The hardwired machinery blames the operator table for every failure. That is true about the operator
axis and useless about the failure: no operator, at any arity or budget, can make an expression
depend on a signal the interface does not read.

The corrected machinery holds its **attribution rule as lineage state**, expressed as a program in
the very language the interpreter runs, over failure features rather than task signals. Every rule
consistent with the attribution episodes is non-monotone, so a lineage still holding only the
monotone fragment cannot express its own corrected attribution rule at all. Generation 1 is a
provable precondition for generation 2, and the proof is a lemma rather than a failed search.

The expression substrate is imported unchanged from `m107_runtime`. That is deliberate: the
mechanism M107 qualified is the mechanism M108 builds on, and a fork would end the chain. M108's
enumerator generalizes M107's to a wider signal interface; `interpreter_equivalence_certificate`
proves the two agree exactly at M107's width, so the generalization is not a second interpreter.

Nothing in this module names negation, attribution polarity, or any specific target. Operators,
rules and demands are data.
"""

from __future__ import annotations

import hashlib
import itertools
import json
from typing import Any, Iterable

from metamorphosis import m107_runtime as expr

STATE_SCHEMA = "m108-machinery-state-v1"
ATTRIBUTION_SCHEMA = "m108-attribution-rule-v1"
EPISODE_SCHEMA = "m108-attribution-episode-v1"
DEMAND_SCHEMA = "m108-capability-demand-v1"

# The registry of extensible machinery components. Both exist from the start; what a lineage may
# lack is the ability to attribute a failure to the right one.
COMPONENT_OPERATORS = "operator_table"
COMPONENT_SIGNALS = "signal_interface"
COMPONENTS = (COMPONENT_OPERATORS, COMPONENT_SIGNALS)

BASE_SIGNAL_WIDTH = 2
WORLD_SIGNAL_WIDTH = 3
MAX_EXPRESSION_NODES = expr.MAX_EXPRESSION_NODES

# A lineage may extend a component; it may never extend the registry, raise its own bounds, or grant
# itself further authority. These ceilings are part of the claim, not an obstacle to it.
MAX_SIGNAL_WIDTH = WORLD_SIGNAL_WIDTH
MAX_MACHINERY_STEPS = 2

# Failure features, in a fixed order. The attribution rule is a program over exactly these.
#   f0 - extending the operator table would strictly enlarge the reach of the lineage.
#   f1 - the demand behaves as a function of the signals the interface reads.
# Neither feature names a component, and neither is a relabelling of the answer: f0 is true in the
# monotone phase of the lineage own history and false once the operator table is saturated, while
# f1 is false exactly when a hidden signal drives the demand. The separating information lives in
# the NEGATION of f1, which is why a monotone lineage cannot express any consistent rule.
FEATURE_NAMES = ("operator_axis_progress_available", "demand_consistent_with_readable_signals")
FEATURE_COUNT = len(FEATURE_NAMES)
FEATURE_ROWS: tuple[tuple[bool, ...], ...] = tuple(
    tuple(row) for row in itertools.product((False, True), repeat=FEATURE_COUNT)
)


def canonical_json(value: Any) -> str:
    return expr.canonical_json(value)


def digest(value: Any) -> str:
    return expr.digest(value)


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


# ----------------------------------------------------------------------------------------
# The world, and what a narrower interface can see of it.
# ----------------------------------------------------------------------------------------


def rows_for_width(width: int) -> list[tuple[bool, ...]]:
    return [tuple(row) for row in itertools.product((False, True), repeat=width)]


def world_rows() -> list[tuple[bool, ...]]:
    return rows_for_width(WORLD_SIGNAL_WIDTH)


def depends_on_signal(table: Iterable[bool], index: int) -> bool:
    rows = world_rows()
    values = list(table)
    for position, row in enumerate(rows):
        mirror = list(row)
        mirror[index] = not mirror[index]
        if values[position] != values[rows.index(tuple(mirror))]:
            return True
    return False


def lift(narrow_table: Iterable[bool], width: int) -> tuple[bool, ...]:
    """Lift a `width`-signal function into the world; constant along every axis not read."""
    values = list(narrow_table)
    narrow = rows_for_width(width)
    return tuple(values[narrow.index(row[:width])] for row in world_rows())


def liftable_images(width: int) -> set[tuple[bool, ...]]:
    """Every world function ANY expression over the first `width` signals could ever denote."""
    return {
        lift(table, width) for table in itertools.product((False, True), repeat=2 ** width)
    }


# ----------------------------------------------------------------------------------------
# The interpreter, generalized to the interface width. It holds no operator semantics.
# ----------------------------------------------------------------------------------------


def signal_node(index: int) -> dict[str, Any]:
    return {"node": "SIGNAL", "index": int(index)}


def apply_node(operator_name: str, children: list[dict[str, Any]]) -> dict[str, Any]:
    return {"node": "APPLY", "operator": operator_name, "children": list(children)}


def node_count(expression: dict[str, Any]) -> int:
    return expr.node_count(expression)


def execute_expression(
    operators: dict[str, dict[str, Any]],
    expression: dict[str, Any],
    values: tuple[bool, ...],
) -> bool:
    if expression.get("node") == "SIGNAL":
        index = expression.get("index")
        if not isinstance(index, int) or index not in range(len(values)):
            raise ValueError("M108 signal index is outside the interface")
        return bool(values[index])
    if expression.get("node") != "APPLY":
        raise ValueError("M108 expression node is invalid")
    operator = operators.get(expression.get("operator"))
    if operator is None:
        raise ValueError("M108 operator is not in the state table")
    children = expression.get("children") or []
    if len(children) != operator["arity"]:
        raise ValueError("M108 operator arity mismatch")
    index = 0
    for child in children:
        index = (index << 1) | (1 if execute_expression(operators, child, values) else 0)
    return bool(operator["truth_table"][index])


def truth_table(
    operators: dict[str, dict[str, Any]], expression: dict[str, Any], width: int
) -> tuple[bool, ...]:
    return tuple(execute_expression(operators, expression, row) for row in rows_for_width(width))


def expression_image(
    state_operators: Iterable[dict[str, Any]],
    width: int,
    max_nodes: int = MAX_EXPRESSION_NODES,
) -> dict[tuple[bool, ...], dict[str, Any]]:
    """Exhaustive enumeration to the node bound: every function expressible at this interface.

    Witnesses are canonical: the first expression reaching a signature at the smallest node count,
    ordered by canonical JSON, so the image is a pure function of (operators, width, bound).
    """
    operators = {item["name"]: item for item in state_operators}
    by_size: dict[int, list[dict[str, Any]]] = {1: [signal_node(index) for index in range(width)]}
    reached: dict[tuple[bool, ...], dict[str, Any]] = {}
    for node in by_size[1]:
        reached.setdefault(truth_table(operators, node, width), node)
    for size in range(2, max_nodes + 1):
        produced: dict[str, dict[str, Any]] = {}
        for name in sorted(operators):
            operator = operators[name]
            for split in expr._compositions(size - 1, operator["arity"]):
                pools = [by_size.get(part, []) for part in split]
                if not all(pools):
                    continue
                for combination in itertools.product(*pools):
                    node = apply_node(name, list(combination))
                    produced[canonical_json(node)] = node
        fresh: dict[tuple[bool, ...], dict[str, Any]] = {}
        for key in sorted(produced):
            node = produced[key]
            signature = truth_table(operators, node, width)
            if signature not in reached and signature not in fresh:
                fresh[signature] = node
        by_size[size] = list(fresh.values())
        reached.update(fresh)
    return reached


def interpreter_equivalence_certificate(
    state_operators: Iterable[dict[str, Any]], max_nodes: int = MAX_EXPRESSION_NODES
) -> dict[str, Any]:
    """M108 enumerates with M107 semantics generalized -- never with a second interpreter.

    Checks that at M107's own width the two images denote exactly the same set of functions, and
    that M107's interpreter executes M108's witnesses to the same tables.
    """
    operators = list(state_operators)
    mine = expression_image(operators, expr.SIGNAL_COUNT, max_nodes)
    theirs = expr.complete_image(operators, max_nodes)
    table = expr.operator_map(operators)
    executes = True
    for signature, node in sorted(mine.items()):
        try:
            if expr.truth_table(table, node) != signature:
                executes = False
        except Exception:  # noqa: BLE001 - a divergent interpreter is the finding
            executes = False
    certificate = {
        "schema": "m108-interpreter-equivalence-v1",
        "width": expr.SIGNAL_COUNT,
        "max_nodes": max_nodes,
        "m108_image_size": len(mine),
        "m107_image_size": len(theirs),
        "images_identical": set(mine) == set(theirs),
        "m107_executes_m108_witnesses": executes,
    }
    certificate["confirmed"] = bool(
        certificate["images_identical"] and certificate["m107_executes_m108_witnesses"]
    )
    return certificate


# ----------------------------------------------------------------------------------------
# Lineage state: interpreter table, signal interface, machinery attribution rule.
# ----------------------------------------------------------------------------------------


def attribution_rule(body: dict[str, Any], table: Iterable[bool]) -> dict[str, Any]:
    rows = [bool(value) for value in table]
    if len(rows) != 2 ** FEATURE_COUNT:
        raise ValueError("M108 attribution truth table has the wrong length")
    payload: dict[str, Any] = {
        "schema": ATTRIBUTION_SCHEMA,
        "features": list(FEATURE_NAMES),
        "body": body,
        "truth_table": rows,
        "blames_when_true": COMPONENT_SIGNALS,
        "blames_when_false": COMPONENT_OPERATORS,
    }
    payload["rule_id"] = "attribution-" + digest(payload)[:16]
    return payload


def decode_attribution(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict) or raw.get("schema") != ATTRIBUTION_SCHEMA:
        raise ValueError("M108 attribution payload is invalid")
    if list(raw.get("features") or []) != list(FEATURE_NAMES):
        raise ValueError("M108 attribution feature vocabulary changed")
    rebuilt = attribution_rule(raw.get("body"), raw.get("truth_table") or [])
    if rebuilt["rule_id"] != raw.get("rule_id"):
        raise ValueError("M108 attribution identity mismatch")
    return rebuilt


def create_state(
    operators: Iterable[dict[str, Any]] | None = None,
    *,
    signal_width: int = BASE_SIGNAL_WIDTH,
    attribution: dict[str, Any] | None = None,
) -> dict[str, Any]:
    width = int(signal_width)
    if width not in range(1, MAX_SIGNAL_WIDTH + 1):
        raise ValueError("M108 signal interface width is outside the authored ceiling")
    source = list(operators) if operators is not None else expr.initial_operators()
    payload = {
        "operators": [expr.decode_operator(item) for item in source],
        "signal_width": width,
        "attribution": decode_attribution(attribution) if attribution else None,
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
        raise ValueError("M108 state payload is invalid")
    if list(value.get("component_registry") or []) != list(COMPONENTS):
        raise ValueError("M108 component registry changed")
    rebuilt = create_state(
        value.get("operators") or [],
        signal_width=int(value.get("signal_width", BASE_SIGNAL_WIDTH)),
        attribution=value.get("attribution"),
    )
    if rebuilt["state_digest"] != value.get("state_digest"):
        raise ValueError("M108 state digest mismatch")
    return rebuilt


def encode_state(state: dict[str, Any]) -> bytes:
    return canonical_json(decode_state(state)).encode("ascii")


def state_image(
    state: dict[str, Any], max_nodes: int = MAX_EXPRESSION_NODES
) -> dict[tuple[bool, ...], dict[str, Any]]:
    """The lineage's reach expressed in world terms, so states of different width compare."""
    width = state["signal_width"]
    return {
        lift(table, width): node
        for table, node in expression_image(state["operators"], width, max_nodes).items()
    }


# ----------------------------------------------------------------------------------------
# Demands, failure features, and the machinery that attributes a failure to a component.
# ----------------------------------------------------------------------------------------


def capability_demand(demand_id: str, target: Iterable[bool]) -> dict[str, Any]:
    """A demand is behavioural evidence: the world rows and what the environment answered."""
    table = [bool(value) for value in target]
    if len(table) != 2 ** WORLD_SIGNAL_WIDTH:
        raise ValueError("M108 demand target has the wrong length")
    payload: dict[str, Any] = {
        "schema": DEMAND_SCHEMA,
        "demand_id": demand_id,
        "observations": [
            {"signals": list(row), "output": table[index]}
            for index, row in enumerate(world_rows())
        ],
    }
    payload["demand_digest"] = digest(payload)
    return payload


def demand_target(demand: dict[str, Any]) -> tuple[bool, ...]:
    rows = world_rows()
    seen: dict[tuple[bool, ...], bool] = {}
    for item in demand.get("observations") or []:
        seen[tuple(bool(value) for value in item["signals"])] = bool(item["output"])
    if set(seen) != set(rows):
        raise ValueError("M108 demand does not cover the world")
    return tuple(seen[row] for row in rows)


def decode_demand(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict) or raw.get("schema") != DEMAND_SCHEMA:
        raise ValueError("M108 demand payload is invalid")
    rebuilt = capability_demand(raw.get("demand_id"), demand_target(raw))
    if rebuilt["demand_digest"] != raw.get("demand_digest"):
        raise ValueError("M108 demand identity mismatch")
    return rebuilt


def demand_consistent_with_readable_signals(demand: dict[str, Any], width: int) -> bool:
    """f1. Two observations agreeing on every readable signal must agree on the output."""
    projected: dict[tuple[bool, ...], bool] = {}
    for item in demand.get("observations") or []:
        key = tuple(bool(value) for value in item["signals"])[:width]
        output = bool(item["output"])
        if projected.setdefault(key, output) != output:
            return False
    return True


def operator_axis_progress_available(
    state: dict[str, Any], max_nodes: int = MAX_EXPRESSION_NODES
) -> bool:
    """f0. Would adding some candidate operator strictly enlarge what the lineage can express?

    A pure property of the state and the authored candidate space. It never inspects the demand,
    so it cannot smuggle the answer in.
    """
    width = state["signal_width"]
    current = len(expression_image(state["operators"], width, max_nodes))
    held = {(item["arity"], tuple(item["truth_table"])) for item in state["operators"]}
    for candidate in expr.operator_space():
        if (candidate["arity"], tuple(candidate["truth_table"])) in held:
            continue
        probe = state["operators"] + [
            expr.operator_definition(
                "PROBE_%s" % candidate["operator_id"][-8:],
                candidate["arity"],
                candidate["truth_table"],
            )
        ]
        if len(expression_image(probe, width, max_nodes)) > current:
            return True
    return False


def failure_features(
    state: dict[str, Any], demand: dict[str, Any], max_nodes: int = MAX_EXPRESSION_NODES
) -> dict[str, Any]:
    values = (
        operator_axis_progress_available(state, max_nodes),
        demand_consistent_with_readable_signals(demand, state["signal_width"]),
    )
    return {
        "schema": "m108-failure-features-v1",
        "features": list(FEATURE_NAMES),
        "values": [bool(value) for value in values],
        "row_index": FEATURE_ROWS.index(values),
    }


def attribute(state: dict[str, Any], features: dict[str, Any]) -> dict[str, Any]:
    """Which component does the machinery blame? Hardwired below; state-held once A is adopted."""
    rule = state.get("attribution")
    if rule is None:
        return {
            "component": COMPONENT_OPERATORS,
            "mode": "hardwired_operator_axis",
            "rule_id": None,
        }
    blame_signals = bool(rule["truth_table"][features["row_index"]])
    return {
        "component": COMPONENT_SIGNALS if blame_signals else COMPONENT_OPERATORS,
        "mode": "state_held_rule",
        "rule_id": rule["rule_id"],
    }


# The states a lineage in this world can occupy while an acquisition is under way. Authored, and
# declared: the attribution domain below is a census over this family, never a sample of it.
PROBE_WIDTHS = (1, 2, 3)


def probe_states() -> list[dict[str, Any]]:
    """Every (operator table, interface width) a lineage of this world can hold."""
    tables = [expr.initial_operators()]
    for candidate in expr.operator_space():
        extended = expr.initial_operators() + [
            expr.operator_definition(
                "PROBE_%s" % candidate["operator_id"][-8:],
                candidate["arity"],
                candidate["truth_table"],
            )
        ]
        tables.append(extended)
    return [
        create_state(table, signal_width=width)
        for table in tables
        for width in PROBE_WIDTHS
    ]


_DOMAIN_MEMO: dict[int, str] = {}


def attribution_domain(max_nodes: int = MAX_EXPRESSION_NODES) -> dict[str, Any]:
    """Which failure-feature rows can arise *while attributing*, over the whole state family.

    Attribution is only ever consulted on a demand the lineage could not construct. A row that no
    unconstructible demand can produce is not part of the machinery operative domain, and two rules
    differing only there are the same machinery. This is a complete census over every state of the
    family and every function of the world -- not a search.
    """
    if max_nodes in _DOMAIN_MEMO:
        return json.loads(_DOMAIN_MEMO[max_nodes])
    world = list(itertools.product((False, True), repeat=2 ** WORLD_SIGNAL_WIDTH))
    witnesses: dict[int, dict[str, Any]] = {}
    examined = 0
    for state in probe_states():
        image = state_image(state, max_nodes)
        readable = demand_consistent_with_readable_signals
        progress = operator_axis_progress_available(state, max_nodes)
        for table in world:
            target = tuple(table)
            if target in image:
                continue
            examined += 1
            demand = capability_demand("domain-probe", target)
            values = (progress, readable(demand, state["signal_width"]))
            row = FEATURE_ROWS.index(values)
            witnesses.setdefault(
                row,
                {
                    "row_index": row,
                    "values": [bool(value) for value in values],
                    "signal_width": state["signal_width"],
                    "operator_count": len(state["operators"]),
                    "target": list(target),
                },
            )
    census = {
        "schema": "m108-attribution-domain-v1",
        "rows": sorted(witnesses),
        "unreachable_rows": [row for row in range(len(FEATURE_ROWS)) if row not in witnesses],
        "state_family_size": len(probe_states()),
        "world_function_count": len(world),
        "unconstructible_pairs_examined": examined,
        "census_complete": True,
        "witnesses": [witnesses[row] for row in sorted(witnesses)],
    }
    _DOMAIN_MEMO[max_nodes] = canonical_json(census)
    return json.loads(_DOMAIN_MEMO[max_nodes])

# ----------------------------------------------------------------------------------------
# Acquiring the attribution rule from the behavioural record of the lineage's own past.
# ----------------------------------------------------------------------------------------


def attribution_episode(
    episode_id: str,
    *,
    operators: Iterable[dict[str, Any]],
    signal_width: int,
    target: Iterable[bool],
    blamed_component: str,
) -> dict[str, Any]:
    """One recorded past failure: the state in force, the demand, and the component extended.

    The blame label is authored supervision drawn from the recorded history of the lineage. It is
    evidence about attribution, never about the later demand B, which does not yet exist.
    """
    if blamed_component not in COMPONENTS:
        raise ValueError("M108 episode blames a component outside the registry")
    payload: dict[str, Any] = {
        "schema": EPISODE_SCHEMA,
        "episode_id": episode_id,
        "operators": [expr.decode_operator(item) for item in operators],
        "signal_width": int(signal_width),
        "demand": capability_demand("%s-demand" % episode_id, target),
        "blamed_component": blamed_component,
    }
    payload["episode_digest"] = digest(payload)
    return payload


def decode_episode(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict) or raw.get("schema") != EPISODE_SCHEMA:
        raise ValueError("M108 episode payload is invalid")
    rebuilt = attribution_episode(
        raw.get("episode_id"),
        operators=raw.get("operators") or [],
        signal_width=int(raw.get("signal_width", BASE_SIGNAL_WIDTH)),
        target=demand_target(raw.get("demand") or {}),
        blamed_component=raw.get("blamed_component"),
    )
    if rebuilt["episode_digest"] != raw.get("episode_digest"):
        raise ValueError("M108 episode identity mismatch")
    return rebuilt


def episode_feature_row(episode: dict[str, Any], max_nodes: int = MAX_EXPRESSION_NODES) -> int:
    past = create_state(episode["operators"], signal_width=episode["signal_width"])
    return failure_features(past, episode["demand"], max_nodes)["row_index"]


def acquire_attribution(
    state: dict[str, Any],
    episodes: Iterable[dict[str, Any]],
    *,
    register_result: bool,
    max_nodes: int = MAX_EXPRESSION_NODES,
) -> dict[str, Any]:
    """Search the programs the lineage can express for one reproducing its own blame record.

    The candidate space is `expression_image(state operators)` over the feature signals -- the
    language of the lineage itself, not a host-supplied menu. A lineage still holding only the
    monotone fragment provably has no consistent rule in that space, and the acquisition refuses.
    """
    decoded = [decode_episode(item) for item in episodes]
    observed: dict[int, bool] = {}
    for episode in decoded:
        row = episode_feature_row(episode, max_nodes)
        blames_signals = episode["blamed_component"] == COMPONENT_SIGNALS
        if observed.setdefault(row, blames_signals) != blames_signals:
            return {
                "schema": "m108-attribution-acquisition-v1",
                "confirmed": False,
                "reason": "attribution_episodes_are_contradictory",
                "episode_count": len(decoded),
                "observed_feature_rows": sorted(observed),
            }

    space = expression_image(state["operators"], FEATURE_COUNT, max_nodes)
    consistent = {
        table: node
        for table, node in space.items()
        if all(bool(table[row]) is value for row, value in observed.items())
    }
    domain = attribution_domain(max_nodes)
    classes: dict[tuple[bool, ...], list[tuple[bool, ...]]] = {}
    for table in consistent:
        key = tuple(bool(table[row]) for row in domain["rows"])
        classes.setdefault(key, []).append(table)

    report: dict[str, Any] = {
        "schema": "m108-attribution-acquisition-v1",
        "episode_count": len(decoded),
        "observed_feature_rows": sorted(observed),
        "attribution_domain_rows": domain["rows"],
        "attribution_domain_covered": sorted(observed) == domain["rows"],
        "rule_space_size": len(space),
        "rule_space_exhausted": True,
        "consistent_rule_count": len(consistent),
        "surviving_attribution_classes": len(classes),
        "every_consistent_rule_is_non_monotone": bool(consistent)
        and all(not expr._is_monotone(table) for table in consistent),
    }
    if not consistent:
        report["confirmed"] = False
        report["reason"] = "no_expressible_rule_reproduces_the_blame_record"
        return report
    if len(classes) != 1:
        report["confirmed"] = False
        report["reason"] = "attribution_underdetermined_by_episodes"
        return report

    canonical = min(
        consistent,
        key=lambda table: (node_count(consistent[table]), canonical_json(consistent[table])),
    )
    rule = attribution_rule(consistent[canonical], canonical)
    report["confirmed"] = True
    report["adopted_rule"] = rule
    report["registered"] = bool(register_result)
    if register_result:
        report["next_state"] = create_state(
            state["operators"], signal_width=state["signal_width"], attribution=rule
        )
    return report


# ----------------------------------------------------------------------------------------
# Extending a component, and the bounded machinery loop that decides which one.
# ----------------------------------------------------------------------------------------


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
        "witness": witness,
        "witness_nodes": node_count(witness) if witness else None,
    }
    if witness is not None:
        table = {item["name"]: item for item in state["operators"]}
        replay = tuple(
            execute_expression(table, witness, row[: state["signal_width"]])
            for row in world_rows()
        )
        report["executes_to_target"] = replay == wanted
    else:
        report["executes_to_target"] = False
    return report


def search_operator_extension(
    state: dict[str, Any], demand: dict[str, Any], max_nodes: int = MAX_EXPRESSION_NODES
) -> dict[str, Any]:
    """Exhaust the authored operator candidate space against this demand."""
    wanted = demand_target(demand)
    space = expr.operator_space()
    for candidate in space:
        extended = create_state(
            state["operators"]
            + [
                expr.operator_definition(
                    "ACQUIRED_%s" % candidate["operator_id"][-8:],
                    candidate["arity"],
                    candidate["truth_table"],
                )
            ],
            signal_width=state["signal_width"],
            attribution=state["attribution"],
        )
        if construct(extended, wanted, max_nodes)["constructible"]:
            return {
                "confirmed": True,
                "operator_space_size": len(space),
                "operator_space_exhausted": False,
                "next_state": extended,
            }
    return {
        "confirmed": False,
        "reason": "operator_candidate_space_exhausted",
        "operator_space_size": len(space),
        "operator_space_exhausted": True,
    }


def extend_signal_interface(state: dict[str, Any]) -> dict[str, Any]:
    width = state["signal_width"] + 1
    if width > MAX_SIGNAL_WIDTH:
        return {"confirmed": False, "reason": "signal_interface_ceiling_reached"}
    return {
        "confirmed": True,
        "signal_width": width,
        "next_state": create_state(
            state["operators"], signal_width=width, attribution=state["attribution"]
        ),
    }


def resolve(
    state: dict[str, Any], demand: dict[str, Any], max_nodes: int = MAX_EXPRESSION_NODES
) -> dict[str, Any]:
    """The acquisition machinery, bounded. Attribution decides which component it extends."""
    decoded = decode_demand(demand)
    wanted = demand_target(decoded)
    current = decode_state(state)
    trace: list[dict[str, Any]] = []
    for step in range(MAX_MACHINERY_STEPS + 1):
        built = construct(current, wanted, max_nodes)
        if built["constructible"]:
            return {
                "schema": "m108-resolution-v1",
                "confirmed": True,
                "steps": step,
                "trace": trace,
                "construction": built,
                "final_signal_width": current["signal_width"],
                "final_state_digest": current["state_digest"],
            }
        if step == MAX_MACHINERY_STEPS:
            break
        features = failure_features(current, decoded, max_nodes)
        blame = attribute(current, features)
        entry = {"step": step, "features": features, "attribution": blame}
        if blame["component"] == COMPONENT_SIGNALS:
            extension = extend_signal_interface(current)
        else:
            extension = search_operator_extension(current, decoded, max_nodes)
        entry["extension"] = {
            key: value for key, value in extension.items() if key != "next_state"
        }
        trace.append(entry)
        if not extension["confirmed"]:
            return {
                "schema": "m108-resolution-v1",
                "confirmed": False,
                "reason": extension.get("reason", "extension_refused"),
                "steps": step + 1,
                "trace": trace,
                "construction": built,
                "final_signal_width": current["signal_width"],
                "final_state_digest": current["state_digest"],
            }
        current = extension["next_state"]
    return {
        "schema": "m108-resolution-v1",
        "confirmed": False,
        "reason": "machinery_step_ceiling_reached",
        "steps": MAX_MACHINERY_STEPS,
        "trace": trace,
        "construction": construct(current, wanted, max_nodes),
        "final_signal_width": current["signal_width"],
        "final_state_digest": current["state_digest"],
    }


def structural_exclusion_certificate(target: Iterable[bool], width: int) -> dict[str, Any]:
    """B is outside the reach of ANY state at this interface width -- a census, not a search."""
    wanted = tuple(bool(value) for value in target)
    liftable = liftable_images(width)
    certificate: dict[str, Any] = {
        "schema": "m108-structural-exclusion-v1",
        "width": width,
        "liftable_image_count": len(liftable),
        "world_function_count": 2 ** (2 ** WORLD_SIGNAL_WIDTH),
        "target_in_any_liftable_image": wanted in liftable,
        "depends_on_unread_signal": any(
            depends_on_signal(wanted, index) for index in range(width, WORLD_SIGNAL_WIDTH)
        ),
        "budget_independent": True,
        "operator_set_independent": True,
    }
    certificate["confirmed"] = bool(
        not certificate["target_in_any_liftable_image"]
        and certificate["depends_on_unread_signal"]
    )
    return certificate


def is_monotone(table: Iterable[bool], width: int) -> bool:
    """Raising any signal never lowers the output. M107's lemma, generalized to the width."""
    rows = rows_for_width(width)
    values = list(table)
    for i, row_i in enumerate(rows):
        for j, row_j in enumerate(rows):
            if all(a <= b for a, b in zip(row_i, row_j)) and values[i] and not values[j]:
                return False
    return True


def monotone_exclusion_certificate(
    state_operators: Iterable[dict[str, Any]],
    target: Iterable[bool],
    width: int = WORLD_SIGNAL_WIDTH,
    max_nodes: int = MAX_EXPRESSION_NODES,
) -> dict[str, Any]:
    """The target is outside this image for every node bound, because monotone operators compose.

    This is the second, independent half of B's exclusion: even a lineage whose interface already
    read every signal of the world could not build B while its operator table stayed monotone.
    """
    operators = list(state_operators)
    wanted = tuple(bool(value) for value in target)
    image = expression_image(operators, width, max_nodes)
    all_operators_monotone = all(expr._operator_is_monotone(item) for item in operators)
    image_all_monotone = all(is_monotone(table, width) for table in image)
    target_monotone = is_monotone(wanted, width)
    lemma = bool(all_operators_monotone and image_all_monotone and not target_monotone)
    certificate: dict[str, Any] = {
        "schema": "m108-monotone-exclusion-v1",
        "target": list(wanted),
        "width": width,
        "max_nodes": max_nodes,
        "image_size": len(image),
        "target_in_image": wanted in image,
        "target_is_monotone": target_monotone,
        "every_operator_is_monotone": all_operators_monotone,
        "complete_image_is_monotone": image_all_monotone,
        "excluded_by_monotonicity_lemma": lemma,
        "budget_independent": lemma,
    }
    certificate["confirmed"] = bool(not certificate["target_in_image"] and lemma)
    certificate["certificate_digest"] = digest(certificate)
    return certificate
