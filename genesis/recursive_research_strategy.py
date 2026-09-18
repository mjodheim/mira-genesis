"""Evidence-driven recursive research strategy for Genesis.

This module adds one mutable level above body, policy and MetaPolicy search without moving the
scientific authority boundary.  A lineage may hold a content-addressed *research strategy* that
chooses among inert candidate experiments using only aggregate, explicitly admitted observations.
The strategy itself may change when repeated outcomes falsify its search preferences.

The important split is the same one used elsewhere in Genesis:

* the trust root/evaluator decides whether a descendant is actually better;
* this module only decides which experiment is worth trying next;
* hidden cases, grader state and evaluator internals never enter the research memory;
* every strategy change names its parent digest and is persisted in lineage state.

That makes the research process recursively mutable while keeping selection authority outside the
mutable lineage.  It is DEVELOPMENT apparatus, not a new scientific result.
"""
from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence

from genesis import state as lineage_state
from genesis.trust_root import digest_of, provenance

STRATEGY_SCHEMA = "genesis-recursive-research-strategy-v1"
OUTCOME_SCHEMA = "genesis-recursive-research-outcome-v1"
CANDIDATE_SCHEMA = "genesis-recursive-research-candidate-v1"
MEMORY_SCHEMA = "genesis-recursive-research-memory-v1"
PLAN_SCHEMA = "genesis-recursive-research-plan-v1"
STRATEGY_TOOL_NAME = "recursive_research_strategy"
STRATEGY_ROLE = "lineage_experiment_search"

WEIGHT_KEYS = (
    "novelty",
    "information_gain",
    "causal_specificity",
    "local_validation",
    "safety",
    "repeat_failure",
    "stepping_stone",
    "unresolved_axis",
)

DEFAULT_WEIGHTS = {
    "novelty": 5,
    "information_gain": 5,
    "causal_specificity": 4,
    "local_validation": 3,
    "safety": 6,
    "repeat_failure": 7,
    "stepping_stone": 3,
    "unresolved_axis": 5,
}


class RecursiveResearchError(RuntimeError):
    """Raised when recursive research state would exceed its admitted information boundary."""


def _strings(values: Iterable[Any], *, field: str, maximum: int = 64) -> list[str]:
    result: list[str] = []
    for value in values:
        text = str(value).strip()
        if not text:
            raise RecursiveResearchError("%s contains an empty value" % field)
        result.append(text)
    if len(result) > maximum:
        raise RecursiveResearchError("%s exceeds its bounded item count" % field)
    if len(set(result)) != len(result):
        raise RecursiveResearchError("%s contains a duplicate" % field)
    return sorted(result)


def create_strategy(
    *,
    weights: Mapping[str, int] | None = None,
    generation: int = 0,
    parent_strategy_digest: str = "",
    evidence_memory_digest: str = "",
) -> dict[str, Any]:
    chosen = dict(DEFAULT_WEIGHTS if weights is None else weights)
    if set(chosen) != set(WEIGHT_KEYS):
        raise RecursiveResearchError("research strategy weights do not match the admitted schema")
    clean: dict[str, int] = {}
    for key in WEIGHT_KEYS:
        value = chosen[key]
        if isinstance(value, bool) or not isinstance(value, int) or value < 1 or value > 20:
            raise RecursiveResearchError("research strategy weight %r is outside [1, 20]" % key)
        clean[key] = value
    generation = int(generation)
    if generation < 0:
        raise RecursiveResearchError("research strategy generation may not be negative")
    parent = str(parent_strategy_digest or "")
    evidence = str(evidence_memory_digest or "")
    if generation == 0 and (parent or evidence):
        raise RecursiveResearchError("seed research strategy may not name parent or adaptation evidence")
    if generation > 0 and (not parent or not evidence):
        raise RecursiveResearchError(
            "descendant research strategy must name both parent and adaptation evidence"
        )
    payload = {
        "schema": STRATEGY_SCHEMA,
        "generation": generation,
        "parent_strategy_digest": parent,
        "evidence_memory_digest": evidence,
        "weights": clean,
    }
    return {**payload, "strategy_digest": digest_of(payload)}


