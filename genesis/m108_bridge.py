"""Bridge M108's qualified lineage-held attribution rule into the Genesis runtime.

This is DEVELOPMENT integration apparatus. M108 itself remains frozen. The bridge replays the
committed M108 history, requires that the operator table is exactly the state produced by the M107
bridge, acquires the unchanged M108 attribution rule, then packages that state as a reconstructible
Genesis ``ConfiguredBody``.

The dependency semantics are intentional and executable:

* with neither acquisition, the body has M107's original monotone operator table and hardwired M108
  attribution;
* with M107 only, it has M107's acquired operator table but M108's original hardwired attribution;
* with M107 + M108, it has the state-held attribution rule M108 acquired from its history.

That makes Genesis' ordinary runtime-derived ablation meaningful. Removing M107 from the M108 body
leaves the M108 dependency marker and all configuration untouched, but the rule cannot be active
because the language that made it expressible is gone. Removing M108 while retaining M107 restores
M108 M0. No caller supplies either counterfactual arm.
"""
from __future__ import annotations

import functools
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from genesis import m107_bridge
from genesis import trust_root as tr
from genesis.artifacts import ConfiguredBody
from genesis.loop import LineageContext, Proposal
from metamorphosis import m107_runtime as m107
from metamorphosis import m108_runtime as m108

ROOT = Path(__file__).resolve().parents[1]
EPISODES_PATH = ROOT / "experiments" / "M108" / "EPISODES.json"
DEMAND_PATH = ROOT / "experiments" / "M108" / "DEMAND.json"

BODY_TARGET = "genesis.m108_bridge:M108Body"
ACQUISITION_NAME = "m108_attribution_rule"


class M108BridgeError(RuntimeError):
    """Raised when the committed M108 chain no longer adapts without changing its meaning."""


def _monotone_state() -> dict[str, Any]:
    return m108.create_state(
        m107.initial_operators(), signal_width=m108.BASE_SIGNAL_WIDTH, attribution=None
    )


def _m0_from_configured(configured: Mapping[str, Any]) -> dict[str, Any]:
    return m108.create_state(
        configured["operators"], signal_width=m108.BASE_SIGNAL_WIDTH, attribution=None
    )


@functools.lru_cache(maxsize=64)
def _resolution(state_json: str, target: tuple[bool, ...]) -> dict[str, Any]:
    state = m108.decode_state(json.loads(state_json))
    demand = m108.capability_demand("genesis-m108-bridge", target)
    return m108.resolve(state, demand)


class M108Body:
    """One body that retains the M107 task family and can exercise M108 world demands."""

    def __init__(self, *, state: Mapping[str, Any], capabilities: Sequence[str] = ()) -> None:
        configured = m108.decode_state(dict(state))
        held = frozenset(str(name) for name in capabilities)
        allowed = {m107_bridge.ACQUISITION_NAME, ACQUISITION_NAME}
        unexpected = held - allowed
        if unexpected:
            raise M108BridgeError(
                "M108 bridge received unknown capabilities: %s" % ", ".join(sorted(unexpected))
            )
        if configured["signal_width"] != m108.BASE_SIGNAL_WIDTH:
            raise M108BridgeError("M108 configured attribution state is not at its acquisition width")
        if m107_bridge.ACQUISITION_NAME in held and len(configured["operators"]) <= len(
            m107.initial_operators()
        ):
            raise M108BridgeError(
                "M107 dependency is present but the configured M108 state contains no M107 extension"
            )
        if ACQUISITION_NAME in held and configured.get("attribution") is None:
            raise M108BridgeError(
                "M108 attribution dependency is present but the configured state carries no rule"
            )

        if m107_bridge.ACQUISITION_NAME not in held:
            active = _monotone_state()
        elif ACQUISITION_NAME not in held:
            active = _m0_from_configured(configured)
        else:
            active = configured

        self.state = active
        self.capabilities = held
        self._state_json = m108.canonical_json(active)

    def _attempt_m107(self, target: tuple[bool, ...], signals: tuple[bool, ...]) -> Any:
        image = m107.complete_image(self.state["operators"])
        expression = image.get(target)
        if expression is None:
            return m107_bridge.REFUSED
        return m107.execute_expression(
            m107.operator_map(self.state["operators"]), expression, signals
        )

    def _attempt_m108(self, target: tuple[bool, ...], signals: tuple[bool, ...]) -> Any:
        resolution = _resolution(self._state_json, target)
        if not resolution.get("confirmed"):
            return m107_bridge.REFUSED

        # This adapter can execute a resolution whose machinery changed the signal interface while
        # keeping the admitted M107 operator table. If an operator extension were part of the trace,
        # the final operator state is not published by M108's resolution record, so fail closed
        # rather than execute a witness under the wrong table.
        for step in resolution.get("trace") or []:
            attribution = step.get("attribution") or {}
            extension = step.get("extension") or {}
            if (
                attribution.get("component") == m108.COMPONENT_OPERATORS
                and extension.get("confirmed")
            ):
                return m107_bridge.REFUSED

        construction = resolution.get("construction") or {}
        witness = construction.get("witness")
        if witness is None or not construction.get("executes_to_target"):
            return m107_bridge.REFUSED
        width = int(resolution.get("final_signal_width", self.state["signal_width"]))
        return m108.execute_expression(
            {item["name"]: item for item in self.state["operators"]},
            witness,
            tuple(signals[:width]),
        )

    def attempt(self, task: Mapping[str, Any]) -> Any:
        target = tuple(bool(value) for value in (task.get("target") or []))
        signals = tuple(bool(value) for value in (task.get("signals") or []))
        if len(target) == len(m107.SIGNAL_ROWS) and len(signals) == m107.SIGNAL_COUNT:
            return self._attempt_m107(target, signals)
        if len(target) == len(m108.world_rows()) and len(signals) == m108.WORLD_SIGNAL_WIDTH:
            return self._attempt_m108(target, signals)
        raise M108BridgeError("task does not belong to the M107/M108 bridge evaluation family")


