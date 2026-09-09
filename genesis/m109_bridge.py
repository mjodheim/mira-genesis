"""Bridge M109's two machinery generations into the Genesis DEVELOPMENT runtime.

M109 is not treated as a direct third generation of the M107 -> M108 DEVELOPMENT lineage here.
It has its own frozen M0/M1/M2 machinery sequence and its own staged-information boundary. This
adapter therefore seeds a fresh Genesis lineage at M109 M0 and asks two questions:

1. can Genesis admit M109 generation one without reading stage two; and
2. can generation two then be shown, by Genesis' own runtime-derived ablation, to need generation one?

The workload is M109's exhaustive ``ReachImprove`` census, not the two authored curriculum demands.
Every one of the 256 world functions is evaluated. The frozen M109 result reports the strict sizes
6 < 20 < 243, so the second Genesis generation has 223 newly solved census rows. Under the repaired
causal metrology, removing generation one must lose those new rows rather than merely break retained
work.

This is DEVELOPMENT integration apparatus only. It does not edit, re-freeze, or reinterpret any
M109 scientific artifact.
"""
from __future__ import annotations

import functools
import itertools
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from genesis import trust_root as tr
from genesis.artifacts import ConfiguredBody
from genesis.loop import LineageContext, Proposal
from metamorphosis import m109_runtime as m109

ROOT = Path(__file__).resolve().parents[1]
STAGE1_PATH = ROOT / "experiments" / "M109" / "DEMAND_STAGE1.json"
STAGE2_PATH = ROOT / "experiments" / "M109" / "DEMAND_STAGE2.json"

BODY_TARGET = "genesis.m109_bridge:M109Body"
GENERATION_ONE = "m109_generation_one_rule"
GENERATION_TWO = "m109_generation_two_rule"
REFUSED = "__m109_bridge_refused__"
REACH_BUDGET = 2


class M109BridgeError(RuntimeError):
    """Raised when the frozen M109 sequence no longer adapts without changing its meaning."""