def validate_strategy(record: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(record, Mapping) or record.get("schema") != STRATEGY_SCHEMA:
        raise RecursiveResearchError("research strategy uses an unrecognised schema")
    rebuilt = create_strategy(
        weights=dict(record.get("weights") or {}),
        generation=int(record.get("generation", -1)),
        parent_strategy_digest=str(record.get("parent_strategy_digest") or ""),
        evidence_memory_digest=str(record.get("evidence_memory_digest") or ""),
    )
    if rebuilt != dict(record):
        raise RecursiveResearchError("research strategy does not reconstruct from its own fields")
    return rebuilt


def create_outcome(
    *,
    attempt: int,
    family: str,
    target_axes: Sequence[str],
    mechanisms: Sequence[str],
    changed_regions: Sequence[str],
    hard_pass: bool,
    capability_deltas: Mapping[str, int],
    improvements: Sequence[str] = (),
    regressions: Sequence[str] = (),
    parent_kind: str = "champion",
    parent_lineage_depth: int = 0,
    parent_digest: str = "",
    child_digest: str = "",
    source_digest: str = "",
) -> dict[str, Any]:
    attempt = int(attempt)
    if attempt < 1:
        raise RecursiveResearchError("research outcome attempt must be positive")
    family = str(family).strip()
    if not family:
        raise RecursiveResearchError("research outcome must name a hypothesis family")
    parent_kind = str(parent_kind)
    if parent_kind not in {"champion", "neutral"}:
        raise RecursiveResearchError("research outcome parent kind is invalid")
    depth = int(parent_lineage_depth)
    if depth < 0:
        raise RecursiveResearchError("research outcome lineage depth may not be negative")
    deltas: dict[str, int] = {}
    for key, value in sorted(dict(capability_deltas).items()):
        if isinstance(value, bool) or not isinstance(value, int):
            raise RecursiveResearchError("capability delta %r is not an integer" % key)
        deltas[str(key)] = value
    payload = {
        "schema": OUTCOME_SCHEMA,
        "attempt": attempt,
        "family": family,
        "target_axes": _strings(target_axes, field="target_axes"),
        "mechanisms": _strings(mechanisms, field="mechanisms"),
        "changed_regions": _strings(changed_regions, field="changed_regions"),
        "hard_pass": bool(hard_pass),
        "capability_deltas": deltas,
        "improvements": _strings(improvements, field="improvements"),
        "regressions": _strings(regressions, field="regressions"),
        "parent_kind": parent_kind,
        "parent_lineage_depth": depth,
        "parent_digest": str(parent_digest),
        "child_digest": str(child_digest),
        "source_digest": str(source_digest),
    }
    return {**payload, "outcome_digest": digest_of(payload)}


def validate_outcome(record: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(record, Mapping) or record.get("schema") != OUTCOME_SCHEMA:
        raise RecursiveResearchError("research outcome uses an unrecognised schema")
    rebuilt = create_outcome(
        attempt=int(record.get("attempt", 0)),
        family=str(record.get("family") or ""),
        target_axes=list(record.get("target_axes") or []),
        mechanisms=list(record.get("mechanisms") or []),
        changed_regions=list(record.get("changed_regions") or []),
        hard_pass=bool(record.get("hard_pass")),
        capability_deltas=dict(record.get("capability_deltas") or {}),
        improvements=list(record.get("improvements") or []),
        regressions=list(record.get("regressions") or []),
        parent_kind=str(record.get("parent_kind") or ""),
        parent_lineage_depth=int(record.get("parent_lineage_depth", -1)),
        parent_digest=str(record.get("parent_digest") or ""),
        child_digest=str(record.get("child_digest") or ""),
        source_digest=str(record.get("source_digest") or ""),
    )
    if rebuilt != dict(record):
        raise RecursiveResearchError("research outcome does not reconstruct from its own fields")
    return rebuilt


def create_candidate(
    *,
    candidate_id: str,
    family: str,
    target_axes: Sequence[str],
    mechanisms: Sequence[str],
    changed_regions: Sequence[str],
    causal_claims: Sequence[str],
    local_checks: Sequence[str],
    risk_flags: Sequence[str] = (),
    parent_kind: str = "champion",
    parent_lineage_depth: int = 0,
    parent_digest: str = "",
) -> dict[str, Any]:
    candidate_id = str(candidate_id).strip()
    family = str(family).strip()
    if not candidate_id or not family:
        raise RecursiveResearchError("research candidate needs an id and hypothesis family")
    parent_kind = str(parent_kind)
    if parent_kind not in {"champion", "neutral"}:
        raise RecursiveResearchError("research candidate parent kind is invalid")
    depth = int(parent_lineage_depth)
    if depth < 0:
        raise RecursiveResearchError("research candidate lineage depth may not be negative")
    payload = {
        "schema": CANDIDATE_SCHEMA,
        "candidate_id": candidate_id,
        "family": family,
        "target_axes": _strings(target_axes, field="target_axes"),
        "mechanisms": _strings(mechanisms, field="mechanisms"),
        "changed_regions": _strings(changed_regions, field="changed_regions"),
        "causal_claims": _strings(causal_claims, field="causal_claims"),
        "local_checks": _strings(local_checks, field="local_checks"),
        "risk_flags": _strings(risk_flags, field="risk_flags"),
        "parent_kind": parent_kind,
        "parent_lineage_depth": depth,
        "parent_digest": str(parent_digest),
    }
    return {**payload, "candidate_digest": digest_of(payload)}


def validate_candidate(record: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(record, Mapping) or record.get("schema") != CANDIDATE_SCHEMA:
        raise RecursiveResearchError("research candidate uses an unrecognised schema")
    rebuilt = create_candidate(
        candidate_id=str(record.get("candidate_id") or ""),
        family=str(record.get("family") or ""),
        target_axes=list(record.get("target_axes") or []),
        mechanisms=list(record.get("mechanisms") or []),
        changed_regions=list(record.get("changed_regions") or []),
        causal_claims=list(record.get("causal_claims") or []),
        local_checks=list(record.get("local_checks") or []),
        risk_flags=list(record.get("risk_flags") or []),
        parent_kind=str(record.get("parent_kind") or ""),
        parent_lineage_depth=int(record.get("parent_lineage_depth", -1)),
        parent_digest=str(record.get("parent_digest") or ""),
    )
    if rebuilt != dict(record):
        raise RecursiveResearchError("research candidate does not reconstruct from its own fields")
    return rebuilt


def build_memory(
    outcomes: Sequence[Mapping[str, Any]],
    *,
    unresolved_axes: Sequence[str] = (),
) -> dict[str, Any]:
    validated = sorted((validate_outcome(item) for item in outcomes), key=lambda item: item["attempt"])
    attempts = [item["attempt"] for item in validated]
    if len(set(attempts)) != len(attempts):
        raise RecursiveResearchError("research history repeats an attempt identity")

    families: dict[str, dict[str, Any]] = {}
    all_mechanisms: set[str] = set()
    all_regions: set[str] = set()
    promotions = 0
    regressions = 0

    for item in validated:
        family = families.setdefault(
            item["family"],
            {
                "attempts": [],
                "zero_signal_count": 0,
                "promotion_count": 0,
                "regression_count": 0,
                "hard_fail_count": 0,
                "mechanisms": set(),
                "changed_regions": set(),
                "target_axes": set(),
            },
        )
        family["attempts"].append(item["attempt"])
        family["mechanisms"].update(item["mechanisms"])
        family["changed_regions"].update(item["changed_regions"])
        family["target_axes"].update(item["target_axes"])
        all_mechanisms.update(item["mechanisms"])
        all_regions.update(item["changed_regions"])

        positive = any(value > 0 for value in item["capability_deltas"].values()) or bool(
            item["improvements"]
        )
        negative = any(value < 0 for value in item["capability_deltas"].values()) or bool(
            item["regressions"]
        )
        if not item["hard_pass"]:
            family["hard_fail_count"] += 1
        elif positive and not negative:
            family["promotion_count"] += 1
            promotions += 1
        elif negative:
            family["regression_count"] += 1
            regressions += 1
        else:
            family["zero_signal_count"] += 1

    public_families: dict[str, Any] = {}
    for name in sorted(families):
        item = families[name]
        confidence = 1000
        for _ in range(int(item["zero_signal_count"])):
            confidence = (confidence * 55) // 100
        for _ in range(int(item["regression_count"]) + int(item["hard_fail_count"])):
            confidence = (confidence * 35) // 100
        for _ in range(int(item["promotion_count"])):
            confidence = min(1000, confidence + 400)
        public_families[name] = {
            "attempts": list(item["attempts"]),
            "zero_signal_count": int(item["zero_signal_count"]),
            "promotion_count": int(item["promotion_count"]),
            "regression_count": int(item["regression_count"]),
            "hard_fail_count": int(item["hard_fail_count"]),
            "mechanisms": sorted(item["mechanisms"]),
            "changed_regions": sorted(item["changed_regions"]),
            "target_axes": sorted(item["target_axes"]),
            "confidence_milli": confidence,
            "empirically_weakened": int(item["zero_signal_count"]) >= 2,
        }

    payload = {
        "schema": MEMORY_SCHEMA,
        "attempt_count": len(validated),
        "promotion_count": promotions,
        "regression_count": regressions,
        "families": public_families,
        "seen_mechanisms": sorted(all_mechanisms),
        "seen_changed_regions": sorted(all_regions),
        "unresolved_axes": _strings(unresolved_axes, field="unresolved_axes"),
        "outcome_digests": [item["outcome_digest"] for item in validated],
    }
    return {**payload, "memory_digest": digest_of(payload)}


def derive_strategy_descendant(
    strategy: Mapping[str, Any],
    memory: Mapping[str, Any],
) -> dict[str, Any]:
    current = validate_strategy(strategy)
    if memory.get("schema") != MEMORY_SCHEMA:
        raise RecursiveResearchError("strategy adaptation requires a recursive-research memory")
    unsigned = dict(memory)
    recorded = unsigned.pop("memory_digest", "")
    if recorded != digest_of(unsigned):
        raise RecursiveResearchError("research memory digest does not reproduce")

    if current["evidence_memory_digest"] == memory["memory_digest"]:
        return {"changed": False, "strategy": current, "reasons": []}

    weights = dict(current["weights"])
    reasons: list[str] = []
    weakened = [
        name
        for name, item in sorted(dict(memory.get("families") or {}).items())
        if bool(item.get("empirically_weakened"))
    ]
    if weakened:
        weights["novelty"] = min(20, weights["novelty"] + 1)
        weights["information_gain"] = min(20, weights["information_gain"] + 1)
        weights["repeat_failure"] = min(20, weights["repeat_failure"] + 2)
        reasons.append("repeated zero-signal families: " + ", ".join(weakened))

    if int(memory.get("attempt_count", 0)) >= 4 and int(memory.get("promotion_count", 0)) == 0:
        weights["causal_specificity"] = min(20, weights["causal_specificity"] + 1)
        weights["unresolved_axis"] = min(20, weights["unresolved_axis"] + 1)
        reasons.append("four or more observations without a promotion")

    if int(memory.get("regression_count", 0)) > 0:
        weights["safety"] = min(20, weights["safety"] + 2)
        reasons.append("observed protected regression")

    if weights == current["weights"]:
        return {"changed": False, "strategy": current, "reasons": []}

    descendant = create_strategy(
        weights=weights,
        generation=int(current["generation"]) + 1,
        parent_strategy_digest=current["strategy_digest"],
        evidence_memory_digest=str(memory["memory_digest"]),
    )
    return {"changed": True, "strategy": descendant, "reasons": reasons}


def _candidate_score(
    candidate: Mapping[str, Any],
    memory: Mapping[str, Any],
    strategy: Mapping[str, Any],
) -> dict[str, Any]:
    item = validate_candidate(candidate)
    held = validate_strategy(strategy)
    families = dict(memory.get("families") or {})
    family = dict(families.get(item["family"]) or {})
    seen_mechanisms = set(memory.get("seen_mechanisms") or [])
    seen_regions = set(memory.get("seen_changed_regions") or [])
    unresolved = set(memory.get("unresolved_axes") or [])

    new_mechanisms = sorted(set(item["mechanisms"]) - seen_mechanisms)
    new_regions = sorted(set(item["changed_regions"]) - seen_regions)
    family_unseen = item["family"] not in families
    novelty_units = len(new_mechanisms) + len(new_regions) + (2 if family_unseen else 0)

    family_mechanisms = set(family.get("mechanisms") or [])
    mechanism_pivot = bool(family) and bool(set(item["mechanisms"]) - family_mechanisms)
    weakened = bool(family.get("empirically_weakened"))
    information_units = len(set(item["target_axes"]) & unresolved)
    if mechanism_pivot and weakened:
        information_units += 2
    elif family_unseen:
        information_units += 1

    causal_units = min(4, len(item["causal_claims"]))
    validation_units = min(4, len(item["local_checks"]))
    safety_units = max(0, 3 - len(item["risk_flags"]))
    repeat_penalty = int(family.get("zero_signal_count", 0))
    if weakened and not mechanism_pivot:
        repeat_penalty += 2

    depth = int(item["parent_lineage_depth"])
    if item["parent_kind"] == "neutral" and depth == 1:
        stepping_units = 2
    elif item["parent_kind"] == "neutral" and depth >= 2:
        stepping_units = -1
    else:
        stepping_units = 0

    unresolved_units = len(set(item["target_axes"]) & unresolved)
    weights = held["weights"]
    score = (
        weights["novelty"] * novelty_units
        + weights["information_gain"] * information_units
        + weights["causal_specificity"] * causal_units
        + weights["local_validation"] * validation_units
        + weights["safety"] * safety_units
        + weights["stepping_stone"] * stepping_units
        + weights["unresolved_axis"] * unresolved_units
        - weights["repeat_failure"] * repeat_penalty
    )
    return {
        "candidate": item,
        "score": score,
        "components": {
            "novelty_units": novelty_units,
            "information_units": information_units,
            "causal_units": causal_units,
            "validation_units": validation_units,
            "safety_units": safety_units,
            "repeat_penalty": repeat_penalty,
            "stepping_units": stepping_units,
            "unresolved_units": unresolved_units,
            "new_mechanisms": new_mechanisms,
            "new_regions": new_regions,
            "mechanism_pivot": mechanism_pivot,
        },
    }


def tournament(
    candidates: Sequence[Mapping[str, Any]],
    *,
    memory: Mapping[str, Any],
    strategy: Mapping[str, Any],
) -> dict[str, Any]:
    if not candidates:
        raise RecursiveResearchError("candidate tournament is empty")
    ranked = [_candidate_score(item, memory, strategy) for item in candidates]
    ranked.sort(key=lambda item: (-int(item["score"]), item["candidate"]["candidate_digest"]))
    return {
        "strategy_digest": validate_strategy(strategy)["strategy_digest"],
        "memory_digest": str(memory["memory_digest"]),
        "ranking": ranked,
        "selected_candidate_digest": ranked[0]["candidate"]["candidate_digest"],
    }


SEED_PROVENANCE = provenance(
    "host_written",
    produced_by="Genesis recursive research strategy admission",
    detail="bounded deterministic search-strategy weights admitted prospectively",
)


def _strategy_tool(genesis) -> Mapping[str, Any] | None:
    matches = [
        tool
        for tool in genesis.state.get("tools", [])
        if tool.get("name") == STRATEGY_TOOL_NAME and tool.get("role") == STRATEGY_ROLE
    ]
    if not matches:
        return None
    if len(matches) != 1:
        raise RecursiveResearchError("lineage carries duplicate recursive research strategies")
    return matches[0]


def bound_strategy(genesis) -> dict[str, Any] | None:
    tool = _strategy_tool(genesis)
    if tool is None:
        return None
    artifact = tool.get("artifact")
    if not isinstance(artifact, Mapping):
        raise RecursiveResearchError("recursive research tool carries no strategy artifact")
    return validate_strategy(artifact)


def _replace_strategy(genesis, strategy, *, provenance_record, observation=None) -> None:
    validated = validate_strategy(strategy)
    tools = []
    replaced = False
    for tool in genesis.state.get("tools", []):
        if tool.get("name") == STRATEGY_TOOL_NAME and tool.get("role") == STRATEGY_ROLE:
            if replaced:
                raise RecursiveResearchError("lineage carries duplicate recursive research strategies")
            tools.append(
                {
                    "name": STRATEGY_TOOL_NAME,
                    "role": STRATEGY_ROLE,
                    "artifact": validated,
                    "provenance": provenance_record,
                }
            )
            replaced = True
        else:
            tools.append(tool)
    if not replaced:
        tools.append(
            {
                "name": STRATEGY_TOOL_NAME,
                "role": STRATEGY_ROLE,
                "artifact": validated,
                "provenance": provenance_record,
            }
        )
    observations = list(genesis.state.get("observations", []))
    if observation is not None:
        observations.append(dict(observation))
    genesis.state = lineage_state.create_state(
        body_digest=genesis.state["body_digest"],
        components=genesis.state["components"],
        vocabulary=genesis.state["vocabulary"],
        tools=tools,
        acquisitions=genesis.state["acquisitions"],
        observations=observations,
        generation=genesis.state["generation"],
    )


def admit_seed_strategy(genesis, strategy: Mapping[str, Any] | None = None) -> bool:
    incoming = validate_strategy(strategy or create_strategy())
    current = bound_strategy(genesis)
    if current is not None:
        if current != incoming:
            raise RecursiveResearchError(
                "lineage already holds a research strategy; replacement requires evidence-backed adaptation"
            )
        return False
    _replace_strategy(genesis, incoming, provenance_record=SEED_PROVENANCE)
    genesis.journal.append(
        "observation",
        genesis.state["generation"],
        {
            "arm": "recursive_research_strategy_admission",
            "strategy_digest": incoming["strategy_digest"],
            "new_state_digest": genesis.state["state_digest"],
        },
    )
    return True


def _install_descendant(genesis, descendant, *, memory, reasons) -> None:
    current = bound_strategy(genesis)
    if current is None:
        raise RecursiveResearchError("lineage has no research strategy to evolve")
    child = validate_strategy(descendant)
    if child["parent_strategy_digest"] != current["strategy_digest"]:
        raise RecursiveResearchError("research strategy descendant does not name the current strategy")
    observation = {
        "kind": "recursive_research_strategy_updated",
        "prior_strategy_digest": current["strategy_digest"],
        "new_strategy_digest": child["strategy_digest"],
        "memory_digest": memory["memory_digest"],
        "reasons": list(reasons),
    }
    _replace_strategy(
        genesis,
        child,
        provenance_record=provenance(
            "lineage_owned",
            produced_by="recursive research strategy adaptation",
            detail=memory["memory_digest"],
        ),
        observation=observation,
    )
    genesis.journal.append(
        "observation",
        genesis.state["generation"],
        {
            "arm": "recursive_research_strategy_update",
            "update": observation,
            "new_state_digest": genesis.state["state_digest"],
        },
    )


def adaptive_plan(
    genesis,
    *,
    outcomes: Sequence[Mapping[str, Any]],
    candidates: Sequence[Mapping[str, Any]],
    unresolved_axes: Sequence[str] = (),
    seed_strategy: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Adapt the held strategy from aggregate evidence, then choose one pre-evaluation candidate.

    The call performs no scientific evaluation and reads no hidden case.  Its only authority is to
    install a direct descendant of the lineage-held research strategy and to record which inert
    candidate that strategy selected.
    """
    if bound_strategy(genesis) is None:
        admit_seed_strategy(genesis, seed_strategy or create_strategy())
    elif seed_strategy is not None and validate_strategy(seed_strategy) != bound_strategy(genesis):
        raise RecursiveResearchError("cannot replace an already-held strategy through seed admission")

    before = bound_strategy(genesis)
    if before is None:  # pragma: no cover - admission above closes this path
        raise RecursiveResearchError("research strategy admission failed")
    memory = build_memory(outcomes, unresolved_axes=unresolved_axes)
    adaptation = derive_strategy_descendant(before, memory)
    if adaptation["changed"]:
        _install_descendant(
            genesis,
            adaptation["strategy"],
            memory=memory,
            reasons=adaptation["reasons"],
        )
    current = bound_strategy(genesis)
    if current is None:  # pragma: no cover
        raise RecursiveResearchError("lineage lost its research strategy")

    competition = tournament(candidates, memory=memory, strategy=current)
    payload = {
        "schema": PLAN_SCHEMA,
        "prior_strategy_digest": before["strategy_digest"],
        "strategy_digest": current["strategy_digest"],
        "strategy_evolved": current["strategy_digest"] != before["strategy_digest"],
        "adaptation_reasons": list(adaptation["reasons"]),
        "memory_digest": memory["memory_digest"],
        "selected_candidate_digest": competition["selected_candidate_digest"],
        "ranking": competition["ranking"],
    }
    plan = {**payload, "plan_digest": digest_of(payload)}
    observations = list(genesis.state.get("observations", [])) + [plan]
    genesis.state = lineage_state.create_state(
        body_digest=genesis.state["body_digest"],
        components=genesis.state["components"],
        vocabulary=genesis.state["vocabulary"],
        tools=genesis.state["tools"],
        acquisitions=genesis.state["acquisitions"],
        observations=observations,
        generation=genesis.state["generation"],
    )
    genesis.journal.append(
        "observation",
        genesis.state["generation"],
        {
            "arm": "recursive_research_plan",
            "plan_digest": plan["plan_digest"],
            "strategy_digest": current["strategy_digest"],
            "selected_candidate_digest": plan["selected_candidate_digest"],
            "new_state_digest": genesis.state["state_digest"],
        },
    )
    return plan