def _episodes_document() -> dict[str, Any]:
    document = json.loads(EPISODES_PATH.read_text(encoding="ascii"))
    if document.get("schema") != "m108-episodes-v1":
        raise M108BridgeError("committed M108 episode record has an unexpected schema")
    return document


def _demand_document() -> dict[str, Any]:
    document = json.loads(DEMAND_PATH.read_text(encoding="ascii"))
    if document.get("schema") != "m108-later-demand-v1":
        raise M108BridgeError("committed M108 demand record has an unexpected schema")
    m108.decode_demand(document.get("demand"))
    return document


def replay_frozen_attribution() -> dict[str, Any]:
    """Reproduce M108's attribution acquisition and its dependency on M107."""
    episodes_document = _episodes_document()
    episodes = [m108.decode_episode(item) for item in episodes_document.get("episodes") or []]
    if not episodes:
        raise M108BridgeError("committed M108 history contains no attribution episodes")
    m0_operators = [
        m107.decode_operator(item) for item in episodes_document.get("m0_operators") or []
    ]
    m0 = m108.create_state(m0_operators, signal_width=m108.BASE_SIGNAL_WIDTH)

    predecessor = m107_bridge.replay_frozen_acquisition()
    predecessor_operators = m107.decode_state(predecessor["next_state"])["operators"]
    if m108.canonical_json(predecessor_operators) != m108.canonical_json(m0_operators):
        raise M108BridgeError(
            "M108 M0 is no longer exactly the operator table produced by the frozen M107 replay"
        )

    blocked = m108.acquire_attribution(_monotone_state(), episodes, register_result=False)
    if blocked.get("confirmed") or blocked.get("reason") != "no_expressible_rule_reproduces_the_blame_record":
        raise M108BridgeError("M108 attribution is no longer structurally dependent on M107")
    if blocked.get("rule_space_size") != 4:
        raise M108BridgeError("the pre-M107 M108 rule space no longer has the qualified size")

    acquired = m108.acquire_attribution(m0, episodes, register_result=True)
    if not acquired.get("confirmed") or not isinstance(acquired.get("next_state"), Mapping):
        raise M108BridgeError("the committed M108 history no longer determines an attribution rule")
    if not acquired.get("attribution_domain_covered") or acquired.get("surviving_attribution_classes") != 1:
        raise M108BridgeError("the committed M108 history no longer determines one operative class")
    if acquired.get("rule_space_size") != 16 or not acquired.get("every_consistent_rule_is_non_monotone"):
        raise M108BridgeError("the M107-enabled M108 rule space no longer has the qualified shape")

    m1 = m108.decode_state(acquired["next_state"])
    demand_document = _demand_document()
    demand = m108.decode_demand(demand_document["demand"])
    target = m108.demand_target(demand)
    hardwired = m108.resolve(m0, demand)
    corrected = m108.resolve(m1, demand)
    if hardwired.get("confirmed") or hardwired.get("reason") != "operator_candidate_space_exhausted":
        raise M108BridgeError("M108 M0 no longer fails on its committed later demand as qualified")
    if not corrected.get("confirmed") or corrected.get("final_signal_width") != m108.WORLD_SIGNAL_WIDTH:
        raise M108BridgeError("the acquired M108 rule no longer resolves the committed later demand")
    if not (corrected.get("construction") or {}).get("executes_to_target"):
        raise M108BridgeError("the M108 resolution witness no longer executes to the committed target")
    if not m108.structural_exclusion_certificate(target, m108.BASE_SIGNAL_WIDTH).get("confirmed"):
        raise M108BridgeError("M108 later demand is no longer excluded by the narrow interface")
    if not m108.monotone_exclusion_certificate(m107.initial_operators(), target).get("confirmed"):
        raise M108BridgeError("M108 later demand is no longer excluded from the pre-M107 language")

    return {
        **acquired,
        "source_milestone": "M108",
        "source_episodes_digest": str(episodes_document.get("episodes_digest") or ""),
        "source_demand_fixture_digest": str(demand_document.get("demand_fixture_digest") or ""),
        "pre_m107_rule_space_size": int(blocked["rule_space_size"]),
        "m107_enabled_rule_space_size": int(acquired["rule_space_size"]),
        "hardwired_resolution_confirmed": bool(hardwired.get("confirmed")),
        "corrected_resolution_confirmed": bool(corrected.get("confirmed")),
        "development_replay_only": True,
    }


