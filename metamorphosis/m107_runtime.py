"""M107 - state-owned lower interpreter over a deliberately incomplete operator set.

M105 and M106 could never extend Boolean reach: their interpreter hardcodes CONST/INPUT/NOT/AND/OR
and is *semantically complete* over two signals, so every one of the sixteen functions is already
inside the complete image and no acquisition can enlarge it.

M107 removes that ceiling by construction. The interpreter here holds **no operator semantics at
all**. It evaluates an expression by looking each internal node's operator up in a table carried in
the lineage's own state, and applying that operator's truth table. The initial table is the monotone
fragment {AND, OR}, whose complete image is four of sixteen functions and which is closed under its
own operators: every negation-dependent function is excluded by a monotonicity lemma rather than by
a search bound. Acquiring an operator is therefore a change to the interpreter's reach, not a
selection among capabilities it already had.

Nothing in this module names negation or any specific target. Operators are data.
"""

from __future__ import annotations

import functools
import hashlib
import itertools
import json
from typing import Any, Iterable

STATE_SCHEMA = "m107-lineage-state-v1"
OPERATOR_SCHEMA = "m107-operator-v1"
OPERATOR_DEMAND_SCHEMA = "m107-operator-demand-v1"

SIGNAL_COUNT = 2
SIGNAL_ROWS: tuple[tuple[bool, bool], ...] = (
    (False, False),
    (False, True),
    (True, False),
    (True, True),
)
# Nine nodes is the fixed point: every complete image below is identical at 9, 11 and 13 nodes,
# while S0 stays at four functions at every bound. The bound therefore records the true closure
# rather than a search budget, which is what makes the reach claims budget-independent.
MAX_EXPRESSION_NODES = 9
MAX_ACQUIRED_ARITY = 2


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("ascii")).hexdigest()


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


# ----------------------------------------------------------------------------------------
# Operators are data. The interpreter knows none of them.
# ----------------------------------------------------------------------------------------


def operator_definition(name: str, arity: int, table: Iterable[bool]) -> dict[str, Any]:
    if not isinstance(name, str) or not name or len(name) > 24:
        raise ValueError("M107 operator name is invalid")
    if arity not in (1, 2):
        raise ValueError("M107 operator arity must be 1 or 2")
    rows = [bool(value) for value in table]
    if len(rows) != 2 ** arity:
        raise ValueError("M107 operator truth table has the wrong length")
    payload: dict[str, Any] = {
        "schema": OPERATOR_SCHEMA,
        "name": name,
        "arity": arity,
        "truth_table": rows,
    }
    payload["operator_id"] = "operator-" + digest(payload)[:16]
    return payload


def decode_operator(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict) or raw.get("schema") != OPERATOR_SCHEMA:
        raise ValueError("M107 operator payload is invalid")
    rebuilt = operator_definition(raw.get("name"), raw.get("arity"), raw.get("truth_table") or [])
    if rebuilt["operator_id"] != raw.get("operator_id"):
        raise ValueError("M107 operator identity mismatch")
    return rebuilt


def initial_operators() -> list[dict[str, Any]]:
    """The monotone fragment. Closed under itself; four of sixteen functions reachable."""
    return [
        operator_definition("AND", 2, [False, False, False, True]),
        operator_definition("OR", 2, [False, True, True, True]),
    ]


def operator_space(max_arity: int = MAX_ACQUIRED_ARITY) -> list[dict[str, Any]]:
    """Every 1- and 2-ary Boolean operator. The host codes the space, never the answer."""
    space: list[dict[str, Any]] = []
    for arity in range(1, max_arity + 1):
        for index, table in enumerate(itertools.product((False, True), repeat=2 ** arity)):
            space.append(operator_definition("CAND%d_%02d" % (arity, index), arity, list(table)))
    return space


# ----------------------------------------------------------------------------------------
# The interpreter. It contains no operator semantics whatsoever.
# ----------------------------------------------------------------------------------------


def signal_node(index: int) -> dict[str, Any]:
    if index not in range(SIGNAL_COUNT):
        raise ValueError("M107 signal index is out of range")
    return {"node": "SIGNAL", "index": index}


def apply_node(operator_name: str, children: list[dict[str, Any]]) -> dict[str, Any]:
    return {"node": "APPLY", "operator": operator_name, "children": list(children)}


def node_count(expression: dict[str, Any]) -> int:
    if expression.get("node") == "SIGNAL":
        return 1
    return 1 + sum(node_count(child) for child in expression["children"])


