"""Bridge the frozen M107 interpreter-extension mechanism into the Genesis runtime.

This module is DEVELOPMENT apparatus. It does not modify M107, create a new M107 observation, or
advance a scientific/generalisation gate. It replays the already-committed M107 acquisition and
packages the resulting state as a reconstructible ``ConfiguredBody`` so Genesis can judge a real
lineage-owned interpreter extension with its ordinary trust root, sandbox and persistence machinery.

The important separation is deliberate:

* ``metamorphosis.m107_runtime`` remains the authority for M107 state, reach and acquisition;
* this bridge contributes only adaptation into Genesis' body/task interface;
* the evaluation task answers are withheld from the body and graded in the parent process;
* removing ``M107_OPERATOR_EXTENSION`` from the configured body's dependencies restores M107 S0
  behaviour without changing any other artifact configuration.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from genesis import trust_root as tr
from genesis.artifacts import ConfiguredBody
from genesis.loop import LineageContext, Proposal
from metamorphosis import m107_runtime as m107

ROOT = Path(__file__).resolve().parents[1]
FROZEN_DEMANDS_PATH = ROOT / "experiments" / "M107" / "DEMANDS.json"

BODY_TARGET = "genesis.m107_bridge:M107Body"
ACQUISITION_NAME = "m107_operator_extension"
REFUSED = "__m107_bridge_refused__"

SEED_TARGET = (False, False, False, True)
DEVELOPMENT_TARGETS = (
    (True, False, False, True),
    (True, False, True, False),
)


class M107BridgeError(RuntimeError):
    """Raised when the frozen M107 record cannot be adapted without changing its meaning."""


class M107Body:
    """Execute tasks through an M107 state carried as configured artifact data.

    ``state`` is always decoded even when the acquisition capability is absent, so malformed
    candidate configuration cannot hide behind an ablation. The only behavioural switch is the
    dependency set: with ``M107_OPERATOR_EXTENSION`` the configured acquired state is active;
    without it the body falls back to byte-reproducible M107 S0.
    """

    def __init__(self, *, state: Mapping[str, Any], capabilities: Sequence[str] = ()) -> None:
        configured = m107.decode_state(dict(state))
        held = frozenset(str(name) for name in capabilities)
        unexpected = held - {ACQUISITION_NAME}
        if unexpected:
            raise M107BridgeError(
                "M107 bridge received unknown capabilities: %s" % ", ".join(sorted(unexpected))
            )

        seed = m107.create_state()
        if ACQUISITION_NAME in held:
            if len(configured["operators"]) <= len(seed["operators"]):
                raise M107BridgeError(
                    "M107 acquisition capability is present but the configured state adds no operator"
                )
            active = configured
        else:
            active = seed

        self.state = active
        self.capabilities = held

    def attempt(self, task: Mapping[str, Any]) -> Any:
        target = tuple(bool(value) for value in (task.get("target") or []))
        signals = tuple(bool(value) for value in (task.get("signals") or []))
        if len(target) != len(m107.SIGNAL_ROWS):
            raise M107BridgeError("M107 bridge task target has the wrong truth-table width")
        if len(signals) != m107.SIGNAL_COUNT:
            raise M107BridgeError("M107 bridge task signal vector has the wrong width")

        construction = m107.construct(self.state, target)
        if not construction["constructible"]:
            return REFUSED
        expression = construction["expression"]
        return m107.execute_expression(
            m107.operator_map(self.state["operators"]),
            expression,
            signals,
        )


def grade(task: Mapping[str, Any], answer: Any) -> str:
    """Parent-side grader; the body's sandbox never receives ``expected``."""
    if answer == REFUSED:
        return "refused"
    if not isinstance(answer, bool):
        return "unsolved"
    return "solved" if answer is bool(task["expected"]) else "unsolved"