def evaluation_tasks() -> list[dict[str, Any]]:
    """Retain every M107 bridge task and add all rows of M108's committed later demand."""
    tasks = [dict(item) for item in m107_bridge.evaluation_tasks()]
    document = _demand_document()
    demand = m108.decode_demand(document["demand"])
    target = m108.demand_target(demand)
    for index, signals in enumerate(m108.world_rows()):
        tasks.append(
            {
                "task_id": "m108-bridge:B:%d" % index,
                "target": list(target),
                "signals": list(signals),
                "expected": bool(target[index]),
            }
        )
    return tasks


def acquired_body_factory(replay: Mapping[str, Any] | None = None) -> ConfiguredBody:
    result = dict(replay or replay_frozen_attribution())
    state = result.get("next_state")
    if not isinstance(state, Mapping):
        raise M108BridgeError("M108 replay carries no acquired attribution state")
    return ConfiguredBody(
        target=BODY_TARGET,
        configuration={"state": dict(state)},
        dependencies=frozenset({m107_bridge.ACQUISITION_NAME, ACQUISITION_NAME}),
    )


def propose_frozen_m108_attribution(
    context: LineageContext, tasks: Sequence[Mapping[str, Any]]
) -> Proposal | None:
    """Offer M108 only after Genesis' own lineage record says M107 was acquired."""
    del tasks  # Acquisition evidence is the committed M108 history, never current answer keys.
    if ACQUISITION_NAME in context.acquisitions:
        return None
    if m107_bridge.ACQUISITION_NAME not in context.acquisitions:
        return None

    replay = replay_frozen_attribution()
    return Proposal(
        name=ACQUISITION_NAME,
        body_factory=acquired_body_factory(replay),
        depends_on=m107_bridge.ACQUISITION_NAME,
        provenance=tr.provenance(
            "lineage_owned",
            produced_by="metamorphosis.m108_runtime.acquire_attribution",
            detail=(
                "DEVELOPMENT replay of M108's committed lineage-history episodes; creates no new "
                "M108 scientific observation"
            ),
        ),
        rationale={
            "development_only": True,
            "source_milestone": "M108",
            "source_episodes_digest": replay["source_episodes_digest"],
            "source_demand_fixture_digest": replay["source_demand_fixture_digest"],
            "pre_m107_rule_space_size": replay["pre_m107_rule_space_size"],
            "m107_enabled_rule_space_size": replay["m107_enabled_rule_space_size"],
            "surviving_attribution_classes": replay["surviving_attribution_classes"],
        },
    )