def execute_expression(
    operators: dict[str, dict[str, Any]],
    expression: dict[str, Any],
    signals: Iterable[bool],
) -> bool:
    values = tuple(bool(value) for value in signals)
    if len(values) != SIGNAL_COUNT:
        raise ValueError("M107 signal vector has the wrong width")

    def run(node: dict[str, Any]) -> bool:
        kind = node.get("node")
        if kind == "SIGNAL":
            return values[node["index"]]
        if kind != "APPLY":
            raise ValueError("M107 expression node is invalid")
        operator = operators.get(node.get("operator"))
        if operator is None:
            # The interpreter cannot invent semantics the state does not hold.
            raise ValueError("M107 operator is not in the state table")
        children = node.get("children") or []
        if len(children) != operator["arity"]:
            raise ValueError("M107 operator arity mismatch")
        index = 0
        for child in children:
            index = (index << 1) | (1 if run(child) else 0)
        return bool(operator["truth_table"][index])

    return run(expression)


def truth_table(
    operators: dict[str, dict[str, Any]], expression: dict[str, Any]
) -> tuple[bool, ...]:
    return tuple(execute_expression(operators, expression, row) for row in SIGNAL_ROWS)


def operator_map(state_operators: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {operator["name"]: operator for operator in state_operators}


def _compositions(total: int, parts: int) -> list[tuple[int, ...]]:
    if parts == 1:
        return [(total,)] if total >= 1 else []
    out: list[tuple[int, ...]] = []
    for first in range(1, total - parts + 2):
        for rest in _compositions(total - first, parts - 1):
            out.append((first,) + rest)
    return out


@functools.lru_cache(maxsize=64)
def _image_cached(operator_key: str, max_nodes: int) -> str:
    operators = {item["name"]: item for item in json.loads(operator_key)}
    by_size: dict[int, list[dict[str, Any]]] = {
        1: [signal_node(index) for index in range(SIGNAL_COUNT)]
    }
    reached: dict[tuple[bool, ...], dict[str, Any]] = {
        truth_table(operators, node): node for node in by_size[1]
    }
    for size in range(2, max_nodes + 1):
        produced: dict[str, dict[str, Any]] = {}
        for operator in sorted(operators.values(), key=lambda item: item["name"]):
            for split in _compositions(size - 1, operator["arity"]):
                pools = [by_size.get(part, []) for part in split]
                if not all(pools):
                    continue
                for combination in itertools.product(*pools):
                    node = apply_node(operator["name"], list(combination))
                    produced[canonical_json(node)] = node
        fresh: dict[tuple[bool, ...], dict[str, Any]] = {}
        for key in sorted(produced):
            node = produced[key]
            table = truth_table(operators, node)
            if table not in reached and table not in fresh:
                fresh[table] = node
        by_size[size] = list(fresh.values())
        reached.update(fresh)
    return canonical_json(
        {
            "".join("1" if bit else "0" for bit in table): node
            for table, node in sorted(reached.items())
        }
    )


def _operator_key(state_operators: Iterable[dict[str, Any]]) -> str:
    items = sorted(
        (
            {"name": o["name"], "arity": o["arity"], "truth_table": list(o["truth_table"])}
            for o in state_operators
        ),
        key=lambda item: item["name"],
    )
    return canonical_json(items)


def complete_image(
    state_operators: Iterable[dict[str, Any]], max_nodes: int = MAX_EXPRESSION_NODES
) -> dict[tuple[bool, ...], dict[str, Any]]:
    """Every truth table reachable by any expression within the node bound. Exhaustive."""
    raw = json.loads(_image_cached(_operator_key(state_operators), max_nodes))
    return {tuple(bit == "1" for bit in key): node for key, node in raw.items()}


# ----------------------------------------------------------------------------------------
# Structural insufficiency: a lemma, not a search bound.
# ----------------------------------------------------------------------------------------


def _is_monotone(table: tuple[bool, ...]) -> bool:
    for i, row_i in enumerate(SIGNAL_ROWS):
        for j, row_j in enumerate(SIGNAL_ROWS):
            if all(a <= b for a, b in zip(row_i, row_j)) and table[i] and not table[j]:
                return False
    return True


def _operator_is_monotone(operator: dict[str, Any]) -> bool:
    """A k-ary operator is monotone when raising any argument never lowers its output."""
    arity = operator["arity"]
    table = operator["truth_table"]
    rows = list(itertools.product((False, True), repeat=arity))
    for i, row_i in enumerate(rows):
        for j, row_j in enumerate(rows):
            if all(a <= b for a, b in zip(row_i, row_j)) and table[i] and not table[j]:
                return False
    return True


def insufficiency_certificate(
    state_operators: Iterable[dict[str, Any]],
    target: tuple[bool, ...],
    max_nodes: int = MAX_EXPRESSION_NODES,
) -> dict[str, Any]:
    """Prove the target is unreachable for a structural reason, independent of any budget."""
    operators = list(state_operators)
    image = complete_image(operators, max_nodes)
    all_operators_monotone = all(_operator_is_monotone(item) for item in operators)
    image_all_monotone = all(_is_monotone(table) for table in image)
    target_monotone = _is_monotone(tuple(target))
    lemma = bool(all_operators_monotone and image_all_monotone and not target_monotone)
    certificate: dict[str, Any] = {
        "schema": "m107-insufficiency-certificate-v1",
        "target": list(target),
        "max_nodes": max_nodes,
        "image_size": len(image),
        "target_in_image": tuple(target) in image,
        "target_is_monotone": target_monotone,
        "every_operator_is_monotone": all_operators_monotone,
        "complete_image_is_monotone": image_all_monotone,
        # Monotone operators compose to monotone functions at every depth, so a non-monotone target
        # is excluded for every node bound, not merely for the one enumerated here.
        "excluded_by_monotonicity_lemma": lemma,
        "budget_independent": lemma,
    }
    certificate["confirmed"] = bool(not certificate["target_in_image"] and lemma)
    certificate["certificate_digest"] = digest(certificate)
    return certificate


# ----------------------------------------------------------------------------------------
# Lineage state. The operator table lives here, not in this module.
# ----------------------------------------------------------------------------------------


def create_state() -> dict[str, Any]:
    state: dict[str, Any] = {
        "schema": STATE_SCHEMA,
        "operators": initial_operators(),
        "definitions": [],
    }
    state["state_digest"] = digest(
        {"operators": state["operators"], "definitions": state["definitions"]}
    )
    return state


def decode_state(raw: bytes | str | dict[str, Any]) -> dict[str, Any]:
    if isinstance(raw, (bytes, bytearray)):
        value = json.loads(bytes(raw).decode("ascii"))
    elif isinstance(raw, str):
        value = json.loads(raw)
    else:
        value = json.loads(canonical_json(raw))
    if not isinstance(value, dict) or value.get("schema") != STATE_SCHEMA:
        raise ValueError("M107 state payload is invalid")
    operators = [decode_operator(item) for item in value.get("operators") or []]
    definitions = list(value.get("definitions") or [])
    expected = digest({"operators": operators, "definitions": definitions})
    if value.get("state_digest") != expected:
        raise ValueError("M107 state digest mismatch")
    return {
        "schema": STATE_SCHEMA,
        "operators": operators,
        "definitions": definitions,
        "state_digest": expected,
    }


def encode_state(state: dict[str, Any]) -> bytes:
    return canonical_json(decode_state(state)).encode("ascii")


def _next_state(state: dict[str, Any], operators: list[dict[str, Any]], definitions: list[dict[str, Any]]) -> dict[str, Any]:
    nxt = {
        "schema": STATE_SCHEMA,
        "operators": operators,
        "definitions": definitions,
    }
    nxt["state_digest"] = digest({"operators": operators, "definitions": definitions})
    return nxt


# ----------------------------------------------------------------------------------------
# Acquisition: the lineage extends its own interpreter's operator table.
# ----------------------------------------------------------------------------------------


def operator_demand(demand_id: str, observations: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    for item in observations:
        rows.append(
            {
                "case_id": str(item["case_id"]),
                "signals": [bool(value) for value in item["signals"]],
                "nonce": str(item["nonce"]),
                "expected": bool(item["expected"]),
            }
        )
    if not rows:
        raise ValueError("M107 operator demand needs observations")
    payload = {
        "schema": OPERATOR_DEMAND_SCHEMA,
        "demand_id": str(demand_id),
        "observations": sorted(rows, key=lambda row: row["case_id"]),
    }
    payload["demand_digest"] = digest(payload)
    return payload


def decode_operator_demand(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict) or raw.get("schema") != OPERATOR_DEMAND_SCHEMA:
        raise ValueError("M107 operator demand payload is invalid")
    rebuilt = operator_demand(raw.get("demand_id"), raw.get("observations") or [])
    if rebuilt["demand_digest"] != raw.get("demand_digest"):
        raise ValueError("M107 operator demand digest mismatch")
    return rebuilt


def _observed_table(demand: dict[str, Any]) -> dict[tuple[bool, bool], bool]:
    seen: dict[tuple[bool, bool], bool] = {}
    for row in demand["observations"]:
        key = (row["signals"][0], row["signals"][1])
        if key in seen and seen[key] != row["expected"]:
            raise ValueError("M107 operator demand is internally inconsistent")
        seen[key] = row["expected"]
    return seen


def acquire_operator(
    state: dict[str, Any], demands: Any, *, register_result: bool
) -> dict[str, Any]:
    """Search the generic operator space for one that makes the demanded behaviour constructible.

    The lineage never receives the target operator, its name, arity, table or identity. It receives
    behavioural observations and its own interpreter, and must find which single extension to its
    operator table brings the demanded function inside the complete image.
    """
    state = decode_state(state)
    # One or several demanded behaviours. Several jointly constrain the extension far more than one:
    # a single behaviour leaves distinct reach classes and must be refused.
    raw_demands = demands if isinstance(demands, list) else [demands]
    decoded_demands = [decode_operator_demand(item) for item in raw_demands]
    observed_tables = [_observed_table(item) for item in decoded_demands]
    complete = all(len(table) == len(SIGNAL_ROWS) for table in observed_tables)
    wanted = (
        [tuple(table.get(row) for row in SIGNAL_ROWS) for table in observed_tables]
        if complete
        else []
    )

    base_operators = state["operators"]
    base_image = complete_image(base_operators)
    already = complete and all(target in base_image for target in wanted)

    survivors: list[dict[str, Any]] = []
    if complete and not already:
        existing_names = {item["name"] for item in base_operators}
        existing_tables = {
            (item["arity"], tuple(item["truth_table"])) for item in base_operators
        }
        for candidate in operator_space():
            if candidate["name"] in existing_names:
                continue
            if (candidate["arity"], tuple(candidate["truth_table"])) in existing_tables:
                continue
            extended = base_operators + [candidate]
            image = complete_image(extended)
            if all(target in image for target in wanted):
                survivors.append(
                    {
                        "operator": candidate,
                        "image_size": len(image),
                        "witnesses": [image[target] for target in wanted],
                    }
                )

    # A survivor class is a distinct *reach*: two candidates that produce the same complete image
    # are the same extension as far as the interpreter is concerned.
    classes: dict[str, list[dict[str, Any]]] = {}
    for item in survivors:
        key = canonical_json(
            sorted("".join("1" if b else "0" for b in table) for table in complete_image(
                base_operators + [item["operator"]]
            ))
        )
        classes.setdefault(key, []).append(item)

    report: dict[str, Any] = {
        "schema": "m107-operator-acquisition-v1",
        "demand_ids": [item["demand_id"] for item in decoded_demands],
        "demand_digests": [item["demand_digest"] for item in decoded_demands],
        "demand_count": len(decoded_demands),
        "demanded_targets": [list(target) for target in wanted],
        "observation_rows": [len(table) for table in observed_tables],
        "observations_complete": complete,
        "targets_already_in_base_image": already,
        "base_image_size": len(base_image),
        "operator_space_size": len(operator_space()),
        "operator_space_exhausted": True,
        "surviving_candidates": len(survivors),
        "surviving_reach_classes": len(classes),
    }

    if not complete:
        report.update({"confirmed": False, "registered": False,
                       "reason": "observations_do_not_determine_a_total_function",
                       "next_state": None})
        return report
    if already:
        report.update({"confirmed": False, "registered": False,
                       "reason": "demanded_functions_are_already_constructible",
                       "next_state": None})
        return report
    if not survivors:
        report.update({"confirmed": False, "registered": False,
                       "reason": "no_single_operator_extension_reaches_the_demand",
                       "next_state": None})
        return report
    if len(classes) != 1:
        report.update({"confirmed": False, "registered": False,
                       "reason": "extension_underdetermined_by_observations",
                       "next_state": None})
        return report

    # One reach class survived. Adopt its canonical shortest-table representative.
    chosen = sorted(
        classes[next(iter(classes))],
        key=lambda item: (item["operator"]["arity"], canonical_json(item["operator"]["truth_table"])),
    )[0]
    adopted = operator_definition(
        "ACQUIRED_%s" % digest(chosen["operator"]["truth_table"])[:10],
        chosen["operator"]["arity"],
        chosen["operator"]["truth_table"],
    )
    extended = base_operators + [adopted]
    report.update(
        {
            "confirmed": True,
            "adopted_operator": adopted,
            "extended_image_size": len(complete_image(extended)),
            "witness_expressions": chosen["witnesses"],
        }
    )
    if register_result:
        report["registered"] = True
        report["next_state"] = _next_state(state, extended, list(state["definitions"]))
    else:
        report["registered"] = False
        report["next_state"] = None
    return report


def construct(state: dict[str, Any], target: Iterable[bool]) -> dict[str, Any]:
    """Try to construct the target function inside the state's current interpreter reach."""
    state = decode_state(state)
    image = complete_image(state["operators"])
    key = tuple(bool(value) for value in target)
    node = image.get(key)
    return {
        "schema": "m107-construction-v1",
        "target": list(key),
        "constructible": node is not None,
        "image_size": len(image),
        "expression": node,
        "operator_names": sorted(item["name"] for item in state["operators"]),
    }