def _read_stage(path: Path, stage: int) -> dict[str, Any]:
    raw = path.read_bytes()
    try:
        document = json.loads(raw.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise M109BridgeError("M109 staged demand is not canonical ASCII JSON") from error
    if m109.canonical_json(document).encode("ascii") != raw:
        raise M109BridgeError("M109 staged demand is not canonical")
    if document.get("schema") != "m109-staged-demand-v1":
        raise M109BridgeError("M109 staged demand has an unexpected schema")
    if document.get("stage") != stage or document.get("revealed_after_stage") != stage - 1:
        raise M109BridgeError("M109 staged reveal chronology changed")
    payload = {key: value for key, value in document.items() if key != "stage_digest"}
    if document.get("stage_digest") != m109.digest(payload):
        raise M109BridgeError("M109 staged demand digest mismatch")
    m109.decode_demand(document.get("demand"))
    return document


@functools.lru_cache(maxsize=1)
def _domain() -> dict[str, Any]:
    domain = m109.attribution_domain()
    if not domain.get("census_complete") or domain.get("ambiguous_rows"):
        raise M109BridgeError("M109 attribution domain is no longer a complete unambiguous census")
    return domain


def replay_generation_one() -> dict[str, Any]:
    """Replay generation one while stage two remains unread and therefore unavailable.

    This function deliberately has no reference to ``STAGE2_PATH``. A regression test instruments
    file reads and fails if generation-one replay ever touches the second staged demand.
    """
    stage1 = _read_stage(STAGE1_PATH, 1)
    demand1 = m109.decode_demand(stage1["demand"])
    domain = _domain()
    m0 = m109.create_state()

    episode1 = m109.record_episode(m0, demand1)
    if not episode1.get("usable"):
        raise M109BridgeError("M109 stage-one lineage trial is no longer usable")
    if (episode1.get("trial") or {}).get("label_source") != "lineage_component_trial":
        raise M109BridgeError("M109 stage-one blame label is no longer lineage-determined")
    if episode1.get("component") != m109.COMPONENT_SIGNALS:
        raise M109BridgeError("M109 stage-one trial no longer selects the signal interface")

    acquired = m109.acquire_rule(m0, [episode1], domain, register_result=True)
    if not acquired.get("confirmed") or not isinstance(acquired.get("next_state"), Mapping):
        raise M109BridgeError("M109 generation one is no longer acquired")
    if acquired.get("selected_component") != m109.COMPONENT_SIGNALS:
        raise M109BridgeError("M109 generation one no longer targets the signal interface")
    if acquired.get("surviving_rule_classes") != 1:
        raise M109BridgeError("M109 generation one is no longer uniquely determined")

    m1 = m109.decode_state(acquired["next_state"])
    resolved = m109.resolve(m1, demand1)
    if not resolved.get("confirmed"):
        raise M109BridgeError("M109 generation one no longer resolves stage one")
    if resolved.get("final_signal_width") != m109.WORLD_SIGNAL_WIDTH:
        raise M109BridgeError("M109 stage-one resolution no longer reaches world signal width")
    if not (resolved.get("construction") or {}).get("executes_to_target"):
        raise M109BridgeError("M109 stage-one witness no longer executes to its target")

    # This transient post-resolution state is the state from which M109 scientifically derives
    # generation two. It is intentionally not the M1 snapshot used by the frozen ReachImprove
    # M0/M1/M2 census.
    m1_after = m109.create_state(
        m1["operators"],
        signal_width=resolved["final_signal_width"],
        candidate_space=resolved["final_candidate_space"],
        rules=m1["rules"],
    )

    reach0 = m109.reach_improve(m0, REACH_BUDGET)
    reach1 = m109.reach_improve(m1, REACH_BUDGET)
    if reach0.get("size") != 6 or reach1.get("size") != 20:
        raise M109BridgeError("M109 generation-one ReachImprove sizes changed")
    if not set(reach0["tables"]) < set(reach1["tables"]):
        raise M109BridgeError("M109 generation one no longer strictly enlarges ReachImprove")

    return {
        **acquired,
        "source_milestone": "M109",
        "stage_one_digest": stage1["stage_digest"],
        "m0_state": m0,
        "m1_state": m1,
        "m1_after_state": m1_after,
        "episode1": episode1,
        "stage_one_resolution": resolved,
        "reach_m0": reach0,
        "reach_m1": reach1,
        "development_replay_only": True,
    }


def replay_generation_two(first_replay: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Reveal stage two only after the stage-one replay has established its resolution."""
    first = dict(first_replay or replay_generation_one())
    resolution1 = first.get("stage_one_resolution")
    if not isinstance(resolution1, Mapping) or not resolution1.get("confirmed"):
        raise M109BridgeError("stage two cannot be revealed before stage one is resolved")

    # The second file is first touched only after the preceding check.
    stage2 = _read_stage(STAGE2_PATH, 2)
    demand2 = m109.decode_demand(stage2["demand"])

    m0 = m109.decode_state(first["m0_state"])
    m1 = m109.decode_state(first["m1_state"])
    m1_after = m109.decode_state(first["m1_after_state"])
    episode1 = dict(first["episode1"])
    domain = _domain()

    unresolved = m109.resolve(m1_after, demand2)
    if unresolved.get("confirmed"):
        raise M109BridgeError("M109 stage two is no longer blocked before generation two")

    episode2 = m109.record_episode(m1_after, demand2)
    if not episode2.get("usable"):
        raise M109BridgeError("M109 stage-two lineage trial is no longer usable")
    if (episode2.get("trial") or {}).get("label_source") != "lineage_component_trial":
        raise M109BridgeError("M109 stage-two blame label is no longer lineage-determined")
    if episode2.get("component") != m109.COMPONENT_CANDIDATES:
        raise M109BridgeError("M109 stage-two trial no longer selects the candidate space")

    acquired = m109.acquire_rule(
        m1_after, [episode1, episode2], domain, register_result=True
    )
    if not acquired.get("confirmed") or not isinstance(acquired.get("next_state"), Mapping):
        raise M109BridgeError("M109 generation two is no longer acquired")
    if acquired.get("selected_component") != m109.COMPONENT_CANDIDATES:
        raise M109BridgeError("M109 generation two no longer targets the candidate space")
    if acquired.get("surviving_rule_classes") != 1:
        raise M109BridgeError("M109 generation two is no longer uniquely determined")

    m2 = m109.decode_state(acquired["next_state"])
    resolved = m109.resolve(m2, demand2)
    if not resolved.get("confirmed"):
        raise M109BridgeError("M109 generation two no longer resolves stage two")
    if resolved.get("final_candidate_space") != m109.COMPLETE_SPACE:
        raise M109BridgeError("M109 stage-two resolution no longer widens the candidate space")
    if not (resolved.get("construction") or {}).get("executes_to_target"):
        raise M109BridgeError("M109 stage-two witness no longer executes to its target")

    handed = m109.acquire_rule(m0, [episode2], domain, register_result=False)
    if handed.get("confirmed") or handed.get("reason") != (
        "no_expressible_rule_reproduces_the_trial_record"
    ):
        raise M109BridgeError("M109 generation two is no longer inexpressible before generation one")

    reach1 = m109.reach_improve(m1, REACH_BUDGET)
    reach2 = m109.reach_improve(m2, REACH_BUDGET)
    if reach1.get("size") != 20 or reach2.get("size") != 243:
        raise M109BridgeError("M109 generation-two ReachImprove sizes changed")
    if not set(reach1["tables"]) < set(reach2["tables"]):
        raise M109BridgeError("M109 generation two no longer strictly enlarges ReachImprove")

    return {
        **acquired,
        "source_milestone": "M109",
        "stage_one_digest": first["stage_one_digest"],
        "stage_two_digest": stage2["stage_digest"],
        "m0_state": m0,
        "m1_state": m1,
        "m1_after_state": m1_after,
        "m2_state": m2,
        "episode1": episode1,
        "episode2": episode2,
        "stage_one_resolution": dict(resolution1),
        "stage_two_before_generation_two": unresolved,
        "stage_two_resolution": resolved,
        "handed_counterfactual": handed,
        "reach_m1": reach1,
        "reach_m2": reach2,
        "generation_two_inexpressible_before_generation_one": True,
        "development_replay_only": True,
    }


@functools.lru_cache(maxsize=64)
def _reach_tables(state_json: str) -> frozenset[str]:
    state = m109.decode_state(json.loads(state_json))
    census = m109.reach_improve(state, REACH_BUDGET)
    return frozenset(str(table) for table in census["tables"])


class M109Body:
    """A reconstructible body whose task outcome is membership in a frozen-machinery reach census."""

    def __init__(
        self,
        *,
        generation: int,
        m0_state: Mapping[str, Any],
        parent_state: Mapping[str, Any],
        active_state: Mapping[str, Any],
        capabilities: Sequence[str] = (),
    ) -> None:
        level = int(generation)
        if level not in (0, 1, 2):
            raise M109BridgeError("M109 bridge generation is outside the DEVELOPMENT sequence")

        m0 = m109.decode_state(dict(m0_state))
        parent = m109.decode_state(dict(parent_state))
        active = m109.decode_state(dict(active_state))
        held = frozenset(str(name) for name in capabilities)
        allowed = {GENERATION_ONE, GENERATION_TWO}
        unexpected = held - allowed
        if unexpected:
            raise M109BridgeError(
                "M109 bridge received unknown capabilities: %s"
                % ", ".join(sorted(unexpected))
            )
        if m0["rules"]:
            raise M109BridgeError("M109 M0 snapshot unexpectedly carries an acquired rule")

        if level == 0:
            if held:
                raise M109BridgeError("M109 seed body cannot carry generation markers")
            selected = m0
        elif level == 1:
            if GENERATION_TWO in held:
                raise M109BridgeError("M109 generation-one body cannot carry generation two")
            if len(active["rules"]) != 1:
                raise M109BridgeError("M109 generation-one active snapshot must carry one rule")
            selected = active if GENERATION_ONE in held else m0
        else:
            if len(parent["rules"]) != 1 or len(active["rules"]) != 2:
                raise M109BridgeError(
                    "M109 generation-two snapshots do not carry the expected one/two rules"
                )
            if GENERATION_ONE not in held:
                # Keep the generation-two marker and the admitted artifact configuration fixed. If
                # its predecessor is absent, the later generation has no lineage state on which it
                # can act and collapses to M0.
                selected = m0
            elif GENERATION_TWO in held:
                selected = active
            else:
                selected = parent

        self.generation = level
        self.capabilities = held
        self.state = selected
        self._tables = _reach_tables(m109.canonical_json(selected))

    def attempt(self, task: Mapping[str, Any]) -> Any:
        table = task.get("table")
        expected_width = 2 ** m109.WORLD_SIGNAL_WIDTH
        if (
            not isinstance(table, str)
            or len(table) != expected_width
            or any(bit not in "01" for bit in table)
        ):
            raise M109BridgeError("task is not one M109 world-function census row")
        return True if table in self._tables else REFUSED


def grade(task: Mapping[str, Any], answer: Any) -> str:
    """Parent-side grading: reachable is solved; unreachable is an explicit refusal."""
    del task
    if answer == REFUSED:
        return "refused"
    return "solved" if answer is True else "unsolved"


@functools.lru_cache(maxsize=1)
def _evaluation_rows() -> tuple[tuple[str, bool], ...]:
    width = 2 ** m109.WORLD_SIGNAL_WIDTH
    return tuple(
        ("".join("1" if bit else "0" for bit in row), True)
        for row in itertools.product((False, True), repeat=width)
    )


def evaluation_tasks() -> list[dict[str, Any]]:
    """Every world function exactly once: a complete 256-row ReachImprove census."""
    tasks = []
    for index, (table, expected) in enumerate(_evaluation_rows()):
        tasks.append(
            {
                "task_id": "m109-reach:%03d:%s" % (index, table),
                "table": table,
                "expected": expected,
            }
        )
    return tasks


def seed_body_factory() -> ConfiguredBody:
    m0 = m109.create_state()
    return ConfiguredBody(
        target=BODY_TARGET,
        configuration={
            "generation": 0,
            "m0_state": m0,
            "parent_state": m0,
            "active_state": m0,
        },
        dependencies=frozenset(),
    )


def generation_one_body_factory(
    replay: Mapping[str, Any] | None = None,
) -> ConfiguredBody:
    first = dict(replay or replay_generation_one())
    return ConfiguredBody(
        target=BODY_TARGET,
        configuration={
            "generation": 1,
            "m0_state": first["m0_state"],
            "parent_state": first["m0_state"],
            "active_state": first["m1_state"],
        },
        dependencies=frozenset({GENERATION_ONE}),
    )


def generation_two_body_factory(
    replay: Mapping[str, Any] | None = None,
) -> ConfiguredBody:
    second = dict(replay or replay_generation_two())
    return ConfiguredBody(
        target=BODY_TARGET,
        configuration={
            "generation": 2,
            "m0_state": second["m0_state"],
            # ReachImprove's frozen strict chain is M0 < M1 < M2. The transient m1_after state is
            # preserved in the replay and is used to *derive* generation two, but the DEVELOPMENT
            # census compares the same M1 snapshot the scientific result reports.
            "parent_state": second["m1_state"],
            "active_state": second["m2_state"],
        },
        dependencies=frozenset({GENERATION_ONE, GENERATION_TWO}),
    )


def propose_generation_one(
    context: LineageContext, tasks: Sequence[Mapping[str, Any]]
) -> Proposal | None:
    """Offer M109 generation one from stage-one lineage evidence, never current answer keys."""
    del tasks
    if GENERATION_ONE in context.acquisitions:
        return None
    first = replay_generation_one()
    return Proposal(
        name=GENERATION_ONE,
        body_factory=generation_one_body_factory(first),
        depends_on="",
        provenance=tr.provenance(
            "lineage_owned",
            produced_by="metamorphosis.m109_runtime.acquire_rule",
            detail=(
                "DEVELOPMENT replay of M109 generation one from the lineage-controlled stage-one "
                "trial; stage two is not read"
            ),
        ),
        rationale={
            "development_only": True,
            "source_milestone": "M109",
            "stage_one_digest": first["stage_one_digest"],
            "selected_component": first["selected_component"],
            "surviving_rule_classes": first["surviving_rule_classes"],
            "reach_before": first["reach_m0"]["size"],
            "reach_after": first["reach_m1"]["size"],
            "stage_two_not_part_of_generation_one_replay": True,
        },
    )


def propose_generation_two(
    context: LineageContext, tasks: Sequence[Mapping[str, Any]]
) -> Proposal | None:
    """Offer generation two only after Genesis' lineage record contains generation one."""
    del tasks
    if GENERATION_ONE not in context.acquisitions or GENERATION_TWO in context.acquisitions:
        return None
    first = replay_generation_one()
    second = replay_generation_two(first)
    return Proposal(
        name=GENERATION_TWO,
        body_factory=generation_two_body_factory(second),
        depends_on=GENERATION_ONE,
        provenance=tr.provenance(
            "lineage_owned",
            produced_by="metamorphosis.m109_runtime.acquire_rule",
            detail=(
                "DEVELOPMENT replay of M109 generation two after stage one resolved and stage two "
                "was revealed; creates no new M109 scientific observation"
            ),
        ),
        rationale={
            "development_only": True,
            "source_milestone": "M109",
            "stage_one_digest": second["stage_one_digest"],
            "stage_two_digest": second["stage_two_digest"],
            "selected_component": second["selected_component"],
            "surviving_rule_classes": second["surviving_rule_classes"],
            "generation_two_inexpressible_before_generation_one": second[
                "generation_two_inexpressible_before_generation_one"
            ],
            "reach_before": second["reach_m1"]["size"],
            "reach_after": second["reach_m2"]["size"],
        },
    )
