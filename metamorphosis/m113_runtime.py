"""M113 - a learner that is handed a carrier and no description of what it does.

M110 carried an acquired machinery modification into a consumer family the project designed. M111
added a lineage that can tell when its own observation does not determine the answer. M112 took the
*worlds* out of the project's hands and kept the carrier. This module is the body that meets a
carrier the project did not design either.

## What this learner is given, and what it is not

Given: a `carrier_host.Channel`, an invocation budget, and a demand naming a target observation and
the observable cell names it is stated over. Through the channel it may read the meta-channel -- the
wire grammar and the action names and arities -- and send requests.

Not given, at any point: the carrier's cells, their domains, its initial configuration, which
cells are latent, any precondition, any effect, the error vocabulary, the mapping from a refused
action to a code, and the reachable set. The carrier object never enters this module.

The boundary is enforced where it can be, and its limit is stated rather than glossed. `Channel`
holds the carrier in a closure, which is introspectable in Python and therefore not a sandbox. What
makes the boundary real is `scripts/audit_m113_boundaries.py`, which parses this file and refuses it
if it names a carrier-internal key, calls a host function that reads carrier structure, or imports
the evaluator. The claim is that this learner does not read the carrier, and that the claim is
checked -- not that reading it would be impossible.

## The three axes, and why they are the same three

M110's move was to register the producer's components under the producer's names and compute the
producer's features under their declared semantics in a materially different domain -- so that
`m109_runtime.attribute`, imported unchanged, could be *wrong*, and be measured. The same move is
made here, one carrier further out:

| M109 / M110 | M113 |
|---|---|
| `operator_table` | the **action vocabulary**: how many of the carrier's declared actions the learner will use |
| `signal_interface` | the **observation interface**: how many of the response's fields it parses |
| `candidate_space` | the **composition space**: sequences to depth two, or expanded to a fixed point |

The names, the feature vocabulary and the cascade are shared authored vocabulary read from the
producer module rather than restated, so a drift is an import error here and not a silent
disagreement about what a rule selects.

## Refusal is a reach fact, and non-commitment is a third answer

A learner that has explored to a fixed point and cannot produce the target refuses, and the refusal
carries the certificate that says the fixed point was reached rather than the budget. A learner
whose exploration did not close, or whose diagnostic vocabulary does not determine which component
is limiting, returns **undetermined** -- which is neither a success nor a refusal, and is the
outcome M110's row 5 would have deserved.
"""

from __future__ import annotations

import json
from typing import Any, Iterable, Mapping, Sequence

from metamorphosis import carrier_host as host
from metamorphosis import m109_runtime as lineage
from metamorphosis import m111_runtime as diagnosis

STATE_SCHEMA = "m113-carrier-lineage-state-v1"
MODEL_SCHEMA = "m113-inferred-model-v1"
OUTCOME_SCHEMA = "m113-attempt-outcome-v1"

# Shared authored vocabulary, read from the producer rather than restated.
COMPONENT_ACTIONS = lineage.COMPONENT_OPERATORS
COMPONENT_OBSERVATION = lineage.COMPONENT_SIGNALS
COMPONENT_COMPOSITION = lineage.COMPONENT_CANDIDATES
COMPONENT_DIAGNOSTIC = diagnosis.COMPONENT_DIAGNOSTIC
COMPONENTS = lineage.COMPONENTS
FEATURE_NAMES = lineage.FEATURE_NAMES
FEATURE_COUNT = lineage.FEATURE_COUNT
FEATURE_ROWS = lineage.FEATURE_ROWS

BOUNDED_SPACE = lineage.MONOTONE_SPACE
COMPLETE_SPACE = lineage.COMPLETE_SPACE
COMPOSITION_SPACES = lineage.CANDIDATE_SPACES

BASE_ACTION_WIDTH = 2
BASE_OBSERVATION_WIDTH = 1
BOUNDED_COMPOSITION_DEPTH = 2
MACHINERY_STEP_BUDGET = 1
DEFAULT_PROBE_BUDGET = diagnosis.DEFAULT_PROBE_BUDGET