def evaluation_tasks() -> list[dict[str, Any]]:
    """A small complete-row task family that measures retained S0 reach plus new M107 reach."""
    tasks: list[dict[str, Any]] = []
    targets = (("seed", SEED_TARGET),) + tuple(
        ("acquired_%d" % index, target)
        for index, target in enumerate(DEVELOPMENT_TARGETS, start=1)
    )
    for label, target in targets:
        for row_index, signals in enumerate(m107.SIGNAL_ROWS):
            tasks.append(
                {
                    "task_id": "m107-bridge:%s:%d" % (label, row_index),
                    "target": list(target),
                    "signals": list(signals),
                    "expected": bool(target[row_index]),
                }
            )
    return tasks


def replay_frozen_acquisition() -> dict[str, Any]:
    """Replay the committed M107 joint demand through M107's unchanged acquisition function."""
    document = json.loads(FROZEN_DEMANDS_PATH.read_text(encoding="ascii"))
    if document.get("schema") != "m107-demands-v1" or document.get("milestone") != "M107":
        raise M107BridgeError("committed M107 demand record has an unexpected identity")

    joint = document.get("joint") or {}
    first = m107.decode_operator_demand(joint.get("first"))
    second = m107.decode_operator_demand(joint.get("second"))
    seed = m107.create_state()

    for target in document.get("targets") or []:
        certificate = m107.insufficiency_certificate(seed["operators"], tuple(bool(v) for v in target))
        if not certificate["confirmed"]:
            raise M107BridgeError("a committed M107 target is no longer excluded from S0 by its lemma")

    report = m107.acquire_operator(seed, [first, second], register_result=True)
    if not report.get("confirmed") or not isinstance(report.get("next_state"), Mapping):
        raise M107BridgeError("the committed M107 joint demand no longer reproduces its acquisition")
    if report.get("base_image_size") != 4 or report.get("extended_image_size") != 16:
        raise M107BridgeError("the replayed M107 reach changed from the qualified 4 -> 16 shape")

    next_state = m107.decode_state(report["next_state"])
    for target in document.get("targets") or []:
        if not m107.construct(next_state, target)["constructible"]:
            raise M107BridgeError("the replayed M107 extension no longer constructs a committed target")

    return {
        **report,
        "source_milestone": "M107",
        "source_demands_digest": str(document.get("demands_digest") or ""),
        "source_authorship": str(document.get("authorship") or ""),
        "development_replay_only": True,
    }


def seed_body_factory() -> ConfiguredBody:
    """Genesis body factory for M107 S0."""
    return ConfiguredBody(
        target=BODY_TARGET,
        configuration={"state": m107.create_state()},
        dependencies=frozenset(),
    )


def acquired_body_factory(replay: Mapping[str, Any] | None = None) -> ConfiguredBody:
    """Genesis body factory for the M107 state produced by the frozen joint demand."""
    result = dict(replay or replay_frozen_acquisition())
    state = result.get("next_state")
    if not isinstance(state, Mapping):
        raise M107BridgeError("M107 replay carries no acquired state")
    return ConfiguredBody(
        target=BODY_TARGET,
        configuration={"state": dict(state)},
        dependencies=frozenset({ACQUISITION_NAME}),
    )


def propose_frozen_m107_extension(
    context: LineageContext, tasks: Sequence[Mapping[str, Any]]
) -> Proposal | None:
    """Offer the frozen M107 acquisition once, without consulting evaluation answer keys."""
    del tasks  # The proposal is bound to the committed M107 demand record, not these test answers.
    if ACQUISITION_NAME in context.acquisitions:
        return None

    replay = replay_frozen_acquisition()
    return Proposal(
        name=ACQUISITION_NAME,
        body_factory=acquired_body_factory(replay),
        provenance=tr.provenance(
            "lineage_owned",
            produced_by="metamorphosis.m107_runtime.acquire_operator",
            detail=(
                "DEVELOPMENT replay of the committed project-controlled M107 joint demand; "
                "this bridge creates no new M107 scientific observation"
            ),
        ),
        rationale={
            "development_only": True,
            "source_milestone": "M107",
            "source_demands_digest": replay["source_demands_digest"],
            "base_image_size": replay["base_image_size"],
            "extended_image_size": replay["extended_image_size"],
            "operator_space_exhausted": bool(replay["operator_space_exhausted"]),
        },
    )