# Two ways not to commit, recorded apart because they mean different things. The first is a fact
# about this run's resources; the second is a fact about the lineage's own vocabulary, and is the
# one M110 showed the cost of not having.
UNDETERMINED_BUDGET = "exploration_did_not_close_within_budget"
UNDETERMINED_VOCABULARY = "diagnostic_vocabulary_does_not_determine_this_carrier"

canonical_json = host.canonical_json
digest = host.digest


class CarrierLineageError(RuntimeError):
    """Raised when lineage state or a channel is malformed. Every path fails closed."""


# ----------------------------------------------------------------------------------------
# Lineage state. Everything except `rules` and `policy` is the adapter, identical across arms.
# ----------------------------------------------------------------------------------------


def create_state(
    *,
    action_width: int = BASE_ACTION_WIDTH,
    observation_width: int = BASE_OBSERVATION_WIDTH,
    composition_space: str = BOUNDED_SPACE,
    rules: Iterable[Mapping[str, Any]] | None = None,
    policy: Mapping[str, Any] | None = None,
    probe_budget: int = DEFAULT_PROBE_BUDGET,
    pooled_record: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if int(action_width) < 1:
        raise CarrierLineageError("M113 action width is below the authored floor")
    if int(observation_width) < 1:
        raise CarrierLineageError("M113 observation width is below the authored floor")
    if composition_space not in COMPOSITION_SPACES:
        raise CarrierLineageError("M113 composition space is outside the authored registry")
    cascade = [lineage.decode_rule(item) for item in (rules or [])]
    decoded_policy = diagnosis.decode_policy(policy) if policy else None
    record = dict(pooled_record) if pooled_record else None
    payload: dict[str, Any] = {
        "action_width": int(action_width),
        "observation_width": int(observation_width),
        "composition_space": composition_space,
        "rules": cascade,
        "policy": decoded_policy,
        "probe_budget": int(probe_budget),
        "pooled_record": record,
        "component_registry": list(COMPONENTS),
        "feature_vocabulary": list(FEATURE_NAMES),
    }
    return {"schema": STATE_SCHEMA, **payload, "state_digest": digest(payload)}


def decode_state(raw: bytes | str | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(raw, (bytes, bytearray)):
        value = json.loads(bytes(raw).decode("ascii"))
    elif isinstance(raw, str):
        value = json.loads(raw)
    else:
        value = json.loads(canonical_json(raw))
    if not isinstance(value, dict) or value.get("schema") != STATE_SCHEMA:
        raise CarrierLineageError("M113 lineage state payload is invalid")
    if list(value.get("component_registry") or []) != list(COMPONENTS):
        raise CarrierLineageError("M113 component registry changed")
    if list(value.get("feature_vocabulary") or []) != list(FEATURE_NAMES):
        raise CarrierLineageError("M113 feature vocabulary changed")
    rebuilt = create_state(
        action_width=int(value.get("action_width", BASE_ACTION_WIDTH)),
        observation_width=int(value.get("observation_width", BASE_OBSERVATION_WIDTH)),
        composition_space=value.get("composition_space", BOUNDED_SPACE),
        rules=value.get("rules") or [],
        policy=value.get("policy"),
        probe_budget=int(value.get("probe_budget", DEFAULT_PROBE_BUDGET)),
        pooled_record=value.get("pooled_record"),
    )
    if rebuilt["state_digest"] != value.get("state_digest"):
        raise CarrierLineageError("M113 lineage state digest mismatch")
    return rebuilt


def encode_state(state: Mapping[str, Any]) -> bytes:
    return canonical_json(decode_state(state)).encode("ascii")


def adapter_projection(state: Mapping[str, Any]) -> dict[str, Any]:
    """Everything except the acquired cascade, the acquired policy and its record.

    Equality of this projection across arms is a measured predicate, not a promise: it is what makes
    "the only difference is the Genesis machinery" a checkable statement rather than a claim.
    """
    decoded = decode_state(state)
    return {
        key: value
        for key, value in decoded.items()
        if key not in ("rules", "policy", "pooled_record", "state_digest")
    }


# ----------------------------------------------------------------------------------------
# Speaking the carrier's wire, from the meta-channel alone.
# ----------------------------------------------------------------------------------------


def alphabet_for(meta: Mapping[str, Any], action_width: int) -> list[tuple[str, int]]:
    """Every request the learner's current action vocabulary admits, in declaration order."""
    alphabet: list[tuple[str, int]] = []
    for item in list(meta["actions"])[: int(action_width)]:
        if int(item["arity"]) == 0:
            alphabet.append((str(item["name"]), 0))
        else:
            for value in range(int(item["arg_size"])):
                alphabet.append((str(item["name"]), value))
    return alphabet


def encode_request(meta: Mapping[str, Any], name: str, argument: int) -> str:
    surface = meta["surface"]
    kind = surface["kind"]
    if kind == "json_object":
        return canonical_json({surface["action_key"]: name, surface["argument_key"]: int(argument)})
    if kind == "json_array":
        return canonical_json([name, int(argument)])
    if kind == "text_line":
        return "%s%s%d" % (name, surface["field_separator"], int(argument))
    index = next(
        (
            position
            for position, item in enumerate(meta["actions"])
            if str(item["name"]) == str(name)
        ),
        len(list(meta["actions"])),
    )
    return "%d%d" % (index % 10, int(argument) % 10)


def parse_response(
    meta: Mapping[str, Any], response: str, observed_cells: Sequence[str]
) -> tuple[int, ...] | None:
    """Read one response, or return None when the carrier refused the request.

    The learner is told which cell names the demand is stated over -- a demand has to be stateable
    -- and nothing about what they mean, what they range over or which of them the carrier will move.
    On a positional wire it is told nothing at all beyond the order.
    """
    surface = meta["surface"]
    kind = surface["kind"]
    names = [str(item) for item in observed_cells]
    if kind == "json_object":
        try:
            parsed = json.loads(response)
        except (ValueError, TypeError):
            return None
        if not isinstance(parsed, dict) or parsed.get(surface["status_key"]) != surface["ok_token"]:
            return None
        try:
            return tuple(int(parsed[name]) for name in names)
        except (KeyError, TypeError, ValueError):
            return None
    if kind == "json_array":
        try:
            parsed = json.loads(response)
        except (ValueError, TypeError):
            return None
        if not isinstance(parsed, list) or not parsed or parsed[0] != surface["ok_token"]:
            return None
        values = parsed[1:]
        if len(values) != len(names):
            return None
        try:
            return tuple(int(value) for value in values)
        except (TypeError, ValueError):
            return None
    if kind == "text_line":
        parts = response.split(surface["field_separator"])
        if not parts or parts[0] != surface["ok_token"]:
            return None
        found: dict[str, int] = {}
        for item in parts[1:]:
            piece = item.split(surface["pair_separator"])
            if len(piece) != 2 or not piece[1].lstrip("-").isdigit():
                return None
            found[piece[0]] = int(piece[1])
        try:
            return tuple(found[name] for name in names)
        except KeyError:
            return None
    token = surface["ok_token"]
    if not response.startswith(token):
        return None
    digits = response[len(token) :]
    if len(digits) != len(names) or not digits.isdigit():
        return None
    return tuple(int(char) for char in digits)


# ----------------------------------------------------------------------------------------
# Exploration. A fixed point over what was observed, not a bound anybody guessed.
# ----------------------------------------------------------------------------------------


def _replay(
    channel: host.Channel,
    meta: Mapping[str, Any],
    sequence: Sequence[tuple[str, int]],
    observed_cells: Sequence[str],
) -> tuple[int, ...] | None:
    """Drive the carrier from its initial configuration through one request sequence."""
    session = channel.restart()
    seen: tuple[int, ...] | None = None
    for name, argument in sequence:
        seen = parse_response(
            meta, session.send(encode_request(meta, name, argument)), observed_cells
        )
    return seen


def _distinguish(
    channel: host.Channel,
    meta: Mapping[str, Any],
    names: Sequence[str],
    width: int,
    alphabet: Sequence[tuple[str, int]],
    known: Mapping[tuple[int, ...], Sequence[tuple[str, int]]],
    alternates: Mapping[tuple[int, ...], Sequence[Sequence[tuple[str, int]]]],
) -> tuple[bool, int, bool]:
    """Ask whether two ways of reaching the same projection are two ways of reaching one place.

    Exploration alone cannot answer this. It prunes on the projection, so each projection is only
    ever expanded from one path, and a machine that is not a machine in the learner's language will
    look like one right up until two arrivals are compared. So they are compared: the same request
    is issued after each of the two paths, and a disagreement is proof that the projection is not a
    state. This is the learner's one equivalence experiment, and it costs the same budget everything
    else does.
    """
    experiments = 0
    for projection, others in sorted(alternates.items()):
        canonical = list(known[projection])
        for alternative in others:
            for name, argument in alphabet:
                need = len(canonical) + len(alternative) + 2 + 2
                if channel.invocations_left < need:
                    # Not "no collision was found": the comparison could not be afforded. Saying
                    # those two things with one value would let a budget shortfall be read as
                    # evidence that the projection is a state, which is the shape of defect this
                    # milestone exists to avoid rather than to commit at a new level.
                    return False, experiments, False
                experiments += 1
                left = _replay(channel, meta, list(canonical) + [(name, argument)], names)
                right = _replay(channel, meta, list(alternative) + [(name, argument)], names)
                narrow_left = None if left is None else left[:width]
                narrow_right = None if right is None else right[:width]
                if narrow_left != narrow_right:
                    return True, experiments, True
    return False, experiments, True


def explore(
    channel: host.Channel, state: Mapping[str, Any], observed_cells: Sequence[str]
) -> dict[str, Any]:
    """Breadth-first over request sequences, expanded until a level adds no new observation.

    The convergence criterion is frozen here and is a property of the search, not of any carrier:
    a level that produces no observation the learner has not already seen ends the expansion, and
    the certificate records which level that was. Nothing asserts that some depth is deep enough.
    `bounded` stops at depth two instead, which is a genuinely different component and the reason
    the composition space is an axis at all.

    A learner whose budget runs out first gets `closed: false`, and every downstream reading of a
    non-closed exploration is `undetermined` rather than a refusal.
    """
    meta = channel.describe()
    alphabet = alphabet_for(meta, state["action_width"])
    width = int(state["observation_width"])
    names = [str(item) for item in observed_cells]
    narrowed = names[:width]
    ceiling = (
        BOUNDED_COMPOSITION_DEPTH if state["composition_space"] == BOUNDED_SPACE else None
    )

    known: dict[tuple[int, ...], list[tuple[str, int]]] = {}
    alternates: dict[tuple[int, ...], list[list[tuple[str, int]]]] = {}
    frontier: list[list[tuple[str, int]]] = [[]]
    depth = 0
    closed = False
    exhausted = False
    complete_for_the_bound = False
    while frontier:
        if ceiling is not None and depth >= ceiling:
            # A bounded space stops because it was told to. That is not a fixed point, but it is
            # still completeness of a kind the experiment depends on: every sequence the composition
            # space admits has been tried. Conflating the two costs the milestone its bounded arm --
            # a first draft reported `closed: false` here, so every bounded attempt came back
            # `undetermined` with a budget reason while only two attempts in eighty-eight had
            # actually reached the ceiling.
            complete_for_the_bound = True
            break
        depth += 1
        following: list[list[tuple[str, int]]] = []
        for prefix in frontier:
            for name, argument in alphabet:
                candidate = prefix + [(name, argument)]
                if channel.invocations_left < len(candidate) + 1:
                    exhausted = True
                    break
                observed = _replay(channel, meta, candidate, names)
                if observed is None:
                    continue
                projection = observed[:width]
                if projection in known:
                    # A second way of arriving at what the interface calls the same place. Kept,
                    # because comparing the two is the only evidence the learner can ever get that
                    # it is not the same place.
                    if len(alternates.setdefault(projection, [])) < 1:
                        alternates[projection].append(candidate)
                    continue
                known[projection] = candidate
                following.append(candidate)
            if exhausted:
                break
        if exhausted:
            break
        if not following:
            closed = True
            break
        frontier = following

    nondeterministic, distinguished, distinguishing_completed = _distinguish(
        channel, meta, names, width, alphabet, known, alternates
    )
    if not distinguishing_completed:
        # An exploration whose distinguishing experiments were cut short has not finished, whatever
        # its frontier did. Everything downstream of an unfinished exploration is `undetermined`.
        closed = False
        complete_for_the_bound = False
        exhausted = True

    return {
        "schema": MODEL_SCHEMA,
        # Two different completeness facts, kept apart because they justify different things.
        # `closed_by_fixed_point` is a level that added nothing new; `complete_for_the_bound` is
        # every sequence the composition space admits having been tried. Either makes a refusal a
        # reach fact; neither is budget exhaustion.
        "closed_by_fixed_point": bool(closed),
        "complete_for_the_bound": bool(complete_for_the_bound),
        "closed": bool(closed or complete_for_the_bound),
        "budget_exhausted": bool(exhausted),
        "levels_expanded": depth,
        "closed_at_level": depth if closed else None,
        "composition_space": state["composition_space"],
        "composition_ceiling": ceiling,
        "action_width": int(state["action_width"]),
        "observation_width": width,
        "observed_cells": list(names),
        "narrowed_cells": list(narrowed),
        "alphabet_size": len(alphabet),
        "projections": {key: list(value) for key, value in sorted(known.items())},
        "observationally_nondeterministic": bool(nondeterministic),
        "distinguishing_completed": bool(distinguishing_completed),
        "distinguishing_experiments": int(distinguished),
        "projections_reached_two_ways": len(alternates),
        "reach_size": len(known),
        "invocations_used": channel.invocations_used,
    }


def construct(model: Mapping[str, Any], target: Sequence[int]) -> dict[str, Any]:
    """Does the learner hold a request sequence it believes lands on the target?

    Belief is the operative word, and the design depends on it. The target is stated over every
    observable cell; a learner parsing fewer of them compares the narrowed projection and cannot
    tell whether the rest agrees. So a narrow learner can hand back a sequence in good faith that
    does not arrive -- and on an unreachable demand it can hand back a sequence for a target the
    carrier structurally cannot show, which is the invented adapter G1 names.

    Nothing here checks that against the carrier, because the learner has no carrier to check it
    against. The evaluator replays the sequence and scores where it actually lands.

    One thing the learner may legitimately notice, and does: if its exploration answered the same
    request two different ways from what its interface calls the same place, then its projection is
    demonstrably not a state, and a match on that projection is not evidence of anything. A claim is
    withheld there. Where no such collision was seen the learner has no reason to doubt its view and
    claims -- which is an honest epistemic position and is exactly where an invented adapter comes
    from. The alternative, refusing whenever the interface is narrow, would be a system that knows
    its own width rather than one that learned something.
    """
    wanted = tuple(int(value) for value in target)
    width = int(model["observation_width"])
    narrowed = wanted[:width]
    sequence = model["projections"].get(narrowed)
    verifiable = width >= len(wanted)
    trustworthy = verifiable or not bool(model["observationally_nondeterministic"])
    return {
        "schema": "m113-construction-v1",
        "target": list(wanted),
        "narrowed_target": list(narrowed),
        "interface_covers_the_target": verifiable,
        "projection_found": sequence is not None,
        "view_is_demonstrably_not_a_state": bool(model["observationally_nondeterministic"])
        and not verifiable,
        "constructible": bool(sequence is not None and trustworthy),
        "sequence": [list(item) for item in sequence] if sequence is not None and trustworthy else None,
        "reach_size": int(model["reach_size"]),
    }


# ----------------------------------------------------------------------------------------
# The three axes.
# ----------------------------------------------------------------------------------------


def extend_action_vocabulary(
    state: Mapping[str, Any], meta: Mapping[str, Any]
) -> dict[str, Any]:
    declared = len(list(meta["actions"]))
    width = int(state["action_width"]) + 1
    if width > declared:
        return {
            "confirmed": False,
            "component": COMPONENT_ACTIONS,
            "reason": "the carrier declares no further action",
        }
    return {
        "confirmed": True,
        "component": COMPONENT_ACTIONS,
        "action_width": width,
        "next_state": create_state(
            action_width=width,
            observation_width=int(state["observation_width"]),
            composition_space=state["composition_space"],
            rules=state["rules"],
            policy=state["policy"],
            probe_budget=int(state["probe_budget"]),
            pooled_record=state["pooled_record"],
        ),
    }


def extend_observation_interface(
    state: Mapping[str, Any], observed_cells: Sequence[str]
) -> dict[str, Any]:
    width = int(state["observation_width"]) + 1
    if width > len(list(observed_cells)):
        return {
            "confirmed": False,
            "component": COMPONENT_OBSERVATION,
            "reason": "the response carries no further field",
        }
    return {
        "confirmed": True,
        "component": COMPONENT_OBSERVATION,
        "observation_width": width,
        "next_state": create_state(
            action_width=int(state["action_width"]),
            observation_width=width,
            composition_space=state["composition_space"],
            rules=state["rules"],
            policy=state["policy"],
            probe_budget=int(state["probe_budget"]),
            pooled_record=state["pooled_record"],
        ),
    }


def widen_composition_space(state: Mapping[str, Any]) -> dict[str, Any]:
    if state["composition_space"] == COMPLETE_SPACE:
        return {
            "confirmed": False,
            "component": COMPONENT_COMPOSITION,
            "reason": "the composition space is already expanded to a fixed point",
        }
    return {
        "confirmed": True,
        "component": COMPONENT_COMPOSITION,
        "composition_space": COMPLETE_SPACE,
        "next_state": create_state(
            action_width=int(state["action_width"]),
            observation_width=int(state["observation_width"]),
            composition_space=COMPLETE_SPACE,
            rules=state["rules"],
            policy=state["policy"],
            probe_budget=int(state["probe_budget"]),
            pooled_record=state["pooled_record"],
        ),
    }


def extension_for(
    state: Mapping[str, Any], component: str, meta: Mapping[str, Any], observed_cells: Sequence[str]
) -> dict[str, Any]:
    if component == COMPONENT_OBSERVATION:
        return extend_observation_interface(state, observed_cells)
    if component == COMPONENT_COMPOSITION:
        return widen_composition_space(state)
    return extend_action_vocabulary(state, meta)


# ----------------------------------------------------------------------------------------
# Features, in the inherited vocabulary, computed from what the learner actually observed.
# ----------------------------------------------------------------------------------------


def failure_features(
    state: Mapping[str, Any],
    model: Mapping[str, Any],
    target: Sequence[int],
    step_models: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """The producer's three features, read off this carrier's structure.

    `g0` is the general reading of `demand_needs_an_unread_signal`, and it is a thing the learner
    watched happen rather than a restatement of how wide its interface is: somewhere in the
    exploration, one request was answered two different ways from what the interface reports as the
    same place. `g1` and `g2` are computed from a one-step widening of the action vocabulary,
    exactly as M110 computed them from a one-step operator addition.

    Nothing here reads the carrier. The features are functions of what the learner observed through
    the channel, which is the only honest way to compute them for a body whose source it cannot see.
    """
    wanted = tuple(int(value) for value in target)

    g0 = bool(model["observationally_nondeterministic"])
    step = step_models.get(COMPONENT_ACTIONS)
    if step is None:
        g1 = True
        g2 = False
    else:
        # `projection_found`, not `constructible`. `g1` is the producer's
        # `candidate_search_exhausted_for_this_demand` -- a fact about whether the search turned
        # anything up, not about whether the learner would stake a claim on it. Reading the trusted
        # verdict here couples `g1` to `g0`: withholding a claim whenever the view is not a state
        # would make `g0` true imply `g1` true, four of the eight feature rows would become
        # unreachable, and the reachable arm would never once land on a row where the inherited
        # cascades disagree. That was measured before this line was written.
        g1 = not construct(step, wanted)["projection_found"]
        g2 = int(step["reach_size"]) > int(model["reach_size"])

    values = (bool(g0), bool(g1), bool(g2))
    return {
        "schema": "m113-failure-features-v1",
        "features": list(FEATURE_NAMES),
        "values": [bool(value) for value in values],
        "row_index": FEATURE_ROWS.index(values),
    }


def attribute(state: Mapping[str, Any], features: Mapping[str, Any]) -> dict[str, Any]:
    """Delegated to the producer module unchanged. A reimplementation would end the chain."""
    return lineage.attribute({"rules": list(state["rules"])}, dict(features))


def record_says_undetermined(state: Mapping[str, Any], row_index: int) -> bool:
    """Does the lineage's own inherited record mark this feature row as undetermined?

    This is the only thing the lineage has to go on before it spends anything. M111 acquired that
    record on the project's own worlds; whether it still describes a carrier the project did not
    design is precisely what M113 measures, and it is allowed to be wrong.
    """
    record = state.get("pooled_record") or {}
    undetermined = record.get("undetermined") or []
    return int(row_index) in {int(value) for value in undetermined}


# ----------------------------------------------------------------------------------------
# Resolution: one machinery step, an identical budget in every arm, three possible answers.
# ----------------------------------------------------------------------------------------


def resolve(
    state: Mapping[str, Any],
    channel: host.Channel,
    demand: Mapping[str, Any],
) -> dict[str, Any]:
    """Try to construct the demand; if that fails, extend exactly one component and try again.

    Every arm enters here with the same adapter, the same channel budget and the same demand. The
    only thing that differs is what `attribute` says, and whether a policy spends the one probe.
    """
    current = decode_state(state)
    observed_cells = [str(item) for item in demand["observed_cells"]]
    target = [int(value) for value in demand["target"]]
    meta = channel.describe()
    trace: list[dict[str, Any]] = []
    probes_spent = 0
    probe_budget = int(current["probe_budget"])

    for step_index in range(MACHINERY_STEP_BUDGET + 1):
        model = explore(channel, current, observed_cells)
        invocations = channel.invocations_used
        built = construct(model, target)
        if built["constructible"]:
            return _outcome(
                "constructed",
                current,
                trace,
                sequence=built["sequence"],
                invocations=invocations,
                model=model,
                probes_spent=probes_spent,
            )
        if model["budget_exhausted"] or not model["closed"]:
            return _outcome(
                "undetermined",
                current,
                trace,
                reason=UNDETERMINED_BUDGET,
                invocations=invocations,
                model=model,
                probes_spent=probes_spent,
            )
        if step_index == MACHINERY_STEP_BUDGET:
            break

        # One-step lookahead on the action axis: the two features that need it, and nothing else.
        step_models: dict[str, dict[str, Any]] = {}
        widened = extend_action_vocabulary(current, meta)
        if widened["confirmed"]:
            step_models[COMPONENT_ACTIONS] = explore(
                channel, widened["next_state"], observed_cells
            )
            invocations = channel.invocations_used

        features = failure_features(current, model, target, step_models)
        blame = attribute(current, features)
        entry: dict[str, Any] = {
            "step": step_index,
            "features": features,
            "attribution": blame,
            "reach_before": int(model["reach_size"]),
        }

        # M111's contribution: before committing, ask whether the lineage's own record says this
        # row does not determine the answer, and spend the scarce probe if a policy fires there.
        fires = diagnosis.policy_fires(current["policy"], features["row_index"])
        entry["policy_fires"] = bool(fires)
        if fires and probes_spent < probe_budget:
            probed = _probe_components(current, channel, observed_cells, target, meta)
            probes_spent += 1
            invocations = channel.invocations_used
            entry["probe"] = probed["report"]
            if probed["component"] is not None:
                blame = {
                    "component": probed["component"],
                    "mode": "diagnostic_probe",
                    "rule_id": None,
                    "generation": None,
                }
                entry["attribution"] = blame
            else:
                trace.append(entry)
                return _outcome(
                    "undetermined",
                    current,
                    trace,
                    reason=UNDETERMINED_VOCABULARY,
                    invocations=invocations,
                    model=model,
                    probes_spent=probes_spent,
                )
        elif fires and probes_spent >= probe_budget:
            entry["probe"] = {"spent": False, "reason": "probe budget exhausted"}
            trace.append(entry)
            return _outcome(
                "undetermined",
                current,
                trace,
                reason=UNDETERMINED_VOCABULARY,
                invocations=invocations,
                model=model,
                probes_spent=probes_spent,
            )

        extension = extension_for(current, blame["component"], meta, observed_cells)
        entry["extension"] = {k: v for k, v in extension.items() if k != "next_state"}
        trace.append(entry)
        if not extension["confirmed"]:
            return _outcome(
                "refused",
                current,
                trace,
                reason=extension["reason"],
                invocations=invocations,
                model=model,
                probes_spent=probes_spent,
                closed=True,
            )
        current = extension["next_state"]

    final_model = explore(channel, current, observed_cells)
    invocations = channel.invocations_used
    final = construct(final_model, target)
    if final["constructible"]:
        return _outcome(
            "constructed",
            current,
            trace,
            sequence=final["sequence"],
            invocations=invocations,
            model=final_model,
            probes_spent=probes_spent,
        )
    if not final_model["closed"]:
        return _outcome(
            "undetermined",
            current,
            trace,
            reason=UNDETERMINED_BUDGET,
            invocations=invocations,
            model=final_model,
            probes_spent=probes_spent,
        )
    return _outcome(
        "refused",
        current,
        trace,
        reason="the machinery step budget was spent and the exploration closed without the target",
        invocations=invocations,
        model=final_model,
        probes_spent=probes_spent,
        closed=True,
    )


def _probe_components(
    state: Mapping[str, Any],
    channel: host.Channel,
    observed_cells: Sequence[str],
    target: Sequence[int],
    meta: Mapping[str, Any],
) -> dict[str, Any]:
    """Extend each live component, test whether it resolves the demand, and roll back.

    The state afterwards is the state before, and that is measured rather than promised: the digest
    is compared, exactly as M111 does. A probe that leaves exactly one resolving component
    determines the answer; a probe that leaves none or more than one does not, and saying so is the
    point of having it.
    """
    before = dict(state)["state_digest"]
    resolving: list[str] = []
    reports: dict[str, Any] = {}
    for component in (COMPONENT_OBSERVATION, COMPONENT_COMPOSITION, COMPONENT_ACTIONS):
        extension = extension_for(state, component, meta, observed_cells)
        if not extension["confirmed"]:
            reports[component] = {"available": False, "reason": extension["reason"]}
            continue
        model = explore(channel, extension["next_state"], observed_cells)
        built = construct(model, target)
        reports[component] = {
            "available": True,
            "resolves": bool(built["constructible"]),
            "closed": bool(model["closed"]),
            "reach_size": int(model["reach_size"]),
        }
        if built["constructible"]:
            resolving.append(component)
    after = decode_state(state)["state_digest"]
    return {
        "component": resolving[0] if len(resolving) == 1 else None,
        "report": {
            "spent": True,
            "state_unchanged": before == after,
            "resolving_components": sorted(resolving),
            "determined": len(resolving) == 1,
            "components": reports,
        },
    }


def _outcome(
    verdict: str,
    state: Mapping[str, Any],
    trace: Sequence[Mapping[str, Any]],
    *,
    sequence: Sequence[Sequence[Any]] | None = None,
    reason: str | None = None,
    invocations: int = 0,
    model: Mapping[str, Any] | None = None,
    probes_spent: int = 0,
    closed: bool | None = None,
) -> dict[str, Any]:
    return {
        "schema": OUTCOME_SCHEMA,
        "verdict": verdict,
        "reason": reason,
        "sequence": [list(item) for item in sequence] if sequence else None,
        "invocations_used": int(invocations),
        "probes_spent": int(probes_spent),
        "steps": len(list(trace)),
        "trace": [dict(item) for item in trace],
        "final_state_digest": decode_state(state)["state_digest"],
        "final_action_width": int(state["action_width"]),
        "final_observation_width": int(state["observation_width"]),
        "final_composition_space": state["composition_space"],
        "exploration_closed": bool(model["closed"]) if model is not None else bool(closed),
        "reach_size": int(model["reach_size"]) if model is not None else None,
    }
